import { create } from "zustand";
import { persist } from "zustand/middleware";

interface CandidateState {
  candidateName: string;
  candidateEmail: string;
  token: string;
  setCandidateInfo: (name: string, email: string, token: string) => void;
  clearCandidateInfo: () => void;
}

export const useCandidateStore = create<CandidateState>()(
  persist(
    (set) => ({
      candidateName: "",
      candidateEmail: "",
      token: "",
      setCandidateInfo: (name, email, token) => set({ candidateName: name, candidateEmail: email, token: token }),
      clearCandidateInfo: () => set({ candidateName: "", candidateEmail: "", token: "" }),
    }),
    {
      name: "imocha-candidate-storage",
    }
  )
);
