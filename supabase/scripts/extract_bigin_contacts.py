import os
import json
import requests
import psycopg
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ACCOUNTS_URL = os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com")
BIGIN_API_BASE_URL = os.getenv("BIGIN_API_BASE_URL", "https://www.zohoapis.com/bigin/v2")
DB_URL = os.getenv("LOCAL_DB_URL")

PER_PAGE = 200
MAX_PAGES = 200  # prueba pequeña primero


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


def upsert_contact(conn, contact):
    owner = contact.get("Owner") or {}

    sql = """
    insert into bigin_contacts (
        bigin_contact_id,
        sellercloud_customer_id,
        first_name,
        last_name,
        full_name,
        email,
        phone,
        mobile,
        owner_name,
        owner_email,
        tags,
        raw_json,
        updated_at
    )
    values (
        %(bigin_contact_id)s,
        %(sellercloud_customer_id)s,
        %(first_name)s,
        %(last_name)s,
        %(full_name)s,
        %(email)s,
        %(phone)s,
        %(mobile)s,
        %(owner_name)s,
        %(owner_email)s,
        %(tags)s::jsonb,
        %(raw_json)s::jsonb,
        now()
    )
    on conflict (bigin_contact_id)
    do update set
        sellercloud_customer_id = excluded.sellercloud_customer_id,
        first_name = excluded.first_name,
        last_name = excluded.last_name,
        full_name = excluded.full_name,
        email = excluded.email,
        phone = excluded.phone,
        mobile = excluded.mobile,
        owner_name = excluded.owner_name,
        owner_email = excluded.owner_email,
        tags = excluded.tags,
        raw_json = excluded.raw_json,
        updated_at = now();
    """

    values = {
        "bigin_contact_id": contact.get("id"),
        "sellercloud_customer_id": contact.get("SellerCloud_Client_ID"),
        "first_name": contact.get("First_Name"),
        "last_name": contact.get("Last_Name"),
        "full_name": contact.get("Full_Name"),
        "email": contact.get("Email"),
        "phone": contact.get("Phone"),
        "mobile": contact.get("Mobile"),
        "owner_name": owner.get("name"),
        "owner_email": owner.get("email"),
        "tags": json.dumps(contact.get("Tag") or []),
        "raw_json": json.dumps(contact),
    }

    conn.execute(sql, values)


def main():
    access_token = get_access_token()

    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
    }

    fields = "id,First_Name,Last_Name,Full_Name,Email,Phone,Mobile,SellerCloud_Client_ID,Tag,Owner"

    total_loaded = 0
    next_page_token = None

    with psycopg.connect(DB_URL) as conn:
        for page in range(1, MAX_PAGES + 1):
            params = {
                "fields": fields,
                "per_page": PER_PAGE,
            }

            if next_page_token:
                params["page_token"] = next_page_token
            else:
                params["page"] = page

            url = f"{BIGIN_API_BASE_URL}/Contacts"
            response = requests.get(url, headers=headers, params=params, timeout=60)

            print(f"Page {page} - Status {response.status_code}")
            response.raise_for_status()

            data = response.json()
            contacts = data.get("data", [])
            info = data.get("info", {})

            print(f"Contacts received: {len(contacts)}")

            for contact in contacts:
                tags = contact.get("Tag") or []
                tag_names = [tag.get("name") for tag in tags]

                if "V - Cliente Activo" not in tag_names:
                    continue

                upsert_contact(conn, contact)
                total_loaded += 1

            next_page_token = info.get("next_page_token")

            if not info.get("more_records"):
                break

        conn.commit()

    print(f"Done. Bigin contacts loaded/updated: {total_loaded}")


if __name__ == "__main__":
    main()