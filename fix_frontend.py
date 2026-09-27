import re

with open('frontend-admin/src/pages/AddQuestion/tabs/AiAssertionsTab.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Add validationResult state
if "const [validationResult" not in text:
    state_injection = '''  const [validationResult, setValidationResult] = useState<{passed: any[], failed: any[]} | null>(null);'''
    text = text.replace('const [toast, setToast]', state_injection + '\n  const [toast, setToast]')

# Rewrite handleGenerate
old_handle_generate = '''  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerationStep(1);
    setTimeout(() => setGenerationStep(2), 1500);
    try {
      const res = await api.post(/questions//generate-assertions);
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
  };'''

new_handle_generate = '''  const handleComplete = async () => {
    setIsGenerating(true);
    try {
      const res = await api.post(/questions//assertions/complete, {
        keep_assertion_ids: validationResult!.passed.map(a => a.id), 
        target_count: 6,
      });
      setAssertions(res.data.assertions);
      const passed = res.data.assertions.filter((a: any) => a.last_validation_status === "passed");
      const failed = res.data.assertions.filter((a: any) => a.last_validation_status === "failed");
      setValidationResult(failed.length ? { passed, failed } : null);
    } catch(e) {
      console.error(e);
      alert("Failed to complete assertions");
    } finally { setIsGenerating(false); }
  };

  const handleRepair = async () => {
    setIsGenerating(true);
    try {
      const res = await api.post(/questions//assertions/repair, {
        failed_assertion_ids: validationResult!.failed.map(a => a.id),
        keep_assertion_ids: validationResult!.passed.map(a => a.id),
      });
      setAssertions(res.data.assertions);
      const passed = res.data.assertions.filter((a: any) => a.last_validation_status === "passed");
      const failed = res.data.assertions.filter((a: any) => a.last_validation_status === "failed");
      setValidationResult(failed.length ? { passed, failed } : null);
    } catch(e) {
      console.error(e);
      alert("Failed to repair assertions");
    } finally { setIsGenerating(false); }
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerationStep(1);
    setTimeout(() => setGenerationStep(2), 1500);
    try {
      const res = await api.post(/questions//generate-assertions);
      setGenerationStep(3);
      setTimeout(() => {
        setAssertions(res.data.assertions || []);
        const passed = (res.data.assertions || []).filter((a: any) => a.last_validation_status === "passed");
        const failed = (res.data.assertions || []).filter((a: any) => a.last_validation_status === "failed");
        setValidationResult(failed.length > 0 ? { passed, failed } : null);
        setIsGenerating(false);
        setGenerationStep(0);
      }, 1000);
    } catch (e: any) {
      console.error(e);
      setIsGenerating(false);
      setGenerationStep(0);
      alert("Failed to generate assertions.");
    }
  };'''

text = text.replace(old_handle_generate, new_handle_generate)

# Inject the validationResult UI before the assertions table
banner_ui = '''
      {/* Validation Result Banner */}
      {validationResult && !isGenerating && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <span className="text-red-600 font-bold">⚠️ Validation Failed</span>
            <span className="text-gray-700 text-sm">{validationResult.failed.length} assertions failed against your reference code.</span>
          </div>
          <div className="flex gap-4">
            <button onClick={handleComplete} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium text-sm transition-colors">
              Keep {validationResult.passed.length} valid, add {validationResult.failed.length} new
            </button>
            <button onClick={handleRepair} className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded font-medium text-sm transition-colors">
              Keep {validationResult.passed.length} valid, fix the other {validationResult.failed.length}
            </button>
          </div>
        </div>
      )}
'''

text = text.replace('{/* Assertions Table */}', banner_ui + '\n      {/* Assertions Table */}')

# Add status pill in the table row
status_pill = '''
                  <td className="p-4 align-top">
                    <span className={px-2 py-1 text-xs font-medium rounded-full }>
                      {a.last_validation_status === 'passed' ? '✅ Passed' : a.last_validation_status === 'failed' ? '❌ Failed' : 'Pending'}
                    </span>
                  </td>
'''

# Wait, the table header needs a column. Let's look at the headers first.
# I'll do this carefully.
with open('frontend-admin/src/pages/AddQuestion/tabs/AiAssertionsTab.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
