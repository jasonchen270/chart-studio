import { createClient } from "@supabase/supabase-js";

export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "1";

// In demo mode we never call Supabase, but the import must still resolve to
// something with the right shape so existing call sites (signOut, etc.)
// don't crash. The placeholder URL is never contacted because RequireAuth
// short-circuits.
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL || "https://demo.invalid",
  import.meta.env.VITE_SUPABASE_ANON_KEY || "demo-anon-key",
);

export async function getAccessToken(): Promise<string | null> {
  if (DEMO_MODE) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
