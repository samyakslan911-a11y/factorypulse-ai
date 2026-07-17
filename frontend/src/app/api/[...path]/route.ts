import { NextRequest, NextResponse } from "next/server";

const BACKEND =
  process.env.BACKEND_URL ||
  (process.env.NODE_ENV === "production"
    ? "https://factorypulse-ai-production.up.railway.app"
    : "http://localhost:8000");

async function proxy(req: NextRequest, method: string, _path: string) {
  const rawPath = req.nextUrl.pathname.replace(/^\/api\//, "");
  const url = `${BACKEND}/${rawPath}${req.nextUrl.search}`;
  const init: RequestInit = { method };

  if (method === "POST" || method === "PUT" || method === "PATCH") {
    const body = await req.text();
    init.body = body;
    init.headers = { "Content-Type": "application/json" };
  }

  const res = await fetch(url, { ...init, cache: "no-store", redirect: "follow" });

  if (res.headers.get("content-type")?.includes("text/event-stream")) {
    return new NextResponse(res.body, {
      status: res.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxy(req, "GET", path.join("/"));
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxy(req, "POST", path.join("/"));
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxy(req, "DELETE", path.join("/"));
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxy(req, "PATCH", path.join("/"));
}
