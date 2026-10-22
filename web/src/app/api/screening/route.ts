import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { NextResponse } from "next/server";


const execFileAsync = promisify(execFile);

export async function GET(request: Request) {
  const url = new URL(request.url);
  const requestedTop = Number(url.searchParams.get("top") ?? "50");
  const top = Number.isFinite(requestedTop)
    ? Math.max(1, Math.min(200, Math.floor(requestedTop)))
    : 50;

  const root = path.resolve(process.cwd(), "..");
  const python = path.join(root, ".venv", "Scripts", "python.exe");
  const script = path.join(root, "scripts", "screen_approaches.py");

  try {
    const { stdout } = await execFileAsync(
      python,
      [script, "--hours", "0", "--top", String(top), "--format", "json"],
      {
        cwd: root,
        timeout: 120000,
        maxBuffer: 16 * 1024 * 1024,
        windowsHide: true,
      }
    );

    const data: unknown = JSON.parse(stdout);

    return NextResponse.json(data, {
      headers: {
        "Cache-Control": "no-store, max-age=0",
        "X-SKYTRACE-Engine": "python-sgp4",
      },
    });
  } catch (error: unknown) {
    const detail =
      error instanceof Error ? error.message : "Unknown screening error";

    console.error("SKYTRACE screening API error:", detail);

    return NextResponse.json(
      {
        product: "SKYTRACE",
        error: "The Python screening engine could not return valid results.",
        detail,
      },
      { status: 500 }
    );
  }
}
