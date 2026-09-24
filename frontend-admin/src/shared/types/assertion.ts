export type TriggerType = "page_load" | "click" | "change" | "input" | "hover";
export type CheckType =
  | "dom_presence"
  | "computed_style"
  | "text_content"
  | "attribute"
  | "visual_region";
export type AssertionSource = "ai_generated" | "author_added" | "ai_edited";

export interface Assertion {
  id: string;
  question_id: string;
  order: number;
  trigger: TriggerType;
  trigger_selector: string | null;
  check_selector: string | null;
  wait_ms: number;
  check_type: CheckType;
  expected_result: string;
  points: number;
  is_sample: boolean;
  source: AssertionSource;
  assertion_set_version: number;
}

export interface ValidationIssue {
  type: "ambiguous_behaviour" | "solution_mismatch" | "not_ui_observable";
  message: string;
}

export interface GenerateAssertionsResponse {
  validation_status: "passed" | "failed";
  issues: ValidationIssue[];
  assertions?: Assertion[];
}