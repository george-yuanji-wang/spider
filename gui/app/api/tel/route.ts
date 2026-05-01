const BRIDGE = process.env.BRIDGE_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${BRIDGE}/api/tel`, { cache: "no-store" });
    const data = await res.json();
    return Response.json(data);
  } catch {
    return Response.json(null, { status: 503 });
  }
}