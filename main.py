import requests
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header, BackgroundTasks
import datetime
import pytesseract
from pdf2image import convert_from_bytes
import io
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.openapi.docs import get_swagger_ui_html
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI(
    title="Project Alpha API",
    description="### 🚀 Project Alpha: Enterprise Business Intelligence",
    version="1.0.0-beta",
    docs_url=None, 
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIG ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# --- DATABASE / MODELS ---
class LoginRequest(BaseModel):
    email: str
    otp: str = None

SESSIONS = {}
OTPS = {} 

USERS = {
    "ja5p3r@openclaw.ai": {"name": "Jasper", "plan": "OBSIDIAN", "api_key": "MASTER_JASPER_KEY"},
    "peterkalex10@gmail.com": {"name": "Peter", "plan": "OBSIDIAN", "api_key": "MASTER_JASPER_KEY"}
}

API_KEYS = {
    "ALPHA_GUEST_KEY": {"plan": "GUEST", "owner": "Public"},
    "MASTER_JASPER_KEY": {"plan": "OBSIDIAN", "owner": "Jasper"},
}

PLAN_LEVELS = {"GUEST": 1, "FREE": 1, "GOLD": 2, "DIAMOND": 3, "OBSIDIAN": 4}

# Thread pool for off-loading slow SMTP operations
executor = ThreadPoolExecutor(max_workers=3)

# --- EMAIL LOGIC ---
def send_otp_email_sync(receiver_email, otp):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return False
    
    msg = MIMEMultipart()
    msg['From'] = f"Alpha OS Security <{SENDER_EMAIL}>"
    msg['To'] = receiver_email
    msg['Subject'] = f"{otp} is your verification code"

    body = f"""
    <html>
    <body style="font-family: sans-serif; padding: 20px;">
        <h2 style="color: #0ea5e9;">Project Alpha</h2>
        <p>Your one-time access code is:</p>
        <div style="background: #f1f5f9; padding: 20px; font-size: 24px; font-weight: bold; text-align: center; border-radius: 12px;">{otp}</div>
        <p style="font-size: 12px; color: #64748b; margin-top: 20px;">Alpha OS • Enterprise Intelligence</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        # Use a short timeout to prevent blocking
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP ERROR: {e}")
        return False

# --- AUTH LOGIC ---
@app.post("/api/v1/auth/request-otp")
async def request_otp(req: LoginRequest, background_tasks: BackgroundTasks):
    if req.email not in USERS:
        raise HTTPException(status_code=404, detail="Account not found")
    
    otp = str(secrets.randbelow(899999) + 100000)
    OTPS[req.email] = otp
    
    # Run email sending in a background task to prevent freezing the UI
    background_tasks.add_task(send_otp_email_sync, req.email, otp)
    
    return {"status": "success", "message": "Code dispatching via background channel.", "debug_otp": otp}

@app.post("/api/v1/auth/signup")
async def signup(req: LoginRequest, background_tasks: BackgroundTasks):
    if req.email in USERS:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    otp = str(secrets.randbelow(899999) + 100000)
    OTPS[req.email] = otp
    
    # Background task for registration email too
    background_tasks.add_task(send_otp_email_sync, req.email, otp)
    
    return {"status": "success", "message": "Verification code dispatched.", "debug_otp": otp}

@app.post("/api/v1/auth/verify-otp")
async def verify_otp(req: LoginRequest):
    if OTPS.get(req.email) != req.otp:
        raise HTTPException(status_code=401, detail="Invalid code")
    
    if req.email not in USERS:
        USERS[req.email] = {
            "name": req.email.split('@')[0].capitalize(),
            "plan": "FREE",
            "api_key": f"ALPHA_{secrets.token_hex(8).upper()}"
        }
        API_KEYS[USERS[req.email]["api_key"]] = {"plan": "FREE", "owner": req.email}

    user = USERS[req.email]
    session_id = secrets.token_urlsafe(32)
    SESSIONS[session_id] = user
    return {"status": "success", "session_id": session_id, "user": user}

async def verify_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return API_KEYS[x_api_key]

def check_access(user_plan: str, required_level: int):
    level = PLAN_LEVELS.get(user_plan, 0)
    if level < required_level:
        raise HTTPException(status_code=402, detail="Upgrade required")

# --- ENDPOINTS ---
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📈</text></svg>")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Alpha OS | Documentation",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📈</text></svg>"
    )

DASHBOARD_HTML = ""
if os.path.exists("dashboard.html"):
    with open("dashboard.html", "r") as f:
        DASHBOARD_HTML = f.read()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    return DASHBOARD_HTML

@app.get("/api/v1/forex/usd-inr")
async def forex(user: dict = Depends(verify_key)):
    check_access(user['plan'], 1)
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    try:
        r = requests.get(url, timeout=5).json()
        return {"status": "success", "data": {"rate": r['rates'].get('INR'), "date": r.get('date')}}
    except: return {"error": "Source down"}

@app.get("/api/v1/mandi/snapshot")
async def mandi_snapshot(user: dict = Depends(verify_key)):
    if user['plan'] == "GUEST": raise HTTPException(status_code=402, detail="Login required")
    return {"status": "success", "data": [{"commodity": "Wheat", "price": 2550}, {"commodity": "Rice", "price": 3200}]}

@app.get("/api/v1/gst/verify/{gstin}")
async def verify_gst(gstin: str, user: dict = Depends(verify_key)):
    check_access(user['plan'], 2)
    return {"status": "success", "valid": True, "pan": gstin[2:12]}

@app.get("/", response_class=HTMLResponse)
async def home_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Project Alpha | Home</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
        <script>
            tailwind.config = { darkMode: 'class' }
            function toggleTheme() {
                document.documentElement.classList.toggle('dark');
                localStorage.theme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
            }
        </script>
        <style>
            body { font-family: 'Outfit', sans-serif; transition: all 0.3s ease; }
            .dark body { background: #030712; color: white; }
            .light body { background: #f8fafc; color: #0f172a; }
            .glass { backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.1); }
            .dark .glass { background: rgba(17, 24, 39, 0.7); }
            .light .glass { background: rgba(255, 255, 255, 0.7); border-color: rgba(0,0,0,0.05); }
        </style>
    </head>
    <body class="min-h-screen flex items-center justify-center">
        <script>if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) document.documentElement.classList.add('dark'); else document.documentElement.classList.remove('dark');</script>
        <div class="max-w-4xl w-full mx-4 text-center space-y-8">
            <div class="glass p-12 rounded-[2.5rem] shadow-2xl">
                <div class="flex justify-end mb-4">
                    <button onclick="toggleTheme()" class="p-2 rounded-full hover:bg-white/10">🌓</button>
                </div>
                <h1 class="text-6xl font-black tracking-tighter mb-4">Project <span class="text-sky-500">Alpha</span></h1>
                <p class="text-slate-500 text-xl max-w-lg mx-auto mb-10">Advanced Indian Market Intelligence. Real-time, Enterprise-grade.</p>
                <div class="flex flex-wrap justify-center gap-4">
                    <a href="/dashboard" class="bg-sky-500 hover:bg-sky-600 text-white px-10 py-4 rounded-2xl font-bold shadow-lg shadow-sky-500/30 transition-all">Go to Console</a>
                    <a href="/docs" class="glass px-10 py-4 rounded-2xl font-bold hover:bg-white/5 transition-all">API Specs</a>
                </div>
            </div>
            <p class="text-[10px] uppercase tracking-[0.5em] text-slate-500">Scale your business with the Alpha Engine</p>
        </div>
    </body>
    </html>
    """
