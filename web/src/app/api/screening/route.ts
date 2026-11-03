import { NextResponse } from "next/server";


export async function GET(request: Request) {
  const backend = process.env.SKYTRACE_API_URL?.replace(/\/+$/, "");
  if (!backend) {
    return NextResponse.json(
      { product: "SKYTRACE", error: "Screening service is not configured.", detail: "Set SKYTRACE_API_URL in Vercel." },
      { status: 503 }
    );
  }

  const url = new URL(request.url);
  const requestedTop = Number(url.searchParams.get("top") ?? "50");
  const top = Number.isFinite(requestedTop)
    ? Math.max(1, Math.min(200, Math.floor(requestedTop)))
    : 50;
  const requestedHours = Number(url.searchParams.get("hours") ?? "0");
  const hours = Number.isFinite(requestedHours)
    ? Math.max(0, Math.min(24, Math.floor(requestedHours)))
    : 0;
  const requestedStep = Number(url.searchParams.get("step_seconds") ?? "600");
  const stepSeconds = Number.isFinite(requestedStep)
    ? Math.max(10, Math.min(600, Math.floor(requestedStep)))
    : 600;

  try {
    const response = await fetch(
      `${backend}/api/screening?top=${top}&hours=${hours}` +
        `&step_seconds=${stepSeconds}`,
      { cache: "no-store", signal: AbortSignal.timeout(125000) }
    );
    const body = await response.text();

    return new NextResponse(body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store, max-age=0",
        "X-SKYTRACE-Engine": "python-sgp4",
      },
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown backend error";
    console.error("SKYTRACE backend request failed:", detail);
    return NextResponse.json(
      { product: "SKYTRACE", error: "The Python screening service is unavailable.", detail },
      { status: 502 }
    );
  }
}
