import { useState, useEffect, useRef } from "react";
import { api } from "../../../api/client";
import { RichTextEditor } from "../../../components/RichTextEditor";
import { CodeEditor } from "../../../components/CodeEditor";

export function QuestionTab({ questionId, onNext }: { questionId?: string | null, onNext: (id: string) => void }) {
  const [title, setTitle] = useState("Animations: Shapes");
  const [desc, setDesc] = useState("<p>Build a webpage with a rectangle...</p>");
  const [purpose, setPurpose] = useState("");
  const [codeStubType, setCodeStubType] = useState("stub");
  const [activeStubTab, setActiveStubTab] = useState<"html"|"css"|"javascript">("html");
  
  const [stubHtml, setStubHtml] = useState("");
  const [stubCss, setStubCss] = useState("");
  const [stubJs, setStubJs] = useState("");

  const [loading, setLoading] = useState(false);

  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const isInitialMount = useRef(true);

  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    
    if (!questionId) return; // Only auto-save if editing existing question

    const timer = setTimeout(async () => {
      try {
        await api.put(`/questions/${questionId}`, {
          title: title || "Untitled Question",
          description_html: desc,
          purpose: purpose,
          question_type: codeStubType,
          starter_html: stubHtml,
          starter_css: stubCss,
          starter_js: stubJs,
          question_bank_name: "HTML/CSS/JS Coding (Shared)"
        });
        setLastSaved(new Date());
      } catch(e) {
        console.error("Autosave failed", e);
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [title, desc, purpose, codeStubType, stubHtml, stubCss, stubJs, questionId]);


  useEffect(() => {
    if (questionId) {
      api.get(`/questions/${questionId}`).then(res => {
        const q = res.data;
        setTitle(q.title);
        setDesc(q.description_html);
        if (q.purpose) setPurpose(q.purpose);
        if (q.question_type) setCodeStubType(q.question_type);
        setStubHtml(q.starter_html || "");
        setStubCss(q.starter_css || "");
        setStubJs(q.starter_js || "");
      }).catch(e => console.error(e));
    }
  }, [questionId]);


  const handleSave = async () => {
    setLoading(true);
    try {
      let resId = questionId;
      const payload = {
        title: title || "Untitled Question",
        description_html: desc,
        purpose: purpose,
        question_bank_name: "HTML/CSS/JS Coding (Shared)"
      };

      if (questionId) {
        await api.put(`/questions/${questionId}`, payload);
      } else {
        const { data } = await api.post("/questions", payload);
        resId = data.id;
      }
      onNext(resId!);
    } catch (e) {
      alert("Error saving question. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white pb-20">
      <div className="border-b border-gray-200 px-8 py-4 mb-8">
        <h2 className="text-lg font-bold text-[#2A3547]">Add Questions for HTML/CSS/JS</h2>
        {lastSaved && <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded ml-3">Draft saved {lastSaved.toLocaleTimeString()}</span>}
      </div>
      
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* Question Type */}
        <div className="flex">
          <div className="w-48 text-right pr-6 text-[13px] font-semibold text-gray-700 pt-2">
            Question Type:
          </div>
          <div className="flex-1 text-[13px] text-gray-800 pt-2">
            HTML/CSS/JS
          </div>
        </div>

        {/* Question Bank Name */}
        <div className="flex">
          <div className="w-48 text-right pr-6 text-[13px] font-semibold text-gray-700 pt-2">
            Question Bank Name:
          </div>
          <div className="flex-1 text-[13px] text-gray-800 pt-2">
            HTML/CSS/JS Coding (Manual Evaluation) (Shared)
          </div>
        </div>

        {/* Question Title (Not in screenshot but needed for backend) */}
        <div className="flex">
          <div className="w-48 text-right pr-6 text-[13px] font-semibold text-gray-700 pt-2">
            Question Title:
          </div>
          <div className="flex-1">
            <input 
              className="w-full border border-gray-300 rounded p-2 text-sm focus:outline-none focus:border-blue-500" 
              value={title} 
              onChange={e => setTitle(e.target.value)} 
              placeholder="e.g. Animations: Shapes" 
            />
          </div>
        </div>

        {/* Question Rich Text */}
        <div className="flex">
          <div className="w-48 text-right pr-6 pt-2">
            <div className="text-[13px] font-semibold text-gray-700 mb-1">Question:</div>
            <a href="#" className="text-[12px] text-blue-600 hover:underline block mb-1">Add Image</a>
            <a href="#" className="text-[12px] text-blue-600 hover:underline block">Add Audio/Video</a>
          </div>
          <div className="flex-1 border border-gray-300 rounded shadow-sm">
            <RichTextEditor value={desc} onChange={setDesc} />
          </div>
        </div>

        {/* Purpose */}
        <div className="flex">
          <div className="w-48 text-right pr-6 text-[13px] font-semibold text-gray-700 pt-2">
            Purpose of the Question:
          </div>
          <div className="flex-1">
            <textarea 
              rows={4}
              className="w-full border border-gray-300 rounded p-3 text-[13px] focus:outline-none focus:border-blue-500"
              placeholder="Provide a brief description of what this question is designed to assess."
              value={purpose}
              onChange={e => setPurpose(e.target.value)}
            />
          </div>
        </div>

        {/* Code Stub */}
        <div className="flex">
          <div className="w-48 text-right pr-6 text-[13px] font-semibold text-gray-700 pt-2">
            Code Stub:
          </div>
          <div className="flex-1">
            <div className="space-y-2 mb-2 text-[13px] text-gray-700">
              <label className="flex items-center gap-2 cursor-pointer">
                <input 
                  type="radio" 
                  name="codeStub" 
                  checked={codeStubType === "scratch"} 
                  onChange={() => setCodeStubType("scratch")}
                  className="text-blue-600"
                />
                The candidate has to write the complete code
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input 
                  type="radio" 
                  name="codeStub" 
                  checked={codeStubType === "stub"}
                  onChange={() => setCodeStubType("stub")}
                  className="text-blue-600"
                />
                Add code stub
              </label>
            </div>
            <p className="text-[11px] text-gray-500 italic mb-4">
              Note: Code Stub is the starting code. Select whether you wish to provide a code stub or prefer the candidate to write from scratch.
            </p>
            
            {codeStubType === "stub" && (
              <div className="border border-gray-300 rounded bg-white overflow-hidden shadow-sm">
                <div className="flex border-b border-gray-300">
                  {(["html", "css", "javascript"] as const).map(t => (
                    <button 
                      key={t}
                      onClick={() => setActiveStubTab(t)}
                      className={`px-6 py-2 text-[13px] font-semibold ${
                        activeStubTab === t 
                        ? "text-blue-600 border-t-2 border-t-blue-600 bg-white" 
                        : "text-gray-500 bg-gray-50 hover:bg-gray-100"
                      }`}
                    >
                      {t === 'javascript' ? 'JavaScript' : t.toUpperCase()}
                    </button>
                  ))}
                </div>
                <div className="h-[200px] bg-yellow-50/10">
                  {/* Reuse CodeEditor but make it smaller */}
                  {activeStubTab === "html" && <CodeEditor language="html" value={stubHtml} onChange={(v)=>setStubHtml(v||"")} height="200px" />}
                  {activeStubTab === "css" && <CodeEditor language="css" value={stubCss} onChange={(v)=>setStubCss(v||"")} height="200px" />}
                  {activeStubTab === "javascript" && <CodeEditor language="javascript" value={stubJs} onChange={(v)=>setStubJs(v||"")} height="200px" />}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Difficulty & Details */}
        <div className="flex">
          <div className="w-48 text-right pr-6 text-[13px] font-semibold text-gray-700 pt-2">
            Difficulty:
          </div>
          <div className="flex-1">
            <select className="border border-gray-300 rounded p-1.5 text-[13px] w-48 focus:outline-none">
              <option>Easy</option>
              <option selected>Medium</option>
              <option>Hard</option>
            </select>
          </div>
        </div>

        <div className="flex">
          <div className="w-48 text-right pr-6 text-[13px] font-semibold text-gray-700 pt-2">
            Answer Explanation:
          </div>
          <div className="flex-1">
            <textarea 
              rows={4}
              className="w-full border border-gray-300 rounded p-3 text-[13px] focus:outline-none focus:border-blue-500"
            />
            <p className="text-[11px] text-gray-500 italic mt-1">
              Note: Explanation is not visible to the candidate. This is helpful for the question creators to fill in references/explanation for the correct answer.
            </p>
          </div>
        </div>

        <div className="flex">
          <div className="w-48 text-right pr-6 text-[13px] font-semibold text-gray-700 pt-2">
            Points:
          </div>
          <div className="flex-1">
            <input 
              type="number"
              defaultValue={10}
              className="border border-gray-300 rounded p-1.5 text-[13px] w-24 focus:outline-none"
            />
            <p className="text-[11px] text-gray-500 italic mt-1">
              Note: Points for this question type will be based on test case execution.
            </p>
          </div>
        </div>
        
        <div className="flex">
          <div className="w-48 text-right pr-6 text-[13px] font-semibold text-gray-700 pt-2">
            Author:
          </div>
          <div className="flex-1">
            <input 
              type="text"
              defaultValue="John Doe - Sep 2024"
              className="border border-gray-300 rounded p-1.5 text-[13px] w-full max-w-md focus:outline-none"
            />
          </div>
        </div>

        <div className="flex">
          <div className="w-48 text-right pr-6 text-[13px] font-semibold text-gray-700 pt-2">
            Topics:
          </div>
          <div className="flex-1">
            <textarea 
              rows={4}
              defaultValue="Animation"
              className="w-full border border-gray-300 rounded p-3 text-[13px] focus:outline-none focus:border-blue-500"
            />
            <p className="text-[11px] text-gray-500 italic mt-1">
              Note: You can add tags to the questions which help to identify the topics used in the question. E.g. tags can be Exception Handling.
            </p>
          </div>
        </div>

      </div>

      {/* Floating Bottom Bar (simulating the Save/Next bar in iMocha) */}
      <div className="fixed bottom-0 left-20 right-0 bg-white border-t border-gray-200 p-4 flex justify-end px-8 z-10 shadow-[0_-2px_10px_rgba(0,0,0,0.05)]">
        <button 
          onClick={handleSave} 
          disabled={loading}
          className="bg-imocha-orange text-white px-10 py-2 rounded-full font-medium shadow-sm hover:bg-orange-600 disabled:opacity-50"
        >
          {loading ? "Saving..." : "Next"}
        </button>
      </div>
    </div>
  );
}
