import requests

CLIENT_ID = "1000.KQ1L2UI9NBX7S5MR940ORO7WI289IL"
CLIENT_SECRET = "96d9a8e2799af6349f1be306050f2dbf817ae4e2b5"
GRANT_TOKEN = "1000.dc69458636c968481789e280d945732f.38f2d814c61eabedeb859f551d3f385b"

url = "https://accounts.zoho.com/oauth/v2/token"

payload = {
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": GRANT_TOKEN,
}

response = requests.post(url, data=payload, timeout=60)

print("Status:", response.status_code)
print(response.text)