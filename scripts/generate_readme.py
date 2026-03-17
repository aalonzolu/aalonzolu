#!/usr/bin/env python3
"""Generate the GitHub profile README.md from live API data and a Jinja2 template."""

import os
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from github_client import GitHubClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
USERNAME = "aalonzolu"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates"
OUTPUT_FILE = PROJECT_ROOT / "README.md"

# Language → shields.io metadata (logo slug + hex color)
LANG_META = {
    "C++": {"color": "00599C", "logo": "cplusplus"},
    "C": {"color": "A8B9CC", "logo": "c"},
    "Python": {"color": "3776AB", "logo": "python"},
    "C#": {"color": "239120", "logo": "csharp"},
    "PHP": {"color": "777BB4", "logo": "php"},
    "JavaScript": {"color": "F7DF1E", "logo": "javascript"},
    "TypeScript": {"color": "3178C6", "logo": "typescript"},
    "HTML": {"color": "E34F26", "logo": "html5"},
    "CSS": {"color": "1572B6", "logo": "css3"},
    "Shell": {"color": "4EAA25", "logo": "gnubash"},
    "Dockerfile": {"color": "2496ED", "logo": "docker"},
    "HCL": {"color": "7B42BC", "logo": "terraform"},
    "Go": {"color": "00ADD8", "logo": "go"},
    "Java": {"color": "ED8B00", "logo": "openjdk"},
    "Ruby": {"color": "CC342D", "logo": "ruby"},
    "Rust": {"color": "000000", "logo": "rust"},
    "Dart": {"color": "0175C2", "logo": "dart"},
    "Kotlin": {"color": "7F52FF", "logo": "kotlin"},
    "Swift": {"color": "F05138", "logo": "swift"},
    "Vue": {"color": "4FC08D", "logo": "vuedotjs"},
    "SCSS": {"color": "CC6699", "logo": "sass"},
    "Makefile": {"color": "427819", "logo": "gnu"},
    "Blade": {"color": "FF2D20", "logo": "laravel"},
}


def make_bar(percentage: float, width: int = 20) -> str:
    """Generate a Unicode progress bar."""
    filled = round(width * percentage / 100)
    return "\u2588" * filled + "\u2591" * (width - filled)


def enrich_languages(languages: list[dict]) -> list[dict]:
    """Add color, logo, and progress bar to each language entry."""
    for lang in languages:
        meta = LANG_META.get(lang["name"], {"color": "555555", "logo": ""})
        lang["color"] = meta["color"]
        lang["logo"] = meta["logo"]
        lang["bar"] = make_bar(lang["percentage"])
    return languages


def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("ERROR: GH_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching data for {USERNAME}...")
    client = GitHubClient(token, USERNAME)

    try:
        context = client.collect_all()
    except Exception as exc:
        print(f"ERROR: Failed to fetch GitHub data: {exc}", file=sys.stderr)
        sys.exit(1)

    context["languages"] = enrich_languages(context["languages"])

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), keep_trailing_newline=True)
    template = env.get_template("README.md.j2")
    readme_content = template.render(**context)

    OUTPUT_FILE.write_text(readme_content, encoding="utf-8")
    print(f"README.md generated successfully ({len(readme_content)} bytes).")


if __name__ == "__main__":
    main()
