import { create } from "zustand";
import { persist } from "zustand/middleware";

interface CandidateState {
  candidateName: string;
  candidateEmail: string;
  setCandidateInfo: (name: string, email: string) => void;
  clearCandidateInfo: () => void;
}

export const useCandidateStore = create<CandidateState>()(
  persist(
    (set) => ({
      candidateName: "",
      candidateEmail: "",
      setCandidateInfo: (name, email) => set({ candidateName: name, candidateEmail: email }),
      clearCandidateInfo: () => set({ candidateName: "", candidateEmail: "" }),
    }),
    {
      name: "imocha-candidate-storage",
    }
  )
);
