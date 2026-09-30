import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import { ChevronRight, Search } from "lucide-react";

export function ReportsList() {
  const [submissions, setSubmissions] = useState([]);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/submissions")
      .then(res => {
        setSubmissions(res.data);
      })
      .catch(console.error);
  }, []);

  return (
    <div className="bg-[#F8FAFC] min-h-screen text-gray-800 font-sans p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Candidate Reports</h1>
      
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-4 border-b bg-gray-50 flex items-center justify-between">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-400" />
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search candidates..." className="pl-9 pr-4 py-2 border rounded-md text-sm w-64 focus:ring-1 focus:ring-blue-500" />
          </div>
        </div>
        
        <table className="w-full text-sm text-left">
          <thead className="bg-white text-gray-500 border-b">
            <tr>
              <th className="py-4 px-6 font-semibold">Candidate Name</th>
              <th className="py-4 px-6 font-semibold">Assessment Date</th>
              <th className="py-4 px-6 font-semibold">Score</th>
              <th className="py-4 px-6 font-semibold">Status</th>
              <th className="py-4 px-6 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {submissions.filter((s: any) => !search || (s.candidate_name || "").toLowerCase().includes(search.toLowerCase())).map((sub: any) => (
              <tr key={sub.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => navigate(`/reports/${sub.id}`)}>
                <td className="py-4 px-6 font-medium text-gray-800 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-xs">
                    {(sub.candidate_name || 'Unknown Candidate').split(' ').map((n: string) => n[0]).join('')}
                  </div>
                  {sub.candidate_name || "Unknown Candidate"}
                </td>
                <td className="py-4 px-6 text-gray-600">
                  {new Date(sub.submitted_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                </td>
                <td className="py-4 px-6 font-semibold text-gray-800">{sub.total_score ?? 0} / 100</td>
                <td className="py-4 px-6">
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${sub.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                    {sub.status === 'completed' ? 'Completed' : 'Pending'}
                  </span>
                </td>
                <td className="py-4 px-6 text-right">
                  <button 
                    onClick={() => navigate(`/reports/${sub.id}`)}
                    className="text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 ml-auto"
                  >
                    View Report <ChevronRight className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
