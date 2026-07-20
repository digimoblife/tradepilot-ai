import { post, get } from "./client";
import type { LoginRequest, LoginResponse, MeResponse, LogoutResponse } from "@/types/auth";

export function login(data: LoginRequest): Promise<LoginResponse> {
  return post<LoginResponse>("/api/auth/login", data);
}

export function logout(): Promise<LogoutResponse> {
  return post<LogoutResponse>("/api/auth/logout");
}

export function getMe(): Promise<MeResponse> {
  return get<MeResponse>("/api/auth/me");
}
