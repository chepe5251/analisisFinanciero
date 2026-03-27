/**
 * Middleware de Next.js para protección de rutas.
 * Corre en el Edge Runtime antes de renderizar cada página.
 *
 * Lógica:
 * - Si la ruta NO es pública y no hay cookie auth_token → redirige a /login
 * - Si ya hay token y se intenta acceder a /login → redirige al dashboard
 *
 * Nota: la cookie auth_token es seteada por el AuthProvider al hacer login.
 * La autorización por rol se hace en los componentes de página (client-side)
 * y en los endpoints del backend — el middleware solo verifica autenticación.
 */
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login"];

export function middleware(request: NextRequest) {
  const token = request.cookies.get("auth_token")?.value;
  const { pathname } = request.nextUrl;

  const isPublic = PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));

  if (!token && !isPublic) {
    const loginUrl = new URL("/login", request.url);
    // Guarda la ruta original para redirigir de vuelta tras el login
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (token && isPublic) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Aplica el middleware a todas las rutas excepto assets estáticos y API interna
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"],
};
