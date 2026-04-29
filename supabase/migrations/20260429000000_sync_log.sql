create table if not exists sync_log (
    id bigserial primary key,
    source text not null,
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    records_updated integer,
    status text not null default 'running',
    error_message text
);

create index if not exists sync_log_source_started_idx on sync_log (source, started_at desc);
