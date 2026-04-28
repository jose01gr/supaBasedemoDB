create table if not exists bigin_contacts (
    bigin_contact_id text primary key,
    sellercloud_customer_id text,
    first_name text,
    last_name text,
    full_name text,
    email text,
    phone text,
    mobile text,
    owner_name text,
    owner_email text,
    tags jsonb,
    raw_json jsonb,
    extracted_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_bigin_contacts_email
on bigin_contacts (email);

create index if not exists idx_bigin_contacts_sellercloud_customer_id
on bigin_contacts (sellercloud_customer_id);