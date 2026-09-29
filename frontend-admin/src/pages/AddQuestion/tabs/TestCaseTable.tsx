import { useState } from "react";

type Assertion = {
  id: string;
  trigger: string;
  trigger_selector: string | null;
  check_selector: string | null;
  check_type: string;
  input_value?: string;
  property_name?: string;
  operator: string;
  expected_value?: string;
  points: number;
  is_sample: boolean;
  execution_mode?: string;
  group_id?: string | null;
  sequence_order?: number | null;
  depends_on_state?: string | null;
};

type ValidationResult = {
  assertion_id: string;
  passed: boolean;
  actual_value: string;
  error: string;
  points_awarded: number;
};

type Props = {
  assertions: Assertion[];
  results: ValidationResult[];
};

function describeTrigger(a: Assertion): string {
  const map: Record<string, string> = {
    page_load: "On page load",
    click: `Click ${a.trigger_selector}`,
    hover: `Hover ${a.trigger_selector}`,
    input: `Type into ${a.trigger_selector}`,
    change: `Change ${a.trigger_selector}`,
    call_function: `Call ${a.trigger_selector}(${a.input_value || "[]"})`,
  };
  return map[a.trigger] ?? a.trigger;
}

function describeCheck(a: Assertion): string {
  const map: Record<string, string> = {
    dom_presence: `${a.check_selector} exists`,
    dom_absence: `${a.check_selector} does not exist`,
    element_count: `${a.check_selector} count`,
    computed_style: `${a.check_selector} (style)`,
    attribute: `${a.check_selector} (attribute)`,
    text_content: `${a.check_selector} text`,
  };
  return map[a.check_type] ?? a.check_type;
}

export function TestCaseTable({ assertions, results }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(
    assertions[0]?.id ?? null
  );

  const resultFor = (assertionId: string) =>
    results.find((r) => r.assertion_id === assertionId);

  const selectedAssertion = assertions.find((a) => a.id === selectedId) || assertions[0];
  const selectedResult = selectedAssertion ? resultFor(selectedAssertion.id) : undefined;

  return (
    <div className="flex gap-4 min-h-[400px]">
      {/* left: list */}
      <div className="w-1/3 border border-gray-200 rounded-lg divide-y bg-white overflow-hidden shadow-sm">
        {assertions.length === 0 ? (
          <div className="p-8 text-center text-gray-500 italic text-sm">
            No assertions available. Go to the AI Assertions tab to generate them.
          </div>
        ) : null}
        
        {assertions.map((a, idx) => {
          const result = resultFor(a.id);
          const isSelected = (selectedId === null && idx === 0) || selectedId === a.id;
          
          return (
            <button
              key={a.id}
              onClick={() => setSelectedId(a.id)}
              className={`w-full text-left px-4 py-3 transition-colors ${
                isSelected ? "bg-blue-50 border-l-4 border-l-blue-500" : "hover:bg-gray-50 border-l-4 border-l-transparent"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-gray-800 text-sm flex items-center gap-1.5">
                  Test Case {idx + 1}
                  {a.is_sample && (
                    <span className="bg-green-100 text-green-700 text-[10px] px-1.5 py-0.5 rounded-full font-bold" title="Sample Case">
                      S
                    </span>
                  )}
                </span>
                <span className="text-xs text-gray-400 font-medium">{a.points} pts</span>
              </div>
              <div className="text-xs flex justify-between items-center mt-2">
                <span className="text-gray-500 truncate max-w-[120px]">{a.trigger}</span>
                {result ? (
                  <span
                    className={`px-2 py-0.5 rounded font-bold uppercase tracking-wide text-[10px] ${
                      result.passed
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {result.passed ? "Pass" : "Fail"}
                  </span>
                ) : (
                  <span className="text-gray-400 bg-gray-100 px-2 py-0.5 rounded uppercase tracking-wide text-[10px] font-bold">Not run</span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* right: detail panel */}
      <div className="flex-1 border border-gray-200 rounded-lg p-6 bg-white shadow-sm flex flex-col">
        {selectedAssertion ? (
          <>
            <div className="flex justify-between items-center border-b border-gray-100 pb-4 mb-4">
              <h3 className="font-bold text-gray-800 text-lg">Test Case Details</h3>
              <div className="text-sm text-gray-500 flex gap-4">
                <span>Memory: <strong className="text-gray-700">0 KB</strong></span>
                <span>
                  Time:{" "}
                  <strong className="text-gray-700">
                    {selectedResult ? (selectedResult.passed ? "15 ms" : "Timeout") : "-"}
                  </strong>
                </span>
              </div>
            </div>

            <div className="space-y-6 flex-1">
              <div>
                <div className="font-semibold text-gray-700 text-sm mb-1 uppercase tracking-wide">Action Trigger</div>
                <div className="text-gray-800 bg-gray-50 p-3 rounded text-sm font-mono border border-gray-100">
                  {describeTrigger(selectedAssertion)}
                </div>
              </div>

              <div>
                <div className="font-semibold text-gray-700 text-sm mb-1 uppercase tracking-wide">Verification Check</div>
                <div className="text-gray-800 bg-gray-50 p-3 rounded text-sm font-mono border border-gray-100">
                  {describeCheck(selectedAssertion)}
                </div>
              </div>

              <div>
                <div className="font-semibold text-gray-700 text-sm mb-1 uppercase tracking-wide">Expected Output</div>
                <div className="text-gray-800 bg-blue-50 p-3 rounded text-sm font-mono border border-blue-100 whitespace-pre-wrap">
                  {selectedAssertion.property_name ? `${selectedAssertion.property_name} ` : ""}
                  {selectedAssertion.operator} {selectedAssertion.expected_value ?? ""}
                </div>
              </div>

              <div>
                <div className="font-semibold text-gray-700 text-sm mb-1 uppercase tracking-wide">Actual output</div>
                <div className={`p-3 rounded text-sm font-mono border whitespace-pre-wrap min-h-[60px] ${
                  selectedResult 
                    ? selectedResult.passed 
                      ? "bg-green-50 text-green-800 border-green-200" 
                      : "bg-red-50 text-red-800 border-red-200"
                    : "bg-gray-50 text-gray-500 border-gray-100"
                }`}>
                  {selectedResult ? (
                    selectedResult.error || selectedResult.actual_value || "No output returned"
                  ) : (
                    "Click 'Compile and Run' to execute this test case."
                  )}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 italic">
            Select a test case to view details
          </div>
        )}
      </div>
    </div>
  );
}
