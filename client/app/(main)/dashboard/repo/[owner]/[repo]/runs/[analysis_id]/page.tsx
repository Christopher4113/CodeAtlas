import RunPageClient from "./run-page-client";

export default async function RunPage({
  params,
}: {
  params: Promise<{ owner: string; repo: string; analysis_id: string }>;
}) {
  const { owner, repo, analysis_id } = await params;
  return <RunPageClient owner={owner} repo={repo} analysis_id={analysis_id} />;
}
