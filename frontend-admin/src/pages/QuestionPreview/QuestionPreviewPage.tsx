import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import {
  ChevronLeft,
  Pencil,
  Star,
  
  AlignLeft,
  Info,
  Download,
  Tag,
  Clock,
  FileText,
} from "lucide-react";

export function QuestionPreviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [question, setQuestion] = useState<any>(null);
  const [assertions, setAssertions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get(`/questions/${id}`),
      api.get(`/questions/${id}/assertions`).catch(() => ({ data: [] })),
    ]).then(([qRes, aRes]) => {
      setQuestion(qRes.data);
      setAssertions(aRes.data || []);
      setLoading(false);
    });
  }, [id]);

  const handleExport = async () => {
    try {
      const { data } = await api.get(`/questions/${id}/export`);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `question_${id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Export failed");
    }
  };

  const createdAt = question?.created_at
    ? new Date(question.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
    : "—";

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        Loading question preview...
      </div>
    );
  }

  if (!question) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        Question not found.
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8f9fa]">
      {/* ── TOP BREADCRUMB BAR ── */}
      <div className="bg-white border-b border-gray-200 px-8 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm">
          <button
            onClick={() => navigate("/questions")}
            className="text-gray-500 hover:text-gray-700 font-medium"
          >
            Question Library
          </button>
          <ChevronLeft className="w-4 h-4 text-gray-400 rotate-180" />
          <span className="text-gray-800 font-semibold">Question Preview</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/questions")}
            className="flex items-center gap-1.5 text-sm text-gray-600 border border-gray-300 rounded-md px-4 py-1.5 hover:bg-gray-50 font-medium"
          >
            <ChevronLeft className="w-4 h-4" />
            Back to Library
          </button>
          <button
            onClick={() => navigate(`/questions/edit/${id}`)}
            className="flex items-center gap-1.5 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-md px-4 py-1.5 font-semibold"
          >
            <Pencil className="w-3.5 h-3.5" />
            Edit Question
          </button>
        </div>
      </div>

      {/* ── MAIN BODY ── */}
      <div className="max-w-[1280px] mx-auto px-8 py-6 flex gap-6">

        {/* ── LEFT / MAIN CONTENT ── */}
        <div className="flex-1 min-w-0 space-y-5">

          {/* Tag Row */}
          <div className="bg-white rounded-lg border border-gray-200 px-5 py-4">
            <div className="flex items-center gap-3 mb-4 flex-wrap">
              <span className="text-xs font-bold px-2.5 py-1 rounded bg-blue-100 text-blue-700 uppercase tracking-wide">
                {question.question_type || "HTML/CSS/JS"}
              </span>
              <span className="text-xs font-bold px-2.5 py-1 rounded bg-orange-100 text-orange-600">
                Medium
              </span>
              <span className={`text-xs font-bold px-2.5 py-1 rounded ${
                question.is_published
                  ? "bg-green-100 text-green-700"
                  : "bg-gray-100 text-gray-500"
              }`}>
                {question.is_published ? "Active" : "Draft"}
              </span>
              <div className="w-px h-4 bg-gray-200" />
              <span className="text-xs text-gray-500">Q ID: {id?.substring(0, 8).toUpperCase()}</span>
              <div className="w-px h-4 bg-gray-200" />
              <span className="text-xs text-gray-500">Frontend Development and Design</span>
              <div className="w-px h-4 bg-gray-200" />
              <span className="text-xs text-gray-500">HTML/CSS/JS Coding</span>
              <div className="flex-1" />
              <button className="text-gray-400 hover:text-yellow-500 transition-colors">
                <Star className="w-4 h-4" />
              </button>
              
            </div>

            {/* Title */}
            <h1 className="text-[22px] font-bold text-gray-900 leading-tight">
              {question.title}
            </h1>
          </div>

          {/* Question Description Section */}
          <div className="bg-white rounded-lg border border-gray-200 px-6 py-5">
            <div className="flex items-center gap-2 mb-4">
              <AlignLeft className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-bold text-gray-800">Question</span>
            </div>
            <div
              className="prose prose-sm max-w-none text-gray-700 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: question.description_html }}
            />

            {/* Note box */}
            <div className="mt-5 bg-red-50 border border-red-200 rounded-lg p-4 flex gap-3">
              <Info className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
              <div className="text-sm text-red-800">
                <span className="font-bold">Note</span>
                <div className="mt-0.5 text-red-700">
                  Write valid HTML, CSS, and JavaScript. Your solution will be automatically evaluated
                  using visual assertions and AI semantic review. Ensure your code runs without errors.
                </div>
              </div>
            </div>
          </div>

          {/* Reference Code Section */}
          {(question.reference_html || question.reference_css || question.reference_js) && (
            <div className="bg-white rounded-lg border border-gray-200 px-6 py-5">
              <div className="flex items-center gap-2 mb-4">
                <FileText className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-bold text-gray-800">Reference Solution</span>
                <span className="ml-auto text-xs text-gray-400 italic">Hidden from candidates</span>
              </div>
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: "HTML", code: question.reference_html, lang: "html" },
                  { label: "CSS", code: question.reference_css, lang: "css" },
                  { label: "JavaScript", code: question.reference_js, lang: "javascript" },
                ].map(({ label, code }) => (
                  code ? (
                    <div key={label} className="border border-gray-200 rounded-lg overflow-hidden">
                      <div className="bg-gray-50 px-3 py-2 border-b border-gray-200 text-xs font-bold text-gray-600">
                        {label}
                      </div>
                      <pre className="p-3 text-[11px] font-mono text-gray-700 whitespace-pre-wrap bg-white max-h-40 overflow-y-auto leading-relaxed">
                        {code}
                      </pre>
                    </div>
                  ) : null
                ))}
              </div>
            </div>
          )}

          {/* AI Test Assertions Section */}
          {assertions.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 px-6 py-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-4 h-4 rounded bg-blue-600 flex items-center justify-center shrink-0">
                  <span className="text-[9px] font-bold text-white">AI</span>
                </div>
                <span className="text-sm font-bold text-gray-800">AI Generated Test Cases</span>
                <span className="ml-2 text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-medium">
                  {assertions.length} assertions
                </span>
              </div>

              {/* Info note */}
              <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-2.5 flex items-center gap-2 mb-4">
                <Info className="w-4 h-4 text-blue-500 shrink-0" />
                <p className="text-xs text-blue-700">
                  These assertions are auto-generated using AI and run in a headless browser against the candidate's submission.
                </p>
              </div>

              {/* Assertions table */}
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-4 py-2.5 text-xs font-semibold text-gray-600 w-8">#</th>
                      <th className="px-4 py-2.5 text-xs font-semibold text-gray-600">Description</th>
                      <th className="px-4 py-2.5 text-xs font-semibold text-gray-600">Trigger</th>
                      <th className="px-4 py-2.5 text-xs font-semibold text-gray-600">Selector</th>
                      <th className="px-4 py-2.5 text-xs font-semibold text-gray-600">Check Type</th>
                      <th className="px-4 py-2.5 text-xs font-semibold text-gray-600 text-center">Sample</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {assertions.map((a: any, i: number) => (
                      <tr key={a.id} className="hover:bg-gray-50">
                        <td className="px-4 py-2.5 text-xs text-gray-400">{i + 1}</td>
                        <td className="px-4 py-2.5 text-xs text-gray-700">{a.description}</td>
                        <td className="px-4 py-2.5">
                          <span className="text-[11px] font-mono bg-purple-50 text-purple-700 px-2 py-0.5 rounded">
                            {a.trigger_action}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 font-mono text-[11px] text-gray-600">{a.selector}</td>
                        <td className="px-4 py-2.5 text-xs text-gray-500">{a.check_type}</td>
                        <td className="px-4 py-2.5 text-center">
                          {a.is_sample ? (
                            <span className="inline-block w-5 h-5 text-green-600">✓</span>
                          ) : (
                            <span className="inline-block w-5 h-5 text-gray-300">✕</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* ── RIGHT SIDEBAR ── */}
        <div className="w-[260px] shrink-0 space-y-4">

          {/* Question Details Card */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100">
              <Clock className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-bold text-gray-800">Question Details</span>
            </div>
            <dl className="space-y-3">
              {[
                { label: "Type", value: "Coding" },
                { label: "Language / Tech", value: question.question_type || "HTML/CSS/JS" },
                { label: "Difficulty", value: "Medium", pill: "orange" },
                { label: "Status", value: question.is_published ? "Active" : "Draft", pill: question.is_published ? "green" : "gray" },
                { label: "Points", value: "5" },
                { label: "Time Limit", value: "60 min" },
                { label: "Created On", value: createdAt },
                { label: "Author", value: "Admin" },
                { label: "Used in Tests", value: "0" },
                { label: "Attempts", value: "0" },
              ].map(({ label, value, pill }) => (
                <div key={label} className="flex items-start justify-between gap-2">
                  <dt className="text-xs text-gray-500 shrink-0">{label}</dt>
                  {pill ? (
                    <dd>
                      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${
                        pill === "orange" ? "bg-orange-100 text-orange-600" :
                        pill === "green" ? "bg-green-100 text-green-700" :
                        "bg-gray-100 text-gray-500"
                      }`}>
                        {value}
                      </span>
                    </dd>
                  ) : (
                    <dd className="text-xs text-gray-800 font-medium text-right">{value}</dd>
                  )}
                </div>
              ))}
            </dl>
          </div>

          {/* Classification Card */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100">
              <Tag className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-bold text-gray-800">Classification</span>
            </div>
            <dl className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <dt className="text-xs text-gray-500 shrink-0">Category</dt>
                <dd className="text-xs text-gray-800 font-medium text-right">Frontend Development</dd>
              </div>
              <div className="flex items-start justify-between gap-2">
                <dt className="text-xs text-gray-500 shrink-0">Question Bank</dt>
                <dd className="text-xs text-gray-800 font-medium text-right">HTML/CSS/JS Coding</dd>
              </div>
              <div className="flex items-start gap-2">
                <dt className="text-xs text-gray-500 shrink-0 mt-0.5">Topics</dt>
                <dd className="flex flex-wrap gap-1">
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-100">
                    Web UI
                  </span>
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-100">
                    JavaScript
                  </span>
                </dd>
              </div>
              <div className="flex items-start justify-between gap-2">
                <dt className="text-xs text-gray-500 shrink-0">Sub Topics</dt>
                <dd className="text-xs text-gray-400">—</dd>
              </div>
            </dl>
          </div>

          {/* Actions Card */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100">
              <Download className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-bold text-gray-800">Actions</span>
            </div>
            <div className="space-y-2">
              <button
                onClick={handleExport}
                className="w-full flex items-center justify-center gap-2 text-sm text-gray-700 border border-gray-300 rounded-md px-4 py-2 hover:bg-gray-50 font-medium"
              >
                <Download className="w-3.5 h-3.5" />
                Export Question
              </button>
              <button
                onClick={() => {
                  const url = `${import.meta.env.VITE_CANDIDATE_URL || "http://localhost:5174"}/test/${id}`;
                  navigator.clipboard.writeText(url);
                }}
                className="w-full flex items-center justify-center gap-2 text-sm text-blue-600 border border-blue-200 rounded-md px-4 py-2 hover:bg-blue-50 font-medium"
              >
                Copy Test Link
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
