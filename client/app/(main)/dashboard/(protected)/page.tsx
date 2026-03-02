"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Repo = {
  id: number;
  name: string;
  full_name: string;
  private: boolean;
  default_branch: string;
  updated_at: string;
};

function RepoSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg border border-[#21262d] bg-[#161b22] p-4 animate-pulse"
        >
          <div className="h-4 w-64 rounded bg-[#21262d]" />
          <div className="mt-2 h-3 w-32 rounded bg-[#21262d]" />
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    (async () => {
      const res = await fetch("/api/github/repos");
      if (res.ok) setRepos(await res.json());
      setLoading(false);
    })();
  }, []);

  return (
    <main className="min-h-screen flex flex-col bg-[#0d1117]">
      <div className="flex-1 w-full max-w-4xl mx-auto px-4 py-10 md:px-6 md:py-14">
        <div className="flex items-center gap-3 mb-8">
          <svg
            className="size-5 text-[#89929b]"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
            />
          </svg>
          <h1 className="text-xl font-semibold text-[#ecf2f8]">
            Pick a repo
          </h1>
        </div>

        {loading ? (
          <RepoSkeleton />
        ) : repos.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-[#21262d] bg-[#161b22] py-16 px-6 text-center">
            <svg
              className="size-10 text-[#89929b] mb-4"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
              />
            </svg>
            <p className="text-[#c6cdd5] font-medium">
              No repositories found
            </p>
            <p className="mt-1 text-sm text-[#89929b]">
              Connect your GitHub account to get started.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {repos.map((r) => (
              <button
                key={r.id}
                className="group w-full flex items-center justify-between rounded-lg border border-[#21262d] bg-[#161b22] p-4 text-left transition-colors hover:border-[#89929b]/50 hover:bg-[#1c2129] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#77bdfb]"
                onClick={() =>
                  router.push(`/dashboard/repo/${r.full_name}`)
                }
              >
                <div className="flex items-center gap-3 min-w-0">
                  <svg
                    className="size-4 shrink-0 text-[#89929b]"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5"
                    />
                  </svg>
                  <div className="min-w-0">
                    <div className="font-medium text-[#ecf2f8] truncate group-hover:text-[#77bdfb] transition-colors">
                      {r.full_name}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
                          r.private
                            ? "bg-[#faa356]/10 text-[#faa356]"
                            : "bg-[#7ce38b]/10 text-[#7ce38b]"
                        }`}
                      >
                        {r.private ? "Private" : "Public"}
                      </span>
                      <span className="text-xs text-[#89929b] font-mono">
                        {r.default_branch}
                      </span>
                    </div>
                  </div>
                </div>
                <svg
                  className="size-4 shrink-0 text-[#89929b] opacity-0 group-hover:opacity-100 transition-opacity"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="m8.25 4.5 7.5 7.5-7.5 7.5"
                  />
                </svg>
              </button>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
