import os
import sys
import threading
import csv
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import BytesIO, StringIO

import psycopg
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_jobs

load_dotenv()

DB_URL = os.getenv("LOCAL_DB_URL")

# ── Sync state ────────────────────────────────────────────────────────────────

_sync_state = {
    "sellercloud": {
        "status": "idle",
        "last_completed_at": None,
        "last_records_updated": None,
        "last_error": None,
    },
    "bigin": {
        "status": "idle",
        "last_completed_at": None,
        "last_records_updated": None,
        "last_error": None,
    },
}

_sync_locks = {
    "sellercloud": threading.Lock(),
    "bigin": threading.Lock(),
}


def _log_sync_start(source: str):
    try:
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into sync_log (source, status) values (%s, 'running') returning id",
                    (source,),
                )
                row_id = cur.fetchone()[0]
                conn.commit()
        return row_id
    except Exception:
        return None


def _log_sync_done(log_id, records: int):
    if not log_id:
        return
    try:
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "update sync_log set status='success', completed_at=now(), records_updated=%s where id=%s",
                    (records, log_id),
                )
                conn.commit()
    except Exception:
        pass


def _log_sync_fail(log_id, error: str):
    if not log_id:
        return
    try:
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "update sync_log set status='error', completed_at=now(), error_message=%s where id=%s",
                    (error, log_id),
                )
                conn.commit()
    except Exception:
        pass


def _run_sync_in_background(source: str) -> bool:
    lock = _sync_locks[source]
    if not lock.acquire(blocking=False):
        return False

    _sync_state[source]["status"] = "running"

    def run():
        log_id = None
        try:
            log_id = _log_sync_start(source)
            fn = sync_jobs.sync_sellercloud if source == "sellercloud" else sync_jobs.sync_bigin
            result = fn(DB_URL)
            records = result["records_updated"]
            _sync_state[source].update(
                {
                    "status": "success",
                    "last_completed_at": datetime.now(timezone.utc).isoformat(),
                    "last_records_updated": records,
                    "last_error": None,
                }
            )
            _log_sync_done(log_id, records)
        except Exception as exc:
            err = str(exc)
            _sync_state[source].update(
                {
                    "status": "error",
                    "last_completed_at": datetime.now(timezone.utc).isoformat(),
                    "last_error": err,
                }
            )
            _log_sync_fail(log_id, err)
        finally:
            lock.release()

    threading.Thread(target=run, daemon=True).start()
    return True


# ── App lifecycle ─────────────────────────────────────────────────────────────

_scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _scheduler.add_job(
        lambda: _run_sync_in_background("sellercloud"),
        "interval",
        hours=6,
        id="sellercloud_auto_sync",
    )
    _scheduler.add_job(
        lambda: _run_sync_in_background("bigin"),
        "interval",
        hours=6,
        id="bigin_auto_sync",
    )
    _scheduler.start()
    yield
    _scheduler.shutdown(wait=False)


