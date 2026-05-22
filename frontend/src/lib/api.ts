import { getAccessToken } from "./supabase";

const BASE = import.meta.env.VITE_API_URL ?? "";

async function authHeaders(): Promise<HeadersInit> {
  const token = await getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function uploadCsv(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${BASE}/api/upload`, {
    method: "POST",
    headers: await authHeaders(),
    body: fd,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{
    csv_hash: string;
    rows: number;
    columns: { name: string; dtype: string }[];
  }>;
}

export async function executeCode(csvHash: string, code: string) {
  const res = await fetch(`${BASE}/api/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify({ csv_hash: csvHash, code }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{
    ok: boolean;
    figure: object | null;
    error: string | null;
    duration_ms: number;
  }>;
}

export async function saveChart(payload: {
  title: string;
  prompt: string;
  code: string;
  csv_hash: string;
  figure: object;
}) {
  const res = await fetch(`${BASE}/api/charts`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
