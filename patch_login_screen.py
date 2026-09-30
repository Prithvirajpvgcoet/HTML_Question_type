import os

file_path = 'frontend-candidate/src/pages/CandidateLogin/CandidateLoginPage.tsx'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Update the catch block to read the error detail
old_catch = '''      .catch(() => {
        setError("This invite link is invalid or has expired.");
        setLoading(false);
      });'''
new_catch = '''      .catch((err: any) => {
        const detail = err.response?.data?.detail;
        if (detail === "Test already completed") {
          setError("completed");
        } else if (detail === "Invite expired") {
          setError("expired");
        } else {
          setError("invalid");
        }
        setLoading(false);
      });'''
code = code.replace(old_catch, new_catch)

# Update the UI
old_ui = '''  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-8 border border-gray-100 text-center text-red-600 font-medium">
          {error}
        </div>
      </div>
    );
  }'''
new_ui = '''  if (error) {
    if (error === "completed") {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-10 border border-gray-100 text-center">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"></path></svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">Thank You!</h2>
            <p className="text-gray-600 mb-8">
              Your submission has been successfully recorded. You can now close this window.
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-8 border border-gray-100 text-center text-red-600 font-medium">
          {error === "expired" ? "This invite link has expired." : "This invite link is invalid."}
        </div>
      </div>
    );
  }'''
code = code.replace(old_ui, new_ui)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched CandidateLoginPage UI')
