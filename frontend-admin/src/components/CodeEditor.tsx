import Editor from "@monaco-editor/react";

interface Props {
  language: "html" | "css" | "javascript";
  value: string;
  onChange: (val: string | undefined) => void;
  height?: string;
}

export function CodeEditor({ language, value, onChange, height = "400px" }: Props) {
  return (
    <div className={`border border-gray-300 rounded overflow-hidden`} style={{ height }}>
      <Editor
        height="100%"
        language={language}
        value={value}
        onChange={onChange}
        theme="light"
        options={{ minimap: { enabled: false }, fontSize: 14 }}
      />
    </div>
  );
}
