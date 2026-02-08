#!/bin/bash
# Engine Start Script for Jasper
source market_api_venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &
./cloudflared tunnel --url http://localhost:8000 &
echo "Engine Started!"
