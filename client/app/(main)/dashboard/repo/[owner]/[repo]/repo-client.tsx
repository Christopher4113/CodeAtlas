"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function RepoClient({ owner, repo }: { owner: string; repo: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startAnalysis = async () => {
    setLoading(true);
    setError(null);

    const res = await fetch("/api/analysis/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ owner, repo }),
    });

    const data = await res.json();

    if (!res.ok) {
      setError(data?.error ?? "Failed to start analysis");
      setLoading(false);
      return;
    }

    const analysisId = data?.analysis_id;
    if (!analysisId) {
      setError("Missing analysis_id from server");
      setLoading(false);
      return;
    }

    router.push(`/dashboard/repo/${owner}/${repo}/runs/${analysisId}`);
  };

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold text-[#ecf2f8]">
        {owner}/{repo}
      </h1>

      <button
        className="mt-4 rounded-md border border-[#21262d] bg-[#161b22] px-4 py-2 text-[#ecf2f8] hover:bg-[#1c2129] disabled:opacity-50"
        onClick={startAnalysis}
        disabled={loading}
      >
        {loading ? "Starting..." : "Analyze repo"}
      </button>

      {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
    </div>
  );
}