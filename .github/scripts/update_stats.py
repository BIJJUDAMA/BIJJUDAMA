import os
import json
import urllib.request

TOKEN = os.environ.get("GH_TOKEN")
USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER") or "BIJJUDAMA"

# GraphQL query for user stats
query = """
query {
  user(login: "%s") {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
      }
    }
    issues {
      totalCount
    }
    pullRequests {
      totalCount
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
      }
      restrictedContributionsCount
    }
  }
}
""" % USERNAME

req = urllib.request.Request(
    'https://api.github.com/graphql',
    data=json.dumps({"query": query}).encode('utf-8'),
    headers={
        "Authorization": f"Bearer {TOKEN}" if TOKEN else "",
        "Content-Type": "application/json"
    }
)

with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode('utf-8'))['data']['user']

stars = sum(node['stargazerCount'] for node in data['repositories']['nodes'])
repos = data['repositories']['totalCount']
issues = data['issues']['totalCount']
prs = data['pullRequests']['totalCount']
commits = data['contributionsCollection']['contributionCalendar']['totalContributions'] + data['contributionsCollection']['restrictedContributionsCount']

svg = f"""<svg width="450" height="230" viewBox="0 0 450 230" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&amp;display=swap');
      .bg {{ fill: #1a1b26; rx: 8px; stroke: #292e42; stroke-width: 1px; }}
      .title {{ font-family: 'Fira Code', monospace; fill: #70a5fd; font-size: 16px; font-weight: 600; letter-spacing: 0.5px; }}
      .label {{ font-family: 'Fira Code', monospace; fill: #a9b1d6; font-size: 14px; font-weight: 400; }}
      .value {{ font-family: 'Fira Code', monospace; fill: #bb9af7; font-size: 15px; font-weight: 600; text-anchor: end; }}
      .line {{ stroke: #292e42; stroke-width: 1.5; stroke-linecap: round; }}
      .dot {{ fill: #38bdae; }}
    </style>
  </defs>
  <rect width="448" height="228" x="1" y="1" class="bg" />
  
  <text x="35" y="42" class="title">Developer Metrics</text>
  <line x1="35" y1="58" x2="415" y2="58" class="line" />
  
  <circle cx="35" cy="88" r="4" class="dot"/>
  <text x="50" y="93" class="label">Total Stars Earned</text>
  <text x="415" y="93" class="value">{stars}</text>
  
  <circle cx="35" cy="118" r="4" class="dot"/>
  <text x="50" y="123" class="label">Public Repositories</text>
  <text x="415" y="123" class="value">{repos}</text>
  
  <circle cx="35" cy="148" r="4" class="dot"/>
  <text x="50" y="153" class="label">Issues Opened</text>
  <text x="415" y="153" class="value">{issues}</text>
  
  <circle cx="35" cy="178" r="4" class="dot"/>
  <text x="50" y="183" class="label">Pull Requests</text>
  <text x="415" y="183" class="value">{prs}</text>
  
  <circle cx="35" cy="208" r="4" class="dot"/>
  <text x="50" y="213" class="label">Contributions (1 Yr)</text>
  <text x="415" y="213" class="value">{commits}</text>
</svg>"""

with open("github_metrics.svg", "w", encoding="utf-8") as f:
    f.write(svg)
