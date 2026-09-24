import { useEffect, useRef } from "react";

interface Props {
  html: string;
  css: string;
  js: string;
  className?: string;
}


// Lightweight infinite loop protection (prevents browser freezing)
function protectLoops(code: string) {
  const timeoutSetup = `
    window.__loopStart = Date.now();
    window.__checkLoop = function() {
      if (Date.now() - window.__loopStart > 1500) {
        throw new Error("Infinite loop detected! Execution stopped to prevent browser freeze.");
      }
    };
  `;
  // Naive regex to inject check into common loops
  let safeCode = code.replace(/(while\s*\([^)]+\)\s*\{|for\s*\([^)]+\)\s*\{)/g, "$1 window.__checkLoop(); ");
  return timeoutSetup + safeCode;
}

export function LivePreview({ html, css, js, className }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!iframeRef.current) return;
    
    const srcDoc = `
      <!DOCTYPE html>
      <html>
        <head>
          <style>${css}</style>
        </head>
        <body>
          ${html}
          <script>${protectLoops(js)}<\/script>
        </body>
      </html>
    `;
    
    iframeRef.current.srcdoc = srcDoc;
  }, [html, css, js]);

  return (
    <iframe
      ref={iframeRef}
      className={`w-full h-full border border-gray-300 rounded bg-white ${className || ""}`}
      sandbox="allow-scripts"
    />
  );
}
