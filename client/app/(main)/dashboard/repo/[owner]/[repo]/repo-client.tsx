"use client";

import { useState } from "react";

interface AnalysisResult {
  [key: string]: unknown;
}

export default function RepoClient({ owner, repo }: { owner: string; repo: string }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startAnalysis = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

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

    setResult(data);
    setLoading(false);
  };

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold">
        {owner}/{repo}
      </h1>

      <button
        className="mt-4 rounded-md border px-4 py-2 hover:bg-gray-50 disabled:opacity-50"
        onClick={startAnalysis}
        disabled={loading}
      >
        {loading ? "Analyzing..." : "Analyze repo"}
      </button>

      {error && <p className="mt-3 text-sm text-red-500">{error}</p>}

      {result && (
        <pre className="mt-6 rounded-md border p-4 text-xs overflow-auto">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}