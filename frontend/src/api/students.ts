import { apiRequest } from "./client";
import type {
  Student,
  StudentCreateRequest,
  StudentEnrollment,
  StudentImportResult,
} from "../types/student";

export async function listStudents(token: string, search = ""): Promise<Student[]> {
  const query = search.trim() ? "?search=" + encodeURIComponent(search.trim()) : "";
  return apiRequest<Student[]>("/api/students" + query, { method: "GET" }, token);
}

export async function getStudent(token: string, studentId: string): Promise<Student> {
  return apiRequest<Student>("/api/students/" + studentId, { method: "GET" }, token);
}

export async function listStudentEnrollments(
  token: string,
  studentId: string,
): Promise<StudentEnrollment[]> {
  return apiRequest<StudentEnrollment[]>(
    "/api/students/" + studentId + "/enrolments",
    { method: "GET" },
    token,
  );
}

export async function createStudent(
  token: string,
  payload: StudentCreateRequest,
): Promise<Student> {
  return apiRequest<Student>(
    "/api/students",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function importStudentsCsv(
  token: string,
  file: File,
): Promise<StudentImportResult> {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<StudentImportResult>(
    "/api/students/import-csv",
    {
      method: "POST",
      body: formData,
    },
    token,
  );
}
