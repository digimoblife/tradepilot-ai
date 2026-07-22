import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const protectedPaths = ["/sessions"];
const loginPath = "/login";
const COOKIE_NAME = "tradepilot_session";

// Server-only internal backend URL — never exposed to the browser.
// In Docker Compose this is http://backend:8000.
const internalApiBaseUrl =
  process.env.INTERNAL_API_BASE_URL || "http://backend:8000";

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

  // Verify the session by calling the backend through the Docker-internal
  // URL.  This avoids routing auth verification through the public domain
  // or the frontend's own origin.
  try {
    const authMeUrl = new URL("/api/auth/me", internalApiBaseUrl);
    const cookieHeader = request.headers.get("cookie");
    const res = await fetch(authMeUrl, {
      headers: cookieHeader ? { cookie: cookieHeader } : {},
      cache: "no-store",
    });
    if (res.ok) return NextResponse.next();
  } catch {
    // Backend unreachable — allow the page to load (it will show an error).
    // Fail-open: the client-side auth context will redirect if the session
    // cannot be verified after the page loads.
    return NextResponse.next();
  }

  const url = new URL(loginPath, request.url);
  url.searchParams.set("next", pathname);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/sessions/:path*", "/sessions"],
};
