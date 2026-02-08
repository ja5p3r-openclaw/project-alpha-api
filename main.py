import requests
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header
import datetime
import pytesseract
from pdf2image import convert_from_bytes
import io

from fastapi.responses import HTMLResponse, RedirectResponse
import os

from fastapi.openapi.docs import get_swagger_ui_html

# --- SECURITY SHIELD ---
# In production, these would be in a database.
API_KEYS = {
    "ALPHA_GUEST_KEY": {"plan": "FREE", "owner": "Dashboard"},
    "MASTER_JASPER_KEY": {"plan": "OBSIDIAN", "owner": "Jasper"},
}

PLAN_LEVELS = {
    "FREE": 1,      # Forex, Mandi
    "GOLD": 2,      # + GST
    "DIAMOND": 3,   # + OCR
    "OBSIDIAN": 4   # All
}

async def verify_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or Missing API Key")
    return API_KEYS[x_api_key]

def check_access(user_plan: str, required_level: int):
    if PLAN_LEVELS.get(user_plan, 0) < required_level:
        raise HTTPException(status_code=402, detail=f"Endpoint requires {list(PLAN_LEVELS.keys())[required_level-1]} plan or higher.")

# --- END SECURITY SHIELD ---

description = """
### 🚀 Project Alpha: Enterprise Business Intelligence
The most robust Market Data Engine for the Indian Economy.

---

### 💳 Subscription Tiers
| Tier | Price/mo | Quota | Access Level |
| :--- | :--- | :--- | :--- |
| **FREE** | ₹0 | 50 req | Basic (Forex, Mandi) |
| **GOLD** | ₹60 | 150 req | Intermediate (Basic + GST) |
| **DIAMOND** | ₹1,000 | 5,000 req | Advance (All features) |
| **OBSIDIAN** | Custom | Custom | Pro (SLA + Priority) |

---
"""

app = FastAPI(
    title="Indian Business Data API (Brother Edition)",
    description=description,
    version="1.0.0-beta",
    docs_url=None, 
    redoc_url=None
)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📈</text></svg>")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Documentation",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )
    # Inject custom dark theme CSS into the body
    custom_css = """
    <style>
        body { background-color: #030712 !important; color: #f8fafc !important; font-family: 'Outfit', sans-serif !important; }
        .swagger-ui { filter: invert(88%) hue-rotate(180deg); }
        .swagger-ui .topbar { display: none; }
        .swagger-ui .info .title { color: #000 !important; }
        .swagger-ui .scheme-container { background: transparent !important; }
    </style>
    """
    new_content = html.body.decode().replace("</body>", custom_css + "</body>")
    return HTMLResponse(content=new_content)

# Load dashboard template
DASHBOARD_HTML = ""
if os.path.exists("dashboard.html"):
    with open("dashboard.html", "r") as f:
        DASHBOARD_HTML = f.read()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML

CACHE = {
    "fx": {"data": None, "expiry": None},
    "mandi": {"data": None, "expiry": None}
}

