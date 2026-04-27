import os
import json
import requests
import psycopg
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("SELLERCLOUD_BASE_URL")
TOKEN = os.getenv("SELLERCLOUD_BEARER_TOKEN")
DB_URL = os.getenv("LOCAL_DB_URL")

PAGE_SIZE = 50
MAX_PAGES = 14  # por ahora solo prueba pequeña


def map_customer(item):
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


def upsert_customer(conn, customer):
    sql = """
    insert into sellercloud_customers (
        sellercloud_customer_id,
        first_name,
        last_name,
        customer_name,
        email,
        phone,
        corporate_name,
        customer_type,
        city,
        state,
        postal_code,
        country,
        address_line_1,
        address_line_2,
        raw_json,
        updated_at
    )
    values (
        %(sellercloud_customer_id)s,
        %(first_name)s,
        %(last_name)s,
        %(customer_name)s,
        %(email)s,
        %(phone)s,
        %(corporate_name)s,
        %(customer_type)s,
        %(city)s,
        %(state)s,
        %(postal_code)s,
        %(country)s,
        %(address_line_1)s,
        %(address_line_2)s,
        %(raw_json)s::jsonb,
        now()
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
        city = excluded.city,
        state = excluded.state,
        postal_code = excluded.postal_code,
        country = excluded.country,
        address_line_1 = excluded.address_line_1,
        address_line_2 = excluded.address_line_2,
        raw_json = excluded.raw_json,
        updated_at = now();
    """

    conn.execute(sql, customer)


def main():
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    total_inserted = 0

    with psycopg.connect(DB_URL) as conn:
        for page in range(1, MAX_PAGES + 1):
            url = f"{BASE_URL}/rest/api/Customers?model.channel=21&model.pageNumber={page}&model.pageSize={PAGE_SIZE}"
            response = requests.get(url, headers=headers, timeout=60)

            print(f"Page {page} - Status {response.status_code}")

            response.raise_for_status()
            data = response.json()

            items = data.get("Items", [])
            print(f"Items received: {len(items)}")
            
            if items:
                print("First UserID on page:", items[0].get("UserID"))
            

            for item in items:
                customer = map_customer(item)
                if customer["sellercloud_customer_id"]:
                    upsert_customer(conn, customer)
                    total_inserted += 1

        conn.commit()

    print(f"Done. Customers loaded/updated: {total_inserted}")


if __name__ == "__main__":
    main()