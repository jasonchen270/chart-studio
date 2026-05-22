# Supabase setup

Two migrations:

1. `0001_charts.sql`: table, index, updated_at trigger.
2. `0002_charts_rls.sql`: RLS policies scoped to `auth.uid() = owner_id`.

Apply with the Supabase CLI:

```bash
supabase db push
```

Or copy/paste each file into the SQL editor in order.

## Verifying RLS

After applying, sign in two test users in two browsers and confirm:
- User A can list their own charts but not User B's.
- User A's POST with `owner_id` set to User B's id is rejected by `charts_insert_own`.
- Disabling JS auth (anon client without a session) returns an empty list, not an error.
