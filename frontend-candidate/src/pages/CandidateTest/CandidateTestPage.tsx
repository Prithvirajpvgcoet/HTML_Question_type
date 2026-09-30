import DOMPurify from "dompurify";
import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../../api/client";
import { CodeEditor } from "../../components/CodeEditor";
import { LivePreview } from "../../components/LivePreview";
import {
  Clock,
  ChevronLeft,
  
  RotateCcw,
  Play,
  AlertTriangle,
  Info,
  
  Maximize2,
  
} from "lucide-react";
import type { Question } from "../../shared/types";
import { useCandidateStore } from "../../store/candidateStore";

export function CandidateTestPage() {
  const { questionId } = useParams();
  const navigate = useNavigate();
  const { candidateName, candidateEmail, token } = useCandidateStore();
  const [searchParams] = useSearchParams();
  const isPreview = searchParams.get("preview") === "true";

  const [question, setQuestion] = useState<Question | null>(null);
  const [activeCodeTab, setActiveCodeTab] = useState<"html" | "css" | "javascript">("html");
  const [activePreviewTab, setActivePreviewTab] = useState<"preview" | "console">("preview");
  const [activeRightPanel, setActiveRightPanel] = useState<"preview" | "testcases">("preview");
  const [activeDescTab, setActiveDescTab] = useState<"description" | "instructions" | "examples">("description");

  const [html, setHtml] = useState("<!-- Write your HTML code here -->");
  const [css, setCss] = useState("");
  const [js, setJs] = useState("");
  const [preview, setPreview] = useState({ html: "", css: "", js: "" });
  const [autoRun, setAutoRun] = useState(false);
  const [hasRunOnce, setHasRunOnce] = useState(false);
  const [editorTheme, setEditorTheme] = useState<"Light" | "Dark">("Light");

  const [submitting, setSubmitting] = useState(false);
  const [evalStep, setEvalStep] = useState(1);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [closeAttempted, setCloseAttempted] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [timeLeft, setTimeLeft] = useState(3600);

  useEffect(() => {
    if (submitting) {
      setEvalStep(1);
      const timers = [
        setTimeout(() => setEvalStep(2), 2000), // Code Submitted -> Running Playwright
        setTimeout(() => setEvalStep(3), 6000), // Running Playwright -> collecting evidence
        setTimeout(() => setEvalStep(4), 10000) // Collecting evidence -> finalizing report
      ];
      return () => timers.forEach(clearTimeout);
    }
  }, [submitting]);
  const [consoleLogs, setConsoleLogs] = useState<{level: string, text: string}[]>([]);

  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (e.data && e.data.type === 'console') {
        setConsoleLogs(prev => [...prev, { level: e.data.level, text: e.data.text }]);
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const codeRef = useRef({ html, css, js });

  useEffect(() => {
    codeRef.current = { html, css, js };
  }, [html, css, js]);

  // Initialize Server Deadline
  useEffect(() => {
    if (isPreview) return;
    if (token) {
      api.get(`/invites/${token}`).then(res => {
        if (res.data.deadline) {
          const deadlineStr = res.data.deadline.endsWith("Z") ? res.data.deadline : res.data.deadline + "Z";
          const deadline = new Date(deadlineStr).getTime();
          let t: any;
          const updateTime = () => {
            const now = new Date().getTime();
            const distance = Math.floor((deadline - now) / 1000);
            if (distance <= 0) {
               setTimeLeft(0);
               if (t) clearInterval(t);
               executeSubmit();
            } else {
               setTimeLeft(distance);
            }
          };
          updateTime();
          t = setInterval(updateTime, 1000);
          return () => clearInterval(t);
        }
      }).catch(() => {
        alert("Invite invalid or expired");
        navigate(`/login/${questionId || ""}`, { replace: true });
      });
    }
  }, [token, isPreview, questionId, navigate]);


  useEffect(() => {
    if (!candidateName) {
      navigate(`/login/${questionId}`, { replace: true });
    }
  }, [candidateName, navigate, questionId]);

  useEffect(() => {
    if (!autoRun) return;
    const t = setTimeout(() => { setConsoleLogs([]); setPreview({ html, css, js }); setHasRunOnce(true); }, 600);
    return () => clearTimeout(t);
  }, [html, css, js, autoRun]);

  useEffect(() => {
    api.get(`/questions/${questionId}`).then((res) => setQuestion(res.data));
  }, [questionId]);

  const formatTime = (s: number) =>
    `${String(Math.floor(s / 3600)).padStart(2, "0")}:${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const handleRunCode = () => {
    setConsoleLogs([]);
    setPreview({ html, css, js });
    setHasRunOnce(true);
    setActivePreviewTab("preview");
    setActiveRightPanel("preview");
  };

  const handleResetCode = () => {
    setHtml("<!-- Write your HTML code here -->");
    setCss("");
    setJs("");
  };

  const executeSubmit = async () => {
    if (submitting || isSubmitted) return;
    setShowConfirm(false);
    setSubmitting(true);
    try {
      const subRes = await api.post("/submissions", {
        question_id: questionId,
        candidate_name: candidateName,
        candidate_email: candidateEmail,
          token: token,
          submitted_html: codeRef.current.html,
        submitted_css: codeRef.current.css,
        submitted_js: codeRef.current.js,
      });
      const submissionId = subRes.data.id;
      await api.post(`/submissions/${submissionId}/evaluate`);
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        if (attempts >= 60) { clearInterval(poll); setSubmitting(false); alert("Evaluation timed out."); return; }
        try {
          const evalRes = await api.get(`/submissions/${submissionId}/evaluation`);
          if (evalRes.data?.status === "completed" || evalRes.data?.status === "failed") {
            clearInterval(poll);
            setSubmitting(false);
            setIsSubmitted(true);
          }
        } catch (e) { console.error(e); }
      }, 2000);
    } catch (e) {
      console.error(e);
      alert("Submission failed.");
      setSubmitting(false);
    }
  };


  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-10 border border-gray-100 text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"></path></svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Thank You for Submitting!</h1>
          <p className="text-gray-500 text-sm mb-8">Your test has been successfully submitted and evaluated. The recruiter will review your results.</p>
          {!closeAttempted ? (
            <button 
              onClick={() => {
                window.close();
                setTimeout(() => setCloseAttempted(true), 300);
              }} 
              className="px-8 py-3 bg-[#FF6B35] text-white font-semibold rounded-lg hover:bg-orange-600 shadow-sm transition-colors"
            >
              Close Window
            </button>
          ) : (
            <div className="p-4 bg-orange-50 rounded-lg border border-orange-100 text-orange-800 text-sm font-medium">
              You can safely close this browser tab now.
            </div>
          )}
        </div>
      </div>
    );
  }

  if (!question)

    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 text-gray-500 text-sm">
        Loading test environment...
      </div>
    );

  const initial = candidateName.charAt(0).toUpperCase();

  return (
    <div className="flex flex-col h-screen bg-white overflow-hidden" style={{ fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>

      {/* ═══ TOP HEADER ═══ */}
      <header className="h-[56px] bg-white border-b border-gray-200 flex items-center px-5 z-30 shrink-0 gap-3">
        {/* Logo */}
        <div className="flex items-center gap-2 mr-3 shrink-0">
          <div className="w-8 h-8 rounded-full border-[3px] border-[#FF6B35] flex items-center justify-center">
            <div className="w-2.5 h-2.5 bg-[#FF6B35] rounded-full" />
          </div>
          <span className="text-[#FF6B35] text-lg font-bold tracking-tight">iMocha</span>
        </div>

        {/* Title */}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-bold text-gray-900 leading-tight">Frontend Development and Design</div>
          <div className="text-xs text-gray-400 leading-tight">HTML/CSS/JavaScript</div>
        </div>

        {/* Timer */}
        <div className="flex items-center gap-2 shrink-0">
          <Clock className="w-4 h-4 text-gray-400" />
          <div>
            <div className={`font-mono font-bold text-[17px] leading-none ${timeLeft < 300 ? "text-red-500" : "text-gray-800"}`}>
              {formatTime(timeLeft)}
            </div>
            <div className="text-[10px] text-gray-400 leading-none mt-0.5">Time Remaining</div>
          </div>
        </div>

        <div className="flex items-center gap-2 ml-3 shrink-0">
          {/* End Test */}
          <button
            onClick={() => setShowConfirm(true)}
            disabled={submitting}
            className="bg-[#FF6B35] hover:bg-orange-600 text-white font-semibold text-sm px-5 py-2 rounded-md transition-colors"
          >
            {submitting ? "Submitting..." : "Submit Solution"}
          </button>
          {/* Avatar */}
          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xs font-bold text-gray-600">
            {initial}
          </div>
        </div>
      </header>

      {/* ═══ BODY ═══ */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── MAIN CONTENT (column layout) ── */}
        <div className="flex-1 flex flex-col overflow-hidden">


          {/* ── THREE-COLUMN WORK AREA ── */}
          <div className="flex-1 flex overflow-hidden">

            {/* ── COL A: QUESTION DESCRIPTION ── */}
            <div className="w-[320px] flex flex-col bg-white border-r border-gray-200 overflow-hidden shrink-0">
              {/* Tab row */}
              <div className="flex border-b border-gray-200 shrink-0 px-4">
                {(["description", "instructions", "examples"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveDescTab(tab)}
                    className={`py-3 mr-5 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
                      activeDescTab === tab
                        ? "text-blue-600 border-blue-600"
                        : "text-gray-500 border-transparent hover:text-gray-700"
                    }`}
                  >
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {/* Content area */}
              <div className="flex-1 overflow-y-auto p-5">
                {/* Title + tag */}
                <div className="flex items-baseline gap-3 mb-3">
                  <h2 className="text-[17px] font-bold text-gray-900">{question.title}</h2>
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-orange-50 text-orange-600 border border-orange-100 shrink-0">
                    Medium
                  </span>
                </div>

                {activeDescTab === "description" && (
                  <>
                    <div
                      className="prose prose-sm max-w-none text-gray-700 leading-relaxed mb-4"
                      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(question.description_html) }}
                    />
                    {/* Note box */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3.5 flex gap-2.5 mb-5">
                      <Info className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                      <div className="text-sm text-blue-800">
                        <span className="font-semibold">Note</span>
                        <div className="text-blue-700 mt-0.5">Make sure your solution meets all the requirements before submitting.</div>
                      </div>
                    </div>

                  </>
                )}

                {activeDescTab === "instructions" && (
                  <div className="space-y-3 text-sm text-gray-600">
                    <p className="font-semibold text-gray-800">General Instructions</p>
                    <ul className="list-disc pl-5 space-y-2">
                      <li>Write your solution using the HTML, CSS, and JavaScript tabs.</li>
                      <li>Click <strong>Run Code</strong> to test before submitting.</li>
                      <li>Use <strong>Auto Run</strong> to enable live preview as you type.</li>
                      <li>Once you click <strong>Submit Solution</strong>, your submission is final.</li>
                    </ul>
                  </div>
                )}

                {activeDescTab === "examples" && (
                  <div className="space-y-3 text-sm text-gray-600">
                    <p className="font-semibold text-gray-800">Example Patterns</p>
                    <div className="bg-gray-50 rounded-lg p-4 font-mono text-xs border border-gray-200 text-gray-700">
                      <p className="text-gray-400 mb-1">{"<!-- Example -->"}</p>
                      <p>{"<ul id='colors'>"}</p>
                      <p className="pl-4">{"<li>Red</li>"}</p>
                      <p>{"</ul>"}</p>
                    </div>
                    <p className="text-gray-400 text-xs">See Description tab for the specific problem requirements.</p>
                  </div>
                )}
              </div>
            </div>

            {/* ── COL B: CODE EDITOR ── */}
            <div className="flex-1 flex flex-col overflow-hidden border-r border-gray-200">
              {/* Editor header */}
              <div className="h-11 bg-white border-b border-gray-200 flex items-center px-4 justify-between shrink-0">
                <span className="text-sm font-bold text-gray-800">Code Editor</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setEditorTheme(editorTheme === "Light" ? "Dark" : "Light")}
                    className="flex items-center gap-1.5 text-xs text-gray-600 border border-gray-200 rounded px-2.5 py-1.5 hover:bg-gray-50"
                  >
                    {editorTheme}
                    <ChevronLeft className="w-3 h-3 -rotate-90 text-gray-400" />
                  </button>
                  <button
                    onClick={handleResetCode}
                    className="flex items-center gap-1.5 text-xs text-gray-600 border border-gray-200 rounded px-2.5 py-1.5 hover:bg-gray-50"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Reset Code
                  </button>
                  <button className="p-1.5 text-gray-400 hover:text-gray-600 border border-gray-200 rounded">
                    <Maximize2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Code tabs */}
              <div className="flex border-b border-gray-200 bg-white px-4 shrink-0">
                {(["html", "css", "javascript"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveCodeTab(tab)}
                    className={`py-2.5 mr-6 text-sm font-medium border-b-2 -mb-px transition-colors ${
                      activeCodeTab === tab
                        ? "text-blue-600 border-blue-600"
                        : "text-gray-500 border-transparent hover:text-gray-700"
                    }`}
                  >
                    {tab === "javascript" ? "JavaScript" : tab.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* Monaco Editor */}
              <div className="flex-1 overflow-hidden">
                {activeCodeTab === "html" && (
                  <CodeEditor language="html" value={html} onChange={(v) => setHtml(v || "")} height="100%" theme={editorTheme === "Dark" ? "vs-dark" : "vs"} />
                )}
                {activeCodeTab === "css" && (
                  <CodeEditor language="css" value={css} onChange={(v) => setCss(v || "")} height="100%" theme={editorTheme === "Dark" ? "vs-dark" : "vs"} />
                )}
                {activeCodeTab === "javascript" && (
                  <CodeEditor language="javascript" value={js} onChange={(v) => setJs(v || "")} height="100%" theme={editorTheme === "Dark" ? "vs-dark" : "vs"} />
                )}
              </div>

              {/* Run Code footer */}
              <div className="h-[52px] bg-white border-t border-gray-200 flex items-center px-4 gap-4 shrink-0">
                <button
                  onClick={handleRunCode}
                  className="flex items-center gap-2 bg-[#2D9248] hover:bg-green-800 text-white font-semibold text-sm px-5 py-2.5 rounded-md transition-colors"
                >
                  <Play className="w-3.5 h-3.5 fill-white" />
                  Run Code
                </button>
                <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={autoRun}
                    onChange={(e) => { setAutoRun(e.target.checked); if (e.target.checked) setHasRunOnce(true); }}
                    className="w-4 h-4 rounded accent-green-600"
                  />
                  Auto Run
                </label>
                <span className="text-gray-300 text-base">ⓘ</span>

                {/* Spacer */}
                <div className="flex-1" />


              </div>
            </div>

            {/* ── COL C: PREVIEW / OUTPUT ── */}
            <div className="w-[360px] flex flex-col bg-white shrink-0">
              {/* Top panel tabs: Preview/Output | Test Cases */}
              <div className="h-11 bg-white border-b border-gray-200 flex items-center px-0 shrink-0">
                {(["preview", "testcases"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveRightPanel(tab)}
                    className={`h-full px-5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                      activeRightPanel === tab
                        ? "text-blue-600 border-blue-600 bg-white"
                        : "text-gray-500 border-transparent hover:text-gray-700"
                    }`}
                  >
                    {tab === "preview" ? "Preview / Output" : "Test Cases"}
                  </button>
                ))}
              </div>

              {activeRightPanel === "preview" && (
                <>
                  {/* Preview | Console sub-tabs */}
                  <div className="flex border-b border-gray-200 px-4 bg-white shrink-0">
                    {(["preview", "console"] as const).map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setActivePreviewTab(tab)}
                        className={`py-2.5 mr-5 text-sm font-medium border-b-2 -mb-px transition-colors capitalize ${
                          activePreviewTab === tab
                            ? "text-blue-600 border-blue-600"
                            : "text-gray-500 border-transparent hover:text-gray-700"
                        }`}
                      >
                        {tab.charAt(0).toUpperCase() + tab.slice(1)}
                      </button>
                    ))}
                  </div>

                  {/* Preview content */}
                  <div className="flex-1 overflow-hidden bg-white relative">
                    {activePreviewTab === "preview" ? (
                      hasRunOnce ? (
                        <LivePreview {...preview} className="w-full h-full" />
                      ) : (
                        <div className="flex flex-col items-center justify-center h-full text-center px-10">
                          {/* Code icon placeholder */}
                          <div className="w-20 h-16 bg-gray-100 rounded-xl flex items-center justify-center mb-4 relative">
                            <div className="absolute top-2 left-3 flex gap-1">
                              <div className="w-1.5 h-1.5 rounded-full bg-gray-300" />
                              <div className="w-1.5 h-1.5 rounded-full bg-gray-300" />
                              <div className="w-1.5 h-1.5 rounded-full bg-gray-300" />
                            </div>
                            <svg className="w-8 h-8 text-gray-400 mt-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <polyline points="16 18 22 12 16 6" />
                              <polyline points="8 6 2 12 8 18" />
                            </svg>
                          </div>
                          <p className="text-sm font-bold text-gray-800 mb-1">Your output will appear here</p>
                          <p className="text-xs text-gray-400">Run your code to see the result</p>
                        </div>
                      )
                    ) : (
                      <div className="h-full bg-gray-950 p-4 font-mono text-xs overflow-y-auto space-y-2">
                        {consoleLogs.length === 0 ? (
                          <div className="text-gray-500">
                            <span>{"> "}</span>Console output will appear here after running code...
                          </div>
                        ) : (
                          consoleLogs.map((log, i) => (
                            <div key={i} className={`pb-1 border-b border-gray-800 ${log.level === 'error' ? 'text-red-400' : log.level === 'warn' ? 'text-yellow-400' : 'text-green-400'}`}>
                              <span className="text-gray-500 mr-2">{">"}</span>{log.text}
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                </>
              )}

              {activeRightPanel === "testcases" && (
                <div className="flex-1 overflow-y-auto p-5">
                  <p className="text-sm font-semibold text-gray-700 mb-3">Automated Test Cases</p>
                  <p className="text-xs text-gray-400 bg-gray-50 p-4 rounded-lg border border-gray-200 text-center">
                    Submit your solution to see detailed test case results and AI evaluation score.
                  </p>
                </div>
              )}
            </div>

          </div>
        </div>
      </div>

      {/* ═══ CONFIRMATION MODAL ═══ */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-7">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              <h3 className="text-base font-bold text-gray-900">Submit Solution?</h3>
            </div>
            <p className="text-sm text-gray-600 mb-6">
              You are about to submit your solution for AI evaluation. This cannot be undone and your remaining time will be forfeited.
            </p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowConfirm(false)} className="px-4 py-2 text-sm rounded-lg text-gray-700 border border-gray-300 font-medium hover:bg-gray-50">
                Continue Working
              </button>
              <button onClick={executeSubmit} className="px-4 py-2 text-sm rounded-lg bg-[#FF6B35] text-white font-semibold hover:bg-orange-600">
                Submit Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ EVALUATION MODAL ═══ */}
      {submitting && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center backdrop-blur-sm transition-opacity">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8 overflow-hidden relative">
            
            {/* Header */}
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-orange-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-orange-100">
                <div className="w-8 h-8 border-4 border-orange-200 border-t-[#FF6B35] rounded-full animate-spin" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Evaluating Solution</h3>
              <p className="text-gray-500 text-sm">Please do not close this window.</p>
            </div>

            {/* Stepper (fake progression driven by evalStep) */}
            <div className="space-y-5 relative before:absolute before:inset-0 before:ml-[15px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-300 before:to-transparent">
              
              {/* Step 1: Code Submitted */}
              <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 border-white shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-colors ${evalStep >= 1 ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-400'}`}>
                  {evalStep > 1 ? <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"></path></svg> : <div className="w-2.5 h-2.5 bg-white rounded-full animate-ping" />}
                </div>
                <div className={`w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-white p-3 rounded-lg border shadow-sm transition-all ${evalStep === 1 ? 'border-blue-100 bg-blue-50/30' : 'border-gray-100'}`}>
                  <p className="font-semibold text-gray-900 text-sm">Code Submitted</p>
                </div>
              </div>

              {/* Step 2: Running Playwright */}
              <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 border-white shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-colors ${evalStep > 2 ? 'bg-green-500 text-white' : evalStep === 2 ? 'bg-blue-500 text-white animate-pulse' : 'bg-gray-200 text-gray-400'}`}>
                  {evalStep > 2 ? <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"></path></svg> : evalStep === 2 ? <div className="w-2.5 h-2.5 bg-white rounded-full" /> : <div className="w-2.5 h-2.5 bg-gray-400 rounded-full" />}
                </div>
                <div className={`w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-white p-3 rounded-lg border shadow-sm transition-all ${evalStep === 2 ? 'border-blue-100 bg-blue-50/30' : evalStep > 2 ? 'border-gray-100' : 'border-transparent opacity-40'}`}>
                  <p className="font-semibold text-gray-900 text-sm">Running Playwright Tests</p>
                  {evalStep === 2 && <p className="text-xs text-gray-500 mt-1">Checking assertions...</p>}
                </div>
              </div>

              {/* Step 3: Assertion evidence */}
              <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 border-white shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-colors ${evalStep > 3 ? 'bg-green-500 text-white' : evalStep === 3 ? 'bg-blue-500 text-white animate-pulse' : 'bg-gray-200 text-gray-400'}`}>
                  {evalStep > 3 ? <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"></path></svg> : evalStep === 3 ? <div className="w-2.5 h-2.5 bg-white rounded-full" /> : <div className="w-2.5 h-2.5 bg-gray-400 rounded-full" />}
                </div>
                <div className={`w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-white p-3 rounded-lg border shadow-sm transition-all ${evalStep === 3 ? 'border-blue-100 bg-blue-50/30' : evalStep > 3 ? 'border-gray-100' : 'border-transparent opacity-40'}`}>
                  <p className="font-semibold text-gray-900 text-sm">Collecting Assertion Evidence</p>
                </div>
              </div>

              {/* Step 4: Finalizing Report */}
              <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 border-white shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-colors ${evalStep === 4 ? 'bg-blue-500 text-white animate-pulse' : 'bg-gray-200 text-gray-400'}`}>
                  {evalStep === 4 ? <div className="w-2.5 h-2.5 bg-white rounded-full" /> : <div className="w-2.5 h-2.5 bg-gray-400 rounded-full" />}
                </div>
                <div className={`w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-white p-3 rounded-lg border shadow-sm transition-all ${evalStep === 4 ? 'border-blue-100 bg-blue-50/30' : 'border-transparent opacity-40'}`}>
                  <p className="font-semibold text-gray-900 text-sm">Finalizing Report</p>
                </div>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
