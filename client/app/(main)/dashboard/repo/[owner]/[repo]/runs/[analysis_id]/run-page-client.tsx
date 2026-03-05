"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { MermaidDiagram } from "@/components/MermaidDiagram";

type RepoSummary = {
  short_overview?: string;
  how_to_run?: string;
  main_components?: string[];
  stack?: string[];
  notes?: (string | Record<string, unknown>)[];
};

type AnalysisReport = {
  repo_summary?: RepoSummary;
  architecture_mermaid?: string;
  onboarding_doc?: string;
  dependency_mermaid?: string;
  bug_risks?: string[];
  frameworks_summary?: string;
};

type AnalysisStatus = {
  analysis_id: string;
  status: string;
  stage?: string;
  error?: string | null;
  report?: AnalysisReport;
  artifacts?: Record<string, unknown>;
};

function StatusPill({ status }: { status: string }) {
  const base = "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium";
  if (status === "completed") return <span className={`${base} bg-[#7ce38b]/10 text-[#7ce38b]`}>completed</span>;
  if (status === "running") return <span className={`${base} bg-[#77bdfb]/10 text-[#77bdfb]`}>running</span>;
  if (status === "queued") return <span className={`${base} bg-[#89929b]/10 text-[#89929b]`}>queued</span>;
  return <span className={`${base} bg-red-500/10 text-red-400`}>failed</span>;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-[#21262d] bg-[#161b22] p-5">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#8b949e]">{title}</h2>
      {children}
    </section>
  );
}

function getDisplaySummary(summary: RepoSummary | undefined): { overview: string; howToRun: string } {
  if (!summary) return { overview: "—", howToRun: "" };
  let overview = summary.short_overview ?? "";
  let howToRun = summary.how_to_run ?? "";
  if (overview === "Model returned non-JSON output." && summary.notes?.length) {
    const first = summary.notes[0];
    const raw = typeof first === "string" ? first : JSON.stringify(first);
    try {
      const parsed = JSON.parse(raw) as RepoSummary;
      if (parsed.short_overview) overview = parsed.short_overview;
      if (parsed.how_to_run && parsed.how_to_run !== "unknown") howToRun = parsed.how_to_run;
    } catch {
      if (raw.trim().startsWith("{")) {
        const m = raw.match(/"short_overview":\s*"([^"]*)"/);
        if (m) overview = m[1].replace(/\\n/g, "\n");
        const m2 = raw.match(/"how_to_run":\s*"([^"]*)"/);
        if (m2) howToRun = m2[1].replace(/\\n/g, "\n");
      }
    }
  }
  return { overview: overview || "—", howToRun: howToRun === "unknown" ? "" : howToRun };
}

function getDisplayFrameworks(report: AnalysisReport | undefined): string {
  if (!report) return "";
  const fromSummary = report.frameworks_summary?.trim();
  if (fromSummary && fromSummary !== "Unknown") return fromSummary;
  let stack = report.repo_summary?.stack;
  if (!Array.isArray(stack) || stack.length === 0) {
    const first = report.repo_summary?.notes?.[0];
    const raw = typeof first === "string" ? first : "";
    if (raw.trim().startsWith("{")) {
      try {
        const parsed = JSON.parse(raw) as RepoSummary;
        if (Array.isArray(parsed.stack) && parsed.stack.length) stack = parsed.stack;
      } catch {
        const m = raw.match(/"stack":\s*\[([\s\S]*?)\]/);
        if (m) {
          const arr = m[1].match(/"([^"]+)"/g);
          if (arr) stack = arr.map((s) => s.slice(1, -1));
        }
      }
    }
  }
  if (Array.isArray(stack) && stack.length) return stack.join(", ");
  return fromSummary || "—";
}

