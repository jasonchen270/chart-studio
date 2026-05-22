import { useState } from "react";
import { uploadCsv } from "@/lib/api";

type Props = {
  onUploaded: (csvHash: string, columns: { name: string; dtype: string }[]) => void;
};

export function CsvDrop({ onUploaded }: Props) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function handle(file: File) {
    setBusy(true);
    setErr(null);
    try {
      const res = await uploadCsv(file);
      onUploaded(res.csv_hash, res.columns);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="dropzone"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        const f = e.dataTransfer.files[0];
        if (f) handle(f);
      }}
    >
      <input
        type="file"
        accept=".csv"
        disabled={busy}
        onChange={(e) => e.target.files?.[0] && handle(e.target.files[0])}
      />
      <span>{busy ? "Uploading..." : "Drop a CSV here or click to choose"}</span>
      {err && <span className="error">{err}</span>}
    </div>
  );
}
