export type SubmissionStatus =
  | "pending"
  | "queued"
  | "evaluating"
  | "completed"
  | "failed";

export interface Submission {
  id: string;
  question_id: string;
  candidate_name?: string;
  candidate_email?: string;
  submitted_html?: string;
  submitted_css?: string;
  submitted_js?: string;
  assertion_set_version?: number;
  status: SubmissionStatus;
  total_score?: number;
  max_score?: number;
  tc_passed?: number;
  tc_total?: number;
  llm_passed?: number;
  llm_total?: number;
  ai_confidence?: "high" | "medium" | "low";
  ai_feedback_text?: string;
  submitted_at: string;
  evaluated_at?: string;
}

export interface CreateSubmissionPayload {
  question_id: string;
  candidate_name?: string;
  candidate_email?: string;
  submitted_html?: string;
  submitted_css?: string;
  submitted_js?: string;
}