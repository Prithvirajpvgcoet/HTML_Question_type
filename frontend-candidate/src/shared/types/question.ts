export interface Question {
  id: string;
  title: string;
  description_html: string;
  purpose?: string;
  question_type: string;
  question_bank_name?: string;
  reference_html?: string;
  reference_css?: string;
  reference_js?: string;
  validation_status: "not_run" | "passed" | "failed";
  assertion_set_version: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateQuestionPayload {
  title: string;
  description_html?: string;
  purpose?: string;
  question_type?: string;
  question_bank_name?: string;
}

export interface UpdateCodeSolutionPayload {
  reference_html?: string;
  reference_css?: string;
  reference_js?: string;
}