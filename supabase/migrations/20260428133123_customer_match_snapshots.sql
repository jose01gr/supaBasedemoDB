create table if not exists customer_match_snapshots (
    id bigserial primary key,
    snapshot_name text not null,
    total_sellercloud_customers integer not null,
    total_bigin_contacts integer not null,
    email_and_name_match integer not null,
    email_match_name_different integer not null,
    name_match_email_different integer not null,
    pending_review integer not null,
    created_at timestamptz not null default now()
);