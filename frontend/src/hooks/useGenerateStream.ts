import { useCallback, useRef, useState } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";

import { getAccessToken } from "@/lib/supabase";

export type TraceEvent =
  | { type: "thought"; text: string }
  | { type: "tool_call"; name: string; input: Record<string, unknown> }
  | { type: "tool_result"; name: string; result: unknown }
  | { type: "code"; code: string }
  | { type: "done"; code: string | null; stop_reason: string };

const BASE = import.meta.env.VITE_API_URL ?? "";

// `fetch`-based EventSource so we can attach an Authorization header, since the
// browser-native EventSource doesn't allow custom headers.
export function useGenerateStream() {
  const [trace, setTrace] = useState<TraceEvent[]>([]);
  const [code, setCode] = useState<string>("");
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async (csvHash: string, prompt: string) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setTrace([]);
    setCode("");
    setRunning(true);

    const token = await getAccessToken();
    try {
      await fetchEventSource(`${BASE}/api/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ csv_hash: csvHash, prompt }),
        signal: ctrl.signal,
        onmessage(ev) {
          const parsed = JSON.parse(ev.data) as TraceEvent;
          setTrace((prev) => [...prev, parsed]);
          if (parsed.type === "code") setCode(parsed.code);
          if (parsed.type === "done" && parsed.code) setCode(parsed.code);
        },
        onerror(err) {
          // Throw to break the auto-retry that fetch-event-source does by default;
          // we'd rather surface the error to the user than silently reconnect.
          throw err;
        },
      });
    } finally {
      setRunning(false);
    }
  }, []);

  const cancel = useCallback(() => abortRef.current?.abort(), []);

  return { trace, code, running, run, cancel, setCode };
}
