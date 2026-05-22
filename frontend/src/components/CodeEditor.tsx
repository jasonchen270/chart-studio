import Editor from "@monaco-editor/react";

type Props = {
  value: string;
  onChange: (v: string) => void;
  onRun: () => void;
};

export function CodeEditor({ value, onChange, onRun }: Props) {
  return (
    <div className="editor-wrap">
      <div className="editor-toolbar">
        <span>generated.py</span>
        <button onClick={onRun}>Run ⌘↵</button>
      </div>
      <Editor
        height="100%"
        defaultLanguage="python"
        value={value}
        theme="vs-dark"
        onChange={(v) => onChange(v ?? "")}
        onMount={(editor, monaco) => {
          editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, onRun);
        }}
        options={{
          minimap: { enabled: false },
          fontSize: 13,
          tabSize: 4,
          scrollBeyondLastLine: false,
        }}
      />
    </div>
  );
}
