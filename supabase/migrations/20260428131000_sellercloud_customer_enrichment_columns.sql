alter table sellercloud_customers
add column if not exists company_id integer,
add column if not exists account_manager_id integer,
add column if not exists sales_man text,
add column if not exists comment text,
add column if not exists phone_1 text,
add column if not exists phone_2 text,
add column if not exists mobile text,
add column if not exists customer_groups jsonb,
add column if not exists addresses jsonb,
add column if not exists custom_columns jsonb,
add column if not exists enriched_at timestamptz;