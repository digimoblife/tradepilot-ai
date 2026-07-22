import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const protectedPaths = ["/sessions"];
const loginPath = "/login";
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Only protect matching paths
  const isProtected = protectedPaths.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (!isProtected) return NextResponse.next();

  const cookie = request.cookies.get("tradepilot_session");
  if (!cookie?.value) {
    const url = new URL(loginPath, request.url);
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  // Verify the session with the backend
  try {
    const res = await fetch(`${apiBaseUrl}/api/auth/me`, {
      headers: { cookie: `tradepilot_session=${cookie.value}` },
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