app = FastAPI(title="Customer Data Hub API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_connection():
    if not DB_URL:
        raise ValueError("Missing LOCAL_DB_URL in .env")
    return psycopg.connect(DB_URL, prepare_threshold=None)


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
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def build_csv_response(filename, headers, rows):
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    stream.seek(0)
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Sync endpoints ────────────────────────────────────────────────────────────

@app.get("/sync/status")
def get_sync_status():
    return _sync_state


@app.post("/sync/sellercloud")
def trigger_sellercloud_sync():
    started = _run_sync_in_background("sellercloud")
    if not started:
        return {"message": "Sync already running", "status": "running"}
    return {"message": "Sync started", "status": "running"}


@app.post("/sync/bigin")
def trigger_bigin_sync():
    started = _run_sync_in_background("bigin")
    if not started:
        return {"message": "Sync already running", "status": "running"}
    return {"message": "Sync started", "status": "running"}


@app.post("/sync/all")
def trigger_all_sync():
    sc_started = _run_sync_in_background("sellercloud")
    bigin_started = _run_sync_in_background("bigin")
    return {
        "sellercloud": "started" if sc_started else "already running",
        "bigin": "started" if bigin_started else "already running",
    }


@app.get("/sync/logs")
def get_sync_logs():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select id, source, started_at, completed_at, records_updated, status, error_message
                from sync_log
                order by started_at desc
                limit 20
            """)
            rows = cur.fetchall()
    return [
        {
            "id": row[0],
            "source": row[1],
            "started_at": row[2],
            "completed_at": row[3],
            "records_updated": row[4],
            "status": row[5],
            "error_message": row[6],
        }
        for row in rows
    ]


# ── Dashboard endpoints ───────────────────────────────────────────────────────

@app.get("/bigin-without-scid")
def get_bigin_without_scid():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select bigin_contact_id, full_name, email, phone, mobile, owner_name
                from bigin_contacts
                where sellercloud_customer_id is null or sellercloud_customer_id = ''
                order by full_name;
            """)
            rows = cur.fetchall()
    return [
        {
            "bigin_contact_id": row[0],
            "full_name": row[1],
            "email": row[2],
            "phone": row[3],
            "mobile": row[4],
            "owner_name": row[5],
        }
        for row in rows
    ]


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
                    when 'SC ID match' then 6
                    when 'Pending review' then 7
                    else 99
                  end;
            """)
            rows = cur.fetchall()
    return [{"metric": row[0], "value": row[1]} for row in rows]


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
                  match_status,
                  bigin_contact_id_scid,
                  bigin_name_scid,
                  bigin_email_scid,
                  bigin_registered_scid
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
            "bigin_contact_id_scid": row[12],
            "bigin_name_scid": row[13],
            "bigin_email_scid": row[14],
            "bigin_registered_scid": row[15],
        }
        for row in rows
    ]


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
    return {"id": row[0], "snapshot_name": row[1], "created_at": row[2]}


# ── Report endpoints ──────────────────────────────────────────────────────────

@app.get("/reports/{report_type}")
def download_report(report_type: str):
    report_queries = {
        "sellercloud-customers": {
            "filename": "sellercloud_customers.xlsx",
            "headers": ["Sellercloud Customer ID", "Customer Name", "Email", "Sales Man", "Phone"],
            "sql": """
                select sellercloud_customer_id, customer_name, email, sales_man, phone_1
                from sellercloud_customers order by customer_name;
            """,
        },
        "bigin-active-contacts": {
            "filename": "bigin_active_contacts.xlsx",
            "headers": ["Bigin Contact ID", "Full Name", "Email", "Phone", "Mobile", "Owner"],
            "sql": """
                select bigin_contact_id, full_name, email, phone, mobile, owner_name
                from bigin_contacts order by full_name;
            """,
        },
        "email-and-name-match": {
            "filename": "email_and_name_match.xlsx",
            "headers": ["Sellercloud Customer ID", "Sellercloud Name", "Sellercloud Email", "Bigin Contact ID", "Bigin Name", "Bigin Email", "Status"],
            "sql": """
                select sellercloud_customer_id, sellercloud_name, sellercloud_email,
                  bigin_contact_id_email, bigin_name_email, bigin_email_match, match_status
                from customer_bigin_comparison_v2
                where match_status = 'EMAIL_AND_NAME_MATCH' order by sellercloud_name;
            """,
        },
        "email-match-name-different": {
            "filename": "email_match_name_different.xlsx",
            "headers": ["Sellercloud Customer ID", "Sellercloud Name", "Sellercloud Email", "Bigin Contact ID", "Bigin Name", "Bigin Email", "Status"],
            "sql": """
                select sellercloud_customer_id, sellercloud_name, sellercloud_email,
                  bigin_contact_id_email, bigin_name_email, bigin_email_match, match_status
                from customer_bigin_comparison_v2
                where match_status = 'EMAIL_MATCH_NAME_DIFFERENT' order by sellercloud_name;
            """,
        },
        "name-match-email-different": {
            "filename": "name_match_email_different.xlsx",
            "headers": ["Sellercloud Customer ID", "Sellercloud Name", "Sellercloud Email", "Bigin Contact ID", "Bigin Name", "Bigin Email", "Status"],
            "sql": """
                select sellercloud_customer_id, sellercloud_name, sellercloud_email,
                  bigin_contact_id_name, bigin_name_match, bigin_email_name_match, match_status
                from customer_bigin_comparison_v2
                where match_status = 'NAME_MATCH_EMAIL_DIFFERENT' order by sellercloud_name;
            """,
        },
        "pending-review": {
            "filename": "pending_review.xlsx",
            "headers": ["Sellercloud Customer ID", "Sellercloud Name", "Sellercloud Email", "Sales Man", "Phone"],
            "sql": """
                select sellercloud_customer_id, sellercloud_name, sellercloud_email, sales_man, phone_1
                from customer_bigin_pending_review order by sellercloud_name;
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

    return build_excel_response(report["filename"], report["headers"], rows)


