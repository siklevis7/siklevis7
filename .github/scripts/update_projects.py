"""Rebuild the Projects list in README.md from the account's repositories.

With a GH_PAT secret (fine-grained token, "Metadata: read" on all repositories)
private repositories are listed too. Without it, only public repositories are
refreshed and private entries already in the list are kept as they are.
"""
import json
import os
import re
import urllib.request

USER = "siklevis7"
README = "README.md"
START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"

# Live links used when a repository has no website set in its About section.
LIVE = {
    "aircrafty": "https://aircrafty.siklevis7.workers.dev",
    "atpl": "https://atpl-beta.vercel.app",
}

TOKEN = os.environ.get("GH_PAT", "").strip()


def get(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as resp:
        return json.load(resp)


def fetch_repos():
    if TOKEN:
        base = "https://api.github.com/user/repos?affiliation=owner&visibility=all"
    else:
        base = f"https://api.github.com/users/{USER}/repos?type=owner"
    repos, page = [], 1
    while True:
        batch = get(f"{base}&sort=pushed&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    return [
        r for r in repos
        if not r["fork"] and not r["archived"] and r["name"].lower() != USER.lower()
    ]


def entry(repo):
    parts = [f"- [**{repo['name']}**]({repo['html_url']})"]
    if repo.get("description"):
        parts.append(repo["description"].strip())
    if repo.get("language"):
        parts.append(f"`{repo['language']}`")
    live = (repo.get("homepage") or "").strip() or LIVE.get(repo["name"])
    if live:
        parts.append(f"[Live]({live})")
    return " · ".join(parts)


def main():
    with open(README, encoding="utf-8") as f:
        text = f.read()
    head, rest = text.split(START, 1)
    current, tail = rest.split(END, 1)

    repos = fetch_repos()
    lines = [entry(r) for r in repos]

    if not TOKEN:
        listed = {r["name"] for r in repos}
        for line in current.strip().splitlines():
            m = re.match(r"- \[\*\*(.+?)\*\*\]", line)
            if m and m.group(1) not in listed:
                lines.append(line)

    new_text = f"{head}{START}\n" + "\n".join(lines) + f"\n{END}{tail}"
    if new_text != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new_text)
        print("Projects list updated.")
    else:
        print("No changes.")


if __name__ == "__main__":
    main()
