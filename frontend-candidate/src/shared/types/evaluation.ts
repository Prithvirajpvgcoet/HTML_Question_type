export type TCStatus = "passed" | "failed" | "not_evaluated";
export type LLMStatus = "passed" | "failed" | "not_evaluated";
export type ReviewFlag = "none" | "needs_review" | "overridden";

export interface EvaluationResult {
  id: string;
  submission_id: string;
  assertion_id: string;
  assertion_set_version: number;
  // Predefined test case (Playwright) result
  tc_status: TCStatus;
  tc_evidence_url?: string;
  // LLM verification result
  llm_status: LLMStatus;
  llm_evidence_text?: string;
  // Final
  points_awarded: number;
  review_flag: ReviewFlag;
}

export interface AIEvaluationSummary {
  submission_id: string;
  total_score: number;
  max_score: number;
  tc_passed: number;
  tc_total: number;
  llm_passed: number;
  llm_total: number;
  ai_confidence: "high" | "medium" | "low";
  ai_feedback_text: string;
  results: (EvaluationResult & {
    assertion_description?: string;
    expected_result?: string;
    points?: number;
  })[];
}