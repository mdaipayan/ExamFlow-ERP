export type Student = {
  id: string;
  registration_number: string;
  roll_number: string | null;
  full_name: string;
  gender: string | null;
  mother_name: string | null;
  status: string;
};

export type StudentEnrollment = {
  id: string;
  student_id: string;
  programme_id: string;
  programme_code: string;
  programme_name: string;
  admission_year: number;
  category: string | null;
  entry_type: string;
};

export type StudentCreateRequest = {
  registration_number: string;
  roll_number?: string | null;
  full_name: string;
  gender?: string | null;
  mother_name?: string | null;
  status?: string;
};

export type StudentImportResult = {
  created: number;
  updated: number;
  errors: { row: number; message: string }[];
  message: string;
};
