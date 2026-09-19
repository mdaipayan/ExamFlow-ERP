export type UserSummary = {
  id: string;
  email: string;
  full_name: string;
  institution_id: string | null;
  roles: string[];
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer" | string;
  user: UserSummary;
};

export type AuthSession = {
  accessToken: string;
  user: UserSummary;
};
