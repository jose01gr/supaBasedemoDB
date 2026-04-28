import os
import json
import time
import requests
import psycopg
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("SELLERCLOUD_BASE_URL")
TOKEN = os.getenv("SELLERCLOUD_BEARER_TOKEN")
DB_URL = os.getenv("LOCAL_DB_URL")

LIMIT = 652  # prueba pequeña primero


def get_customer_ids(conn):
    sql = """
    select sellercloud_customer_id
    from sellercloud_customers
    order by sellercloud_customer_id desc
    limit %s;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (LIMIT,))
        return [row[0] for row in cur.fetchall()]


def update_customer_details(conn, customer_id, data):
    general = data.get("General", {})
    internal = data.get("Internal", {})
    personal = data.get("Personal", {})
    customer_groups = data.get("CustomerGroups", {})
    addresses = data.get("Addresses", [])
    custom_columns = data.get("CustomColumns", [])

    sql = """
    update sellercloud_customers
    set
        first_name = %s,
        last_name = %s,
        customer_name = %s,
        email = %s,
        corporate_name = %s,
        company_id = %s,
        account_manager_id = %s,
        sales_man = %s,
        comment = %s,
        phone_1 = %s,
        phone_2 = %s,
        mobile = %s,
        customer_groups = %s::jsonb,
        addresses = %s::jsonb,
        custom_columns = %s::jsonb,
        raw_json = %s::jsonb,
        enriched_at = now(),
        updated_at = now()
    where sellercloud_customer_id = %s;
    """

    values = (
        general.get("FirstName"),
        general.get("LastName"),
        general.get("Name"),
        general.get("Email"),
        general.get("CorporateName"),
        internal.get("CompanyID"),
        internal.get("AccountManagerId"),
        internal.get("SalesMan"),
        internal.get("Comment"),
        personal.get("Phone1"),
        personal.get("Phone2"),
        personal.get("Mobile"),
        json.dumps(customer_groups),
        json.dumps(addresses),
        json.dumps(custom_columns),
        json.dumps(data),
        customer_id,
    )

    conn.execute(sql, values)


def main():
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    with psycopg.connect(DB_URL, prepare_threshold=None) as conn:
        customer_ids = get_customer_ids(conn)
        print(f"Customers to enrich: {len(customer_ids)}")

        enriched = 0

        for customer_id in customer_ids:
            url = f"{BASE_URL}/rest/api/Customers/{customer_id}"
            response = requests.get(url, headers=headers, timeout=60)

            print(f"Customer {customer_id} - Status {response.status_code}")

            if response.status_code == 401:
                raise Exception("Token expired or invalid. Generate a new Sellercloud token.")

            if response.status_code != 200:
                print(f"Skipped customer {customer_id} due to status {response.status_code}")
                continue

            data = response.json()

            update_customer_details(conn, customer_id, data)
            enriched += 1

            time.sleep(0.2)

        conn.commit()

    print(f"Done. Customers enriched: {enriched}")


if __name__ == "__main__":
    main()