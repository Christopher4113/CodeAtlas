"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { MermaidDiagram } from "@/components/MermaidDiagram";

function isCodeElement(node: React.ReactNode): boolean {
  return React.isValidElement(node) && (node.type as unknown) === "code";
}

function OnboardingListItem({ children }: { children: React.ReactNode }) {
  const arr = React.Children.toArray(children);
  const first = arr[0];
  const rest = arr.slice(1);
  if (isCodeElement(first) && rest.length > 0) {
    const descStr = rest.map((c) => (typeof c === "string" ? c : "")).join("").replace(/^\s*:\s*/, "").trim();
    return (
      <li className="list-none -ml-5 pl-5 grid grid-cols-[minmax(0,max-content)_1fr] gap-x-3 gap-y-0.5 py-1.5 items-baseline border-b border-[#21262d]/50 last:border-b-0">
        <span className="font-mono text-xs text-[#7ee787] whitespace-nowrap shrink-0">{first}</span>
        <span className="text-[#c6cdd5] text-sm">{descStr || rest}</span>
      </li>
    );
  }
  const single = arr.length === 1 && typeof arr[0] === "string";
  const str = single ? (arr[0] as string) : "";
  const colonIdx = str.indexOf(":");
  if (single && colonIdx > 0 && colonIdx < 60) {
    const pathPart = str.slice(0, colonIdx).replace(/\s+$/, "");
    const descPart = str.slice(colonIdx + 1).replace(/^\s+/, "");
    if (pathPart.length > 0 && descPart.length > 0) {
      return (
        <li className="list-none -ml-5 pl-5 grid grid-cols-[minmax(0,max-content)_1fr] gap-x-3 gap-y-0.5 py-1.5 items-baseline border-b border-[#21262d]/50 last:border-b-0">
          <span className="font-mono text-xs text-[#7ee787] whitespace-nowrap shrink-0">{pathPart}</span>
          <span className="text-[#c6cdd5] text-sm">{descPart}</span>
        </li>
      );
    }
  }
  return <li className="leading-relaxed py-0.5">{children}</li>;
}

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

