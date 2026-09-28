import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useCandidateStore } from "../../store/candidateStore";

import { api } from "../../api/client";

export function CandidateLoginPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { setCandidateInfo } = useCandidateStore();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setError("Invalid invite link.");
      setLoading(false);
      return;
    }

    api.get(`/invites/${token}`)
      .then(res => {
        const { question_id, candidate_name, candidate_email } = res.data;
        setCandidateInfo(candidate_name, candidate_email);
        navigate(`/test/${question_id}`, { replace: true });
      })
      .catch(() => {
        setError("This invite link is invalid or has expired.");
        setLoading(false);
      });
  }, [token, navigate, setCandidateInfo]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="w-12 h-12 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-8 border border-gray-100 text-center text-red-600 font-medium">
          {error}
        </div>
      </div>
    );
  }

  return null;
}
