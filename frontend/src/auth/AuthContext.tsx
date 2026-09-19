import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getCurrentClaims, login as loginRequest } from "../api/auth";
import { clearStoredToken, getStoredToken, storeToken } from "../api/client";
import type { AuthSession, UserSummary } from "../types/auth";

type AuthContextValue = {
  session: AuthSession | null;
  isInitializing: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const token = getStoredToken();

    if (!token) {
      setIsInitializing(false);
      return;
    }

    void (async () => {
      try {
        const claims = await getCurrentClaims(token);
        const rawUser = localStorage.getItem("examflow_user");
        const storedUser = rawUser ? (JSON.parse(rawUser) as UserSummary) : null;

        const user: UserSummary = storedUser ?? {
          id: String(claims.sub ?? ""),
          email: "",
          full_name: "ExamFlow User",
          institution_id: typeof claims.institution_id === "string" ? claims.institution_id : null,
          roles: Array.isArray(claims.roles) ? claims.roles.map(String) : [],
        };

        setSession({ accessToken: token, user });
      } catch {
        clearStoredToken();
        localStorage.removeItem("examflow_user");
        setSession(null);
      } finally {
        setIsInitializing(false);
      }
    })();
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    session,
    isInitializing,
    isAuthenticated: session !== null,

    async login(email: string, password: string) {
      const response = await loginRequest(email.trim(), password);
      storeToken(response.access_token);
      localStorage.setItem("examflow_user", JSON.stringify(response.user));
      setSession({
        accessToken: response.access_token,
        user: response.user,
      });
    },

    logout() {
      clearStoredToken();
      localStorage.removeItem("examflow_user");
      setSession(null);
    },
  }), [isInitializing, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
