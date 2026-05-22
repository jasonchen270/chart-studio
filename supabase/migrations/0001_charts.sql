-- Saved charts. The figure column stores the Plotly JSON so reopening a
-- saved chart doesn't require re-running the user's Python.

create extension if not exists "uuid-ossp";

create table public.charts (
    id          uuid primary key default uuid_generate_v4(),
    owner_id    uuid not null references auth.users (id) on delete cascade,
    title       text not null,
    prompt      text not null,
    code        text not null,
    csv_hash    text not null,
    figure      jsonb not null,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create index charts_owner_created_idx
    on public.charts (owner_id, created_at desc);

-- updated_at maintenance
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

create trigger charts_set_updated_at
    before update on public.charts
    for each row execute function public.set_updated_at();
