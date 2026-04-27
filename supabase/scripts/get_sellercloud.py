import requests

BASE_URL = "https://fc2.api.sellercloud.com"

USERNAME = "api@firstchoiceonline.com"
PASSWORD = "f!gT33MjAfkTUZd"

url = f"{BASE_URL}/rest/api/token"

payload = {
    "Username": USERNAME,
    "Password": PASSWORD,
}

response = requests.post(url, json=payload, timeout=60)

print("Status:", response.status_code)
print(response.text)