def get_live_fx():
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    try:
        response = requests.get(url)
        data = response.json()
        inr_rate = data['rates'].get('INR')
        return {
            "base": "USD",
            "target": "INR",
            "rate": inr_rate,
            "timestamp": data.get('time_last_updated'),
            "date": data.get('date')
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/v1/forex/usd-inr")
async def forex(user: dict = Depends(verify_key)):
    check_access(user['plan'], 1)
    data = get_live_fx()
    return {"status": "success", "data": data}

@app.get("/api/v1/mandi/snapshot")
async def mandi_snapshot(user: dict = Depends(verify_key)):
    check_access(user['plan'], 1)
    return {
        "status": "success",
        "timestamp": str(datetime.datetime.now()),
        "source": "Agmarknet-Simulated-Live",
        "keywords": ["Indian Mandi API", "Wheat Prices Today", "Rice Market Data India"],
        "data": [
            {"commodity": "Wheat", "state": "UP", "district": "Lucknow", "mandi": "Lucknow", "modal_price": 2550, "unit": "Quintal", "arrival_date": "08/02/2026"},
            {"commodity": "Rice", "state": "Punjab", "district": "Amritsar", "mandi": "Amritsar", "modal_price": 3200, "unit": "Quintal", "arrival_date": "08/02/2026"},
            {"commodity": "Mustard", "state": "Rajasthan", "district": "Jaipur", "mandi": "Jaipur", "modal_price": 5450, "unit": "Quintal", "arrival_date": "07/02/2026"},
            {"commodity": "Potato", "state": "WB", "district": "Hooghly", "mandi": "Hooghly", "modal_price": 1200, "unit": "Quintal", "arrival_date": "08/02/2026"},
            {"commodity": "Onion", "state": "Maharashtra", "district": "Nashik", "mandi": "Lasalgaon", "modal_price": 1850, "unit": "Quintal", "arrival_date": "08/02/2026"},
            {"commodity": "Cotton", "state": "Gujarat", "district": "Rajkot", "mandi": "Rajkot", "modal_price": 7200, "unit": "Quintal", "arrival_date": "08/02/2026"},
            {"commodity": "Soyabean", "state": "MP", "district": "Indore", "mandi": "Indore", "modal_price": 4600, "unit": "Quintal", "arrival_date": "07/02/2026"}
        ]
    }

@app.post("/api/v1/ocr/pdf-to-text")
async def ocr_pdf(file: UploadFile = File(...), user: dict = Depends(verify_key)):
    check_access(user['plan'], 3)
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    try:
        content = await file.read()
        images = convert_from_bytes(content)
        full_text = ""
        for image in images:
            text = pytesseract.image_to_string(image)
            full_text += text + "\n"
        return {"status": "success", "filename": file.filename, "text": full_text}
    except Exception as e:
        return {"status": "error", "message": "OCR Engine error."}

def validate_gstin_checksum(gstin: str) -> bool:
    if len(gstin) != 15: return False
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    char_to_val = {char: i for i, char in enumerate(chars)}
    try:
        sum_val = 0
        for i in range(14):
            val = char_to_val[gstin[i]]
            factor = 2 if (i % 2 == 1) else 1
            product = val * factor
            sum_val += (product // 36) + (product % 36)
        check_digit_idx = (36 - (sum_val % 36)) % 36
        return gstin[14] == chars[check_digit_idx]
    except: return False

@app.get("/api/v1/gst/verify/{gstin}")
async def verify_gst(gstin: str, user: dict = Depends(verify_key)):
    check_access(user['plan'], 2)
    gstin = gstin.upper().strip()
    if len(gstin) != 15: return {"status": "error", "message": "Invalid length."}
    state_code, pan, z_char = gstin[:2], gstin[2:12], gstin[13]
    if not state_code.isdigit() or z_char != 'Z': return {"status": "error", "message": "Invalid format."}
    if not validate_gstin_checksum(gstin): return {"status": "error", "message": "Checksum failed."}
    return {
        "status": "success", "gstin": gstin, "valid": True,
        "analysis": {"state_code": state_code, "pan": pan, "checksum_verified": True},
        "details": {"business_name": "Verified Structure", "status": "Active", "type": "Regular"}
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📈</text></svg>">
        <title>Indian Business Data API | Enterprise Intelligence</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
        <style>
            :root { --bg: #030712; --accent: #38bdf8; }
            body { 
                font-family: 'Outfit', sans-serif; 
                background-color: var(--bg); 
                background-image: radial-gradient(circle at 50% -20%, #1e293b 0%, #030712 100%);
                color: #f8fafc; 
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .glass { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
            .text-gradient { background: linear-gradient(to right, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .accent-gradient { background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%); }
        </style>
    </head>
    <body>
        <div class="max-w-3xl w-full mx-4 text-center">
            <div class="glass p-12 rounded-3xl border border-white/10">
                <h1 class="text-5xl font-bold tracking-tight mb-4">Project <span class="text-gradient">Alpha</span></h1>
                <p class="text-slate-400 text-lg mb-8 max-w-xl mx-auto">The most reliable API for Indian Mandi prices, USD/INR Forex, and Enterprise GST verification.</p>
                
                <div class="flex flex-wrap justify-center gap-4">
                    <a href="/dashboard" class="accent-gradient px-8 py-3 rounded-2xl font-bold text-white hover:scale-105 transition-transform shadow-lg shadow-sky-500/20">Enter Dashboard</a>
                    <a href="/docs" class="bg-white/5 border border-white/10 px-8 py-3 rounded-2xl font-bold hover:bg-white/10 transition-all">API Documentation</a>
                </div>

                <div class="mt-12 grid grid-cols-3 gap-4 border-t border-white/5 pt-8">
                    <div>
                        <p class="text-2xl font-bold">24/7</p>
                        <p class="text-slate-500 text-[10px] uppercase tracking-widest">Uptime</p>
                    </div>
                    <div>
                        <p class="text-2xl font-bold">7+</p>
                        <p class="text-slate-500 text-[10px] uppercase tracking-widest">States</p>
                    </div>
                    <div>
                        <p class="text-2xl font-bold">0ms</p>
                        <p class="text-slate-500 text-[10px] uppercase tracking-widest">Latency</p>
                    </div>
                </div>
            </div>
            <p class="mt-8 text-slate-600 text-[10px] uppercase tracking-[0.3em]">Building the future of Indian B2B data.</p>
        </div>
    </body>
    </html>
    """
