/** POST /api/auth/login */
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  id: string;
  email: string;
}

/** GET /api/auth/me */
export interface MeResponse {
  id: string;
  email: string;
}

/** POST /api/auth/logout */
export interface LogoutResponse {
  status: string;
}
