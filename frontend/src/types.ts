export type AgentEvent = {
  type: string;
  stage: string;
  title: string;
  detail: unknown;
  done: boolean;
};

export type ExtractedDetails = {
  symptom: string;
  error_code: string | null;
  feature: string | null;
  timeframe: string | null;
  user_hint: string | null;
  keywords: string[];
};

export type PlanStep = {
  order: number;
  tool: "database" | "api" | "github" | "analyze";
  goal: string;
};

export type Finding = {
  source: string;
  title: string;
  detail: string;
  references: string[];
};

export type ProposedFix = {
  summary: string;
  file_path: string | null;
  current_code: string | null;
  suggested_code: string | null;
  configuration_changes: string[];
  verification_steps: string[];
};

export type InvestigationReport = {
  issue_summary: string;
  extracted: ExtractedDetails;
  plan: string[];
  findings: Finding[];
  root_cause: string;
  proposed_fix: ProposedFix;
  references: string[];
};

export type FlowNode =
  | "ticket"
  | "receive"
  | "plan"
  | "database"
  | "api"
  | "github"
  | "reasoning"
  | "analyze"
  | "output";
