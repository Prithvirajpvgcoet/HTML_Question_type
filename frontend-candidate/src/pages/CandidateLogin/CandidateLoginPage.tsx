import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useCandidateStore } from "../../store/candidateStore";

export function CandidateLoginPage() {
  const { questionId } = useParams();
  const navigate = useNavigate();
  const { candidateName, setCandidateInfo } = useCandidateStore();
  
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");

  useEffect(() => {
    // If they are already logged in, redirect straight to the test
    if (candidateName) {
      navigate(`/test/${questionId}`, { replace: true });
    }
  }, [candidateName, navigate, questionId]);

  const handleStartTest = (e: React.FormEvent) => {
    e.preventDefault();
    if (formName.trim() && formEmail.trim()) {
      setCandidateInfo(formName.trim(), formEmail.trim());
      navigate(`/test/${questionId}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-8 border border-gray-100">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Welcome to the Assessment</h1>
          <p className="text-gray-500 text-sm">Please enter your details to begin the test.</p>
        </div>
        <form onSubmit={handleStartTest} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input
              type="text"
              required
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              placeholder="e.g. Rohit Kumar"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
            <input
              type="email"
              required
              value={formEmail}
              onChange={(e) => setFormEmail(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              placeholder="rohit@example.com"
            />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 text-white rounded-lg py-3 font-semibold hover:bg-blue-700 transition-colors shadow-sm"
          >
            Start Test
          </button>
        </form>
      </div>
    </div>
  );
}
