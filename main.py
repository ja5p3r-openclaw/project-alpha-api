import requests
from fastapi import FastAPI, HTTPException, UploadFile, File
import datetime
import pytesseract
from pdf2image import convert_from_bytes
import io

app = FastAPI(title="Indian Business Data API (Brother Edition)")

# ... (rest of the code)
CACHE = {
    "fx": {"data": None, "expiry": None},
    "mandi": {"data": None, "expiry": None}
}

def get_live_fx():
    # Reliable FX data (USD/INR and others) - Very important for import/export businesses
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
async def forex():
    data = get_live_fx()
    return {"status": "success", "data": data}

@app.get("/api/v1/mandi/snapshot")
async def mandi_snapshot():
    # In a real production environment, we would use data.gov.in API keys 
    # or a robust scraper. For this MVP expansion, we provide a high-fidelity 
    # simulated real-time feed across major Indian states.
    return {
        "status": "success",
        "timestamp": str(datetime.datetime.now()),
        "source": "Agmarknet-Simulated-Live",
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
async def ocr_pdf(file: UploadFile = File(...)):
    # Path C: Document Processing MVP
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    try:
        content = await file.read()
        images = convert_from_bytes(content)
        full_text = ""
        for image in images:
            text = pytesseract.image_to_string(image)
            full_text += text + "\n"
        
        return {
            "status": "success",
            "filename": file.filename,
            "text": full_text
        }
    except Exception as e:
        return {"status": "error", "message": "OCR Engine error. Ensure 'tesseract-ocr' and 'poppler-utils' are installed on host."}

@app.get("/api/v1/gst/verify/{gstin}")
async def verify_gst(gstin: str):
    # This is a critical endpoint for B2B trust.
    # We implement high-level validation logic.
    # In production, this would hit the GSTN portal or a proxy like Karza/Razorpay.
    if len(gstin) != 15:
        return {"status": "error", "message": "Invalid GSTIN length. Must be 15 characters."}
    
    # Simple check for state code (first 2 digits)
    state_code = gstin[:2]
    if not state_code.isdigit():
        return {"status": "error", "message": "Invalid state code in GSTIN."}
    
    return {
        "status": "success",
        "gstin": gstin,
        "valid": True,
        "details": {
            "business_name": "Simulated Entity",
            "state_code": state_code,
            "status": "Active",
            "type": "Regular"
        },
        "note": "Production version requires GSTN portal integration."
    }

@app.get("/")
async def root():
    return {
        "message": "Welcome to the Indian Business Data API",
        "version": "1.0.0-beta",
        "documentation": "/docs",
        "developer": "Brother AI (Pi)"
    }
