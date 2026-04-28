import os

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

DB_URL = os.getenv("LOCAL_DB_URL")

app = FastAPI(title="Customer Data Hub API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connection():
    if not DB_URL:
        raise ValueError("Missing LOCAL_DB_URL in .env")

    return psycopg.connect(DB_URL)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/summary")
def get_summary():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select metric, value
                from customer_bigin_demo_summary
                order by
                  case metric
                    when 'Sellercloud customers' then 1
                    when 'Bigin active contacts' then 2
                    when 'Email and name match' then 3
                    when 'Email match, name different' then 4
                    when 'Name match, email different' then 5
                    when 'Pending review' then 6
                    else 99
                  end;
            """)
            rows = cur.fetchall() 

    return [
        {"metric": row[0], "value": row[1]}
        for row in rows
    ]

@app.get("/pending-review")
def get_pending_review():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                  sellercloud_customer_id,
                  sellercloud_name,
                  sellercloud_email,
                  sales_man,
                  phone_1
                from customer_bigin_pending_review
                order by sellercloud_name;
            """)
            rows = cur.fetchall()

    return [
        {
            "sellercloud_customer_id": row[0],
            "sellercloud_name": row[1],
            "sellercloud_email": row[2],
            "sales_man": row[3],
            "phone_1": row[4],
        }
        for row in rows
    ]