export interface Question {
  id: string;
  title: string;
  description_html: string;
  question_type: string;
  is_published: boolean;
  reference_html?: string;
  reference_css?: string;
  reference_js?: string;
  validation_status: "not_run" | "running" | "passed" | "failed";
  last_validation_results?: any;
  created_at: string;
  updated_at: string;
}

export interface Assertion {
  id: string;
  question_id: string;
  order: number;
  trigger: "page_load" | "click" | "input" | "change" | "hover" | "call_function";
  trigger_selector?: string;
  check_selector?: string;
  wait_ms?: number;
  input_value?: string;
  check_type: "dom_presence" | "dom_absence" | "element_count" | "text_content" | "computed_style" | "attribute" | "function_presence";
  property_name?: string;
  operator: "equals" | "contains" | "regex" | "exists" | "not_exists";
  expected_value?: string;
  points: number;
  is_sample: boolean;
  execution_mode: "isolated" | "sequential";
  group_id?: string;
  sequence_order?: number;
  depends_on_state?: string;
}

export interface AssertionResult {
  assertion_id: string;
  status: "PASS" | "FAIL" | "ERROR";
  reason?: string;
  expected?: string;
  actual?: string;
  points_awarded: number;
  message?: string;
}

export interface SubmissionResult {
  total_points: number;
  max_points: number;
  assertion_results: AssertionResult[];
  console_errors: string[];
}
