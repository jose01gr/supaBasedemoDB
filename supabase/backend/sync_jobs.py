import os
import json
import requests
import psycopg

PAGE_SIZE = 50
PER_PAGE = 200


def sync_sellercloud(db_url: str) -> dict:
    base_url = os.getenv("SELLERCLOUD_BASE_URL")
    token = os.getenv("SELLERCLOUD_BEARER_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    total = 0
    page = 1

    with psycopg.connect(db_url, prepare_threshold=None) as conn:
        while True:
            url = f"{base_url}/rest/api/Customers?model.channel=21&model.pageNumber={page}&model.pageSize={PAGE_SIZE}"
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            items = data.get("Items", [])

            if not items:
                break

            for item in items:
                customer = _map_sellercloud_customer(item)
                if customer["sellercloud_customer_id"]:
                    _upsert_sellercloud_customer(conn, customer)
                    total += 1

            page += 1

        conn.commit()

    return {"records_updated": total}


def sync_bigin(db_url: str) -> dict:
    client_id = os.getenv("ZOHO_CLIENT_ID")
    client_secret = os.getenv("ZOHO_CLIENT_SECRET")
    refresh_token = os.getenv("ZOHO_REFRESH_TOKEN")
    accounts_url = os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com")
    bigin_api_base = os.getenv("BIGIN_API_BASE_URL", "https://www.zohoapis.com/bigin/v2")

    access_token = _get_bigin_access_token(client_id, client_secret, refresh_token, accounts_url)
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    fields = "id,First_Name,Last_Name,Full_Name,Email,Phone,Mobile,SellerCloud_Client_ID,Tag,Owner"
    total = 0
    next_page_token = None
    page = 1

    with psycopg.connect(db_url, prepare_threshold=None) as conn:
        while True:
            params = {"fields": fields, "per_page": PER_PAGE}
            if next_page_token:
                params["page_token"] = next_page_token
            else:
                params["page"] = page

            url = f"{bigin_api_base}/Contacts"
            response = requests.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()

            data = response.json()
            contacts = data.get("data", [])
            info = data.get("info", {})

            for contact in contacts:
                tags = contact.get("Tag") or []
                tag_names = [tag.get("name") for tag in tags]
                if "V - Cliente Activo" not in tag_names:
                    continue
                _upsert_bigin_contact(conn, contact)
                total += 1

            next_page_token = info.get("next_page_token")
            if not info.get("more_records"):
                break
            page += 1

        conn.commit()

    return {"records_updated": total}


def _get_bigin_access_token(client_id, client_secret, refresh_token, accounts_url):
    url = f"{accounts_url}/oauth/v2/token"
    payload = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    response = requests.post(url, data=payload, timeout=60)
    response.raise_for_status()
    return response.json()["access_token"]


def _map_sellercloud_customer(item):
    first_name = item.get("FirstName")
    last_name = item.get("LastName")
    customer_name = " ".join(x for x in [first_name, last_name] if x)
    return {
        "sellercloud_customer_id": str(item.get("UserID")),
        "first_name": first_name,
        "last_name": last_name,
        "customer_name": customer_name or None,
        "email": item.get("Email"),
        "phone": item.get("Phone") or item.get("PhoneNumber"),
        "corporate_name": item.get("CorporateName"),
        "customer_type": item.get("IsWholesaleString"),
        "city": None,
        "state": None,
        "postal_code": None,
        "country": None,
        "address_line_1": None,
        "address_line_2": None,
        "raw_json": json.dumps(item),
    }


def _upsert_sellercloud_customer(conn, customer):
    sql = """
    insert into sellercloud_customers (
        sellercloud_customer_id, first_name, last_name, customer_name,
        email, phone, corporate_name, customer_type, city, state,
        postal_code, country, address_line_1, address_line_2, raw_json, updated_at
    )
    values (
        %(sellercloud_customer_id)s, %(first_name)s, %(last_name)s, %(customer_name)s,
        %(email)s, %(phone)s, %(corporate_name)s, %(customer_type)s, %(city)s, %(state)s,
        %(postal_code)s, %(country)s, %(address_line_1)s, %(address_line_2)s,
        %(raw_json)s::jsonb, now()
    )
    on conflict (sellercloud_customer_id)
    do update set
        first_name = excluded.first_name,
        last_name = excluded.last_name,
        customer_name = excluded.customer_name,
        email = excluded.email,
        phone = excluded.phone,
        corporate_name = excluded.corporate_name,
        customer_type = excluded.customer_type,
        raw_json = excluded.raw_json,
        updated_at = now();
    """
    conn.execute(sql, customer)


def _upsert_bigin_contact(conn, contact):
    owner = contact.get("Owner") or {}
    sql = """
    insert into bigin_contacts (
        bigin_contact_id, sellercloud_customer_id, first_name, last_name, full_name,
        email, phone, mobile, owner_name, owner_email, tags, raw_json, updated_at
    )
    values (
        %(bigin_contact_id)s, %(sellercloud_customer_id)s, %(first_name)s, %(last_name)s,
        %(full_name)s, %(email)s, %(phone)s, %(mobile)s, %(owner_name)s, %(owner_email)s,
        %(tags)s::jsonb, %(raw_json)s::jsonb, now()
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
