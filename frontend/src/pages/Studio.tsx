import { useEffect, useState } from "react";

import { ChartPreview } from "@/components/ChartPreview";
import { CodeEditor } from "@/components/CodeEditor";
import { CsvDrop } from "@/components/CsvDrop";
import { SplitPane } from "@/components/SplitPane";
import { TraceLog } from "@/components/TraceLog";
import { useGenerateStream } from "@/hooks/useGenerateStream";
import { executeCode, saveChart } from "@/lib/api";
import { DEMO_MODE, supabase } from "@/lib/supabase";

type Column = { name: string; dtype: string };

export function Studio() {
  const [csvHash, setCsvHash] = useState<string | null>(null);
  const [columns, setColumns] = useState<Column[]>([]);
  const [prompt, setPrompt] = useState("");
  const [figure, setFigure] = useState<{ data: unknown[]; layout: object } | null>(null);
  const [execError, setExecError] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  const { trace, code, running, run, setCode } = useGenerateStream();

  async function onGenerate() {
    if (!csvHash || !prompt.trim()) return;
    await run(csvHash, prompt);
  }

  async function onRunCode() {
    if (!csvHash || !code.trim()) return;
    setExecuting(true);
    setExecError(null);
    try {
      const res = await executeCode(csvHash, code);
      if (res.ok && res.figure) {
        setFigure(res.figure as { data: unknown[]; layout: object });
      } else {
        setExecError(res.error ?? "execution failed");
      }
    } catch (e) {
      setExecError(e instanceof Error ? e.message : String(e));
    } finally {
      setExecuting(false);
    }
  }

  // Auto-run the generated code once streaming finishes. This saves a click on
  // the happy path while still leaving the editor available for tweaks.
  useEffect(() => {
    if (code && !running && csvHash) onRunCode();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, running]);

  async function onSave() {
    if (!figure || !csvHash) return;
    if (!DEMO_MODE) {
      await saveChart({
        title: prompt.slice(0, 80) || "Untitled chart",
        prompt,
        code,
        csv_hash: csvHash,
        figure,
      });
    }
    setSavedAt(new Date());
  }

  return (
    <div className="studio">
      <header>
        <h1>Chart Studio</h1>
        <div className="header-right">
          {savedAt && <span className="saved">Saved {savedAt.toLocaleTimeString()}</span>}
          {DEMO_MODE ? (
            <span className="saved">demo mode</span>
          ) : (
            <button onClick={() => supabase.auth.signOut()}>Sign out</button>
          )}
        </div>
      </header>

      <section className="setup">
        <CsvDrop
          onUploaded={(hash, cols) => {
            setCsvHash(hash);
            setColumns(cols);
          }}
        />
        {csvHash && (
          <div className="schema">
            <strong>Columns:</strong>{" "}
            {columns.map((c) => (
              <span key={c.name} className="pill">
                {c.name} <em>{c.dtype}</em>
              </span>
            ))}
          </div>
        )}
        <div className="prompt-row">
          <input
            placeholder="e.g. monthly revenue trend coloured by region"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onGenerate()}
            disabled={!csvHash}
          />
          <button onClick={onGenerate} disabled={!csvHash || running}>
            {running ? "Generating..." : "Generate"}
          </button>
          <button onClick={onSave} disabled={!figure}>Save</button>
        </div>
      </section>

      <SplitPane
        left={
          <div className="left-stack">
            <CodeEditor value={code} onChange={setCode} onRun={onRunCode} />
            <TraceLog events={trace} />
          </div>
        }
        right={<ChartPreview figure={figure} error={execError} loading={executing} />}
      />
    </div>
  );
}
