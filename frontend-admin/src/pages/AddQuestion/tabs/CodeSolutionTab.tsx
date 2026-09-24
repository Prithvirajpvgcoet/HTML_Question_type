import { useState, useEffect, useRef } from "react";
import { api } from "../../../api/client";
import { CodeEditor } from "../../../components/CodeEditor";
import { LivePreview } from "../../../components/LivePreview";

export function CodeSolutionTab({ questionId, onBack, onNext }: { questionId: string, onBack: () => void, onNext: () => void }) {
  const [html, setHtml] = useState("<!-- Your HTML -->\n<div id=\"box\"></div>");
  const [css, setCss] = useState("/* Your CSS */\n#box { width: 100px; height: 100px; background: red; }");
  const [js, setJs] = useState("// Your JS");
  const [preview, setPreview] = useState({ html: "", css: "", js: "" });
  
  const isInitialMount = useRef(true);

  // Fetch initial data
  useEffect(() => {
    if (!questionId) return;
    
    api.get(`/questions/${questionId}`).then(res => {
      setHtml(res.data.reference_html || "");
      setCss(res.data.reference_css || "");
      setJs(res.data.reference_js || "");
      setPreview({
        html: res.data.reference_html || "",
        css: res.data.reference_css || "",
        js: res.data.reference_js || ""
      });
    });
  }, [questionId]);

  // Handle auto-updating preview (debounced)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    const timer = setTimeout(() => {
      setPreview({ html, css, js });
    }, 1000);
    return () => clearTimeout(timer);
  }, [html, css, js]);

  const handleSaveAndNext = async () => {
    try {
      await api.put(`/questions/${questionId}/code-solution`, {
        reference_html: html,
        reference_css: css,
        reference_js: js
      });
      onNext();
    } catch (e: any) {
      if (e.response?.status === 400 || e.response?.status === 409) {
        alert("Cannot save: " + (e.response?.data?.detail?.message || e.response?.data?.detail));
      } else {
        alert("Failed to save code solution");
      }
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-sm">
      <div className="flex-1 overflow-auto p-8 pb-32">
        <div className="mb-6">
          <h2 className="text-xl font-bold text-gray-800">Code Solution</h2>
          <p className="text-gray-500 text-sm mt-1">Write the reference solution and compile it against your assertions.</p>
        </div>

        <div className="grid grid-cols-2 gap-8 h-[650px]">
          <div className="flex flex-col border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
            <div className="bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700 border-b border-gray-200">
              Code Editor
            </div>
            <div className="flex-1 flex flex-col overflow-y-auto">
              <div className="flex flex-col min-h-[200px] flex-1 border-b border-gray-200">
                <div className="bg-gray-200/60 px-3 py-1.5 text-xs font-bold text-gray-600 uppercase tracking-wider flex items-center justify-between">
                  <span>index.html</span>
                </div>
                <div className="flex-1 relative overflow-hidden bg-white"><CodeEditor language="html" value={html} onChange={(v) => setHtml(v || "")} /></div>
              </div>
              <div className="flex flex-col min-h-[200px] flex-1 border-b border-gray-200">
                <div className="bg-gray-200/60 px-3 py-1.5 text-xs font-bold text-gray-600 uppercase tracking-wider flex items-center justify-between">
                  <span>styles.css</span>
                </div>
                <div className="flex-1 relative overflow-hidden bg-white"><CodeEditor language="css" value={css} onChange={(v) => setCss(v || "")} /></div>
              </div>
              <div className="flex flex-col min-h-[200px] flex-1">
                <div className="bg-gray-200/60 px-3 py-1.5 text-xs font-bold text-gray-600 uppercase tracking-wider flex items-center justify-between">
                  <span>script.js</span>
                </div>
                <div className="flex-1 relative overflow-hidden bg-white"><CodeEditor language="javascript" value={js} onChange={(v) => setJs(v || "")} /></div>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col border border-gray-200 rounded-lg overflow-hidden relative">
            <div className="bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700 border-b border-gray-200">
              Live Preview
            </div>
            <div className="flex-1 bg-white relative">
              <LivePreview html={preview.html} css={preview.css} js={preview.js} />
            </div>
          </div>
        </div>

        {/* Removing the test cases section which will now live in ReviewTab */}
      </div>

      {/* Floating Bottom Bar */}
      <div className="fixed bottom-0 left-20 right-0 bg-white border-t border-gray-200 p-4 flex justify-between px-8 z-40 shadow-[0_-2px_10px_rgba(0,0,0,0.05)]">
        <button 
          onClick={onBack}
          className="border border-blue-400 text-blue-500 px-8 py-2 rounded-full font-medium hover:bg-blue-50"
        >
          Back
        </button>
        <div className="flex gap-4 items-center">
          <button 
            onClick={handleSaveAndNext}
            className="bg-imocha-orange text-white px-8 py-2 rounded-full font-medium shadow-sm hover:bg-orange-600 transition-all"
          >
            Save Code Solution
          </button>
        </div>
      </div>
    </div>
  );
}
