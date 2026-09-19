import { apiRequest } from "./client";
import type { DashboardData } from "../types/dashboard";

export async function getDashboard(token: string): Promise<DashboardData> {
  return apiRequest<DashboardData>("/api/dashboard", { method: "GET" }, token);
}
