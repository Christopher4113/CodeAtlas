"use client";

import { createClient } from "@/lib/supabase/client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function ConnectGithubPage() {
  const supabase = createClient();
  const router = useRouter();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const { data: { user } } = await supabase.auth.getUser();
      const hasGithub = user?.identities?.some((i) => i.provider === "github");

      if (hasGithub) {
        router.replace("/dashboard");
        return;
      }
      setLoading(false);
    })();
  }, [router, supabase]);

  const connectGithub = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) console.error(error);
  };

  if (loading) return <div className="p-6 bg-[#0d1117] text-[#c6cdd5]">Loading...</div>;

  return (
    <div className="p-6 bg-[#0d1117] max-w-lg">
      <h1 className="text-xl font-semibold text-white">Connect GitHub</h1>
      <p className="mt-2 text-sm text-[#c6cdd5]">
        Connect GitHub to list and analyze repositories.
      </p>
      <button
        className="mt-4 rounded-md border border-[#21262d] bg-[#238636] px-4 py-2 text-white hover:bg-[#2ea043]"
        onClick={connectGithub}
      >
        Connect with GitHub (OAuth)
      </button>
      <p className="mt-4 text-sm text-[#8b949e]">
        Or add a{" "}
        <Link href="/dashboard/settings" className="text-[#58a6ff] hover:underline">
          Personal Access Token in Settings
        </Link>{" "}
        to use repo analysis without OAuth.
      </p>
    </div>
  );
}