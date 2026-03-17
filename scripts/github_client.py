"""GitHub API client for fetching public repos, languages, and contribution stats."""

import requests
from datetime import datetime, timezone


class GitHubClient:
    """Fetches data from GitHub REST and GraphQL APIs."""

    GRAPHQL_URL = "https://api.github.com/graphql"
    REST_BASE = "https://api.github.com"

    def __init__(self, token: str, username: str):
        self.token = token
        self.username = username
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            }
        )

    # ------------------------------------------------------------------ REST

    def fetch_repos(self) -> list[dict]:
        """Fetch all public, non-fork repos owned by the user."""
        repos = []
        page = 1
        while True:
            resp = self.session.get(
                f"{self.REST_BASE}/users/{self.username}/repos",
                params={"type": "owner", "per_page": 100, "page": page},
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            repos.extend(batch)
            page += 1
        return [r for r in repos if not r.get("fork")]

    def fetch_repo_languages(self, repo_name: str) -> dict[str, int]:
        """Return {language: bytes} for a single repo."""
        resp = self.session.get(
            f"{self.REST_BASE}/repos/{self.username}/{repo_name}/languages"
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_all_languages(self, repos: list[dict]) -> dict[str, int]:
        """Aggregate language bytes across all repos."""
        totals: dict[str, int] = {}
        for repo in repos:
            langs = self.fetch_repo_languages(repo["name"])
            for lang, byte_count in langs.items():
                totals[lang] = totals.get(lang, 0) + byte_count
        return totals

    # --------------------------------------------------------------- GraphQL

    def fetch_contribution_stats(self) -> dict:
        """Fetch contribution stats via GraphQL (includes private counts)."""
        query = """
        query($username: String!) {
          user(login: $username) {
            contributionsCollection {
              totalCommitContributions
              totalPullRequestContributions
              totalIssueContributions
              totalRepositoryContributions
              restrictedContributionsCount
              contributionCalendar {
                totalContributions
              }
            }
            followers { totalCount }
            following { totalCount }
            repositories(ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
          }
        }
        """
        resp = self.session.post(
            self.GRAPHQL_URL,
            json={"query": query, "variables": {"username": self.username}},
        )
        resp.raise_for_status()
        data = resp.json()

        if "errors" in data:
            raise RuntimeError(f"GraphQL errors: {data['errors']}")

        user = data["data"]["user"]
        cc = user["contributionsCollection"]
        calendar_total = cc["contributionCalendar"]["totalContributions"]
        private_count = cc["restrictedContributionsCount"]

        return {
            "total_contributions": calendar_total + private_count,
            "total_commits": cc["totalCommitContributions"],
            "total_prs": cc["totalPullRequestContributions"],
            "total_issues": cc["totalIssueContributions"],
            "total_repos_created": cc["totalRepositoryContributions"],
            "private_contributions": private_count,
            "followers": user["followers"]["totalCount"],
            "following": user["following"]["totalCount"],
            "public_repo_count": user["repositories"]["totalCount"],
        }

    # ------------------------------------------------------------ Aggregate

    def collect_all(self) -> dict:
        """Collect all data needed for the README template."""
        repos = self.fetch_repos()
        lang_bytes = self.fetch_all_languages(repos)
        contribution_stats = self.fetch_contribution_stats()

        # Compute language percentages
        total_bytes = sum(lang_bytes.values()) or 1
        languages = [
            {"name": lang, "bytes": b, "percentage": round(b / total_bytes * 100, 1)}
            for lang, b in sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)
        ]

        # Top repos by stars
        top_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:4]
        top_repos = [
            {
                "name": r["name"],
                "url": r["html_url"],
                "description": r.get("description") or "",
                "stars": r["stargazers_count"],
                "forks": r["forks_count"],
                "language": r.get("language") or "",
            }
            for r in top_repos
        ]

        return {
            "username": self.username,
            "repos": repos,
            "total_stars": sum(r.get("stargazers_count", 0) for r in repos),
            "total_forks": sum(r.get("forks_count", 0) for r in repos),
            "total_repos": len(repos),
            "languages": languages,
            "top_repos": top_repos,
            "stats": contribution_stats,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
