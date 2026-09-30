import { useState, useEffect } from "react";
import { api } from "../../../api/client";
import { TestCaseTable } from "./TestCaseTable";

export function ReviewTab({ questionId, onBack, onPublish }: { questionId: string, onBack: () => void, onPublish: () => void }) {
  const [assertions, setAssertions] = useState<any[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [running, setRunning] = useState(false);
  const [validationStatus, setValidationStatus] = useState<string>("unvalidated");
  
  useEffect(() => {
    if (!questionId) return;
    
    api.get(`/questions/${questionId}`).then(res => {
      setValidationStatus(res.data.validation_status || "unvalidated");
      
      if (res.data.last_validation_results) {
        try {
          const parsed = JSON.parse(res.data.last_validation_results);
          if (parsed && parsed.run_1) {
            setResults(parsed.run_1);
          } else {
            setResults(Array.isArray(parsed) ? parsed : []);
          }
        } catch (e) {
          console.error("Failed to parse last validation results", e);
        }
      }
    });
    
    api.get(`/questions/${questionId}/assertions`).then(res => {
      setAssertions(res.data);
    });
  }, [questionId]);

  const handleCompileAndRun = async () => {
    setRunning(true);
    try {
      const res = await api.post(`/questions/${questionId}/code-solution/validate`);
      setResults(res.data.results);
      setValidationStatus(res.data.all_passed ? "passed" : "failed");
    } catch (e) {
      console.error("Compile failed", e);
      alert("Validation failed. Please try again.");
    } finally {
      setRunning(false);
    }
  };

  const isValidated = validationStatus === "passed";

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-sm">
      <div className="flex-1 overflow-auto p-8 pb-32">
        <div className="mb-6">
          <h2 className="text-xl font-bold text-gray-800">Review & Validate</h2>
          <p className="text-gray-500 text-sm mt-1">
            Run the AI generated assertions against your reference code solution to verify they are correct before publishing.
          </p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
          <div className="flex justify-between items-center bg-gray-50 p-4 border-b border-gray-200">
            <h3 className="font-semibold text-gray-700">Assertion Validation</h3>
            <div className="flex items-center gap-4">
              {validationStatus === "failed" && <span className="text-sm font-bold text-red-600">Some assertions failed! Edit the code or the assertions.</span>}
              {validationStatus === "passed" && <span className="text-sm font-bold text-green-600">? All assertions passed against reference code</span>}
              {validationStatus === "unvalidated" && <span className="text-sm font-medium text-amber-600">Please Validate Assertions.</span>}
              
              <button 
                onClick={handleCompileAndRun}
                disabled={running || assertions.length === 0}
                className="bg-blue-600 text-white px-6 py-2 rounded-md font-medium text-sm shadow hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {running ? "Validating..." : "Validate Assertions"}
              </button>
            </div>
          </div>
          
          <div className="p-0">
            <TestCaseTable assertions={assertions} results={results} />
          </div>
        </div>

        {isValidated && (
          <div className="mt-8 bg-green-50 border border-green-200 rounded-lg p-8 text-center shadow-sm max-w-2xl mx-auto">
            <div className="w-12 h-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-3 text-xl">?</div>
            <h3 className="text-xl font-bold text-gray-800 mb-2">Ready to Publish</h3>
            <p className="text-gray-600 mb-6 text-sm">Your question has been configured, assertions are set, and the reference solution compiles correctly.</p>
            
            <div className="flex gap-4 justify-center">
              <button onClick={() => window.open(`${import.meta.env.VITE_CANDIDATE_URL || "http://localhost:5174"}/test/${questionId}`, "_blank")} className="px-5 py-2 border border-gray-300 rounded-md text-gray-700 font-medium hover:bg-white bg-gray-50 text-sm">
                Preview Candidate View
              </button>
            </div>
          </div>
        )}
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
          {!isValidated && (
            <span className="text-sm text-red-600 font-medium mr-2">
              ⚠️ Must pass all assertions to publish
            </span>
          )}
          <button 
            disabled={!isValidated}
            onClick={onPublish}
            className={`px-8 py-2 rounded-full font-medium shadow-sm transition-all ${isValidated ? "bg-imocha-orange text-white hover:bg-orange-600" : "bg-gray-300 text-gray-500 cursor-not-allowed"}`}
          >
            Publish Question
          </button>
        </div>
      </div>
    </div>
  );
}
