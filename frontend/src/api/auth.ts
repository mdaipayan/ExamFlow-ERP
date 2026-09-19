import { apiRequest } from "./client";
import type { LoginResponse } from "../types/auth";

export async function login(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  }, null);
}

export async function getCurrentClaims(token: string): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>("/api/auth/me", { method: "GET" }, token);
}
