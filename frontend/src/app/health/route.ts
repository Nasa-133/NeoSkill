// Process liveness only. Business API/DB outages do not take down the web server.
export const dynamic = 'force-dynamic';

export function GET() {
  return Response.json(
    { status: 'ok', service: 'neoskill-frontend' },
    { headers: { 'Cache-Control': 'no-store' } },
  );
}
