"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AnalysisTerminal, type ProgressStep } from "./analysis-terminal";

const POLL_INTERVAL_MS = 1500;

export default function RepoClient({ owner, repo }: { owner: string; repo: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [status, setStatus] = useState<"running" | "completed" | "error" | null>(null);
  const [progress, setProgress] = useState<ProgressStep[]>([]);
  const [jobError, setJobError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startAnalysis = async () => {
    setLoading(true);
    setError(null);
    setJobError(null);
    setProgress([]);
    setStatus(null);

    const res = await fetch("/api/analysis/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ owner, repo }),
    });

    const data = await res.json();

    if (!res.ok) {
      const msg =
        data?.error === "missing_github_token"
          ? "Add a GitHub token in Settings to run analysis."
          : (data?.error ?? "Failed to start analysis");
      setError(msg);
      setLoading(false);
      return;
    }

    const id = data?.analysis_id;
    if (!id) {
      setError("Missing analysis_id from server");
      setLoading(false);
      return;
    }

    setAnalysisId(id);
    setStatus("running");
    setLoading(false);
  };

  useEffect(() => {
    if (!analysisId || status !== "running") return;

    const poll = async () => {
      try {
        const res = await fetch(`/api/analysis/${analysisId}`, { cache: "no-store" });
        const data = await res.json();
        if (!res.ok) return;

        const jobProgress = (data.progress ?? []) as ProgressStep[];
        setProgress(jobProgress);
        const jobStatus = data.status as "running" | "completed" | "error";
        setStatus(jobStatus);
        if (data.error) setJobError(data.error);

        if (jobStatus === "completed") {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
          // Brief delay so user sees "Analysis complete" and dashboard link
          setTimeout(() => {
            router.push(`/dashboard/repo/${owner}/${repo}/runs/${analysisId}`);
          }, 1800);
        }
      } catch {
        // keep polling
      }
    };

    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [analysisId, status, owner, repo, router]);

  const showTerminal = analysisId != null && status != null;
  const dashboardUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/dashboard/repo/${owner}/${repo}/runs/${analysisId}`
      : "";

  return (
    <main className="min-h-screen flex flex-col bg-[#0d1117]">
      <div className="flex-1 w-full max-w-4xl mx-auto px-4 py-10 md:px-6 md:py-14">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-xl font-semibold text-[#ecf2f8] truncate">
              {owner}/{repo}
            </h1>
            <p className="mt-1 text-sm text-[#89929b]">
              Run a full-code analysis to get architecture diagrams, onboarding docs, and risk insights.
            </p>
          </div>
          <Link
            href="/dashboard"
            className="shrink-0 text-sm text-[#58a6ff] hover:underline"
          >
            ← Back to repos
          </Link>
        </div>

        {!showTerminal && (
          <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-sm text-[#c6cdd5]">
                <p className="font-medium text-[#ecf2f8]">
                  Analyze this repository
                </p>
                <p className="mt-1 text-[#89929b]">
                  CodeAtlas will clone the repo, inspect the structure, and generate summaries and diagrams.
                </p>
              </div>
              <button
                type="button"
                onClick={startAnalysis}
                disabled={loading}
                className="mt-3 inline-flex items-center justify-center rounded-md border border-[#21262d] bg-[#238636] px-4 py-2 text-sm font-medium text-white hover:bg-[#2ea043] disabled:opacity-50 disabled:pointer-events-none sm:mt-0"
              >
                {loading ? "Starting…" : "Start analysis"}
              </button>
            </div>

            {error && (
              <p className="mt-4 text-sm text-red-400">
                {error}
                {error.includes("GitHub token") && (
                  <>
                    {" "}
                    <Link href="/dashboard/settings" className="text-[#58a6ff] hover:underline">
                      Open Settings
                    </Link>
                  </>
                )}
              </p>
            )}
          </div>
        )}

        {showTerminal && (
          <div className="space-y-4">
            <AnalysisTerminal
              owner={owner}
              repo={repo}
              progress={progress}
              status={status ?? "running"}
              error={jobError}
              dashboardUrl={dashboardUrl}
            />
            {status === "error" && (
              <p className="text-sm text-[#89929b]">
                <Link href="/dashboard" className="text-[#58a6ff] hover:underline">
                  ← Back to repos
                </Link>
              </p>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
