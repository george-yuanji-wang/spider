export async function GET() {
  const upstream = await fetch("http://localhost:8001/stream", {
    cache: "no-store",
  });

  return new Response(upstream.body, {
    headers: {
      "Content-Type":  "multipart/x-mixed-replace; boundary=frame",
      "Cache-Control": "no-cache",
      "Pragma":        "no-cache",
    },
  });
}