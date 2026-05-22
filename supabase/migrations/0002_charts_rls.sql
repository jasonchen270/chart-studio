-- Row-level security on charts. The policies are deliberately named so it's
-- obvious in `\d charts` what each one does. auth.uid() is the Supabase
-- helper that pulls the user id out of the JWT claim. RLS treats anonymous
-- requests as auth.uid() IS NULL, which fails every policy below.

alter table public.charts enable row level security;

-- Force RLS even for the service role? No. The API uses the service role
-- key and intentionally filters by owner_id at the application layer for
-- list/delete. Leaving FORCE off keeps server-side admin tasks possible.
-- But every policy below scopes to auth.uid(), so anon/authenticated clients
-- (i.e. the browser via the anon key) can ONLY see their own rows.

create policy "charts_select_own"
    on public.charts for select
    using (auth.uid() = owner_id);

create policy "charts_insert_own"
    on public.charts for insert
    with check (auth.uid() = owner_id);

create policy "charts_update_own"
    on public.charts for update
    using (auth.uid() = owner_id)
    with check (auth.uid() = owner_id);

create policy "charts_delete_own"
    on public.charts for delete
    using (auth.uid() = owner_id);
