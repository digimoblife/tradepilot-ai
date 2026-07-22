import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const protectedPaths = ["/sessions"];
const loginPath = "/login";
const COOKIE_NAME = "tradepilot_session";

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Only protect matching paths
  const isProtected = protectedPaths.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (!isProtected) return NextResponse.next();

  const cookie = request.cookies.get(COOKIE_NAME);
  if (!cookie?.value) {
    const url = new URL(loginPath, request.url);
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  // Verify the session with the backend using the incoming request origin
  // so the URL is always /api/auth/me (never /api/api/auth/me).
  try {
    const authMeUrl = new URL("/api/auth/me", request.url);
    const cookieHeader = request.headers.get("cookie");
    const res = await fetch(authMeUrl, {
      headers: cookieHeader ? { cookie: cookieHeader } : {},
      cache: "no-store",
    });
    if (res.ok) return NextResponse.next();
  } catch {
    // Backend unreachable — allow the page to load (it will show an error)
    return NextResponse.next();
  }

  const url = new URL(loginPath, request.url);
  url.searchParams.set("next", pathname);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/sessions/:path*", "/sessions"],
};
