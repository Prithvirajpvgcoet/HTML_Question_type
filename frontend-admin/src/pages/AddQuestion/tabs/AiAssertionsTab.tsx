import { useState, useEffect } from "react";
import { api } from "../../../api/client";
import type { Assertion } from "../../../types";
import { Sparkles, Plus, Edit2, Trash2, CheckCircle2, HelpCircle } from "lucide-react";

export function AiAssertionsTab({ questionId, onBack, onNext }: { questionId: string, onBack: () => void, onNext: () => void }) {
  const [assertions, setAssertions] = useState<Assertion[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState(0);

  const getDifficultyBadge = (trigger: string, checkType: string) => {
    if (trigger === "page_load" && checkType === "dom_presence")
      return <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">Easy</span>;
    if ((trigger === "click" || trigger === "input") && checkType === "computed_style")
      return <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">Hard</span>;
    return <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs font-medium">Medium</span>;
  };

  const fetchAssertions = async () => {
    try {
      const res = await api.get(`/questions/${questionId}/assertions`);
      setAssertions(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (questionId) fetchAssertions();
  }, [questionId]);

  const handleGenerateEdgeCases = async () => {
    setIsGenerating(true);
    try {
      const res = await api.post(`/questions/${questionId}/generate-edge-cases`);
      setAssertions(prev => [...prev, ...res.data.assertions]);
    } catch (e) {
      console.error(e);
      alert("Failed to generate edge cases.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerationStep(1);
    setTimeout(() => setGenerationStep(2), 1500);
    try {
      const res = await api.post(`/questions/${questionId}/generate-assertions`);
      setGenerationStep(3);
      setTimeout(() => {
        setAssertions(res.data.assertions || []);
        setIsGenerating(false);
        setGenerationStep(0);
        fetchAssertions();
      }, 1000);
    } catch (e: any) {
      console.error(e);
      setIsGenerating(false);
      setGenerationStep(0);
      
      let errMsg = "Failed to generate assertions.";
      if (e.response?.data?.detail) {
        const detail = e.response.data.detail;
        if (typeof detail === 'string') {
          errMsg = detail;
        } else if (detail.message) {
          errMsg = detail.message;
        }
      }
      alert(errMsg);
    }
  };

  const [editingAssertion, setEditingAssertion] = useState<any | null>(null);

  const handleDeleteAssertion = async (assertionId: string) => {
    try {
      await api.delete(`/questions/assertions/${assertionId}`);
      setAssertions(prev => prev.filter(a => a.id !== assertionId));
    } catch (e) {
      console.error(e);
      alert("Failed to delete assertion");
    }
  };

  const handleSaveEdit = async () => {
    if (!editingAssertion) return;
    try {
      await api.put(`/questions/assertions/${editingAssertion.id}`, editingAssertion);
      setAssertions(prev => prev.map(a => (a.id === editingAssertion.id ? editingAssertion : a)));
      setEditingAssertion(null);
    } catch (e) {
      console.error(e);
      alert("Failed to update assertion");
    }
  };

  return (
    <div className="space-y-6">
      {/* Generate Banner */}
      {assertions.length === 0 && !isGenerating && (
        <div className="bg-blue-50 rounded-lg p-6 flex justify-between items-center border border-blue-100">
          <div className="flex gap-4">
            <div className="bg-white p-3 rounded-full text-blue-600 shadow-sm">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-blue-900">Generate AI Assertions</h3>
              <p className="text-blue-700/80 text-sm mt-1">
                AI generates 6 test cases directly from your question description. Each assertion is a Playwright-ready check covering key frontend requirements.
              </p>
            </div>
          </div>
          <button onClick={handleGenerate} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-md font-medium flex items-center gap-2 shadow-sm transition-colors whitespace-nowrap">
            <Sparkles className="w-4 h-4" />
            Generate with AI
          </button>
        </div>
      )}

      {/* Re-generate / Edge Cases buttons when assertions already exist */}
      {assertions.length > 0 && !isGenerating && (
        <div className="flex justify-between items-center">
          <p className="text-sm text-gray-500">{assertions.length} assertions generated. Each assertion counts as a Playwright test case (50% of total score).</p>
          <div className="flex gap-3">
            <button
              onClick={handleGenerateEdgeCases}
              disabled={isGenerating}
              className="border border-purple-500 text-purple-600 px-4 py-1.5 rounded-md font-medium text-sm hover:bg-purple-50 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> AI Edge Cases
            </button>
            <button onClick={handleGenerate} className="text-blue-600 font-medium flex items-center gap-2 border border-blue-200 px-4 py-1.5 rounded-md hover:bg-blue-50 transition-colors text-sm">
              <Sparkles className="w-4 h-4" />
              Re-generate
            </button>
          </div>
        </div>
      )}

      {/* Assertions Table */}
      {assertions.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-4 border-b border-gray-200 flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-800">AI Generated Assertions (Editable)</h3>
          </div>

          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-gray-500 text-sm border-b border-gray-200">
                <th className="p-4 font-medium w-10">#</th>
                <th className="p-4 font-medium">Trigger</th>
                <th className="p-4 font-medium">Selector / Element</th>
                <th className="p-4 font-medium">Check Type</th>
                <th className="p-4 font-medium">Expected Result</th>
                <th className="p-4 font-medium">Difficulty</th>
                <th className="p-4 font-medium">Points</th>
                <th className="p-4 font-medium text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {assertions.map((a, idx) => (
                <tr key={a.id || idx} className="hover:bg-gray-50/50">
                  <td className="p-4 text-gray-500 text-sm">{idx + 1}</td>
                  <td className="p-4">
                    <span className="bg-blue-50 text-blue-700 text-xs font-mono px-2 py-1 rounded">
                      {a.trigger}
                    </span>
                  </td>
                  <td className="p-4 text-blue-600 font-mono text-sm">{a.trigger_selector && a.trigger_selector !== a.check_selector ? `${a.trigger_selector} → ` : ''}{a.check_selector}</td>
                  <td className="p-4 text-gray-600 text-sm">{a.check_type}</td>
                  <td className="p-4 text-gray-800 text-sm max-w-[200px] truncate">{a.expected_result}</td>
                  <td className="p-4">{getDifficultyBadge(a.trigger, a.check_type)}</td>
                  <td className="p-4 text-gray-800 font-medium">{a.points}</td>
                  <td className="p-4">
                    <div className="flex justify-center gap-3 text-blue-600">
                      <button className="hover:text-blue-800" onClick={() => setEditingAssertion(a)}>
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button className="text-red-400 hover:text-red-600" onClick={() => a.id && handleDeleteAssertion(a.id)}>
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

      {/* Tip */}
      {assertions.length > 0 && (
        <div className="flex items-center gap-2 text-sm text-blue-800 bg-blue-50/60 p-4 rounded-lg border border-blue-100">
          <Sparkles className="w-4 h-4 text-purple-500 shrink-0" />
          <span><span className="font-semibold">Tip:</span> These assertions account for 50% of the total score. LLM semantic verification accounts for the remaining 50%.</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between pt-6 border-t border-gray-200 mt-8">
        <button onClick={onBack} className="px-6 py-2 border border-gray-300 rounded-full text-gray-600 font-medium hover:bg-gray-50">Back</button>
        <div className="flex gap-4">
          <button className="px-6 py-2 border border-gray-300 rounded-full text-gray-600 font-medium hover:bg-gray-50">Save</button>
          <button onClick={onNext} className="px-8 py-2 bg-imocha-orange text-white rounded-full font-medium hover:bg-orange-600 shadow-sm">Next</button>
        </div>
      </div>

      {/* Generation Modal */}
      {isGenerating && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden flex">
            <div className="w-1/3 bg-gray-50 p-6 border-r border-gray-100">
              <h3 className="font-semibold text-gray-800 mb-6">Generate AI Assertions</h3>
              <div className="space-y-6">
                <div className={`flex items-center gap-3 text-sm font-medium ${generationStep >= 1 ? "text-green-600" : "text-gray-400"}`}>
                  <CheckCircle2 className="w-5 h-5" /> Analyze Question
                </div>
                <div className={`flex items-center gap-3 text-sm font-medium ${generationStep >= 2 ? "text-blue-600" : "text-gray-400"}`}>
                  <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs">2</div>
                  Generate 6 Assertions
                </div>
                <div className={`flex items-center gap-3 text-sm font-medium ${generationStep >= 3 ? "text-green-600" : "text-gray-400"}`}>
                  <div className="w-5 h-5 rounded-full border-2 border-gray-300 flex items-center justify-center text-xs">3</div>
                  Review & Validate
                </div>
              </div>
              <button onClick={() => setIsGenerating(false)} className="mt-12 px-6 py-2 border border-gray-300 rounded-full text-gray-600 text-sm font-medium w-full">Cancel</button>
            </div>
            <div className="w-2/3 p-10 flex flex-col items-center text-center justify-center">
              <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-6">
                <Sparkles className="w-8 h-8" />
              </div>
              <h4 className="text-xl font-semibold text-gray-800 mb-4">Generating test cases...</h4>
              <p className="text-gray-500 text-sm mb-8 px-4">
                AI is reading your question description and generating Playwright assertions. This may take a few seconds.
              </p>
              <div className="w-full bg-gray-100 rounded-full h-2 mb-4 overflow-hidden">
                <div className="bg-blue-600 h-2 rounded-full w-1/2 animate-pulse"></div>
              </div>
              <div className="bg-purple-50 text-purple-800 text-xs p-4 rounded-lg flex items-start gap-2 text-left w-full">
                <HelpCircle className="w-4 h-4 mt-0.5 shrink-0" />
                These assertions = 50% of the score. The other 50% comes from LLM semantic verification during candidate evaluation.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingAssertion && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <h3 className="text-lg font-bold text-gray-800 mb-4">Edit Assertion</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Trigger</label>
                <select
                  value={editingAssertion.trigger}
                  onChange={e => setEditingAssertion({...editingAssertion, trigger: e.target.value})}
                  className="w-full border border-gray-300 rounded p-2 focus:ring focus:ring-blue-200 text-sm"
                >
                  <option value="page_load">page_load</option>
                  <option value="click">click</option>
                  <option value="hover">hover</option>
                  <option value="input">input</option>
                  <option value="change">change</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Trigger Selector</label>
                <input
                  type="text"
                  value={editingAssertion.trigger_selector || ''}
                  onChange={e => setEditingAssertion({...editingAssertion, trigger_selector: e.target.value})}
                  className="w-full border border-gray-300 rounded p-2 focus:ring focus:ring-blue-200 text-sm font-mono mb-3"
                  placeholder="#button1"
                />
                <label className="block text-sm font-medium text-gray-700 mb-1">Check Selector</label>
                <input
                  type="text"
                  value={editingAssertion.check_selector || ''}
                  onChange={e => setEditingAssertion({...editingAssertion, check_selector: e.target.value})}
                  className="w-full border border-gray-300 rounded p-2 focus:ring focus:ring-blue-200 text-sm font-mono"
                  placeholder="#targetElement"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Check Type</label>
                <select
                  value={editingAssertion.check_type}
                  onChange={e => setEditingAssertion({...editingAssertion, check_type: e.target.value})}
                  className="w-full border border-gray-300 rounded p-2 focus:ring focus:ring-blue-200 text-sm"
                >
                  <option value="dom_presence">dom_presence</option>
                  <option value="computed_style">computed_style</option>
                  <option value="text_content">text_content</option>
                  <option value="attribute">attribute</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Expected Result</label>
                <textarea
                  rows={3}
                  value={editingAssertion.expected_result}
                  onChange={e => setEditingAssertion({...editingAssertion, expected_result: e.target.value})}
                  className="w-full border border-gray-300 rounded p-2 focus:ring focus:ring-blue-200 text-sm"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Points</label>
                <input
                  type="number"
                  value={editingAssertion.points}
                  onChange={e => setEditingAssertion({...editingAssertion, points: parseInt(e.target.value, 10)})}
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
