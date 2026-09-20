from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.demo import GITHUB_COMMITS, GITHUB_PRS
from app.models import ToolResult


class GitHubTool:
    name = "github"

    def __init__(self) -> None:
        self.token = settings.github_token
        self.repo = settings.github_repo

    def search_code_changes(self, query: str, limit: int = 8) -> ToolResult:
        if self.token:
            return self._live_search_commits(query, limit)
        q = query.lower()
        ranked = []
        for commit in GITHUB_COMMITS:
            blob = " ".join(
                [commit["message"], " ".join(commit["files"]), commit.get("diff", "")]
            ).lower()
            score = sum(1 for word in q.split() if word in blob) + (
                2 if commit["relevance"] == "high" else 0
            )
            ranked.append((score, commit))
        ranked.sort(key=lambda item: item[0], reverse=True)
        matches = [commit for score, commit in ranked if score > 0][:limit] or [
            GITHUB_COMMITS[0]
        ]
        top = matches[0]
        return ToolResult(
            tool=self.name,
            action="search_code_changes",
            summary=(
                f"Found {len(matches)} relevant commits. "
                f"Most relevant: {top['sha']} — {top['message']}."
            ),
            data={"query": query, "repo": self.repo, "commits": matches},
            references=[c["html_url"] for c in matches],
        )

    def search_pull_requests(self, query: str) -> ToolResult:
        if self.token:
            return self._live_search_pulls(query)
        q = query.lower()
        matches = [
            pr
            for pr in GITHUB_PRS
            if any(word in (pr["title"] + pr["body"]).lower() for word in q.split())
        ] or GITHUB_PRS[:1]
        top = matches[0]
        return ToolResult(
            tool=self.name,
            action="search_pull_requests",
            summary=f"Matched {len(matches)} PRs. Latest relevant: #{top['number']} {top['title']} ({top['state']}).",
            data={"query": query, "pull_requests": matches},
            references=[pr["html_url"] for pr in matches],
        )

    def get_commit_diff(self, sha: str) -> ToolResult:
        if self.token:
            return self._live_commit(sha)
        commit = next((c for c in GITHUB_COMMITS if c["sha"].startswith(sha)), None)
        if not commit:
            return ToolResult(
                tool=self.name,
                action="get_commit_diff",
                summary=f"No demo commit found for {sha}.",
                data={"sha": sha},
            )
        return ToolResult(
            tool=self.name,
            action="get_commit_diff",
            summary=f"Loaded diff for {commit['sha']}: {commit['message']}.",
            data=commit,
            references=[commit["html_url"]],
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _live_search_commits(self, query: str, limit: int) -> ToolResult:
        url = "https://api.github.com/search/commits"
        try:
            response = httpx.get(
                url,
                params={"q": f"repo:{self.repo} {query}", "per_page": limit},
                headers=self._headers(),
                timeout=15.0,
            )
            payload = response.json()
            items = payload.get("items", [])[:limit]
            commits = [
                {
                    "sha": item["sha"][:10],
                    "html_url": item.get("html_url"),
                    "message": item.get("commit", {}).get("message", "").split("\n")[0],
                    "author": item.get("commit", {}).get("author", {}).get("name"),
                    "committed_at": item.get("commit", {}).get("author", {}).get("date"),
                }
                for item in items
            ]
            return ToolResult(
                tool=self.name,
                action="search_code_changes",
                summary=f"GitHub commit search returned {len(commits)} hits for '{query}'.",
                data={"query": query, "commits": commits, "total": payload.get("total_count")},
                references=[c["html_url"] for c in commits if c.get("html_url")],
            )
        except Exception as exc:
            return ToolResult(
                tool=self.name,
                action="search_code_changes",
                summary=f"Live GitHub search failed, falling back is not automatic: {exc}",
                data={"error": str(exc)},
            )

    def _live_search_pulls(self, query: str) -> ToolResult:
        url = f"https://api.github.com/repos/{self.repo}/pulls"
        try:
            response = httpx.get(
                url,
                params={"state": "all", "per_page": 20, "sort": "updated"},
                headers=self._headers(),
                timeout=15.0,
            )
            items = response.json() if response.status_code == 200 else []
            q = query.lower()
            matches = [
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "html_url": pr["html_url"],
                    "state": pr.get("merged_at") and "merged" or pr["state"],
                    "merged_at": pr.get("merged_at"),
                    "author": (pr.get("user") or {}).get("login"),
                    "body": (pr.get("body") or "")[:500],
                }
                for pr in items
                if q in (pr.get("title", "") + (pr.get("body") or "")).lower()
            ][:8]
            return ToolResult(
                tool=self.name,
                action="search_pull_requests",
                summary=f"GitHub PR search returned {len(matches)} matches.",
                data={"query": query, "pull_requests": matches},
                references=[pr["html_url"] for pr in matches],
            )
        except Exception as exc:
            return ToolResult(
                tool=self.name,
                action="search_pull_requests",
                summary=f"Live GitHub PR search failed: {exc}",
                data={"error": str(exc)},
            )

    def _live_commit(self, sha: str) -> ToolResult:
        url = f"https://api.github.com/repos/{self.repo}/commits/{sha}"
        try:
            response = httpx.get(url, headers=self._headers(), timeout=15.0)
            payload: Any = response.json()
            files = [f.get("filename") for f in payload.get("files", [])]
            return ToolResult(
                tool=self.name,
                action="get_commit_diff",
                summary=f"Loaded live commit {sha[:10]} touching {len(files)} files.",
                data={
                    "sha": payload.get("sha"),
                    "html_url": payload.get("html_url"),
                    "message": payload.get("commit", {}).get("message"),
                    "files": files,
                    "files_detail": payload.get("files", [])[:12],
                },
                references=[payload.get("html_url")] if payload.get("html_url") else [],
            )
        except Exception as exc:
            return ToolResult(
                tool=self.name,
                action="get_commit_diff",
                summary=f"Live commit lookup failed: {exc}",
                data={"error": str(exc), "sha": sha},
            )
