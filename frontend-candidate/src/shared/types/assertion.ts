export type TriggerType = "page_load" | "click" | "change" | "input" | "hover" | "call_function";
export type CheckType =
  | "dom_presence"
  | "dom_absence"
  | "element_count"
  | "computed_style"
  | "text_content"
  | "attribute"
  | "function_presence";
export type AssertionSource = "ai_generated" | "author_added" | "ai_edited";

export interface Assertion {
  id: string;
  question_id: string;
  order: number;
  trigger: TriggerType;
  trigger_selector?: string;
  check_selector?: string;
  wait_ms: number;
  check_type: CheckType;
  input_value?: string;
  property_name?: string;
  operator: "equals" | "contains" | "regex" | "exists" | "not_exists";
  expected_value?: string;
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
