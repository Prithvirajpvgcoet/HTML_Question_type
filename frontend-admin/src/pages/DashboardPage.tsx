import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { BarChart3, Users, CheckCircle2, TrendingUp } from "lucide-react";

export function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/analytics/summary").then((res: { data: any }) => setStats(res.data)).catch(console.error);
  }, []);

  if (!stats) return <div className="p-8 text-center text-gray-500">Loading metrics...</div>;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-gray-800">Platform Analytics</h1>
        <div className="flex gap-4">
          <button onClick={() => navigate("/questions")} className="px-5 py-2 border border-gray-300 rounded font-medium text-gray-700 bg-white hover:bg-gray-50 shadow-sm">
            View All Questions
          </button>
          <button onClick={() => navigate("/questions/add")} className="px-5 py-2 bg-imocha-orange text-white rounded font-medium hover:bg-orange-600 shadow-sm">
            + Create New Assessment
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex items-center gap-4">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg"><BarChart3 className="w-6 h-6" /></div>
          <div>
            <div className="text-sm text-gray-500 font-medium">Questions Authored</div>
            <div className="text-2xl font-bold text-gray-900">{stats.questions_count}</div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex items-center gap-4">
          <div className="p-3 bg-purple-50 text-purple-600 rounded-lg"><Users className="w-6 h-6" /></div>
          <div>
            <div className="text-sm text-gray-500 font-medium">Candidates Evaluated</div>
            <div className="text-2xl font-bold text-gray-900">{stats.submissions_count}</div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex items-center gap-4">
          <div className="p-3 bg-orange-50 text-imocha-orange rounded-lg"><TrendingUp className="w-6 h-6" /></div>
          <div>
            <div className="text-sm text-gray-500 font-medium">Average Score</div>
            <div className="text-2xl font-bold text-gray-900">{stats.submissions_count === 0 ? "N/A" : <>{stats.avg_score}<span className="text-sm text-gray-400 font-normal">/100</span></>}</div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex items-center gap-4">
          <div className="p-3 bg-green-50 text-green-600 rounded-lg"><CheckCircle2 className="w-6 h-6" /></div>
          <div>
            <div className="text-sm text-gray-500 font-medium">Pass Rate</div>
            <div className="text-2xl font-bold text-gray-900">{stats.submissions_count === 0 ? "N/A" : `${stats.pass_rate}%`}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