@app.get("/excel/pending-review.csv")
def excel_pending_review_csv():
    headers = ["sellercloud_customer_id", "sellercloud_name", "sellercloud_email", "sales_man", "phone_1"]
    sql = """
        select sellercloud_customer_id, sellercloud_name, sellercloud_email, sales_man, phone_1
        from customer_bigin_pending_review order by sellercloud_name;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return build_csv_response("pending_review.csv", headers, rows)


@app.get("/excel/{report_type}.csv")
def excel_dynamic_report_csv(report_type: str):
    report_queries = {
        "sellercloud-customers": {
            "filename": "sellercloud_customers.csv",
            "headers": ["sellercloud_customer_id", "customer_name", "email", "sales_man", "phone_1"],
            "sql": "select sellercloud_customer_id, customer_name, email, sales_man, phone_1 from sellercloud_customers order by customer_name;",
        },
        "bigin-active-contacts": {
            "filename": "bigin_active_contacts.csv",
            "headers": ["bigin_contact_id", "full_name", "email", "phone", "mobile", "owner_name"],
            "sql": "select bigin_contact_id, full_name, email, phone, mobile, owner_name from bigin_contacts order by full_name;",
        },
        "email-and-name-match": {
            "filename": "email_and_name_match.csv",
            "headers": ["sellercloud_customer_id", "sellercloud_name", "sellercloud_email", "bigin_contact_id", "bigin_name", "bigin_email", "match_status"],
            "sql": """
                select sellercloud_customer_id, sellercloud_name, sellercloud_email,
                  bigin_contact_id_email, bigin_name_email, bigin_email_match, match_status
                from customer_bigin_comparison_v2
                where match_status = 'EMAIL_AND_NAME_MATCH' order by sellercloud_name;
            """,
        },
        "email-match-name-different": {
            "filename": "email_match_name_different.csv",
            "headers": ["sellercloud_customer_id", "sellercloud_name", "sellercloud_email", "bigin_contact_id", "bigin_name", "bigin_email", "match_status"],
            "sql": """
                select sellercloud_customer_id, sellercloud_name, sellercloud_email,
                  bigin_contact_id_email, bigin_name_email, bigin_email_match, match_status
                from customer_bigin_comparison_v2
                where match_status = 'EMAIL_MATCH_NAME_DIFFERENT' order by sellercloud_name;
            """,
        },
        "name-match-email-different": {
            "filename": "name_match_email_different.csv",
            "headers": ["sellercloud_customer_id", "sellercloud_name", "sellercloud_email", "bigin_contact_id", "bigin_name", "bigin_email", "match_status"],
            "sql": """
                select sellercloud_customer_id, sellercloud_name, sellercloud_email,
                  bigin_contact_id_name, bigin_name_match, bigin_email_name_match, match_status
                from customer_bigin_comparison_v2
                where match_status = 'NAME_MATCH_EMAIL_DIFFERENT' order by sellercloud_name;
            """,
        },
        "pending-review": {
            "filename": "pending_review.csv",
            "headers": ["sellercloud_customer_id", "sellercloud_name", "sellercloud_email", "sales_man", "phone_1"],
            "sql": "select sellercloud_customer_id, sellercloud_name, sellercloud_email, sales_man, phone_1 from customer_bigin_pending_review order by sellercloud_name;",
        },
        "comparison-results": {
            "filename": "comparison_results.csv",
            "headers": ["sellercloud_customer_id", "sellercloud_name", "sellercloud_email", "sales_man", "phone_1", "bigin_name", "bigin_email", "match_status"],
            "sql": """
                select sellercloud_customer_id, sellercloud_name, sellercloud_email, sales_man, phone_1,
                  coalesce(bigin_name_email, bigin_name_match) as bigin_name,
                  coalesce(bigin_email_match, bigin_email_name_match) as bigin_email,
                  match_status
                from customer_bigin_comparison_v2
                order by match_status, sellercloud_name;
            """,
        },
        "snapshots": {
            "filename": "snapshots.csv",
            "headers": ["id", "snapshot_name", "total_sellercloud_customers", "total_bigin_contacts", "email_and_name_match", "email_match_name_different", "name_match_email_different", "pending_review", "created_at"],
            "sql": "select id, snapshot_name, total_sellercloud_customers, total_bigin_contacts, email_and_name_match, email_match_name_different, name_match_email_different, pending_review, created_at from customer_match_snapshots order by created_at desc;",
        },
    }

    if report_type not in report_queries:
        return {"error": "Invalid report type"}

    report = report_queries[report_type]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(report["sql"])
            rows = cur.fetchall()

    return build_csv_response(report["filename"], report["headers"], rows)
