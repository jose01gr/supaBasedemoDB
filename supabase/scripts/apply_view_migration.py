import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("LOCAL_DB_URL")

SQL = """
create index if not exists idx_sc_email_lower
  on sellercloud_customers (lower(trim(email)));

create index if not exists idx_sc_name_lower
  on sellercloud_customers (lower(trim(customer_name)));

create index if not exists idx_bigin_email_lower
  on bigin_contacts (lower(trim(email)));

create index if not exists idx_bigin_name_lower
  on bigin_contacts (lower(trim(full_name)));

create or replace view customer_bigin_comparison_v2 as
select
  sc.sellercloud_customer_id,
  sc.customer_name as sellercloud_name,
  sc.email as sellercloud_email,
  sc.sales_man,
  sc.phone_1,
  bc_email.bigin_contact_id as bigin_contact_id_email,
  bc_email.full_name as bigin_name_email,
  bc_email.email as bigin_email_match,
  bc_name.bigin_contact_id as bigin_contact_id_name,
  bc_name.full_name as bigin_name_match,
  bc_name.email as bigin_email_name_match,
  case
    when bc_scid.bigin_contact_id is not null
      then 'SC_ID_MATCH'
    when bc_email.bigin_contact_id is not null
      and lower(trim(sc.customer_name)) = lower(trim(bc_email.full_name))
      then 'EMAIL_AND_NAME_MATCH'
    when bc_email.bigin_contact_id is not null
      and lower(trim(sc.customer_name)) <> lower(trim(bc_email.full_name))
      then 'EMAIL_MATCH_NAME_DIFFERENT'
    when bc_email.bigin_contact_id is null
      and bc_name.bigin_contact_id is not null
      then 'NAME_MATCH_EMAIL_DIFFERENT'
    else 'NO_MATCH_IN_BIGIN'
  end as match_status,
  bc_scid.bigin_contact_id as bigin_contact_id_scid,
  bc_scid.full_name as bigin_name_scid,
  bc_scid.email as bigin_email_scid,
  coalesce(
    bc_scid.sellercloud_customer_id,
    bc_email.sellercloud_customer_id,
    bc_name.sellercloud_customer_id
  ) as bigin_registered_scid
from sellercloud_customers sc
left join bigin_contacts bc_email
  on lower(trim(sc.email)) = lower(trim(bc_email.email))
left join bigin_contacts bc_name
  on lower(trim(sc.customer_name)) = lower(trim(bc_name.full_name))
left join bigin_contacts bc_scid
  on sc.sellercloud_customer_id = bc_scid.sellercloud_customer_id
     and bc_scid.sellercloud_customer_id is not null
     and bc_scid.sellercloud_customer_id <> '';
"""

print("Conectando a la base de datos...")
with psycopg.connect(DB_URL, prepare_threshold=None) as conn:
    conn.autocommit = True
    with conn.cursor() as cur:
        for statement in SQL.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                print(f"Ejecutando: {stmt[:60]}...")
                cur.execute(stmt)
    print("Migracion aplicada exitosamente.")
