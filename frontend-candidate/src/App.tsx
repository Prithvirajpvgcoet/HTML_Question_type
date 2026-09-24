import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { queryClient } from "./lib/queryClient";
import { CandidateTestPage } from "./pages/CandidateTest/CandidateTestPage";
import { CandidateLoginPage } from "./pages/CandidateLogin/CandidateLoginPage";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login/:questionId" element={<CandidateLoginPage />} />
          <Route path="/test/:questionId" element={<CandidateTestPage />} />
          <Route path="*" element={<div className="p-8 text-center text-gray-500">Candidate Portal - Please use a valid test link.</div>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
