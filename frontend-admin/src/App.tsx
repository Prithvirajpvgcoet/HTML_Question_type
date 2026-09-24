import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { queryClient } from "./lib/queryClient";

import { AppShell } from "./components/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { QuestionsList } from "./pages/QuestionsList";
import { AddQuestionPage } from "./pages/AddQuestion/AddQuestionPage";
import { QuestionPreviewPage } from "./pages/QuestionPreview/QuestionPreviewPage";
import { ReportPage } from "./pages/Reports/ReportPage";
import { ReportsList } from "./pages/Reports/ReportsList";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell>
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />
            
            {/* Protected Routes */}
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/questions" element={<ProtectedRoute><QuestionsList /></ProtectedRoute>} />
            <Route path="/questions/preview/:id" element={<ProtectedRoute><QuestionPreviewPage /></ProtectedRoute>} />
            <Route path="/questions/add" element={<ProtectedRoute><AddQuestionPage /></ProtectedRoute>} />
            <Route path="/questions/edit/:id" element={<ProtectedRoute><AddQuestionPage /></ProtectedRoute>} />
            <Route path="/reports" element={<ProtectedRoute><ReportsList /></ProtectedRoute>} />
            <Route path="/reports/:id" element={<ProtectedRoute><ReportPage /></ProtectedRoute>} />
            
            
                      </Routes>
        </AppShell>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
