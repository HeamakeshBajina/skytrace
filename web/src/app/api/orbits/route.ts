import { NextResponse } from "next/server";

export async function GET() {
  const backend = process.env.SKYTRACE_API_URL?.replace(/\/+$/, "");

  if (!backend) {
    return NextResponse.json(
      {
        product: "SKYTRACE",
        error: "Orbital data service is not configured.",
        detail: "Set SKYTRACE_API_URL in Vercel.",
      },
      { status: 503 },
    );
  }

  try {
    const response = await fetch(`${backend}/api/orbits`, {
      cache: "no-store",
      signal: AbortSignal.timeout(30000),
    });
    const body = await response.text();

    return new NextResponse(body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store, max-age=0",
        "X-SKYTRACE-Engine": "python-sgp4",
      },
    });
  } catch (error) {
    const detail =
      error instanceof Error ? error.message : "Unknown backend error";

    console.error("SKYTRACE orbital request failed:", detail);

    return NextResponse.json(
      {
        product: "SKYTRACE",
        error: "The orbital data service is unavailable.",
        detail,
      },
      { status: 502 },
    );
  }
}
