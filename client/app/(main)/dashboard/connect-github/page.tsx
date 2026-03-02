"use client";

import { createClient } from "@/lib/supabase/client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

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

  if (loading) return <div>Loading...</div>;

  return (
    <div className="p-6 bg-[#0d1117]">
      <h1 className="text-xl font-semibold text-white">Connect GitHub</h1>
      <p className="mt-2 text-sm text-white">
        You need to connect GitHub to analyze repositories.
      </p>
      <button
        className="mt-4 rounded-md border px-4 py-2 hover:bg-gray-50 text-white"
        onClick={connectGithub}
      >
        Connect GitHub
      </button>
    </div>
  );
}