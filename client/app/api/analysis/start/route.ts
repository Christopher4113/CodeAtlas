import { NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function POST(req: Request) {
  const cookieStore = await cookies();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll() {},
      },
    }
  );

  const { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const token = session.provider_token;
  if (!token) {
    return NextResponse.json({ error: "missing_github_token" }, { status: 400 });
  }

  const body = await req.json();
  const owner = body?.owner;
  const repo = body?.repo;

  if (!owner || !repo) {
    return NextResponse.json({ error: "owner_and_repo_required" }, { status: 400 });
  }

  const fastapiUrl = process.env.FASTAPI_URL; // eg http://localhost:8000
  if (!fastapiUrl) {
    return NextResponse.json({ error: "FASTAPI_URL_not_set" }, { status: 500 });
  }

  const r = await fetch(`${fastapiUrl}/analyze/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      owner,
      repo,
      github_token: token,
    }),
    cache: "no-store",
  });

  const text = await r.text();
  let data: Record<string, unknown> | null = null;
  try {
    data = JSON.parse(text);
  } catch {
    data = { raw: text };
  }

  if (!r.ok) {
    return NextResponse.json(
      { error: "fastapi_error", detail: data },
      { status: 502 }
    );
  }

  return NextResponse.json(data);
}