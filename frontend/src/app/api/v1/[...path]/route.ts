import type { NextRequest } from 'next/server';

/**
 * Same-origin API proxy.
 *
 * The browser calls this app at /api/v1/... and this handler forwards to the API
 * server. Keeping requests same-origin means the app works from localhost, a LAN
 * address or a real domain with no CORS configuration, and session cookies are
 * first-party. Read at request time, so BACKEND_INTERNAL_URL is a runtime setting.
 */
function backendOrigin() {
  return (process.env.BACKEND_INTERNAL_URL ?? 'http://localhost:8000').replace(/\/$/, '');
}

// Hop-by-hop and host-specific headers must not be replayed upstream.
const stripRequest = new Set(['host', 'connection', 'keep-alive', 'transfer-encoding', 'upgrade', 'content-length', 'accept-encoding']);
const stripResponse = new Set(['connection', 'keep-alive', 'transfer-encoding', 'upgrade', 'content-encoding', 'content-length']);

async function proxy(request: NextRequest, path: string[]) {
  const target = `${backendOrigin()}/api/v1/${path.map(encodeURIComponent).join('/')}${request.nextUrl.search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => { if (!stripRequest.has(key.toLowerCase())) headers.set(key, value); });

  const hasBody = request.method !== 'GET' && request.method !== 'HEAD';
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      ...(hasBody ? { body: await request.arrayBuffer() } : {}),
      redirect: 'manual',
      cache: 'no-store',
    });
  } catch {
    return Response.json({ detail: 'API serveriga ulanib bo‘lmadi.' }, { status: 502 });
  }

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => { if (!stripResponse.has(key.toLowerCase())) responseHeaders.append(key, value); });
  // getSetCookie preserves every cookie separately; a joined header would break them.
  responseHeaders.delete('set-cookie');
  for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append('set-cookie', cookie);

  return new Response(upstream.status === 204 || upstream.status === 304 ? null : upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

type Context = { params: Promise<{ path: string[] }> };
const handler = async (request: NextRequest, context: Context) => proxy(request, (await context.params).path);

export const GET = handler;
export const POST = handler;
export const PATCH = handler;
export const PUT = handler;
export const DELETE = handler;
export const HEAD = handler;
export const OPTIONS = handler;
export const dynamic = 'force-dynamic';
