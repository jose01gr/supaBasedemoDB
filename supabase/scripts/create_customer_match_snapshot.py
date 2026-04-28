import os
from datetime import datetime

import psycopg
from dotenv import load_dotenv


load_dotenv()

DB_URL = os.getenv("LOCAL_DB_URL")


def main():
    if not DB_URL:
        raise ValueError("Missing LOCAL_DB_URL in .env")

    snapshot_name = f"customer_match_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (snapshot_name,))
            result = cur.fetchone()
            conn.commit()

    print("Snapshot created:")
    print(f"ID: {result[0]}")
    print(f"Name: {result[1]}")
    print(f"Created at: {result[2]}")


if __name__ == "__main__":
    main()