async function downloadOnboardingPdf(title: string, markdown: string) {
  const [jspdfModule, markedModule, html2canvasModule] = await Promise.all([
    import("jspdf"),
    import("marked"),
    import("html2canvas"),
  ]);
  const jsPDF = jspdfModule.default;
  const markedLib = (markedModule as { marked?: (s: string) => string | Promise<string>; parse?: (s: string) => string | Promise<string>; default?: (s: string) => string | Promise<string> }).marked ?? (markedModule as { parse?: (s: string) => string | Promise<string> }).parse ?? (markedModule as { default?: (s: string) => string | Promise<string> }).default;
  const html2canvas = html2canvasModule.default;

  const safeTitle = title.replace(/</g, "&lt;").replace(/[\\/:*?"<>|]/g, "-");
  if (!markedLib) throw new Error("marked parser not found");
  const parsed = markedLib(markdown);
  const htmlContent = typeof parsed === "string" ? parsed : await parsed;

  const container = document.createElement("div");
  container.style.position = "absolute";
  container.style.left = "-9999px";
  container.style.top = "0";
  container.style.width = "210mm";
  container.style.padding = "20mm";
  container.style.fontFamily = "system-ui, -apple-system, sans-serif";
  container.style.fontSize = "11pt";
  container.style.lineHeight = "1.6";
  container.style.color = "#1a1a1a";
  container.style.background = "#fff";
  container.innerHTML = `
    <style>
      .pdf-doc h1 { font-size: 1.5em; margin: 0 0 0.5em; border-bottom: 1px solid #eee; padding-bottom: 0.25em; }
      .pdf-doc h2 { font-size: 1.25em; margin: 1em 0 0.35em; }
      .pdf-doc h3 { font-size: 1.1em; margin: 0.75em 0 0.25em; }
      .pdf-doc p { margin: 0 0 0.5em; }
      .pdf-doc ul, .pdf-doc ol { margin: 0 0 0.5em; padding-left: 1.5em; }
      .pdf-doc code { background: #f5f5f5; padding: 0.15em 0.4em; border-radius: 4px; font-size: 0.95em; }
      .pdf-doc pre { background: #f5f5f5; padding: 0.75em; overflow-x: auto; margin: 0.5em 0; border-radius: 4px; font-size: 0.9em; }
      .pdf-doc pre code { background: none; padding: 0; }
      .pdf-doc table { border-collapse: collapse; width: 100%; margin: 0.5em 0; }
      .pdf-doc th, .pdf-doc td { border: 1px solid #ddd; padding: 0.4em 0.6em; text-align: left; }
      .pdf-doc th { background: #f5f5f5; font-weight: 600; }
      .pdf-doc hr { border: none; border-top: 1px solid #eee; margin: 1em 0; }
    </style>
    <div class="pdf-doc">${htmlContent}</div>
  `;
  document.body.appendChild(container);

  try {
    const canvas = await html2canvas(container, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: "#ffffff",
    });
    document.body.removeChild(container);

    const imgData = canvas.toDataURL("image/jpeg", 0.95);
    const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const margin = 10;
    const contentW = pageW - 2 * margin;
    const contentH = pageH - 2 * margin;
    const imgW = contentW;
    const imgH = (canvas.height * contentW) / canvas.width;
    let heightLeft = imgH;
    let position = 0;

    pdf.addImage(imgData, "JPEG", margin, margin, imgW, imgH, undefined, "FAST");
    heightLeft -= contentH;

    while (heightLeft > 0) {
      position = heightLeft - imgH;
      pdf.addPage();
      pdf.addImage(imgData, "JPEG", margin, position, imgW, imgH, undefined, "FAST");
      heightLeft -= contentH;
    }

    pdf.save(`${safeTitle.replace(/\s+/g, "-")}-onboarding.pdf`);
  } catch (e) {
    document.body.removeChild(container);
    console.error(e);
  }
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
                  <div className="prose-onboarding text-sm text-[#c6cdd5]">
                    <ReactMarkdown
                      components={{
                        h1: ({ children }) => <h1 className="mb-2 mt-4 border-b border-[#21262d] pb-1 text-lg font-semibold text-[#ecf2f8] first:mt-0">{children}</h1>,
                        h2: ({ children }) => <h2 className="mb-1.5 mt-3 text-base font-semibold text-[#ecf2f8]">{children}</h2>,
                        h3: ({ children }) => <h3 className="mb-1 mt-2 text-sm font-semibold text-[#c6cdd5]">{children}</h3>,
                        p: ({ children }) => <p className="mb-2 leading-relaxed">{children}</p>,
                        ul: ({ children }) => (
                          <ul className="mb-2 list-disc pl-5 space-y-0.5 has-[>li[class*='grid']]:list-none has-[>li[class*='grid']]:pl-0 has-[>li[class*='grid']]:border has-[>li[class*='grid']]:border-[#21262d] has-[>li[class*='grid']]:rounded-md has-[>li[class*='grid']]:overflow-hidden">
                            {children}
                          </ul>
                        ),
                        ol: ({ children }) => <ol className="mb-2 list-decimal pl-5 space-y-0.5">{children}</ol>,
                        li: ({ children }) => <OnboardingListItem>{children}</OnboardingListItem>,
                        code: ({ className, children }) => {
                          const isBlock = className?.includes("language-");
                          if (isBlock) {
                            return <pre className="my-2 overflow-x-auto rounded border border-[#21262d] bg-[#161b22] p-3 text-xs"><code>{children}</code></pre>;
                          }
                          return <code className="rounded bg-[#161b22] px-1.5 py-0.5 font-mono text-xs">{children}</code>;
                        },
                        pre: ({ children }) => <>{children}</>,
                        table: ({ children }) => <div className="my-2 overflow-x-auto"><table className="w-full border-collapse text-left">{children}</table></div>,
                        thead: ({ children }) => <thead>{children}</thead>,
                        tbody: ({ children }) => <tbody>{children}</tbody>,
                        tr: ({ children }) => <tr className="border-b border-[#21262d]">{children}</tr>,
                        th: ({ children }) => <th className="border-b border-[#21262d] bg-[#161b22] px-3 py-2 text-xs font-semibold text-[#ecf2f8]">{children}</th>,
                        td: ({ children }) => <td className="px-3 py-2 text-xs">{children}</td>,
                        hr: () => <hr className="my-3 border-[#21262d]" />,
                        strong: ({ children }) => <strong className="font-semibold text-[#ecf2f8]">{children}</strong>,
                        a: ({ href, children }) => <a href={href} className="text-[#58a6ff] hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                      }}
                    >
                      {report.onboarding_doc}
                    </ReactMarkdown>
                  </div>
                </div>
                <p className="mt-2 text-xs text-[#8b949e]">
                  Download saves a PDF file to your computer. Copy stores the raw markdown.
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
