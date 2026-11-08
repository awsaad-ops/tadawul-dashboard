from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

app = FastAPI(
    title="لوحة تحليل السوق السعودي المدمجة",
    description="تحليل متقدم وشامل لأسهم تاسي مع إجمالي الأسهم وأحجام التداول",
    version="16.0"
)

# قاموس مفصل يضم رموز شركات تاسي وأسماءها العربية الرسمية
SECTORS_DATA = {
    "البنوك والخدمات المالية": {
        "name_ar": "البنوك",
        "stocks": {
            "1010": "بنك الرياض",
            "1020": "الجزيرة",
            "1060": "الاستثمار",
            "1080": "الخليج الدولي",
            "1111": "تداول السعودية",
            "1120": "مصرف الراجحي",
            "1150": "مصرف الإنماء",
            "1180": "البنك الأهلي",
            "1212": "البلد للاستثمار"
        }
    },
    "المواد الأساسية": {
        "name_ar": "المواد الأساسية",
        "stocks": {
            "2010": "سابك",
            "2020": "سابك للمغذيات",
            "2060": "التصنيع الوطنية",
            "2080": "سبكيم",
            "2090": "الوطنية للتسويق",
            "2100": "مجموعة أسيج",
            "2110": "الجبيل الكيماوية",
            "2120": "بترورابغ",
            "2130": "المتقدمة",
            "2150": "الكيماويات المتخصصة"
        }
    },
    "الطاقة والمرافق": {
        "name_ar": "الطاقة",
        "stocks": {
            "2222": "أرامكو السعودية",
            "1301": "أكوا باور",
            "1302": "الكهرباء السعودية",
            "1303": "حفر الباطن للطاقة",
            "1304": "الباحة للطاقة",
            "5110": "ساسكو"
        }
    },
    "الاتصالات وتقنية المعلومات": {
        "name_ar": "الاتصالات",
        "stocks": {
            "7010": "إس تي سي (stc)",
            "7020": "زين السعودية",
            "7030": "عذيب للاتصالات",
            "7040": "المتكاملة للاتصالات"
        }
    },
    "الصناديق العقارية (REITs)": {
        "name_ar": "صناديق ريت",
        "stocks": {
            "4321": "جدوى ريت الحرمين",
            "4331": "تعليم ريت",
            "4332": "الرياض ريت",
            "4333": "الجزيرة ريت",
            "4334": "الملكة ريت",
            "4335": "التهامة ريت",
            "4336": "بيلتون ريت",
            "4337": "الإنماء ريت",
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

def format_large_number(num):
    if num >= 1_000_000_000:
        return f"{round(num / 1_000_000_000, 2)} مليار"
    elif num >= 1_000_000:
        return f"{round(num / 1_000_000, 2)} مليون"
    else:
        return f"{num:,}"

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
                
                # إجمالي عدد الأسهم المصدرة للشركة
                info = stock.info
                total_shares_raw = info.get('sharesOutstanding', 0)
                total_shares = format_large_number(total_shares_raw) if total_shares_raw else "غير متوفر"
                
                hist['RSI'] = calculate_rsi(hist['Close'], period=14)
                current_price = float(hist['Close'].iloc[-1])
                prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                change_percent = round(((current_price - prev_close) / prev_close) * 100, 2)
                volume = int(hist['Volume'].iloc[-1])
                
                latest_rsi_val = hist['RSI'].iloc[-1]
                latest_rsi = round(float(latest_rsi_val), 2) if not pd.isna(latest_rsi_val) else 50.0

                if volume > 500000 and change_percent > 0:
                    order_status = "🟢 شراء قوي"
                elif volume > 500000 and change_percent < 0:
                    order_status = "🔴 ضغط بيع"
                else:
                    order_status = "🟡 سيولة هادئة"

                if latest_rsi <= 35:
                    recommendation = "فرصة شراء (قاع)"
                    badge_class = "buy"
                elif change_percent > 0.8 and latest_rsi < 68:
                    recommendation = "إيجابي (صاعد)"
                    badge_class = "buy"
                elif latest_rsi >= 70 or change_percent < -1.5:
                    recommendation = "مخاطرة / جني أرباح"
                    badge_class = "risky"
                else:
                    recommendation = "محايد (احتفاظ)"
                    badge_class = "neutral"

                scanned_stocks.append({
                    "symbol": symbol,
                    "name": stock_name,
                    "sector": sector_info["name_ar"],
                    "current_price": round(current_price, 2),
                    "change_percent": change_percent,
                    "total_shares": total_shares,
                    "volume": f"{volume:,}",
                    "order_status": order_status,
                    "rsi": latest_rsi,
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
            <td>{s['current_price']}</td>
            <td style="color: {'#198754' if s['change_percent'] >= 0 else '#dc3545'}; font-weight: bold;">{s['change_percent']}%</td>
            <td style="color: #0d6efd; font-weight: bold;">{s['total_shares']}</td>
            <td>{s['volume']}</td>
            <td style="font-size: 12px;">{s['order_status']}</td>
            <td>{s['rsi']}</td>
            <td><span class="badge {s['badge_class']}">{s['recommendation']}</span></td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>لوحة تحليل السوق السعودي (تاسي)</title>
        <style>
            body {{
                font-family: 'Cairo', 'Tajawal', Tahoma, sans-serif;
                background-color: #f0f2f5;
                margin: 0;
                padding: 10px;
                color: #333;
                direction: rtl;
                text-align: right;
            }}
            .container {{
                max-width: 1350px;
                margin: auto;
                background: #ffffff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            }}
            h1 {{
                text-align: center;
                color: #0f5132;
                margin-bottom: 2px;
                font-size: 22px;
            }}
            p.sub {{
                text-align: center;
                color: #6c757d;
                margin-bottom: 15px;
                font-size: 13px;
            }}
            .controls {{
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
                background: #f8f9fa;
                padding: 12px;
                border-radius: 6px;
            }}
            .controls input, .controls select {{
                padding: 8px 12px;
                border: 1px solid #ced4da;
                border-radius: 5px;
                font-size: 13px;
                flex: 1;
                min-width: 180px;
                font-family: inherit;
            }}
            .table-container {{
                width: 100%;
                overflow-x: auto;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 5px;
                font-size: 12px;
            }}
            th, td {{
                padding: 10px 10px;
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
                padding: 3px 6px;
                border-radius: 4px;
                font-size: 11px;
            }}
            .badge {{
                padding: 4px 8px;
                border-radius: 15px;
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
            <h1>📊 لوحة متابعة وتحليل أسهم تاسي</h1>
            <p class="sub">أسماء الشركات، إجمالي الأسهم، أحجام التداول، وتقييم السيولة اللحظي</p>
            
            <div class="controls">
                <input type="text" id="searchInput" placeholder="🔍 بحث بالاسم أو الرمز (مثل: أرامكو أو 2222)..." onkeyup="filterTable()">
                
                <select id="sectorSelect" onchange="filterTable()">
                    <option value="">🏢 كل القطاعات</option>
                    <option value="البنوك">البنوك</option>
                    <option value="المواد الأساسية">المواد الأساسية</option>
                    <option value="الطاقة">الطاقة</option>
                    <option value="الاتصالات">الاتصالات</option>
                    <option value="صناديق ريت">صناديق ريت</option>
                </select>

                <select id="filterSelect" onchange="filterTable()">
                    <option value="">🎯 كل التوصيات</option>
                    <option value="فرصة شراء">فرصة شراء</option>
                    <option value="إيجابي">إيجابي (صاعد)</option>
                    <option value="محايد">محايد</option>
                    <option value="مخاطرة">مخاطرة / جني أرباح</option>
                </select>
            </div>

            <div class="table-container">
                <table id="stocksTable">
                    <thead>
                        <tr>
                            <th>الرمز</th>
                            <th>الشركة</th>
                            <th>القطاع</th>
                            <th>السعر</th>
                            <th>التغير %</th>
                            <th>إجمالي الأسهم</th>
                            <th>التداول اليومي</th>
                            <th>حالة السيولة</th>
                            <th>RSI</th>
                            <th>التوصية</th>
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