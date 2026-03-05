"use client";

import { useEffect, useRef, useState } from "react";

export function MermaidDiagram({ code, id }: { code: string; id: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code?.trim() || !containerRef.current) return;

    let cancelled = false;
    setError(null);

    import("mermaid")
      .then(async ({ default: mermaid }) => {
        if (cancelled || !containerRef.current) return;
        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          securityLevel: "loose",
        });
        const uniqueId = `mermaid-${id}-${Math.random().toString(36).slice(2, 9)}`;
        try {
          const { svg } = await mermaid.render(uniqueId, code);
          if (!cancelled && containerRef.current) {
            containerRef.current.innerHTML = svg;
          }
        } catch (e) {
          if (!cancelled) setError(e instanceof Error ? e.message : "Failed to render");
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load mermaid");
      });

    return () => {
      cancelled = true;
    };
  }, [code, id]);

  if (error) {
    return (
      <pre className="whitespace-pre-wrap overflow-auto rounded-md border border-[#21262d] bg-[#0d1117] p-4 text-xs text-[#c6cdd5]">
        {code}
      </pre>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex min-h-[120px] items-center justify-center rounded-md border border-[#21262d] bg-[#0d1117] p-4 [&_svg]:max-w-full [&_svg]:h-auto"
    />
  );
}
