from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

app = FastAPI(
    title="لوحة تحليل السوق السعودي الشاملة",
    description="تحليل متقدم مع أسماء الشركات، أحجام التداول، والقطاعات",
    version="15.0"
)

# قاموس مفصل يضم رموز شركات تاسي وأسماءها العربية الرسمية موزعاً حسب القطاعات
SECTORS_DATA = {
    "البنوك والخدمات المالية": {
        "name_ar": "البنوك والخدمات المالية",
        "stocks": {
            "1010": "بنك الرياض",
            "1020": "البنك السعودي الجزيرة",
            "1060": "البنك السعودي للاستثمار",
            "1080": "بنك الخليج الدولي",
            "1111": "مجموعة تداول السعودية",
            "1120": "مصرف الراجحي",
            "1150": "مصرف الإنماء",
            "1180": "البنك الأهلي السعودي",
            "1212": "البلد للاستثمار"
        }
    },
    "المواد الأساسية": {
        "name_ar": "المواد الأساسية",
        "stocks": {
            "2010": "الشركة السعودية للصناعات الأساسية (سابك)",
            "2020": "سافكو / سابك للمغذيات الزراعية",
            "2060": "التصنيع الوطنية",
            "2080": "الصحراء العالمية للبتروكيماويات (سبكيم)",
            "2090": "الوطنية للبناء والتسويق",
            "2100": "مجموعة أسيج",
            "2110": "الجبيل للصناعات الكيماوية",
            "2120": "بترورابغ",
            "2130": "المتقدمة للبتروكيماويات",
            "2150": "الكيماويات المتخصصة"
        }
    },
    "الطاقة والمرافق": {
        "name_ar": "الطاقة والمرافق",
        "stocks": {
            "2222": "أرامكو السعودية",
            "1301": "أكوا باور",
            "1302": "الكهرباء السعودية",
            "1303": "حفر الباطن للطاقة",
            "1304": "الباحة للطاقة",
            "5110": "الشركة السعودية لخدمات السيارات (ساسكو)"
        }
    },
    "الاتصالات وتقنية المعلومات": {
        "name_ar": "الاتصالات وتقنية المعلومات",
        "stocks": {
            "7010": "شركة الاتصالات السعودية (إس تي سي)",
            "7020": "الاتصالات المتنقلة السعودية (زين)",
            "7030": "عذيب للاتصالات",
            "7040": "المتكاملة للاتصالات"
        }
    },
    "الصناديق العقارية (REITs)": {
        "name_ar": "الصناديق العقارية المتداولة",
        "stocks": {
            "4321": "جدوى ريت الحرمين",
            "4331": "تعليم ريت",
            "4332": "الرياض ريت",
            "4333": "الجزيرة ريت",
            "4334": "الملكة ريت",
            "4335": "التهامة ريت",
            "4336": "بيلتون ريت",
            "4337": "الإنماء ريت التجزئة",
            "4338": "مشاركة ريت",
            "4339": "الخبير ريت"
        }
    }
}

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def fetch_market_data():
    scanned_stocks = []
    
    for sector_name, sector_info in SECTORS_DATA.items():
        for symbol, stock_name in sector_info["stocks"].items():
            ticker_symbol = f"{symbol}.SR"
            try:
                stock = yf.Ticker(ticker_symbol)
                hist = stock.history(period="30d")
                
                if hist.empty or len(hist) < 15:
                    continue
                
                hist['RSI'] = calculate_rsi(hist['Close'], period=14)
                current_price = float(hist['Close'].iloc[-1])
                prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                change_percent = round(((current_price - prev_close) / prev_close) * 100, 2)
                volume = int(hist['Volume'].iloc[-1]) # كمية التداول اليومية
                
                latest_rsi_val = hist['RSI'].iloc[-1]
                latest_rsi = round(float(latest_rsi_val), 2) if not pd.isna(latest_rsi_val) else 50.0

                # محاكاة تحليل ضغط الطلبات والسيولة بناءً على الحجم وحركة السعر
                if volume > 500000 and change_percent > 0:
                    order_status = "🟢 طلبات شراء قوية (ضغط شراء عالٍ)"
                elif volume > 500000 and change_percent < 0:
                    order_status = "🔴 ضغط بيع وعروض مرتفعة"
                else:
                    order_status = "🟡 سيولة متوازنة (طلب وعرض هادئ)"

                if latest_rsi <= 35:
                    buy_zone = f"بين {round(current_price * 0.98, 2)} و {round(current_price, 2)}"
                    target_price = round(current_price * 1.05, 2)
                    stop_loss = round(current_price * 0.96, 2)
                    recommendation = "فرصة شراء (ارتداد قاع)"
                    badge_class = "buy"
                elif change_percent > 0.8 and latest_rsi < 68:
                    buy_zone = f"السعر الحالي {round(current_price, 2)}"
                    target_price = round(current_price * 1.04, 2)
                    stop_loss = round(current_price * 0.97, 2)
                    recommendation = "إيجابي (اتجاه صاعد)"
                    badge_class = "buy"
                elif latest_rsi >= 70 or change_percent < -1.5:
                    buy_zone = "لا يوجد (تشبع شراء)"
                    target_price = 0.0
                    stop_loss = round(current_price * 0.95, 2)
                    recommendation = "مخاطرة / جني أرباح"
                    badge_class = "risky"
                else:
                    buy_zone = f"قرب الدعم {round(current_price * 0.97, 2)}"
                    target_price = round(current_price * 1.03, 2)
                    stop_loss = round(current_price * 0.97, 2)
                    recommendation = "محايد (احتفاظ)"
                    badge_class = "neutral"

                scanned_stocks.append({
                    "symbol": symbol,
                    "name": stock_name,
                    "sector": sector_name,
                    "current_price": round(current_price, 2),
                    "change_percent": change_percent,
                    "volume": f"{volume:,}",
                    "order_status": order_status,
                    "rsi": latest_rsi,
                    "buy_zone": buy_zone,
                    "target": target_price if target_price > 0 else "غير متاح",
                    "stop_loss": stop_loss,
                    "recommendation": recommendation,
                    "badge_class": badge_class
                })
            except Exception:
                continue
    return scanned_stocks

