import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";

export function SignIn() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    if (error) setError(error.message);
    else setSent(true);
  }

  // If a session already exists (returning user), skip the form.
  supabase.auth.getSession().then(({ data }) => {
    if (data.session) nav("/", { replace: true });
  });

  return (
    <div className="centered">
      <form onSubmit={submit} className="signin-card">
        <h1>Chart Studio</h1>
        <p>Sign in with a magic link.</p>
        {sent ? (
          <p>Check your inbox for {email}.</p>
        ) : (
          <>
            <input
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <button type="submit">Send link</button>
            {error && <p className="error">{error}</p>}
          </>
        )}
      </form>
    </div>
  );
}
