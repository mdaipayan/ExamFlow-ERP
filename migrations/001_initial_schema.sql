CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE institutions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  code text NOT NULL UNIQUE,
  timezone text NOT NULL DEFAULT 'Asia/Kolkata',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id uuid REFERENCES institutions(id) ON DELETE CASCADE,
  email text NOT NULL UNIQUE,
  full_name text NOT NULL,
  password_hash text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code text NOT NULL UNIQUE,
  name text NOT NULL
);

CREATE TABLE user_roles (
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE regulations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id uuid NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
  name text NOT NULL,
  code text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (institution_id, code)
);

CREATE TABLE regulation_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  regulation_id uuid NOT NULL REFERENCES regulations(id) ON DELETE CASCADE,
  version_label text NOT NULL,
  status text NOT NULL CHECK (status IN ('DRAFT','APPROVED','RETIRED')),
  effective_from date,
  effective_to date,
  parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
  approved_by uuid REFERENCES users(id),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE programmes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id uuid NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
  code text NOT NULL,
  name text NOT NULL,
  level text NOT NULL,
  duration_semesters integer,
  UNIQUE (institution_id, code)
);

CREATE TABLE semesters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  programme_id uuid NOT NULL REFERENCES programmes(id) ON DELETE CASCADE,
  number integer NOT NULL,
  name text NOT NULL,
  UNIQUE (programme_id, number)
);

CREATE TABLE courses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id uuid NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
  code text NOT NULL,
  name text NOT NULL,
  credits numeric(5,2) NOT NULL DEFAULT 0,
  course_type text NOT NULL DEFAULT 'THEORY',
  is_audit boolean NOT NULL DEFAULT false,
  UNIQUE (institution_id, code)
);

CREATE TABLE course_components (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id uuid NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  code text NOT NULL,
  name text NOT NULL,
  max_marks numeric(7,2) NOT NULL,
  weightage numeric(7,4) NOT NULL,
  minimum_marks numeric(7,2),
  sort_order integer NOT NULL DEFAULT 1,
  UNIQUE (course_id, code)
);

CREATE TABLE course_schemes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id uuid NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  regulation_version_id uuid NOT NULL REFERENCES regulation_versions(id),
  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (course_id, regulation_version_id)
);

CREATE TABLE students (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id uuid NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
  registration_number text NOT NULL,
  roll_number text,
  full_name text NOT NULL,
  gender text,
  mother_name text,
  status text NOT NULL DEFAULT 'ACTIVE',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (institution_id, registration_number)
);

CREATE TABLE student_programme_enrolments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id uuid NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  programme_id uuid NOT NULL REFERENCES programmes(id),
  admission_year integer NOT NULL,
  category text,
  entry_type text NOT NULL DEFAULT 'REGULAR',
  UNIQUE (student_id, programme_id, admission_year)
);

CREATE TABLE examinations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id uuid NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
  programme_id uuid NOT NULL REFERENCES programmes(id),
  semester_id uuid NOT NULL REFERENCES semesters(id),
  regulation_version_id uuid NOT NULL REFERENCES regulation_versions(id),
  name text NOT NULL,
  term_label text NOT NULL,
  status text NOT NULL CHECK (status IN ('DRAFT','IN_PROGRESS','TRIAL','UNDER_REVIEW','APPROVED','LOCKED','PUBLISHED')),
  starts_on date,
  ends_on date,
  created_by uuid REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE examination_parameter_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  examination_id uuid NOT NULL UNIQUE REFERENCES examinations(id) ON DELETE CASCADE,
  regulation_id uuid NOT NULL REFERENCES regulations(id),
  regulation_version_id uuid NOT NULL REFERENCES regulation_versions(id),
  version_label text NOT NULL,
  parameters jsonb NOT NULL,
  content_hash text NOT NULL,
  frozen_at timestamptz NOT NULL DEFAULT now(),
  frozen_by_user_id uuid REFERENCES users(id)
);

CREATE TABLE examination_courses (
  examination_id uuid NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
  course_id uuid NOT NULL REFERENCES courses(id),
  PRIMARY KEY (examination_id, course_id)
);

