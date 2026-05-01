const BRIDGE = process.env.BRIDGE_URL ?? "http://localhost:8000";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const res  = await fetch(`${BRIDGE}/api/ctrl`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
    const data = await res.json();
    return Response.json(data);
  } catch {
    return Response.json({ ok: false }, { status: 503 });
  }
}