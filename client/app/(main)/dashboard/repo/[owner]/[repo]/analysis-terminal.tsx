"use client";

export type ProgressStep = { step: string; label: string; status: string };

const TOTAL_STEPS = 10;

function padDots(label: string, width: number = 28): string {
  const len = label.length;
  if (len >= width) return label;
  return label + ".".repeat(Math.max(0, width - len));
}

export function AnalysisTerminal({
  owner,
  repo,
  progress,
  status,
  error,
  dashboardUrl,
}: {
  owner: string;
  repo: string;
  progress: ProgressStep[];
  status: "running" | "completed" | "error" | "cancelled";
  error?: string | null;
  dashboardUrl: string;
}) {
  const nextLabel =
    status === "running" &&
    progress.length < TOTAL_STEPS
      ? (() => {
          const next: Record<number, string> = {
            0: "Cloning repository",
            1: "Ingesting files",
            2: "Classifying file types",
            3: "Summarizing code structure",
            4: "Building architecture diagram",
            5: "Writing onboarding doc",
            6: "Mapping dependencies",
            7: "Detecting bug risks",
            8: "Formatting frameworks",
            9: "Finalizing",
          };
          return next[progress.length] ?? "Working...";
        })()
      : null;

  return (
    <div className="rounded-lg border border-[#21262d] bg-[#0d1117] font-mono text-sm overflow-hidden">
      <div className="flex items-center gap-2 border-b border-[#21262d] px-3 py-2 bg-[#161b22]">
        <span className="w-3 h-3 rounded-full bg-[#f85149]" />
        <span className="w-3 h-3 rounded-full bg-[#f0883e]" />
        <span className="w-3 h-3 rounded-full bg-[#3fb950]" />
        <span className="ml-2 text-[#8b949e] text-xs">codeatlas analyze</span>
      </div>
      <div className="p-4 text-[#c9d1d9] space-y-0.5 min-h-[320px]">
        <div className="text-[#7ee787]">
          $ codeatlas analyze --repo github.com/{owner}/{repo}
        </div>
        {progress.length === 0 && status === "running" && (
          <div className="text-[#7ee787]">&gt; Cloning repository...</div>
        )}
        {progress.length > 0 && status === "running" && nextLabel && (
          <div className="text-[#7ee787]">&gt; {nextLabel}...</div>
        )}
        {progress.map((p, i) => (
          <div key={p.step} className="text-[#c9d1d9]">
            [{i + 1}/{TOTAL_STEPS}] {padDots(p.label)} done
          </div>
        ))}
        {status === "completed" && (
          <>
            <div className="text-[#7ee787] pt-1">
              &gt; Analysis complete. Reports generated.
            </div>
            <div className="text-[#7ee787]">
              &gt; Open dashboard at {dashboardUrl}
            </div>
          </>
        )}
        {status === "cancelled" && (
          <div className="text-[#f0883e] pt-1">&gt; Analysis cancelled.</div>
        )}
        {status === "error" && error && (
          <div className="text-red-400 pt-1">&gt; Error: {error}</div>
        )}
      </div>
    </div>
  );
}
