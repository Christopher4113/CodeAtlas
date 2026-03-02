import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { hasEnvVars } from "../utils";

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  if (!hasEnvVars) return supabaseResponse;

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  const { data } = await supabase.auth.getClaims();
  const user = data?.claims;

  const pathname = request.nextUrl.pathname;

  // Never apply redirects to Next internals, static files, or APIs
  const isBypass =
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.startsWith("/favicon.ico") ||
    pathname.match(/\.(png|jpg|jpeg|gif|svg|webp|ico|css|js|map)$/);

  if (isBypass) return supabaseResponse;

  // 1) Routes that REQUIRE auth
  const protectedRoutes = ["/protected", "/dashboard", "/repo"];
  const isProtectedRoute = protectedRoutes.some((r) => pathname.startsWith(r));

  // 2) Routes that should be inaccessible when logged in (public-only)
  // Put your landing page and auth pages here.
  const publicOnlyRoutes = ["/", "/auth", "/connect-github"];
  const isPublicOnlyRoute = publicOnlyRoutes.some((r) =>
    r === "/" ? pathname === "/" : pathname.startsWith(r),
  );

  // Not logged in → block protected
  if (isProtectedRoute && !user) {
    return NextResponse.redirect(new URL("/auth/login", request.url));
  }

  // Logged in → block public-only
  if (user && isPublicOnlyRoute) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return supabaseResponse;
}