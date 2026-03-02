import RepoClient from "./repo-client";

export default async function RepoPage({
  params,
}: {
  params: Promise<{ owner: string; repo: string }>;
}) {
  const { owner, repo } = await params;
  return <RepoClient owner={owner} repo={repo} />;
}