function downloadOnboardingPdf(title: string, markdown: string) {
  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${title.replace(/</g, "&lt;")} — Onboarding</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; line-height: 1.6; white-space: pre-wrap; }
    h1,h2,h3 { margin-top: 1.5em; }
    code { background: #eee; padding: 0.2em 0.4em; border-radius: 4px; }
    pre { background: #f5f5f5; padding: 1rem; overflow-x: auto; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }
  </style>
</head>
<body><pre>${markdown.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre></body>
</html>`;
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const win = window.open(url, "_blank", "noopener,noreferrer");
  if (!win) {
    URL.revokeObjectURL(url);
    return;
  }
  win.addEventListener("load", () => {
    URL.revokeObjectURL(url);
    win.focus();
    setTimeout(() => {
      win.print();
      win.close();
    }, 300);
  });
}

export default function RunPageClient({
  owner,
  repo,
  analysis_id,
}: {
  owner: string;
  repo: string;
  analysis_id: string;
}) {
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

  const report = data?.report;
  const completed = data?.status === "completed" && report;

  return (
    <div className="min-h-screen w-full bg-[#0d1117]">
      <div className="mx-auto w-full max-w-4xl px-4 py-10">
        <div className="mb-4">
          <Link
            href={`/dashboard/repo/${owner}/${repo}`}
            className="text-sm text-[#58a6ff] hover:underline"
          >
            ← Back to {owner}/{repo}
          </Link>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-[#ecf2f8]">
              {owner}/{repo}
            </h1>
            <p className="mt-1 font-mono text-sm text-[#89929b]">run: {analysis_id}</p>
          </div>
          {data?.status && <StatusPill status={data.status} />}
        </div>

        {loading ? (
          <div className="mt-6 rounded-lg border border-[#21262d] bg-[#161b22] p-5">
            <p className="text-[#89929b]">Loading status...</p>
          </div>
        ) : err ? (
          <div className="mt-6 rounded-lg border border-[#21262d] bg-[#161b22] p-5">
            <p className="text-red-400">{err}</p>
          </div>
        ) : !completed ? (
          <div className="mt-6 rounded-lg border border-[#21262d] bg-[#161b22] p-5">
            <div className="flex items-center gap-2">
              <span className="text-sm text-[#89929b]">stage</span>
              <span className="text-sm text-[#ecf2f8]">{data?.stage ?? "unknown"}</span>
            </div>
            {data?.error && <p className="mt-3 text-sm text-red-400">{data.error}</p>}
            <pre className="mt-4 overflow-auto rounded-md border border-[#21262d] bg-[#0d1117] p-4 text-xs text-[#c6cdd5]">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        ) : (
          <div className="mt-6 flex flex-col gap-6">
            {report.repo_summary && (() => {
              const { overview, howToRun } = getDisplaySummary(report.repo_summary);
              return (
                <Section title="Summary">
                  <p className="text-sm text-[#c6cdd5]">{overview}</p>
                  {howToRun && (
                    <div className="mt-3">
                      <p className="text-xs font-medium text-[#8b949e]">How to run</p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-[#c6cdd5]">{howToRun}</p>
                    </div>
                  )}
                </Section>
              );
            })()}

            <Section title="Frameworks & technologies">
              <p className="text-sm text-[#c6cdd5]">{getDisplayFrameworks(report)}</p>
            </Section>

            {report.architecture_mermaid && (
              <Section title="Architecture diagram">
                <MermaidDiagram code={report.architecture_mermaid} id="arch" />
              </Section>
            )}

            {report.dependency_mermaid && (
              <Section title="Dependency graph">
                <MermaidDiagram code={report.dependency_mermaid} id="deps" />
              </Section>
            )}

            {report.onboarding_doc && (
              <Section title="Onboarding doc (one-page)">
                <div className="rounded-md border border-[#21262d] bg-[#0d1117] p-4">
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => downloadOnboardingPdf(`${owner}/${repo}`, report.onboarding_doc!)}
                      className="rounded-md border border-[#21262d] bg-[#21262d] px-3 py-1.5 text-xs font-medium text-[#c6cdd5] hover:bg-[#30363d]"
                    >
                      Download as PDF
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(report.onboarding_doc!);
                      }}
                      className="rounded-md border border-[#21262d] bg-[#21262d] px-3 py-1.5 text-xs font-medium text-[#c6cdd5] hover:bg-[#30363d]"
                    >
                      Copy to clipboard
                    </button>
                  </div>
                  <div className="whitespace-pre-wrap text-sm text-[#c6cdd5]">{report.onboarding_doc}</div>
                </div>
                <p className="mt-2 text-xs text-[#8b949e]">
                  Use &quot;Download as PDF&quot; to open a print dialog and save as PDF.
                </p>
              </Section>
            )}

            {report.bug_risks && report.bug_risks.length > 0 && (
              <Section title="Bug risk analysis">
                <ul className="list-inside list-disc space-y-1 text-sm text-[#c6cdd5]">
                  {report.bug_risks.map((risk, i) => (
                    <li key={i}>{risk}</li>
                  ))}
                </ul>
              </Section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
