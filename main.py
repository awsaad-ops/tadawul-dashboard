from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

app = FastAPI(
    title="لوحة تحليل السوق السعودي",
    description="نظام متكامل لتحليل وتصنيف جميع أسهم السوق السعودي مع لوحة تحكم تفاعلية باللغة العربية",
    version="12.0"
)

# القائمة الشاملة لجميع رموز شركات السوق السعودي (تاسي)
ALL_TADAWUL_SYMBOLS = [
    # المصارف والخدمات المالية
    "1010", "1020", "1060", "1080", "1111", "1120", "1150", "1180", "1212",
    # المواد الأساسية والبتروكيماويات
    "2010", "2020", "2060", "2080", "2090", "2100", "2110", "2120", "2130", "2150", 
    "2160", "2170", "2180", "2190", "2200", "2210", "2220", "2230", "2240", "2250", 
    "2270", "2280", "2290", "2300", "2310", "2320", "2330", "2340", "2350", "2360", 
    "2370", "2380", "2382", "2381",
    # الطاقة والمرافق الخدمية
    "2222", "1301", "1302", "1303", "1304", "5110",
    # الاتصالات وتقنية المعلومات
    "7010", "7020", "7030", "7040",
    # التجزئة، الأغذية، الضيافة والخدمات
    "4001", "4002", "4003", "4004", "4005", "4006", "4007", "4008", "4009", "4010", 
    "4020", "4030", "4040", "4050", "4061", "4071", "4081", "4090", "4100", "4110", 
    "4130", "4140", "4150", "4160", "4161", "4162", "4163", "4164", "4170", "4180", 
    "4190", "4200", "4210", "4220", "4230", "4240", "4250", "4260", "4270", "4280", 
    "4290", "4300", "4310", "4320", "4330", "4340", "4341",
    # الأسمنت والبناء والمواد الإنشائية
    "3001", "3002", "3003", "3004", "3005", "3007", "3008", "3010", "3020", "3030", 
    "3040", "3050", "3060", "3080", "3090", "3830", "3840",
    # قطاع التأمين
    "8010", "8020", "8030", "8040", "8050", "8060", "8070", "8080", "8090", "8100", 
    "8110", "8120", "8130", "8140", "8150", "8160", "8170", "8180", "8190", "8200", 
    "8210", "8230", "8240", "8250", "8260", "8270", "8280", "8300", "8310", "8311", 
    "8312", "8313", "8314", "8315",
    # الصناديق العقارية المتداولة (REITs) والاستثمار العقاري
    "4321", "4331", "4332", "4333", "4334", "4335", "4336", "4337", "4338", "4339", 
    "4342", "4343", "4344", "4345", "4346", "4347", "4348", "4349", "4350", "6010", 
    "6020", "6040", "6050", "6060", "6070", "6080", "6090", "6100", "6110", "6120",
    # النقل، الإعلام، وتطوير البناء
    "4261", "4262", "4263", "4264", "4265", "4620"
]

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def fetch_market_data():
    scanned_stocks = []
    for symbol in ALL_TADAWUL_SYMBOLS:
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

            # الاستراتيجية ومستويات الأسعار
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
        <tr>
            <td><b>{s['symbol']}</b></td>
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
                max-width: 1350px;
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
                margin-bottom: 30px;
                font-size: 15px;
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
            <p class="sub">تقرير حي ومحدث لجميع الشركات المدرجة مع استراتيجيات الدخول، الأهداف، ووقف الخسارة</p>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>رمز السهم</th>
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
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)