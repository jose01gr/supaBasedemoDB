create table if not exists sellercloud_customers (
    sellercloud_customer_id text primary key,
    first_name text,
    last_name text,
    customer_name text,
    email text,
    phone text,
    corporate_name text,
    customer_type text,
    city text,
    state text,
    postal_code text,
    country text,
    address_line_1 text,
    address_line_2 text,
    raw_json jsonb,
    extracted_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_sellercloud_customers_email
on sellercloud_customers (email);

create index if not exists idx_sellercloud_customers_corporate_name
on sellercloud_customers (corporate_name);