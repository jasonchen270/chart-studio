import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { DEMO_MODE, supabase } from "@/lib/supabase";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<"loading" | "authed" | "guest">(
    DEMO_MODE ? "authed" : "loading",
  );

  useEffect(() => {
    if (DEMO_MODE) return;
    supabase.auth.getSession().then(({ data }) => {
      setState(data.session ? "authed" : "guest");
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setState(session ? "authed" : "guest");
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  if (state === "loading") return <div className="centered">Loading...</div>;
  if (state === "guest") return <Navigate to="/signin" replace />;
  return <>{children}</>;
}
