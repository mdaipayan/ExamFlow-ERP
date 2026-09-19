export type CurrentExamination = {
  id: string;
  name: string;
  term_label: string;
  status: string;
  programme_id: string;
  programme_code: string;
  programme_name: string;
  semester_id: string;
  semester_number: number;
};

export type DashboardMetrics = {
  active_examinations: number;
  registered_students: number;
  marks_recorded: number;
  validation_errors: number;
  validation_warnings: number;
  pending_result_review: number;
  pending_result_approval: number;
};

export type DashboardWorkflow = {
  stage: string;
  label: string;
  action: string;
};

export type DashboardData = {
  institution: {
    id: string;
    name: string;
    code: string;
    timezone: string;
  };
  current_examination: CurrentExamination | null;
  metrics: DashboardMetrics;
  workflow: DashboardWorkflow;
};
