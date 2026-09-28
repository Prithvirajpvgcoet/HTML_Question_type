import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../api/client";

export function QuestionsList() {
  const navigate = useNavigate();
  const [questions, setQuestions] = useState<any[]>([]);
  const [toast, setToast] = useState('');

  
  const handleCopyLink = async (id: string) => {
    const candidateEmail = window.prompt("Enter candidate email to generate a secure invite link:");
    if (!candidateEmail) return;
    const candidateName = window.prompt("Enter candidate name:");
    if (!candidateName) return;

    try {
      const res = await api.post("/invites", {
        question_id: id,
        candidate_name: candidateName,
        candidate_email: candidateEmail,
      });
      const token = res.data.token;
      const url = `${import.meta.env.VITE_CANDIDATE_URL || "http://localhost:5174"}/login/${token}`; // Use token in URL
      navigator.clipboard.writeText(url);
      setToast("Secure Test Link Copied!");
      setTimeout(() => setToast(''), 3000);
    } catch (e) {
      console.error(e);
      alert("Failed to generate invite token.");
    }
  };

  const fetchQuestions = () => {
    api.get("/questions").then(res => setQuestions(res.data)).catch(console.error);
  };

  const handleExport = async (id: string) => {
    try {
      const { data } = await api.get(`/questions/${id}/export`);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `question_${id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Export failed");
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        const json = JSON.parse(ev.target?.result as string);
        await api.post("/questions/import", json);
        alert("Imported successfully!");
        fetchQuestions();
      } catch {
        alert("Invalid JSON format");
      }
    };
    reader.readAsText(file);
    // Reset input so same file can be re-imported
    e.target.value = "";
  };

  useEffect(() => {
    fetchQuestions();
  }, []);

  return (
    <div className="p-8 max-w-5xl mx-auto relative">
      {toast && <div className="fixed top-20 right-8 bg-gray-800 text-white px-4 py-2 rounded shadow-lg z-50 animate-fade-in-down">{toast}</div>}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-imocha-dark">Shared Questions</h1>
        <div className="flex gap-3">
          <label className="bg-white border border-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-50 flex items-center gap-2 font-medium cursor-pointer text-sm">
            Import JSON
            <input type="file" accept=".json" onChange={handleImport} className="hidden" />
          </label>
          <button
            onClick={() => navigate("/questions/add")}
            className="bg-imocha-orange text-white px-4 py-2 rounded shadow hover:bg-orange-600 text-sm font-medium"
          >
            + Add Question
          </button>
        </div>
      </div>

      {questions.length === 0 ? (
        <div className="bg-white p-12 text-center border border-gray-200 rounded text-gray-500">
          No questions yet. Click "Add Question" to start authoring.
        </div>
      ) : (
        <div className="bg-white rounded border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="p-4 font-medium text-gray-600">Title</th>
                <th className="p-4 font-medium text-gray-600">Type</th>
                <th className="p-4 font-medium text-gray-600">Status</th>
                <th className="p-4 font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {questions.map((q: any) => (
                <tr key={q.id} className="hover:bg-gray-50">
                  <td className="p-4 font-medium text-gray-800">
                    <button
                      onClick={() => navigate(`/questions/preview/${q.id}`)}
                      className="text-blue-600 hover:text-blue-800 hover:underline text-left font-semibold"
                    >
                      {q.title}
                    </button>
                  </td>
                  <td className="p-4 text-gray-500">{q.question_type}</td>
                  <td className="p-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${q.is_published ? "bg-green-100 text-green-700" : "bg-blue-100 text-blue-700"}`}>
                      {q.is_published ? "Published" : "Draft"}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex gap-4">
                      <button className="text-gray-600 hover:text-gray-900 font-medium" onClick={() => navigate(`/questions/edit/${q.id}`)}>Edit</button>
                      <button className="text-gray-600 hover:text-gray-900 font-medium" onClick={() => handleExport(q.id)}>Export</button>
                      <button className="text-blue-600 hover:text-blue-800 font-medium" onClick={() => handleCopyLink(q.id)}>Copy Test Link</button>
                      <button className="text-imocha-orange hover:text-orange-700 font-medium" onClick={() => navigate(`/reports?question_id=${q.id}`)}>Reports</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