@app.get("/", response_class=HTMLResponse)
def dashboard():
    stocks = fetch_market_data()
    
    rows_html = ""
    for s in stocks:
        rows_html += f"""
        <tr data-symbol="{s['symbol']}" data-name="{s['name']}" data-sector="{s['sector']}" data-rec="{s['recommendation']}">
            <td><b>{s['symbol']}</b></td>
            <td style="font-weight: bold; color: #0f5132;">{s['name']}</td>
            <td><span class="sector-tag">{s['sector']}</span></td>
            <td>{s['current_price']} ر.س</td>
            <td style="color: {'#198754' if s['change_percent'] >= 0 else '#dc3545'}; font-weight: bold;">{s['change_percent']}%</td>
            <td><b>{s['volume']}</b> سهم</td>
            <td style="font-size: 13px;">{s['order_status']}</td>
            <td>{s['rsi']}</td>
            <td>{s['buy_zone']}</td>
            <td>{s['target']}</td>
            <td>{s['stop_loss']}</td>
            <td><span class="badge {s['badge_class']}">{s['recommendation']}</span></td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>لوحة التحليل الشامل لأسهم تاسي</title>
        <style>
            body {{
                font-family: 'Cairo', 'Tajawal', Tahoma, sans-serif;
                background-color: #f0f2f5;
                margin: 0;
                padding: 20px;
                color: #333;
                direction: rtl;
                text-align: right;
            }}
            .container {{
                max-width: 1550px;
                margin: auto;
                background: #ffffff;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            }}
            h1 {{
                text-align: center;
                color: #0f5132;
                margin-bottom: 5px;
                font-size: 26px;
            }}
            p.sub {{
                text-align: center;
                color: #6c757d;
                margin-bottom: 25px;
                font-size: 15px;
            }}
            .controls {{
                display: flex;
                gap: 15px;
                margin-bottom: 25px;
                flex-wrap: wrap;
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
            }}
            .controls input, .controls select {{
                padding: 10px 15px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
                flex: 1;
                min-width: 220px;
                font-family: inherit;
            }}
            .table-container {{
                overflow-x: auto;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                font-size: 13px;
            }}
            th, td {{
                padding: 12px 14px;
                border-bottom: 1px solid #e9ecef;
                text-align: right;
                white-space: nowrap;
            }}
            th {{
                background-color: #0f5132;
                color: white;
                font-weight: 600;
            }}
            tr:hover {{
                background-color: #f8f9fa;
            }}
            .sector-tag {{
                background: #e2e3e5;
                color: #383d41;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }}
            .badge {{
                padding: 5px 10px;
                border-radius: 20px;
                font-size: 11px;
                font-weight: bold;
                display: inline-block;
                text-align: center;
            }}
            .buy {{ background-color: #d1e7dd; color: #0f5132; }}
            .risky {{ background-color: #f8d7da; color: #842029; }}
            .neutral {{ background-color: #fff3cd; color: #664d03; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 لوحة التحليل الشامل للسوق السعودي (تاسي)</h1>
            <p class="sub">أسماء الشركات، أحجام التداول، تقييم قوى الطلب والعرض، ومؤشر RSI الفوري</p>
            
            <div class="controls">
                <input type="text" id="searchInput" placeholder="🔍 ابحث باسم الشركة أو الرمز (مثل: الراجحي أو 1120)..." onkeyup="filterTable()">
                
                <select id="sectorSelect" onchange="filterTable()">
                    <option value="">🏢 كل القطاعات</option>
                    <option value="البنوك والخدمات المالية">البنوك والخدمات المالية</option>
                    <option value="المواد الأساسية">المواد الأساسية</option>
                    <option value="الطاقة والمرافق">الطاقة والمرافق</option>
                    <option value="الاتصالات وتقنية المعلومات">الاتصالات وتقنية المعلومات</option>
                    <option value="الصناديق العقارية (REITs)">الصناديق العقارية (REITs)</option>
                </select>

                <select id="filterSelect" onchange="filterTable()">
                    <option value="">🎯 كل التوصيات والحالات</option>
                    <option value="فرصة شراء">فرصة شراء (ارتداد قاع)</option>
                    <option value="إيجابي">إيجابي (اتجاه صاعد)</option>
                    <option value="محايد">محايد (احتفاظ)</option>
                    <option value="مخاطرة">مخاطرة / جني أرباح</option>
                </select>
            </div>

            <div class="table-container">
                <table id="stocksTable">
                    <thead>
                        <tr>
                            <th>الرمز</th>
                            <th>اسم الشركة</th>
                            <th>القطاع</th>
                            <th>السعر</th>
                            <th>التغير %</th>
                            <th>كمية التداول (الحجم)</th>
                            <th>حالة الطلب والعرض</th>
                            <th>RSI</th>
                            <th>منطقة الشراء</th>
                            <th>الهدف</th>
                            <th>وقف الخسارة</th>
                            <th>التوصية الفنية</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            function filterTable() {{
                let input = document.getElementById("searchInput").value.toLowerCase();
                let sectorFilter = document.getElementById("sectorSelect").value;
                let recFilter = document.getElementById("filterSelect").value;
                
                let table = document.getElementById("stocksTable");
                let tr = table.getElementsByTagName("tr");

                for (let i = 1; i < tr.length; i++) {{
                    let symbol = tr[i].getAttribute("data-symbol").toLowerCase();
                    let name = tr[i].getAttribute("data-name").toLowerCase();
                    let sector = tr[i].getAttribute("data-sector");
                    let rec = tr[i].getAttribute("data-rec");
                    
                    let matchSearch = symbol.includes(input) || name.includes(input);
                    let matchSector = (sectorFilter === "" || sector === sectorFilter);
                    let matchRec = (recFilter === "" || rec.includes(recFilter));

                    if (matchSearch && matchSector && matchRec) {{
                        tr[i].style.display = "";
                    }} else {{
                        tr[i].style.display = "none";
                    }}
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)