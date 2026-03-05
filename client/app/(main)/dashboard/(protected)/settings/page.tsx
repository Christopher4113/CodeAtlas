"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const GITHUB_PAT_URL = "https://github.com/settings/tokens/new?description=CodeAtlas&scopes=repo,read:user";

export default function SettingsPage() {
  const [token, setToken] = useState("");
  const [hasToken, setHasToken] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    (async () => {
      const res = await fetch("/api/settings/github-token");
      if (res.ok) {
        const data = await res.json();
        setHasToken(!!data?.has_token);
      } else {
        setHasToken(false);
      }
    })();
  }, []);

  const saveToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    setSaving(true);
    try {
      const res = await fetch("/api/settings/github-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ github_token: token }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMessage({ type: "error", text: data?.error === "github_token_required" ? "Please enter a token." : (data?.detail ?? "Failed to save.") });
        return;
      }
      setMessage({ type: "success", text: "GitHub token saved. You can use it for repo analysis." });
      setToken("");
      setHasToken(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col bg-[#0d1117]">
      <div className="flex-1 w-full max-w-2xl mx-auto px-4 py-10 md:px-6 md:py-14">
        <div className="mb-6">
          <Link href="/dashboard" className="text-sm text-[#58a6ff] hover:underline">
            ← Back to dashboard
          </Link>
        </div>
        <h1 className="text-xl font-semibold text-[#ecf2f8] mb-2">Settings</h1>
        <p className="text-sm text-[#8b949e] mb-8">
          Configure GitHub access for listing repos and running analyses.
        </p>

        <section className="rounded-lg border border-[#21262d] bg-[#161b22] p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#8b949e] mb-1">
            GitHub token
          </h2>
          <p className="text-sm text-[#c6cdd5] mb-4">
            CodeAtlas needs a GitHub token to clone and analyze your repositories. You can either connect with GitHub (OAuth) or add a Personal Access Token here.
          </p>

          <div className="rounded-md border border-[#21262d] bg-[#0d1117] p-4 mb-4 text-sm text-[#c6cdd5] space-y-3">
            <p className="font-medium text-[#ecf2f8]">How to create a Personal Access Token (PAT):</p>
            <ol className="list-decimal list-inside space-y-2 text-[#8b949e]">
              <li>Open GitHub → Settings → Developer settings → Personal access tokens.</li>
              <li>Click &quot;Generate new token (classic)&quot;.</li>
              <li>Give it a name (e.g. CodeAtlas), set an expiration, and enable the <strong className="text-[#c6cdd5]">repo</strong> scope (and <strong className="text-[#c6cdd5]">read:user</strong> if you use it for listing repos).</li>
              <li>Generate the token and paste it below. Store it somewhere safe; GitHub won’t show it again.</li>
            </ol>
            <a
              href={GITHUB_PAT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[#58a6ff] hover:underline"
            >
              Open GitHub: Create new token
              <svg className="size-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>

          {hasToken === true && !token && (
            <p className="text-sm text-[#7ce38b]/90 mb-3">You have a token saved. Enter a new value below to replace it.</p>
          )}

          <form onSubmit={saveToken} className="flex flex-col gap-3">
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              className="w-full rounded-md border border-[#21262d] bg-[#0d1117] px-3 py-2 text-sm text-[#ecf2f8] placeholder:text-[#484f58] focus:border-[#58a6ff] focus:outline-none focus:ring-1 focus:ring-[#58a6ff]"
              autoComplete="off"
            />
            <button
              type="submit"
              disabled={saving || !token.trim()}
              className="w-fit rounded-md border border-[#21262d] bg-[#238636] px-4 py-2 text-sm font-medium text-white hover:bg-[#2ea043] disabled:opacity-50 disabled:pointer-events-none"
            >
              {saving ? "Saving..." : "Save token"}
            </button>
          </form>

          {message && (
            <p className={`mt-3 text-sm ${message.type === "success" ? "text-[#7ce38b]" : "text-red-400"}`}>
              {message.text}
            </p>
          )}
        </section>
      </div>
    </main>
  );
}
