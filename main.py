from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

app = FastAPI(
    title="لوحة تحليل السوق السعودي - حسب القطاعات",
    description="نظام متكامل لتحليل وتصنيف أسهم تاسي حسب القطاعات مع بحث وفلترة ذكية",
    version="14.0"
)

# تصنيف الشركات حسب القطاعات الرئيسية في السوق السعودي (تاسي)
SECTORS_DATA = {
    "البنوك والخدمات المالية": {
        "symbols": ["1010", "1020", "1060", "1080", "1111", "1120", "1150", "1180", "1212"],
        "name_ar": "البنوك والخدمات المالية"
    },
    "المواد الأساسية": {
        "symbols": ["2010", "2020", "2060", "2080", "2090", "2100", "2110", "2120", "2130", "2150", "2160", "2170", "2180", "2190", "2200"],
        "name_ar": "المواد الأساسية"
    },
    "الطاقة والمرافق": {
        "symbols": ["2222", "1301", "1302", "1303", "1304", "5110"],
        "name_ar": "الطاقة والمرافق"
    },
    "الاتصالات وتقنية المعلومات": {
        "symbols": ["7010", "7020", "7030", "7040"],
        "name_ar": "الاتصالات وتقنية المعلومات"
    },
    "التجزئة والأغذية": {
        "symbols": ["4001", "4002", "4003", "4004", "4005", "4006", "4007", "4008", "4009", "4010"],
        "name_ar": "التجزئة والأغذية"
    },
    "الصناديق العقارية (REITs)": {
        "symbols": ["4321", "4331", "4332", "4333", "4334", "4335", "4336", "4337", "4338", "4339"],
        "name_ar": "الصناديق العقارية (REITs)"
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
        for symbol in sector_info["symbols"]:
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
                volume = int(hist['Volume'].iloc[-1])
                
                latest_rsi_val = hist['RSI'].iloc[-1]
                latest_rsi = round(float(latest_rsi_val), 2) if not pd.isna(latest_rsi_val) else 50.0

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
                    "sector": sector_name,
                    "current_price": round(current_price, 2),
                    "change_percent": change_percent,
                    "rsi": latest_rsi,
                    "volume": volume,
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
        <tr data-symbol="{s['symbol']}" data-sector="{s['sector']}" data-rec="{s['recommendation']}">
            <td><b>{s['symbol']}</b></td>
            <td><span class="sector-tag">{s['sector']}</span></td>
            <td>{s['current_price']} ر.س</td>
            <td style="color: {'#198754' if s['change_percent'] >= 0 else '#dc3545'}; font-weight: bold;">{s['change_percent']}%</td>
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
        <title>لوحة تحليل السوق السعودي (تاسي)</title>
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
                max-width: 1400px;
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
                font-size: 14px;
            }}
            th, td {{
                padding: 14px 16px;
                border-bottom: 1px solid #e9ecef;
                text-align: right;
            }}
            th {{
                background-color: #0f5132;
                color: white;
                font-weight: 600;
                white-space: nowrap;
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
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                display: inline-block;
                text-align: center;
                white-space: nowrap;
            }}
            .buy {{ background-color: #d1e7dd; color: #0f5132; }}
            .risky {{ background-color: #f8d7da; color: #842029; }}
            .neutral {{ background-color: #fff3cd; color: #664d03; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 لوحة متابعة وتحليل أسهم السوق السعودي (تاسي)</h1>
            <p class="sub">تصنيف قطاعي ذكي مع بحث فوري وفلترة حية لجميع الشركات</p>
            
            <!-- أدوات البحث والفلترة -->
            <div class="controls">
                <input type="text" id="searchInput" placeholder="🔍 ابحث برمز السهم (مثل: 1010)..." onkeyup="filterTable()">
                
                <select id="sectorSelect" onchange="filterTable()">
                    <option value="">🏢 فلترة حسب القطاع (الكل)</option>
                    <option value="البنوك والخدمات المالية">البنوك والخدمات المالية</option>
                    <option value="المواد الأساسية">المواد الأساسية</option>
                    <option value="الطاقة والمرافق">الطاقة والمرافق</option>
                    <option value="الاتصالات وتقنية المعلومات">الاتصالات وتقنية المعلومات</option>
                    <option value="التجزئة والأغذية">التجزئة والأغذية</option>
                    <option value="الصناديق العقارية (REITs)">الصناديق العقارية (REITs)</option>
                </select>

                <select id="filterSelect" onchange="filterTable()">
                    <option value="">🎯 فلترة حسب التوصية (الكل)</option>
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
                            <th>رمز السهم</th>
                            <th>القطاع</th>
                            <th>السعر الحالي</th>
                            <th>التغير %</th>
                            <th>مؤشر القوة (RSI)</th>
                            <th>منطقة الشراء المقترحة</th>
                            <th>سعر الهدف</th>
                            <th>وقف الخسارة</th>
                            <th>حالة السهم والتوصية</th>
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
                    let sector = tr[i].getAttribute("data-sector");
                    let rec = tr[i].getAttribute("data-rec");
                    
                    let matchSymbol = symbol.includes(input);
                    let matchSector = (sectorFilter === "" || sector === sectorFilter);
                    let matchRec = (recFilter === "" || rec.includes(recFilter));

                    if (matchSymbol && matchSector && matchRec) {{
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