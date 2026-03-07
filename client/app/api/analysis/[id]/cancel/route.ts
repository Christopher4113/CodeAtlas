import { NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
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

  const r = await fetch(`${fastapiUrl}/v1/analyses/${id}/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });

  const text = await r.text();
  let data: Record<string, unknown>;
  try { data = JSON.parse(text); } catch { data = { raw: text }; }

  if (!r.ok) {
    const status = r.status === 404 ? 404 : r.status === 400 ? 400 : 502;
    return NextResponse.json(
      { error: (data as { detail?: string })?.detail ?? "cancel_failed", ...data },
      { status }
    );
  }
  return NextResponse.json(data);
}
