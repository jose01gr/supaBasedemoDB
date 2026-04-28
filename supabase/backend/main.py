import os
from io import BytesIO

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openpyxl import Workbook



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

def build_excel_response(filename, headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Report"

    sheet.append(headers)

    for row in rows:
        sheet.append(row)

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )

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

@app.get("/snapshots")
def get_snapshots():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                  id,
                  snapshot_name,
                  total_sellercloud_customers,
                  total_bigin_contacts,
                  email_and_name_match,
                  email_match_name_different,
                  name_match_email_different,
                  pending_review,
                  created_at
                from customer_match_snapshots
                order by created_at desc;
            """)
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "snapshot_name": row[1],
            "total_sellercloud_customers": row[2],
            "total_bigin_contacts": row[3],
            "email_and_name_match": row[4],
            "email_match_name_different": row[5],
            "name_match_email_different": row[6],
            "pending_review": row[7],
            "created_at": row[8],
        }
        for row in rows
    ]

@app.get("/comparison-results")
def get_comparison_results():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                  sellercloud_customer_id,
                  sellercloud_name,
                  sellercloud_email,
                  sales_man,
                  phone_1,
                  bigin_contact_id_email,
                  bigin_name_email,
                  bigin_email_match,
                  bigin_contact_id_name,
                  bigin_name_match,
                  bigin_email_name_match,
                  match_status
                from customer_bigin_comparison_v2
                order by match_status, sellercloud_name;
            """)
            rows = cur.fetchall()

    return [
        {
            "sellercloud_customer_id": row[0],
            "sellercloud_name": row[1],
            "sellercloud_email": row[2],
            "sales_man": row[3],
            "phone_1": row[4],
            "bigin_contact_id_email": row[5],
            "bigin_name_email": row[6],
            "bigin_email_match": row[7],
            "bigin_contact_id_name": row[8],
            "bigin_name_match": row[9],
            "bigin_email_name_match": row[10],
            "match_status": row[11],
        }
        for row in rows
    ]

@app.get("/reports/{report_type}")
def download_report(report_type: str):
    report_queries = {
        "sellercloud-customers": {
            "filename": "sellercloud_customers.xlsx",
            "headers": [
                "Sellercloud Customer ID",
                "Customer Name",
                "Email",
                "Sales Man",
                "Phone",
            ],
            "sql": """
                select
                  sellercloud_customer_id,
                  customer_name,
                  email,
                  sales_man,
                  phone_1
                from sellercloud_customers
                order by customer_name;
            """,
        },
        "bigin-active-contacts": {
            "filename": "bigin_active_contacts.xlsx",
            "headers": [
                "Bigin Contact ID",
                "Full Name",
                "Email",
                "Phone",
                "Mobile",
                "Owner",
            ],
            "sql": """
                select
                  bigin_contact_id,
                  full_name,
                  email,
                  phone,
                  mobile,
                  owner_name
                from bigin_contacts
                order by full_name;
            """,
        },
        "email-and-name-match": {
            "filename": "email_and_name_match.xlsx",
            "headers": [
                "Sellercloud Customer ID",
                "Sellercloud Name",
                "Sellercloud Email",
                "Bigin Contact ID",
                "Bigin Name",
                "Bigin Email",
                "Status",
            ],
            "sql": """
                select
                  sellercloud_customer_id,
                  sellercloud_name,
                  sellercloud_email,
                  bigin_contact_id_email,
                  bigin_name_email,
                  bigin_email_match,
                  match_status
                from customer_bigin_comparison_v2
                where match_status = 'EMAIL_AND_NAME_MATCH'
                order by sellercloud_name;
            """,
        },
        "email-match-name-different": {
            "filename": "email_match_name_different.xlsx",
            "headers": [
                "Sellercloud Customer ID",
                "Sellercloud Name",
                "Sellercloud Email",
                "Bigin Contact ID",
                "Bigin Name",
                "Bigin Email",
                "Status",
            ],
            "sql": """
                select
                  sellercloud_customer_id,
                  sellercloud_name,
                  sellercloud_email,
                  bigin_contact_id_email,
                  bigin_name_email,
                  bigin_email_match,
                  match_status
                from customer_bigin_comparison_v2
                where match_status = 'EMAIL_MATCH_NAME_DIFFERENT'
                order by sellercloud_name;
            """,
        },
        "name-match-email-different": {
            "filename": "name_match_email_different.xlsx",
            "headers": [
                "Sellercloud Customer ID",
                "Sellercloud Name",
                "Sellercloud Email",
                "Bigin Contact ID",
                "Bigin Name",
                "Bigin Email",
                "Status",
            ],
            "sql": """
                select
                  sellercloud_customer_id,
                  sellercloud_name,
                  sellercloud_email,
                  bigin_contact_id_name,
                  bigin_name_match,
                  bigin_email_name_match,
                  match_status
                from customer_bigin_comparison_v2
                where match_status = 'NAME_MATCH_EMAIL_DIFFERENT'
                order by sellercloud_name;
            """,
        },
        "pending-review": {
            "filename": "pending_review.xlsx",
            "headers": [
                "Sellercloud Customer ID",
                "Sellercloud Name",
                "Sellercloud Email",
                "Sales Man",
                "Phone",
            ],
            "sql": """
                select
                  sellercloud_customer_id,
                  sellercloud_name,
                  sellercloud_email,
                  sales_man,
                  phone_1
                from customer_bigin_pending_review
                order by sellercloud_name;
            """,
        },
    }

    if report_type not in report_queries:
        return {"error": "Invalid report type"}

    report = report_queries[report_type]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(report["sql"])
            rows = cur.fetchall()

    return build_excel_response(
        report["filename"],
        report["headers"],
        rows,
    )

@app.post("/snapshots")
def create_snapshot():
    snapshot_name = "dashboard_customer_match_snapshot"

    sql = """
    insert into customer_match_snapshots (
      snapshot_name,
      total_sellercloud_customers,
      total_bigin_contacts,
      email_and_name_match,
      email_match_name_different,
      name_match_email_different,
      pending_review
    )
    select
      %s,
      (select count(*) from sellercloud_customers),
      (select count(*) from bigin_contacts),
      (select count(*) from customer_bigin_comparison_v2 where match_status = 'EMAIL_AND_NAME_MATCH'),
      (select count(*) from customer_bigin_comparison_v2 where match_status = 'EMAIL_MATCH_NAME_DIFFERENT'),
      (select count(*) from customer_bigin_comparison_v2 where match_status = 'NAME_MATCH_EMAIL_DIFFERENT'),
      (select count(*) from customer_bigin_pending_review)
    returning id, snapshot_name, created_at;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (snapshot_name,))
            row = cur.fetchone()
            conn.commit()

    return {
        "id": row[0],
        "snapshot_name": row[1],
        "created_at": row[2],
    }