CREATE TABLE examination_registrations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  examination_id uuid NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
  student_id uuid NOT NULL REFERENCES students(id),
  course_id uuid NOT NULL REFERENCES courses(id),
  attempt_type text NOT NULL DEFAULT 'REGULAR',
  registration_status text NOT NULL DEFAULT 'REGISTERED',
  UNIQUE (examination_id, student_id, course_id)
);

CREATE TABLE eligibility_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  examination_id uuid NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
  student_id uuid NOT NULL REFERENCES students(id),
  course_id uuid NOT NULL REFERENCES courses(id),
  attendance_percent numeric(6,3),
  eligible_for_ese boolean,
  reason text,
  grade_override text,
  UNIQUE (examination_id, student_id, course_id)
);

CREATE TABLE mark_import_batches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  examination_id uuid NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
  course_id uuid REFERENCES courses(id),
  source_filename text NOT NULL,
  imported_by uuid REFERENCES users(id),
  imported_at timestamptz NOT NULL DEFAULT now(),
  status text NOT NULL DEFAULT 'IMPORTED'
);

CREATE TABLE mark_entries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  examination_id uuid NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
  student_id uuid NOT NULL REFERENCES students(id),
  course_id uuid NOT NULL REFERENCES courses(id),
  component_code text NOT NULL,
  marks numeric(8,3),
  max_marks numeric(8,3) NOT NULL,
  source text NOT NULL DEFAULT 'MANUAL',
  import_batch_id uuid REFERENCES mark_import_batches(id),
  original_marks numeric(8,3),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (examination_id, student_id, course_id, component_code)
);

CREATE TABLE mark_validation_issues (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  examination_id uuid NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
  student_id uuid REFERENCES students(id),
  course_id uuid REFERENCES courses(id),
  severity text NOT NULL CHECK (severity IN ('ERROR','WARNING')),
  code text NOT NULL,
  message text NOT NULL,
  resolved_at timestamptz,
  resolved_by uuid REFERENCES users(id)
);

CREATE TABLE result_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  examination_id uuid NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
  version_number integer NOT NULL,
  status text NOT NULL CHECK (status IN ('TRIAL','APPROVED','LOCKED','PUBLISHED','SUPERSEDED')),
  reason text,
  created_by uuid REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (examination_id, version_number)
);

CREATE TABLE result_courses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  result_version_id uuid NOT NULL REFERENCES result_versions(id) ON DELETE CASCADE,
  student_id uuid NOT NULL REFERENCES students(id),
  course_id uuid NOT NULL REFERENCES courses(id),
  total_marks numeric(8,3),
  grade text,
  grade_point numeric(6,3),
  credits numeric(6,2),
  status text NOT NULL,
  notation text,
  explanation jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (result_version_id, student_id, course_id)
);

CREATE TABLE grade_cutoffs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  result_version_id uuid NOT NULL REFERENCES result_versions(id) ON DELETE CASCADE,
  course_id uuid NOT NULL REFERENCES courses(id),
  grading_method text NOT NULL,
  statistics jsonb,
  cutoffs jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (result_version_id, course_id)
);

CREATE TABLE semester_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  result_version_id uuid NOT NULL REFERENCES result_versions(id) ON DELETE CASCADE,
  student_id uuid NOT NULL REFERENCES students(id),
  semester_id uuid NOT NULL REFERENCES semesters(id),
  sgpa numeric(8,4),
  result_status text NOT NULL,
  UNIQUE (result_version_id, student_id, semester_id)
);

CREATE TABLE cgpa_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id uuid NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
  student_id uuid NOT NULL REFERENCES students(id),
  as_of_result_version_id uuid REFERENCES result_versions(id),
  cgpa numeric(8,4),
  percentage numeric(8,4),
  calculation_details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id uuid REFERENCES institutions(id),
  actor_user_id uuid REFERENCES users(id),
  action text NOT NULL,
  entity_type text NOT NULL,
  entity_id uuid,
  reason text,
  before_state jsonb,
  after_state jsonb,
  correlation_id text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_institution ON users(institution_id);
CREATE INDEX idx_students_institution ON students(institution_id);
CREATE INDEX idx_examinations_institution_status ON examinations(institution_id, status);
CREATE INDEX idx_mark_entries_exam_course ON mark_entries(examination_id, course_id);
CREATE INDEX idx_result_courses_version_student ON result_courses(result_version_id, student_id);
CREATE INDEX idx_audit_events_institution_time ON audit_events(institution_id, created_at);
