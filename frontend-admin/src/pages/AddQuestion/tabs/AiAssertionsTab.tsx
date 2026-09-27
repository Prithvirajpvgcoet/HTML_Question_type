import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../../../api/client";
import type { Assertion } from "../../../types";
import { Sparkles, Plus, Edit2, Trash2, CheckCircle2, HelpCircle, XCircle, AlertTriangle, RefreshCw } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

type JobStatus = "queued" | "analyzing" | "validating" | "completed" | "failed" | "cancelled";

interface Job {
  job_id: string;
  status: JobStatus;
  mode: string;
  elapsed_seconds: number;
  error_message: string | null;
  repair_round: number;
  assertions?: AssertionWithStatus[];
  passed_count?: number;
  failed_count?: number;
}

interface AssertionWithStatus extends Assertion {
  last_validation_status: "passed" | "failed" | "not_run";
  last_validation_error: string | null;
  assertion_set_version: number;
}

// ─── Status Pill ─────────────────────────────────────────────────────────────

function StatusPill({ status, error }: { status: string; error?: string | null }) {
  if (status === "passed")
    return <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-medium">✅ Verified</span>;
  if (status === "failed")
    return (
      <span
        className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-medium cursor-help"
        title={error || "Assertion failed"}
      >
        ❌ Failed
      </span>
    );
  return <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full text-xs font-medium">⏳ Pending</span>;
}

// ─── Generation Progress Modal ────────────────────────────────────────────────

