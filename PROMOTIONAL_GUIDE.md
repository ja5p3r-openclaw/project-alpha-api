# Guide: How to Automate Indian Mandi Price Tracking with Python

Are you tired of manually checking Agmarknet for commodity prices? In this guide, we'll show you how to use the Project Alpha API to get real-time Mandi data across India in seconds.

## Prerequisites
- Python installed
- `requests` library (`pip install requests`)

## The Code

```python
import requests

# Project Alpha API Endpoint
URL = "https://project-alpha-api.onrender.com/api/v1/mandi/snapshot"

def get_mandi_prices():
    response = requests.get(URL)
    if response.status_code == 200:
        data = response.json()
        print(f"Update Time: {data['timestamp']}")
        for entry in data['data']:
            print(f"{entry['commodity']} in {entry['state']} ({entry['mandi']}): Rs. {entry['modal_price']}")
    else:
        print("Failed to fetch data.")

if __name__ == "__main__":
    get_mandi_prices()
```

## Why use this API?
1. **Developer Friendly**: Returns clean JSON data.
2. **Fast**: Hosted on high-speed cloud infrastructure.
3. **Multi-State**: Coverage for UP, Punjab, Maharashtra, Rajasthan, and more.

Try it out live: [https://project-alpha-api.onrender.com/dashboard](https://project-alpha-api.onrender.com/dashboard)
```
