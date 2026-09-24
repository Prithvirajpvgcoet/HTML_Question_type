import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import { QuestionTab } from "./tabs/QuestionTab";
import { CodeSolutionTab } from "./tabs/CodeSolutionTab";
import { AiAssertionsTab } from "./tabs/AiAssertionsTab";
import { ReviewTab } from "./tabs/ReviewTab";
import { PageHeader } from "../../components/layout/PageHeader";

export function AddQuestionPage() {
  const [activeTab, setActiveTab] = useState(1);
  const [questionId, setQuestionId] = useState<string | null>(null);
  const { id } = useParams();
  const navigate = useNavigate();

  // Prevent accidental data loss
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "You have unsaved changes. Are you sure you want to leave?";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, []);


  useEffect(() => {
    if (id) {
      setQuestionId(id);
    }
  }, [id]);

  // Swapped tab order based on feedback
  
  const handlePublish = async () => {
    if (!questionId) return;
    try {
      const res = await api.get(`/questions/${questionId}`);
      const q = res.data;
      await api.put(`/questions/${questionId}`, {
        title: q.title,
        description_html: q.description_html,
        question_type: q.question_type,
        is_published: true
      });
      alert("Question Published Successfully!");
      navigate("/questions");
    } catch (e) {
      alert("Failed to publish question.");
    }
  };

  const tabs = ["Question", "Code Solution", "AI Assertions", "Review"];

  return (
    <div className="bg-gray-50 flex flex-col min-h-[calc(100vh-56px)]">
      <PageHeader 
        breadcrumbs={[
          { label: "My Questions" },
          { label: "Shared Questions" },
          { label: id ? "Edit Question" : "Add Question", active: true }
        ]}
      >
        <div className="flex gap-8">
          {tabs.map((tab, idx) => (
            <button
              key={tab}
              onClick={() => setActiveTab(idx + 1)}
              className={`pb-3 font-medium text-sm ${
                activeTab === idx + 1
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-gray-500 hover:text-gray-800"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </PageHeader>

      <main className="flex-1 p-8 w-full max-w-7xl mx-auto">
        {activeTab === 1 && (
          <QuestionTab 
            questionId={questionId}
            onNext={(id) => { setQuestionId(id); setActiveTab(2); }} 
          />
        )}
        {activeTab === 2 && questionId && (
          <CodeSolutionTab 
            questionId={questionId} 
            onBack={() => setActiveTab(1)}
            onNext={() => setActiveTab(3)} 
          />
        )}
        {activeTab === 3 && questionId && (
          <AiAssertionsTab 
            questionId={questionId}
            onBack={() => setActiveTab(2)}
            onNext={() => setActiveTab(4)}
          />
        )}
        {activeTab === 4 && questionId && (
          <ReviewTab 
            questionId={questionId}
            onBack={() => setActiveTab(3)}
            onPublish={handlePublish}
          />
        )}
      </main>
    </div>
  );
}
