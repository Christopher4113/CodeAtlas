import base64
from typing import List, Dict

import httpx


class GitHubError(RuntimeError):
    pass


def _auth_headers(token: str) -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "codeatlas-backend",
    }
    if token:
        # Fine-grained PATs expect a Bearer token.
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_repo_tree(owner: str, repo: str, branch: str, token: str) -> List[Dict]:
    """
    Fetch the full file tree (blobs only) for a repo/branch.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}"
    params = {"recursive": "1"}
    resp = httpx.get(url, headers=_auth_headers(token), params=params, timeout=30.0)
    if resp.status_code >= 400:
        raise GitHubError(
            f"GitHub tree fetch failed ({resp.status_code}): {resp.text[:200]}"
        )
    data = resp.json()
    tree = data.get("tree", [])
    files: List[Dict] = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        files.append(
            {
                "path": item.get("path", ""),
                "sha": item.get("sha", ""),
                "size": int(item.get("size", 0) or 0),
                "content": None,
            }
        )
    return files


def fetch_file_content(
    owner: str, repo: str, branch: str, path: str, token: str
) -> str:
    """
    Fetch a single file's contents via the GitHub contents API.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": branch}
    resp = httpx.get(url, headers=_auth_headers(token), params=params, timeout=30.0)
    if resp.status_code == 404:
        return ""
    if resp.status_code >= 400:
        raise GitHubError(
            f"GitHub content fetch failed for {path} ({resp.status_code}): "
            f"{resp.text[:200]}"
        )

    data = resp.json()
    content = data.get("content")
    encoding = data.get("encoding")
    if not content:
        return ""
    if encoding == "base64":
        return base64.b64decode(content).decode("utf-8", errors="ignore")
    # Fallback – GitHub should always send base64 here, but be defensive.
    return str(content)


def fetch_multiple_file_contents(
    owner: str,
    repo: str,
    branch: str,
    paths: List[str],
    token: str,
    max_bytes: int = 200_000,
) -> Dict[str, str]:
    """
    Fetch contents for a set of paths with a simple size cap.
    """
    out: Dict[str, str] = {}
    for path in paths:
        text = fetch_file_content(owner, repo, branch, path, token)
        if not text:
            continue
        if len(text.encode("utf-8")) > max_bytes:
            # Truncate very large files to keep token usage reasonable.
            text = text[:max_bytes]
        out[path] = text
    return out

