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
    
    const consoleBridge = `
      <script>
        (function() {
          const originalConsole = {
            log: console.log,
            warn: console.warn,
            error: console.error
          };
          
          function post(type, args) {
            const msg = Array.from(args).map(a => 
              typeof a === 'object' ? JSON.stringify(a) : String(a)
            ).join(' ');
            window.parent.postMessage({ type: 'console', level: type, text: msg }, '*');
          }

          console.log = function() { originalConsole.log.apply(console, arguments); post('log', arguments); };
          console.warn = function() { originalConsole.warn.apply(console, arguments); post('warn', arguments); };
          console.error = function() { originalConsole.error.apply(console, arguments); post('error', arguments); };
          
          window.addEventListener('error', function(e) {
            window.parent.postMessage({ type: 'console', level: 'error', text: e.message }, '*');
          });
        })();
      </script>
    `;

    const srcDoc = `
      <!DOCTYPE html>
      <html>
        <head>
          <style>${css}</style>
        </head>
        <body>
          ${html}
          ${consoleBridge}
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
