import { NextRequest, NextResponse } from 'next/server';

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const AGENT_SERVER_URL = process.env.AGENT_SERVER_URL;

  // If env is missing, do not break the app; just pass through.
  if (!AGENT_SERVER_URL) {
    return NextResponse.next();
  }

  if (pathname.startsWith('/api/token/')) {
    const target = new URL(AGENT_SERVER_URL);
    target.pathname = pathname.replace('/api/token/', '/token/');
    target.search = req.nextUrl.search;
    return NextResponse.rewrite(target);
  }

  if (pathname.startsWith('/api/agents/') && !pathname.startsWith('/api/agents/start')) {
    const target = new URL(AGENT_SERVER_URL);
    target.pathname = pathname.replace('/api/agents/', '/');
    target.search = req.nextUrl.search;
    return NextResponse.rewrite(target);
  }

  return NextResponse.next();
}

// Only run middleware for API routes
export const config = {
  matcher: ['/api/:path*'],
}
