import Editor from "@monaco-editor/react";

interface Props {
  language: "html" | "css" | "javascript";
  value: string;
  onChange: (val: string | undefined) => void;
  height?: string;
  theme?: string;
}

export function CodeEditor({ language, value, onChange, height = "400px", theme = "vs" }: Props) {
  return (
    <div style={{ height }} className="overflow-hidden">
      <Editor
        height="100%"
        language={language}
        value={value}
        onChange={onChange}
        theme={theme}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          wordWrap: "on",
          padding: { top: 12, bottom: 12 },
        }}
      />
    </div>
  );
}
