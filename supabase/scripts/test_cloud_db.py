import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

CLOUD_DB_URL = os.getenv("CLOUD_DB_URL")


def main():
    if not CLOUD_DB_URL:
        raise ValueError("Missing CLOUD_DB_URL in .env")

    with psycopg.connect(CLOUD_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("select now();")
            result = cur.fetchone()

    print("Cloud DB connection OK")
    print(f"Server time: {result[0]}")


if __name__ == "__main__":
    main()