function GenerationModal({
  job,
  onCancel,
}: {
  job: Job;
  onCancel: () => void;
}) {
  const steps: { label: string; key: JobStatus[] }[] = [
    { label: "Analyze question", key: ["queued", "analyzing", "validating", "completed", "failed", "cancelled"] },
    { label: "Generate assertions", key: ["analyzing", "validating", "completed", "failed", "cancelled"] },
    { label: "Validate against reference code", key: ["validating", "completed", "failed", "cancelled"] },
  ];

  const stepIndex =
    job.status === "queued" ? 0
    : job.status === "analyzing" ? 1
    : job.status === "validating" ? 2
    : 3;

  const isFailed = job.status === "failed";

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden flex">
        {/* Left: Steps */}
        <div className="w-1/3 bg-gray-50 p-6 border-r border-gray-100 flex flex-col">
          <h3 className="font-semibold text-gray-800 mb-6">Generate AI Assertions</h3>
          <div className="space-y-5 flex-1">
            {steps.map((step, i) => {
              const done = stepIndex > i;
              const active = stepIndex === i && !isFailed;
              return (
                <div key={i} className={`flex items-center gap-3 text-sm font-medium ${done ? "text-green-600" : active ? "text-blue-600" : "text-gray-400"}`}>
                  {done ? (
                    <CheckCircle2 className="w-5 h-5" />
                  ) : (
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs ${active ? "border-blue-600 bg-blue-600 text-white" : "border-gray-300"}`}>
                      {i + 1}
                    </div>
                  )}
                  {step.label}
                </div>
              );
            })}
          </div>
          <button
            onClick={onCancel}
            className="mt-8 px-4 py-2 border border-gray-300 rounded-full text-gray-600 text-sm font-medium w-full hover:bg-gray-100"
          >
            Cancel
          </button>
        </div>

        {/* Right: Status */}
        <div className="w-2/3 p-10 flex flex-col items-center text-center justify-center">
          {isFailed ? (
            <>
              <XCircle className="w-12 h-12 text-red-500 mb-4" />
              <h4 className="text-lg font-semibold text-gray-800 mb-2">Generation Failed</h4>
              <p className="text-red-600 text-sm px-4">{job.error_message || "Unknown error"}</p>
            </>
          ) : (
            <>
              <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-6 animate-pulse">
                <Sparkles className="w-8 h-8" />
              </div>
              <h4 className="text-xl font-semibold text-gray-800 mb-2">
                {job.status === "validating" ? "Validating against your reference code…" : "Generating assertions…"}
              </h4>
              <p className="text-gray-500 text-sm mb-6 px-4">
                {job.status === "validating"
                  ? "Running Playwright to check each assertion against your reference solution."
                  : "AI is reading your question description and generating Playwright assertions."}
              </p>
              <div className="w-full bg-gray-100 rounded-full h-2 mb-3 overflow-hidden">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-1000"
                  style={{ width: `${Math.min(95, (job.elapsed_seconds / 90) * 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-400">{Math.round(job.elapsed_seconds)}s elapsed</p>
              <div className="bg-purple-50 text-purple-800 text-xs p-3 rounded-lg flex items-start gap-2 text-left w-full mt-6">
                <HelpCircle className="w-4 h-4 mt-0.5 shrink-0" />
                These assertions = 50% of the score. The other 50% comes from LLM semantic verification.
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Validation Banner ────────────────────────────────────────────────────────

function ValidationBanner({
  passed,
  failed,
  repairRoundsUsed,
  onComplete,
  onRepair,
  isLoading,
}: {
  passed: AssertionWithStatus[];
  failed: AssertionWithStatus[];
  repairRoundsUsed: number;
  onComplete: () => void;
  onRepair: () => void;
  isLoading: boolean;
}) {
  const canRepair = repairRoundsUsed < 2;

  // Edge case: everything failed — no point in "keep passing" options
  if (passed.length === 0) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-red-600" />
          <span className="text-red-700 font-semibold">All {failed.length} assertions failed validation.</span>
        </div>
        <p className="text-gray-600 text-sm">
          The generated assertions don't match your reference solution at all. A full regeneration is recommended.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-amber-600" />
        <span className="text-gray-800 font-semibold">
          ✅ {passed.length} verified · ❌ {failed.length} need attention
        </span>
      </div>
      <p className="text-gray-600 text-sm -mt-2">
        {failed.length} assertion{failed.length !== 1 ? "s" : ""} failed against your reference code. Choose how to fix them:
      </p>
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={onRepair}
          disabled={isLoading || !canRepair}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-md font-medium text-sm transition-colors flex items-center gap-2"
          title={!canRepair ? "Maximum auto-repair attempts reached. Edit manually." : undefined}
        >
          <RefreshCw className="w-4 h-4" />
          Fix these {failed.length} (attempt {repairRoundsUsed + 1}/2)
        </button>
        <button
          onClick={onComplete}
          disabled={isLoading}
          className="bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 text-gray-700 px-4 py-2 rounded-md font-medium text-sm transition-colors"
        >
          Discard & add {failed.length} fresh new
        </button>
        {!canRepair && (
          <span className="text-xs text-amber-700 self-center">
            ⚠ Auto-repair limit reached. Use the edit (✏) button on failing rows.
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function AiAssertionsTab({
  questionId,
  onBack,
  onNext,
}: {
  questionId: string;
  onBack: () => void;
  onNext: () => void;
}) {
  const [assertions, setAssertions] = useState<AssertionWithStatus[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [validationResult, setValidationResult] = useState<{
    passed: AssertionWithStatus[];
    failed: AssertionWithStatus[];
    repairRoundsUsed: number;
  } | null>(null);
  const [editingAssertion, setEditingAssertion] = useState<AssertionWithStatus | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  };

  const getDifficultyBadge = (trigger: string, checkType: string) => {
    if (trigger === "page_load" && checkType === "dom_presence")
      return <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">Easy</span>;
    if ((trigger === "click" || trigger === "input") && checkType === "computed_style")
      return <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">Hard</span>;
    return <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs font-medium">Medium</span>;
  };

  // ── Polling ────────────────────────────────────────────────────────────────

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const handleJobResponse = useCallback(
    (data: Job) => {
      setJob(data);

      if (data.status === "completed") {
        stopPolling();
        const all = data.assertions || [];
        setAssertions(all);
        const passed = all.filter((a) => a.last_validation_status === "passed");
        const failed = all.filter((a) => a.last_validation_status === "failed");

        // Count completed repair jobs to know if we've hit the limit
        const repairRoundsUsed = data.repair_round ?? 0;

        if (failed.length > 0 && passed.length > 0) {
          setValidationResult({ passed, failed, repairRoundsUsed });
        } else if (failed.length === 0) {
          setValidationResult(null);
          showToast(`✅ All ${passed.length} assertions verified against your reference code.`);
        } else {
          // All failed edge-case — still show the banner so user can full-regen
          setValidationResult({ passed: [], failed, repairRoundsUsed });
        }
      } else if (data.status === "failed") {
        stopPolling();
        showToast(`Generation failed: ${data.error_message || "Unknown error"}`);
      } else if (data.status === "cancelled") {
        stopPolling();
      }
    },
    [stopPolling]
  );

  const startPolling = useCallback(
    (jobId: string) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const res = await api.get(`/questions/${questionId}/generation-jobs/${jobId}`);
          handleJobResponse(res.data);
        } catch {
          // Network blip — keep polling
        }
      }, 2000);
    },
    [questionId, handleJobResponse, stopPolling]
  );

  // ── On mount: resume any in-flight job ─────────────────────────────────────

  useEffect(() => {
    if (!questionId) return;

    const init = async () => {
      // Fetch existing assertions first
      try {
        const res = await api.get(`/questions/${questionId}/assertions`);
        setAssertions(res.data || []);
        const all: AssertionWithStatus[] = res.data || [];
        const passed = all.filter((a) => a.last_validation_status === "passed");
        const failed = all.filter((a) => a.last_validation_status === "failed");
        if (failed.length > 0 && passed.length > 0) {
          setValidationResult({ passed, failed, repairRoundsUsed: 0 });
        }
      } catch {
        /* ignore */
      }

      // Check for any in-flight job to resume polling
      try {
        const res = await api.get(`/questions/${questionId}/generation-jobs/active`);
        const data: Job = res.data;
        if (["queued", "analyzing", "validating"].includes(data.status)) {
          setJob(data);
          startPolling(data.job_id);
        } else if (data.status === "completed" && data.assertions) {
          handleJobResponse(data);
        }
      } catch {
        // No active job — that's fine
      }
    };

    init();
    return () => stopPolling();
  }, [questionId]);

  // ── Job launchers ──────────────────────────────────────────────────────────

  const launchJob = async (endpoint: string, body?: object) => {
    try {
      const res = await api.post(endpoint, body);
      const data: Job = res.data;
      setJob(data);
      setValidationResult(null);
      startPolling(data.job_id);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      if (e?.response?.status === 422) {
        showToast(`⚠ ${detail}`);
      } else if (e?.response?.status === 409) {
        showToast("A generation is already in progress.");
      } else {
        showToast(`Failed: ${detail || e.message}`);
      }
    }
  };

  const handleGenerate = () =>
    launchJob(`/questions/${questionId}/generate-assertions`);

  const handleComplete = () => {
    if (!validationResult) return;
    launchJob(`/questions/${questionId}/assertions/complete`, {
      keep_assertion_ids: validationResult.passed.map((a) => a.id),
      target_count: 6,
    });
  };

  const handleRepair = () => {
    if (!validationResult) return;
    const version = validationResult.passed[0]?.assertion_set_version ?? 1;
    launchJob(`/questions/${questionId}/assertions/repair`, {
      keep_assertion_ids: validationResult.passed.map((a) => a.id),
      failed_assertion_ids: validationResult.failed.map((a) => a.id),
      assertion_set_version: version,
    });
  };

  const handleCancelJob = async () => {
    if (!job) return;
    try {
      await api.post(`/questions/${questionId}/generation-jobs/${job.job_id}/cancel`);
      stopPolling();
      setJob(null);
    } catch {
      showToast("Could not cancel the job.");
    }
  };

  // ── Assertion CRUD ─────────────────────────────────────────────────────────

  const handleDeleteAssertion = async (assertionId: string) => {
    try {
      await api.delete(`/questions/assertions/${assertionId}`);
      const next = assertions.filter((a) => a.id !== assertionId);
      setAssertions(next);
      // Recompute banner
      const passed = next.filter((a) => a.last_validation_status === "passed");
      const failed = next.filter((a) => a.last_validation_status === "failed");
      setValidationResult(failed.length > 0 ? { passed, failed, repairRoundsUsed: validationResult?.repairRoundsUsed ?? 0 } : null);
    } catch {
      showToast("Failed to delete assertion.");
    }
  };

  const handleSaveEdit = async () => {
    if (!editingAssertion) return;
    try {
      const res = await api.put(`/questions/assertions/${editingAssertion.id}`, editingAssertion);
      const updated: AssertionWithStatus = res.data;
      const next = assertions.map((a) => (a.id === updated.id ? updated : a));
      setAssertions(next);
      setEditingAssertion(null);
      showToast("Assertion saved. Re-validate to confirm it still passes.");
    } catch {
      showToast("Failed to save changes.");
    }
  };

  const handleSaveAll = async () => {
    if (assertions.length === 0) { showToast("Generate assertions before saving."); return; }
    setIsSaving(true);
    try {
      showToast("Assertions saved ✓");
      onNext();
    } finally {
      setIsSaving(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  const isJobInFlight = job != null && ["queued", "analyzing", "validating"].includes(job.status);

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div className="fixed top-5 right-5 z-50 bg-gray-900 text-white text-sm px-4 py-2.5 rounded-lg shadow-lg">
          {toast}
        </div>
      )}

      {/* Generation Modal (overlay) */}
      {isJobInFlight && job && (
        <GenerationModal job={job} onCancel={handleCancelJob} />
      )}

      {/* Initial Generate Banner — only when no assertions and nothing running */}
      {assertions.length === 0 && !isJobInFlight && (
        <div className="bg-blue-50 rounded-lg p-6 flex justify-between items-center border border-blue-100">
          <div className="flex gap-4">
            <div className="bg-white p-3 rounded-full text-blue-600 shadow-sm">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-blue-900">Generate AI Assertions</h3>
              <p className="text-blue-700/80 text-sm mt-1">
                AI generates test cases from your question description. Each assertion is a Playwright-ready check.
              </p>
            </div>
          </div>
          <button
            onClick={handleGenerate}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-md font-medium flex items-center gap-2 shadow-sm transition-colors whitespace-nowrap"
          >
            <Sparkles className="w-4 h-4" />
            Generate with AI
          </button>
        </div>
      )}

      {/* Toolbar when assertions exist */}
      {assertions.length > 0 && !isJobInFlight && (
        <div className="flex justify-between items-center">
          <p className="text-sm text-gray-500">
            {assertions.length} assertions ·{" "}
            <span className="text-green-700">{assertions.filter((a) => a.last_validation_status === "passed").length} verified</span>
            {assertions.filter((a) => a.last_validation_status === "failed").length > 0 && (
              <span className="text-red-600 ml-1">· {assertions.filter((a) => a.last_validation_status === "failed").length} failed</span>
            )}
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => launchJob(`/questions/${questionId}/generate-edge-cases`)}
              disabled={isJobInFlight}
              className="border border-purple-500 text-purple-600 px-4 py-1.5 rounded-md font-medium text-sm hover:bg-purple-50 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> AI Edge Cases
            </button>
            <button
              onClick={handleGenerate}
              className="text-blue-600 font-medium flex items-center gap-2 border border-blue-200 px-4 py-1.5 rounded-md hover:bg-blue-50 transition-colors text-sm"
            >
              <RefreshCw className="w-4 h-4" /> Re-generate all
            </button>
          </div>
        </div>
      )}

      {/* Validation Banner */}
      {validationResult && !isJobInFlight && (
        <ValidationBanner
          passed={validationResult.passed}
          failed={validationResult.failed}
          repairRoundsUsed={validationResult.repairRoundsUsed}
          onComplete={handleComplete}
          onRepair={handleRepair}
          isLoading={false}
        />
      )}

      {/* Assertions Table */}
      {assertions.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800">AI Generated Assertions</h3>
          </div>
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-gray-500 text-sm border-b border-gray-200">
                <th className="p-4 font-medium w-8">#</th>
                <th className="p-4 font-medium w-28">Status</th>
                <th className="p-4 font-medium">Trigger</th>
                <th className="p-4 font-medium">Selector / Element</th>
                <th className="p-4 font-medium">Check</th>
                <th className="p-4 font-medium">Expected Result</th>
                <th className="p-4 font-medium">Difficulty</th>
                <th className="p-4 font-medium">Pts</th>
                <th className="p-4 font-medium text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {assertions.map((a, idx) => (
                <tr
                  key={a.id || idx}
                  className={`hover:bg-gray-50/50 ${a.last_validation_status === "failed" ? "bg-red-50/30" : a.last_validation_status === "passed" ? "bg-green-50/20" : ""}`}
                >
                  <td className="p-4 text-gray-400 text-sm">{idx + 1}</td>
                  <td className="p-4">
                    <StatusPill status={a.last_validation_status} error={a.last_validation_error} />
                  </td>
                  <td className="p-4">
                    <span className="bg-blue-50 text-blue-700 text-xs font-mono px-2 py-1 rounded">
                      {a.trigger}
                    </span>
                  </td>
                  <td className="p-4 text-blue-600 font-mono text-xs max-w-[160px] truncate">
                    {a.trigger_selector && a.trigger_selector !== a.check_selector
                      ? `${a.trigger_selector} → `
                      : ""}
                    {a.check_selector}
                  </td>
                  <td className="p-4 text-gray-600 text-sm">{a.check_type}</td>
                  <td className="p-4 text-gray-800 text-sm max-w-[180px]">
                    <span className="truncate block" title={a.expected_result}>{a.expected_result}</span>
                    {a.last_validation_status === "failed" && a.last_validation_error && (
                      <span className="block text-xs text-red-500 mt-0.5 truncate" title={a.last_validation_error}>
                        ↳ {a.last_validation_error}
                      </span>
                    )}
                  </td>
                  <td className="p-4">{getDifficultyBadge(a.trigger, a.check_type)}</td>
                  <td className="p-4 text-gray-800 font-medium text-sm">{a.points}</td>
                  <td className="p-4">
                    <div className="flex justify-center gap-3">
                      <button
                        className="text-gray-400 hover:text-blue-600"
                        title="Edit assertion"
                        onClick={() => setEditingAssertion(a)}
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        className="text-gray-400 hover:text-red-600"
                        title="Delete assertion"
                        onClick={() => a.id && handleDeleteAssertion(a.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Score tip */}
      {assertions.length > 0 && (
        <div className="flex items-center gap-2 text-sm text-blue-800 bg-blue-50/60 p-4 rounded-lg border border-blue-100">
          <Sparkles className="w-4 h-4 text-purple-500 shrink-0" />
          <span>
            <span className="font-semibold">Tip:</span> These assertions account for 50% of the total score.
            LLM semantic verification covers the remaining 50%.
          </span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between pt-6 border-t border-gray-200 mt-8">
        <button
          onClick={onBack}
          className="px-6 py-2 border border-gray-300 rounded-full text-gray-600 font-medium hover:bg-gray-50"
        >
          Back
        </button>
        <div className="flex gap-4">
          <button
            onClick={handleSaveAll}
            disabled={isSaving || assertions.length === 0}
            className="px-6 py-2 border border-gray-300 rounded-full text-gray-600 font-medium hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isSaving ? "Saving…" : "Save"}
          </button>
          <button
            onClick={onNext}
            className="px-8 py-2 bg-imocha-orange text-white rounded-full font-medium hover:bg-orange-600 shadow-sm"
          >
            Next
          </button>
        </div>
      </div>

      {/* Edit Modal */}
      {editingAssertion && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-start justify-between mb-4">
              <h3 className="text-lg font-bold text-gray-800">Edit Assertion</h3>
              {editingAssertion.last_validation_status === "failed" && editingAssertion.last_validation_error && (
                <div className="bg-red-50 border border-red-200 rounded-md px-3 py-2 text-xs text-red-700 max-w-[55%]">
                  <span className="font-semibold block mb-0.5">Why it failed:</span>
                  {editingAssertion.last_validation_error}
                </div>
              )}
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Trigger</label>
                <select
                  value={editingAssertion.trigger}
                  onChange={(e) => setEditingAssertion({ ...editingAssertion, trigger: e.target.value })}
                  className="w-full border border-gray-300 rounded p-2 focus:ring focus:ring-blue-200 text-sm"
                >
                  {["page_load", "click", "hover", "input", "change"].map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Trigger Selector</label>
                <input
                  type="text"
                  value={editingAssertion.trigger_selector || ""}
                  onChange={(e) => setEditingAssertion({ ...editingAssertion, trigger_selector: e.target.value })}
                  className="w-full border border-gray-300 rounded p-2 focus:ring focus:ring-blue-200 text-sm font-mono mb-3"
                  placeholder="#button1"
                />
                <label className="block text-sm font-medium text-gray-700 mb-1">Check Selector</label>
                <input
                  type="text"
                  value={editingAssertion.check_selector || ""}
                  onChange={(e) => setEditingAssertion({ ...editingAssertion, check_selector: e.target.value })}
                  className="w-full border border-gray-300 rounded p-2 focus:ring focus:ring-blue-200 text-sm font-mono"
                  placeholder="#targetElement"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Check Type</label>
                <select
                  value={editingAssertion.check_type}
                  onChange={(e) => setEditingAssertion({ ...editingAssertion, check_type: e.target.value })}
                  className="w-full border border-gray-300 rounded p-2 focus:ring focus:ring-blue-200 text-sm"
                >
                  {["dom_presence", "computed_style", "text_content", "attribute"].map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Expected Result</label>
                <textarea
                  rows={3}
                  value={editingAssertion.expected_result}
                  onChange={(e) => setEditingAssertion({ ...editingAssertion, expected_result: e.target.value })}
                  className="w-full border border-gray-300 rounded p-2 focus:ring focus:ring-blue-200 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Points</label>
                <input
                  type="number"
                  value={editingAssertion.points}
                  onChange={(e) => setEditingAssertion({ ...editingAssertion, points: parseInt(e.target.value, 10) })}
                  className="w-full border border-gray-300 rounded p-2 focus:ring focus:ring-blue-200 text-sm"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setEditingAssertion(null)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-600 hover:bg-gray-50 text-sm font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
