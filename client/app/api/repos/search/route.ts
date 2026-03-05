import { NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function POST(req: Request) {
  const cookieStore = await cookies();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    { cookies: { getAll: () => cookieStore.getAll(), setAll() {} } }
  );

  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const fastapiUrl = process.env.FASTAPI_URL;
  if (!fastapiUrl) return NextResponse.json({ error: "FASTAPI_URL_not_set" }, { status: 500 });

  let body: { query?: string; owner?: string; top_k?: number };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const query = typeof body?.query === "string" ? body.query.trim() : "";
  if (!query) return NextResponse.json({ error: "query_required" }, { status: 400 });

  let owner = typeof body?.owner === "string" ? body.owner.trim() : "";
  if (!owner) {
    const token = session.provider_token;
    if (!token) return NextResponse.json({ error: "missing_github_token" }, { status: 400 });
    const userRes = await fetch("https://api.github.com/user", {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      cache: "no-store",
    });
    if (!userRes.ok) return NextResponse.json({ error: "github_user_failed" }, { status: 502 });
    const user = await userRes.json();
    owner = user?.login ?? "";
  }
  if (!owner) return NextResponse.json({ error: "owner_required" }, { status: 400 });

  const topK = typeof body?.top_k === "number" ? Math.min(Math.max(1, body.top_k), 50) : 10;

  const r = await fetch(`${fastapiUrl}/v1/repos/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, owner, top_k: topK }),
    cache: "no-store",
  });

  const text = await r.text();
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(text);
  } catch {
    data = { raw: text };
  }

  if (!r.ok) return NextResponse.json({ error: "fastapi_error", detail: data }, { status: 502 });
  return NextResponse.json(data);
}
