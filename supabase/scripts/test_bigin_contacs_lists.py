import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ACCOUNTS_URL = os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com")
BIGIN_API_BASE_URL = os.getenv("BIGIN_API_BASE_URL", "https://www.zohoapis.com/bigin/v2")


def get_access_token():
    url = f"{ACCOUNTS_URL}/oauth/v2/token"
    payload = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
    }

    response = requests.post(url, data=payload, timeout=60)
    response.raise_for_status()
    return response.json()["access_token"]


access_token = get_access_token()

url = f"{BIGIN_API_BASE_URL}/Contacts"

headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}",
}

params = {
    "fields": "id,First_Name,Last_Name,Full_Name,Email,Phone,Mobile,SellerCloud_Client_ID,Tag,Owner",
    "page": 1,
    "per_page": 10,
    "tag_names": "V - Cliente Activo",
}

response = requests.get(url, headers=headers, params=params, timeout=60)

print("Status:", response.status_code)
print(response.text[:3000])