"use client";

import { useEffect, useState } from "react";

type AnalysisStatus = {
  analysis_id: string;
  status: string;
  stage?: string;
  error?: string | null;
  artifacts?: Record<string, unknown>;
};

function StatusPill({ status }: { status: string }) {
  const base = "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium";
  if (status === "completed") return <span className={`${base} bg-[#7ce38b]/10 text-[#7ce38b]`}>completed</span>;
  if (status === "running") return <span className={`${base} bg-[#77bdfb]/10 text-[#77bdfb]`}>running</span>;
  if (status === "queued") return <span className={`${base} bg-[#89929b]/10 text-[#89929b]`}>queued</span>;
  return <span className={`${base} bg-red-500/10 text-red-400`}>failed</span>;
}

export default function RunPage({
  params,
}: {
  params: { owner: string; repo: string; analysis_id: string };
}) {
  const { owner, repo, analysis_id } = params;

  const [data, setData] = useState<AnalysisStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const res = await fetch(`/api/analysis/${analysis_id}`, { cache: "no-store" });
        const json = await res.json();

        if (!res.ok) throw new Error(json?.error ?? "failed_to_fetch_status");
        if (!cancelled) {
          setData(json);
          setLoading(false);
          setErr(null);
        }

        const status = json?.status;
        if (status === "queued" || status === "running") {
          setTimeout(poll, 1500);
        }
      } catch (e: Error | unknown) {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : "error");
          setLoading(false);
        }
      }
    };

    poll();
    return () => {
      cancelled = true;
    };
  }, [analysis_id]);

  return (
    <div className="min-h-screen w-full bg-[#0d1117]">
      <div className="mx-auto w-full max-w-4xl px-4 py-10">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-[#ecf2f8]">
              {owner}/{repo}
            </h1>
            <p className="mt-1 text-sm text-[#89929b] font-mono">
              run: {analysis_id}
            </p>
          </div>
          {data?.status && <StatusPill status={data.status} />}
        </div>

        <div className="mt-6 rounded-lg border border-[#21262d] bg-[#161b22] p-5">
          {loading ? (
            <p className="text-[#89929b]">Loading status...</p>
          ) : err ? (
            <p className="text-red-400">{err}</p>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <span className="text-sm text-[#89929b]">stage</span>
                <span className="text-sm text-[#ecf2f8]">{data?.stage ?? "unknown"}</span>
              </div>

              {data?.error && (
                <p className="mt-3 text-sm text-red-400">{data.error}</p>
              )}

              <pre className="mt-4 overflow-auto rounded-md border border-[#21262d] bg-[#0d1117] p-4 text-xs text-[#c6cdd5]">
                {JSON.stringify(data, null, 2)}
              </pre>
            </>
          )}
        </div>
      </div>
    </div>
  );
}