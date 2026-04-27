import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("SELLERCLOUD_BASE_URL")
TOKEN = os.getenv("SELLERCLOUD_BEARER_TOKEN")

url = f"{BASE_URL}/rest/api/Customers?model.channel=21&pageNumber=1&pageSize=10"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

print("BASE_URL:", BASE_URL)
print("URL:", url)

response = requests.get(url, headers=headers, timeout=60)

print("Status:", response.status_code)
print(response.text[:3000])