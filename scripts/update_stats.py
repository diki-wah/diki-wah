#!/usr/bin/env python3
"""Regenerate assets/stats.svg from live GitHub numbers.

Runs in GitHub Actions with GITHUB_TOKEN, so it needs no extra secrets.
Only rewrites the file when a value actually changed, which keeps the
commit history clean.
"""
import json
import os
import sys
import urllib.error
import urllib.request

USER = os.environ.get("GH_USER", "diki-wah")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "stats.svg")

AURORA_A = "#5ef2c0"
AURORA_B = "#6ad0ff"
AURORA_C = "#b48cff"
ICE_DIM = "#a8cfe4"
LIME = "#a6ff3d"


def gql(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch():
    repos = followers = 0
    commits = contribs = 0
    req = urllib.request.Request(
        f"https://api.github.com/users/{USER}",
        headers={"Authorization": f"bearer {TOKEN}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        u = json.load(r)
    repos, followers = u.get("public_repos", 0), u.get("followers", 0)

    q = """
    query($login:String!){
      user(login:$login){
        contributionsCollection{
          totalCommitContributions
          contributionCalendar{ totalContributions }
        }
      }
    }"""
    try:
        d = gql(q, {"login": USER})
        cc = d["data"]["user"]["contributionsCollection"]
        commits = cc["totalCommitContributions"]
        contribs = cc["contributionCalendar"]["totalContributions"]
    except Exception as e:  # keep going with zeros rather than break the workflow
        print(f"warn: contributions query failed: {e}", file=sys.stderr)
    return repos, commits, contribs, followers


def card(x, label, value, accent, dur, delay):
    return f"""<g transform="translate({x},20)">
  <rect width="250" height="112" rx="14" fill="#0a1622" stroke="{accent}" stroke-opacity="0.45"/>
  <rect width="250" height="112" rx="14" fill="{accent}" opacity="0.05">
    <animate attributeName="opacity" values="0.02;0.10;0.02" dur="{dur}s" begin="{delay}s" repeatCount="indefinite"/>
  </rect>
  <text x="24" y="52" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="40"
        font-weight="700" fill="{accent}">{value}</text>
  <text x="24" y="84" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="14"
        fill="{ICE_DIM}" letter-spacing="2">{label}</text>
</g>"""


def render(repos, commits, contribs, followers):
    cards = "".join(
        [
            card(0, "REPOSITORIES", repos, AURORA_A, 6, 0),
            card(270, "COMMITS", commits, AURORA_B, 7, 0.8),
            card(540, "CONTRIBUTIONS", contribs, LIME, 8, 1.6),
            card(810, "FOLLOWERS", followers, AURORA_C, 9, 2.4),
        ]
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1060 152" width="1060" height="152" role="img" aria-label="Profile statistics">
<defs>
  <linearGradient id="sbg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#05080f"/>
    <stop offset="100%" stop-color="#0a1622"/>
  </linearGradient>
</defs>
<rect width="1060" height="152" rx="18" fill="url(#sbg)"/>
{cards}
</svg>
"""


def main():
    if not TOKEN:
        sys.exit("GITHUB_TOKEN is required")
    repos, commits, contribs, followers = fetch()
    svg = render(repos, commits, contribs, followers)
    old = open(OUT).read() if os.path.exists(OUT) else ""
    if old == svg:
        print("stats unchanged")
        return
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"stats updated: repos={repos} commits={commits} contribs={contribs} followers={followers}")


if __name__ == "__main__":
    main()
