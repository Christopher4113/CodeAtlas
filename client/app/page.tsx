import Link from "next/link";
import Navbar from "@/components/navbar";
import { Button } from "@/components/ui/button";

function HeroSection() {
  return (
    <section className="flex flex-col items-center text-center px-4 pt-20 pb-12 md:pt-32 md:pb-16 max-w-4xl mx-auto">
      <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5">
        <span className="size-2 rounded-full bg-[#7ce38b] animate-pulse" />
        <span className="text-sm font-mono text-black">
          Autonomous Codebase Intelligence
        </span>
      </div>
      <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight text-foreground text-balance leading-[1.1] text-white">
        Understand any codebase{" "}
        <span className="text-[#77bdfb]">in minutes, not weeks.</span>
      </h1>
      <p className="mt-6 text-lg md:text-xl text-[#89929b] max-w-2xl text-pretty leading-relaxed">
        CodeAtlas ingests your GitHub repository and produces architecture
        diagrams, dependency graphs, onboarding docs, and bug risk
        analysis&mdash;powered by AI agents.
      </p>
      <div className="mt-10">
        <Button
          asChild
          size="lg"
          className="bg-[#ecf2f8] text-[#0d1117] hover:bg-[#c6cdd5] h-12 px-8 text-base font-semibold rounded-lg"
        >
          <Link href="/auth/sign-up">Get Started</Link>
        </Button>
      </div>
    </section>
  );
}

function TerminalWindow() {
  const lines = [
    { text: "$ codeatlas analyze --repo github.com/acme/platform", color: "#c6cdd5" },
    { text: "", color: "" },
    { text: "> Cloning repository...", color: "#7ce38b" },
    { text: "> Ingesting 847 files across 12 modules", color: "#7ce38b" },
    { text: "", color: "" },
    { text: "  [1/6] Classifying file types .............. done", color: "#89929b" },
    { text: "  [2/6] Summarizing code structure .......... done", color: "#89929b" },
    { text: "  [3/6] Mapping dependencies ................ done", color: "#89929b" },
    { text: "  [4/6] Building architecture diagram ....... done", color: "#89929b" },
    { text: "  [5/6] Detecting bug risks ................. done", color: "#89929b" },
    { text: "  [6/6] Generating report ................... done", color: "#89929b" },
    { text: "", color: "" },
    { text: "> Analysis complete. 6 reports generated.", color: "#ecf2f8" },
    { text: "> Open dashboard at https://app.codeatlas.dev/acme/platform", color: "#77bdfb" },
  ];

  return (
    <section className="w-full max-w-3xl mx-auto px-4 pb-16 md:pb-24">
      <div className="rounded-xl border border-border bg-[#161b22] overflow-hidden shadow-2xl shadow-[#000000]/40">
        {/* Title bar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-[#21262d]">
          <span className="size-3 rounded-full bg-[#fa7970]" />
          <span className="size-3 rounded-full bg-[#faa356]" />
          <span className="size-3 rounded-full bg-[#7ce38b]" />
          <span className="ml-3 text-xs text-[#89929b] font-mono">
            codeatlas analyze
          </span>
        </div>
        {/* Terminal body */}
        <div className="p-5 md:p-6 font-mono text-sm leading-7">
          {lines.map((line, i) =>
            line.text === "" ? (
              <div key={i} className="h-4" />
            ) : (
              <div key={i} style={{ color: line.color }}>
                {line.text}
              </div>
            )
          )}
        </div>
      </div>
    </section>
  );
}

const FEATURES = [
  {
    title: "Architecture Diagrams",
    description:
      "Auto-generated visual maps of your system architecture, updated with every commit.",
    color: "#77bdfb",
    icon: (
      <svg className="size-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25a2.25 2.25 0 0 1-2.25-2.25v-2.25Z" />
      </svg>
    ),
  },
  {
    title: "Dependency Graphs",
    description:
      "Interactive graphs showing how every module connects, with risk scores and coupling metrics.",
    color: "#7ce38b",
    icon: (
      <svg className="size-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
      </svg>
    ),
  },
  {
    title: "Onboarding Docs",
    description:
      "Auto-generate onboarding guides so new engineers understand the codebase from day one.",
    color: "#cea5fb",
    icon: (
      <svg className="size-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
      </svg>
    ),
  },
  {
    title: "Bug Risk Analysis",
    description:
      "Identify code hotspots, complex dependencies, and high-churn files that are likely to break.",
    color: "#faa356",
    icon: (
      <svg className="size-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
      </svg>
    ),
  },
];

function FeaturesSection() {
  return (
    <section className="w-full max-w-4xl mx-auto px-4 py-16 md:py-24">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {FEATURES.map((feature) => (
          <div
            key={feature.title}
            className="flex gap-4 rounded-lg border border-border bg-[#161b22] p-5 transition-colors hover:border-[#89929b]/40"
          >
            <div
              className="flex size-10 shrink-0 items-center justify-center rounded-lg"
              style={{ backgroundColor: `${feature.color}15`, color: feature.color }}
            >
              {feature.icon}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#ecf2f8]">
                {feature.title}
              </h3>
              <p className="mt-1 text-sm text-[#89929b] leading-relaxed">
                {feature.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section className="w-full max-w-3xl mx-auto px-4 pb-16 md:pb-24">
      <div className="rounded-lg border border-border bg-[#161b22] p-8 md:p-12 text-center">
        <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-[#ecf2f8] text-balance">
          Stop onboarding blind.
        </h2>
        <p className="mt-3 text-[#89929b] max-w-lg mx-auto text-pretty">
          Connect your first repository and get a full codebase analysis in
          under five minutes.
        </p>
        <div className="mt-8">
          <Button
            asChild
            size="lg"
            className="bg-[#ecf2f8] text-[#0d1117] hover:bg-[#c6cdd5] h-12 px-8 text-base font-semibold rounded-lg"
          >
            <Link href="/auth/sign-up">Get Started</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="w-full border-t border-border py-8 px-4">
      <div className="max-w-4xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-md bg-[#ecf2f8] text-[#0d1117] text-xs font-bold">
            CA
          </div>
          <span className="text-sm font-semibold text-[#ecf2f8]">
            CodeAtlas
          </span>
        </div>
        <p className="text-xs text-[#89929b]">
          {"Built for engineering teams that ship fast."}
        </p>
      </div>
    </footer>
  );
}

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center bg-[#0d1117]">
      <div className="flex-1 w-full flex flex-col items-center">
        <Navbar />
        <HeroSection />
        <TerminalWindow />
        <FeaturesSection />
        <CTASection />
        <Footer />
      </div>
    </main>
  );
}
