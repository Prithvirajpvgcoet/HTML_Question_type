import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import { 
  ArrowLeft, Download, Trophy, Sparkles, CheckCircle2, 
  Info, Check, ChevronRight, Clock, AlertCircle, Lightbulb, Settings, Eye, ClipboardList, XCircle, Loader2
} from "lucide-react";

const IN_PROGRESS_STATUSES = ["pending", "queued", "evaluating"];

export function ReportPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('evaluation');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchReport = () => {
    if (!id) return;
    api.get(`/submissions/${id}/evaluation`)
      .then(res => {
        setReport(res.data);
        // Stop polling once evaluation is no longer in-progress
        if (!IN_PROGRESS_STATUSES.includes(res.data?.status)) {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      })
      .catch(() => console.error("Could not load report"));
  };

  useEffect(() => {
    fetchReport();
    // Start polling — will self-cancel once status leaves in-progress
    pollRef.current = setInterval(fetchReport, 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [id]);

  const toggleReview = async () => {
    if (!report) return;
    try {
      await api.put(`/submissions/${id}/review`, { needs_review: !report.needs_review });
      setReport({ ...report, needs_review: !report.needs_review });
    } catch (e) {
      alert("Failed to update status");
    }
  };

  const score = report?.total_score || 0;
  const tcPassed = report?.tc_passed || 0;
  const tcTotal = report?.tc_total || 0;
  const maxScore = report?.max_score || (tcTotal * 5 + 50);

  // BUG-12: Compute "Not Evaluated / Skipped" from real llm_status values
  const testCases = report?.results || [];
  const tcSkipped = testCases.filter(
    (tc: any) => tc.llm_status === "skipped_playwright_passed"
  ).length;
  const tcNotRun = testCases.filter(
    (tc: any) => tc.llm_status === "not_run" || !tc.llm_status
  ).length;

  const tcPassedRate = tcTotal > 0 ? Math.round((tcPassed / tcTotal) * 100) : 0;
  const tcFailedRate = tcTotal > 0 ? 100 - tcPassedRate : 0;
  const tcFailed = tcTotal - tcPassed;
  const tcNotEvaluatedCount = tcSkipped + tcNotRun;
  const tcNotEvaluatedRate = tcTotal > 0 ? Math.round((tcNotEvaluatedCount / tcTotal) * 100) : 0;
  const isPassed = maxScore > 0 ? (score / maxScore) >= 0.7 : false;

  const initials = report?.candidate_name ? report.candidate_name.split(' ').map((n: string) => n[0]).join('').substring(0,2).toUpperCase() : 'RK';
  const name = report?.candidate_name || "Rohit Kumar";
  const email = report?.candidate_email || "";
  const dateStr = report?.submitted_at ? new Date(report.submitted_at).toLocaleString() : 'N/A';

  // Show loading spinner while report hasn't loaded yet
  if (!report) {
    return (
      <div className="bg-[#F8FAFC] min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-gray-500">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-sm font-medium">Loading report…</p>
        </div>
      </div>
    );
  }

  // Show evaluation-in-progress screen while backend is still running
  if (IN_PROGRESS_STATUSES.includes(report?.status)) {
    return (
      <div className="bg-[#F8FAFC] min-h-screen flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-12 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-5">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Evaluation in Progress</h2>
          <p className="text-sm text-gray-500 leading-relaxed mb-4">
            AI is running Playwright test cases and scoring the submission. This usually takes 20–60 seconds.
          </p>
          <div className="text-xs text-gray-400">Checking for updates every 3 seconds…</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#F8FAFC] min-h-screen text-gray-800 font-sans pb-12">
      {/* Top Banner Area */}
      <div className="bg-white border-b px-8 pt-4 pb-0">
        
        {/* Breadcrumb & Actions */}
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center text-sm text-gray-500">
            <span className="hover:text-blue-600 cursor-pointer" onClick={() => navigate('/reports')}>Test Results</span>
            <ChevronRight className="w-4 h-4 mx-1" />
            <span className="hover:text-blue-600 cursor-pointer">Candidate Report</span>
            <ChevronRight className="w-4 h-4 mx-1" />
            <span className="font-semibold text-gray-900">AI Evaluation</span>
          </div>
          <div className="flex gap-3">
            <button onClick={() => window.print()} className="flex items-center gap-2 border border-blue-200 text-blue-600 px-4 py-1.5 rounded-md text-sm font-semibold hover:bg-blue-50 transition-colors" title="Print or save as PDF">
              <Download className="w-4 h-4" /> Download Report
            </button>
            <button onClick={toggleReview} className="bg-[#FF5722] hover:bg-[#F4511E] text-white px-4 py-1.5 rounded-md text-sm font-semibold transition-colors">
              {report?.needs_review ? "Clear Review Flag" : "Mark for Review"}
            </button>
            
          </div>
        </div>

        {/* Profile & Summary Cards */}
        <div className="flex gap-6 mb-6">
          {/* Profile */}
          <div className="flex gap-4 items-center flex-1 min-w-[300px]">
            <button onClick={() => navigate(-1)} className="p-2 border border-gray-200 rounded-md hover:bg-gray-50 text-gray-500 h-10 w-10 flex items-center justify-center shrink-0">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="w-14 h-14 rounded-full bg-blue-600 text-white flex items-center justify-center text-xl font-bold shrink-0">
              {initials}
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">{name}</h1>
              <div className="text-sm text-gray-500 leading-tight mt-0.5">
                {email && <>{email}<br/></>}
                Software Development Assessment<br/>
                Attempted on {dateStr}
              </div>
            </div>
          </div>

          {/* Cards */}
          <div className="flex gap-4 flex-[2]">
            {/* Pass Rate */}
            <div className="bg-[#F0FDF4] border border-[#DCFCE7] rounded-xl p-4 flex gap-4 items-center flex-1 shadow-sm">
              <div className="w-10 h-10 rounded-full bg-white border border-green-200 flex items-center justify-center shrink-0">
                <Trophy className="w-5 h-5 text-green-600" />
              </div>
              <div className="flex-1">
                <div className="text-sm text-gray-600 font-medium mb-1">AI Test Case Pass Rate</div>
                <div className="flex items-end justify-between mb-2">
                  <span className="text-2xl font-bold text-green-700 leading-none">{tcPassed} / {tcTotal}</span>
                </div>
                <div className="w-full bg-green-200 rounded-full h-2.5">
                  <div className="bg-green-600 h-2.5 rounded-full" style={{ width: `${(tcPassed/tcTotal)*100}%` }}></div>
                </div>
              </div>
            </div>

            {/* Verification Score */}
            <div className="bg-[#F0F9FF] border border-[#E0F2FE] rounded-xl p-4 flex gap-4 items-center flex-1 shadow-sm">
              <div className="w-10 h-10 rounded-full bg-white border border-blue-200 flex items-center justify-center shrink-0">
                <Sparkles className="w-5 h-5 text-blue-600" />
              </div>
              <div className="flex-1">
                <div className="text-sm text-gray-600 font-medium mb-1">LLM Verification Score</div>
                <div className="flex items-end justify-between mb-2">
                  <span className="text-2xl font-bold text-blue-700 leading-none">{score} / {maxScore}</span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-2.5">
                  <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${maxScore > 0 ? Math.round((score / maxScore) * 100) : 0}%` }}></div>
                </div>
              </div>
            </div>

            {/* Verdict */}
            <div className={`border rounded-xl p-4 flex gap-4 items-center flex-1 shadow-sm ${isPassed ? 'bg-[#F0FDF4] border-[#DCFCE7]' : 'bg-[#FEF2F2] border-[#FEE2E2]'}`}>
              <div className={`w-10 h-10 rounded-full text-white flex items-center justify-center shrink-0 ${isPassed ? 'bg-green-500' : 'bg-red-500'}`}>
                {isPassed ? <Check className="w-6 h-6" /> : <XCircle className="w-6 h-6" />}
              </div>
              <div>
                <div className="text-sm text-gray-600 font-medium mb-0.5">Verdict</div>
                <div className={`text-xl font-bold mb-1 leading-none ${isPassed ? 'text-green-700' : 'text-red-700'}`}>{isPassed ? 'Passed' : 'Failed'}</div>
                <p className={`text-[10px] leading-tight opacity-80 ${isPassed ? 'text-green-800' : 'text-red-800'}`}>
                  {isPassed ? 'Solution is correct for most cases based on AI evaluation.' : 'Solution failed to meet the required criteria.'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-6 border-b border-gray-100">
          <div onClick={() => setActiveTab('evaluation')} className={`px-1 py-3 text-sm cursor-pointer ${activeTab === 'evaluation' ? 'font-bold text-blue-600 border-b-2 border-blue-600' : 'font-medium text-gray-500 hover:text-gray-700'}`}>
            AI Evaluation
          </div>
          <div onClick={() => setActiveTab('code')} className={`px-1 py-3 text-sm cursor-pointer ${activeTab === 'code' ? 'font-bold text-blue-600 border-b-2 border-blue-600' : 'font-medium text-gray-500 hover:text-gray-700'}`}>
            Candidate Code
          </div>
          <div onClick={() => setActiveTab('timeline')} className={`px-1 py-3 text-sm cursor-pointer ${activeTab === 'timeline' ? 'font-bold text-blue-600 border-b-2 border-blue-600' : 'font-medium text-gray-500 hover:text-gray-700'}`}>
            Timeline
          </div>
        </div>
      </div>

      {/* BUG-11: Timeline empty state */}
      {activeTab === 'timeline' && (
        <div className="p-8 max-w-[1600px] mx-auto">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 flex flex-col items-center text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            </div>
            <h3 className="text-lg font-bold text-gray-700 mb-2">Timeline Coming Soon</h3>
            <p className="text-sm text-gray-400 max-w-xs">Detailed event-by-event activity tracking for this submission will appear here in a future release.</p>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      {activeTab === 'code' && (
        <div className="p-8 max-w-[1600px] mx-auto">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 mb-6">
             <h2 className="text-lg font-bold text-gray-900 mb-4">Submitted HTML</h2>
             <pre className="bg-gray-50 p-4 rounded-md overflow-x-auto text-sm text-gray-800 font-mono border border-gray-100">{report?.submitted_html || "No HTML submitted"}</pre>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 mb-6">
             <h2 className="text-lg font-bold text-gray-900 mb-4">Submitted CSS</h2>
             <pre className="bg-gray-50 p-4 rounded-md overflow-x-auto text-sm text-gray-800 font-mono border border-gray-100">{report?.submitted_css || "No CSS submitted"}</pre>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
             <h2 className="text-lg font-bold text-gray-900 mb-4">Submitted JavaScript</h2>
             <pre className="bg-gray-50 p-4 rounded-md overflow-x-auto text-sm text-gray-800 font-mono border border-gray-100">{report?.submitted_js || "No JS submitted"}</pre>
          </div>
        </div>
      )}
      
      {activeTab === 'evaluation' && (
      <div className="p-8 max-w-[1600px] mx-auto flex gap-6">
        
        {/* LEFT COLUMN */}
        <div className="flex-[2] flex flex-col gap-6">
          
          {/* Table Card */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <ClipboardList className="w-5 h-5 text-blue-600" />
                  <h2 className="text-lg font-bold text-gray-900">AI Generated Test Cases Results</h2>
                  <Info className="w-4 h-4 text-gray-400" />
                </div>
                <p className="text-sm text-gray-500">The candidate's solution was evaluated using AI-generated test cases and LLM-based verification.</p>
              </div>
              <button onClick={() => document.getElementById('tc-table')?.scrollIntoView({ behavior: 'smooth' })} className="flex items-center gap-2 text-blue-600 border border-blue-200 px-4 py-1.5 rounded-md text-sm font-semibold hover:bg-blue-50 transition-colors">
                <Eye className="w-4 h-4" /> View All Test Cases
              </button>
            </div>

            <div id="tc-table" className="overflow-x-auto rounded-lg border border-gray-100">
              <table className="w-full text-sm text-left">
                <thead className="bg-[#F8FAFC] text-gray-700 font-semibold border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 w-12">#</th>
                    <th className="px-4 py-3">Test Case (AI Generated)</th>
                    <th className="px-4 py-3 font-mono text-xs">Input</th>
                    <th className="px-4 py-3">LLM Evaluation</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Reasoning (by LLM)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {testCases.map((tc: any, i: number) => {
                    const isPassedRow = tc.status === "passed";
                    const evalText =
                      tc.llm_status === "verified_pass" ? "Verified Pass" :
                      tc.llm_status === "verified_fail" ? "Verified Fail" :
                      tc.llm_status === "skipped_playwright_passed" ? "Passed (no LLM check needed)" :
                      tc.llm_status === "error" ? "LLM Error" :
                      "Not Evaluated";
                    const statusText = isPassedRow ? "Passed" : "Failed";
                    const testName = tc.assertion_check_type ? tc.assertion_check_type.replace('_', ' ') : 'Test Case';
                    const inputVal = tc.assertion_trigger ? `${tc.assertion_trigger} on ${tc.assertion_trigger_selector}` : 'N/A';
                    
                    return (
                      <tr key={i} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3 text-gray-500">{i + 1}</td>
                        <td className="px-4 py-3 text-gray-800 capitalize">{testName}</td>
                        <td className="px-4 py-3 text-gray-600 font-mono text-xs bg-gray-50 rounded mx-2 my-2">{inputVal}</td>
                        <td className={`px-4 py-3 ${tc.llm_status === 'verified_fail' ? 'text-red-500' : 'text-gray-800'}`}>{evalText}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${isPassedRow ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                            {isPassedRow ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                            {statusText}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-600 text-xs">{tc.llm_evidence || tc.actual_result || "Evaluated."}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bottom Grid */}
          <div className="grid grid-cols-2 gap-6">
            
            {/* Metrics */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col">
              <div className="p-6 pb-2">
                <div className="flex items-center gap-2 mb-6">
                  <div className="flex gap-1 items-end h-5">
                    <div className="w-1.5 h-3 bg-blue-600 rounded-sm"></div>
                    <div className="w-1.5 h-5 bg-blue-600 rounded-sm"></div>
                    <div className="w-1.5 h-4 bg-blue-600 rounded-sm"></div>
                  </div>
                  <h2 className="text-lg font-bold text-gray-900">Evaluation Metrics</h2>
                </div>
                
                <div className="space-y-5">
                  {(report?.ai_feedback_breakdown ? [
                    { label: "Functional Correctness", val: (report.ai_feedback_breakdown.functional || 0) * 10, color: "bg-emerald-500" },
                    { label: "Code Structure", val: (report.ai_feedback_breakdown.structure || 0) * 10, color: "bg-blue-500" },
                    { label: "Visual Design", val: (report.ai_feedback_breakdown.design || 0) * 10, color: "bg-purple-500" },
                    { label: "Edge Case Handling", val: (report.ai_feedback_breakdown.edge_cases || 0) * 10, color: "bg-orange-500" },
                    { label: "Completeness", val: (report.ai_feedback_breakdown.completeness || 0) * 10, color: "bg-cyan-500" },
                  ] : []).map((m, i) => (
                    <div key={i}>
                      <div className="flex justify-between text-sm mb-1.5">
                        <span className="text-gray-600">{m.label}</span>
                        <span className="font-bold text-gray-700">{m.val}%</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2.5 flex">
                        <div className={`${m.color} h-2.5 rounded-full`} style={{ width: `${m.val}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-auto bg-[#F0F9FF] p-4 px-6 border-t border-[#E0F2FE] flex items-center justify-between">
                <div className="flex items-center gap-2 text-blue-800 font-semibold">
                  <Sparkles className="w-5 h-5" /> Overall LLM Score
                </div>
                <div className="text-xl font-bold text-blue-700">{score} / {maxScore}</div>
              </div>
            </div>

            {/* Test Case Distribution */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
              <div className="flex items-center gap-2 mb-6">
                <Clock className="w-5 h-5 text-blue-600" />
                <h2 className="text-lg font-bold text-gray-900">Test Case Distribution</h2>
              </div>
              
              <div className="flex items-center gap-8 mb-8 pl-4">
                {/* Donut Chart Mock */}
                <div className="relative w-32 h-32 shrink-0">
                  <svg viewBox="0 0 36 36" className="w-full h-full transform -rotate-90">
                    <path className="text-gray-100" strokeWidth="4" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                    <path className="text-green-500" strokeWidth="4" strokeDasharray={`${tcPassedRate}, 100`} stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                    <path className="text-red-500" strokeWidth="4" strokeDasharray={`${tcFailedRate}, 100`} strokeDashoffset={`-${tcPassedRate}`} stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-3xl font-bold text-gray-900 leading-none">{tcTotal}</span>
                    <span className="text-[9px] font-semibold text-gray-500 leading-tight">Total Test Cases</span>
                  </div>
                </div>

                <div className="flex-1 space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-green-500" /> <span className="text-gray-600">Passed</span></div>
                    <span className="font-bold text-gray-800">{tcPassed} ({tcPassedRate}%)</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-red-500" /> <span className="text-gray-600">Failed</span></div>
                    <span className="font-bold text-gray-800">{tcFailed} ({tcFailedRate}%)</span>
                  </div>
                  <div className="flex items-center justify-between text-sm opacity-60">
                    <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-gray-300" /> <span className="text-gray-600">Not Evaluated</span></div>
                    <span className="font-bold text-gray-800">{tcNotEvaluatedCount} ({tcNotEvaluatedRate}%)</span>
                  </div>
                </div>
              </div>

              <div className="bg-[#F8FAFC] rounded-lg p-4 border border-gray-100 relative">
                <div className="absolute top-4 left-4 text-blue-500">
                  <Settings className="w-5 h-5" />
                </div>
                <div className="pl-8">
                  <h4 className="font-bold text-gray-900 text-sm mb-1">Evaluation Methodology</h4>
                  <p className="text-xs text-gray-500 leading-relaxed mb-3">AI-generated test cases are created to cover standard, edge, and hidden scenarios. The candidate's output is verified using an LLM to ensure semantic correctness and logical accuracy.</p>
                  {/* View Methodology button removed — follow-up ticket for static docs page */}
                </div>
              </div>

            </div>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="flex-1 flex flex-col gap-6">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 h-full flex flex-col">
            <div className="flex items-center gap-2 mb-6">
              <Sparkles className="w-5 h-5 text-blue-600" />
              <h2 className="text-lg font-bold text-gray-900">AI Feedback & Analysis</h2>
            </div>

            <div className="bg-[#F0F9FF] rounded-lg p-4 border border-[#E0F2FE] relative mb-6">
              <div className="absolute top-4 left-4 text-blue-500">
                <Lightbulb className="w-5 h-5" />
              </div>
              <div className="pl-8">
                <h4 className="font-bold text-gray-900 text-sm mb-1">Overall Feedback</h4>
                <p className="text-xs text-gray-600 leading-relaxed">
                  
                  {(() => {
                    const txt = report?.ai_feedback_text;
                    if (!txt) return "No feedback generated.";
                    if (txt.trim().startsWith('{')) {
                      try {
                        const parsed = JSON.parse(txt);
                        return parsed.reasoning || txt;
                      } catch(e) { return txt; }
                    }
                    return txt;
                  })()}

                </p>
              </div>
            </div>

            <div className="mb-6">
              <h4 className="font-bold text-green-700 text-sm flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-4 h-4" /> Strengths
              </h4>
              <ul className="space-y-2.5">
                {(report?.ai_feedback_breakdown?.strengths?.length ? report.ai_feedback_breakdown.strengths : ["No specific strengths recorded"]).map((s: string, i: number) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-600 items-start">
                    <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                    <span className="leading-tight">{s}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mb-auto">
              <h4 className="font-bold text-red-600 text-sm flex items-center gap-2 mb-3">
                <AlertCircle className="w-4 h-4" /> Areas for Improvement
              </h4>
              <ul className="space-y-2.5">
                {(report?.ai_feedback_breakdown?.improvements?.length ? report.ai_feedback_breakdown.improvements : ["No specific areas for improvement recorded"]).map((s: string, i: number) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-600 items-start">
                    <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                    <span className="leading-tight">{s}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-[#F0F9FF] rounded-lg p-4 border border-[#E0F2FE] relative mt-8">
              <div className="absolute top-4 left-4 text-blue-500">
                <Lightbulb className="w-5 h-5" />
              </div>
              <div className="pl-8">
                <div className="flex items-center gap-1 mb-1">
                  <h4 className="font-bold text-gray-900 text-sm">LLM Evaluation Criteria</h4>
                  <Info className="w-3.5 h-3.5 text-gray-400" />
                </div>
                <p className="text-xs text-gray-600 leading-relaxed mb-3">
                  The solution is evaluated using LLM-based semantic verification, which checks correctness, edge case handling, code quality, and output logic against AI-generated test cases.
                </p>
                {/* Learn More button removed — follow-up ticket for static docs page */}
              </div>
            </div>

          </div>
        </div>

      </div>
      )}
    </div>
  );
}
