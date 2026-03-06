import os
import json
import urllib.request
import re

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
        "Authorization": f"Bearer {TOKEN}",
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

stats_md = f"""
<table align="center" style="font-size: 16px; width: 60%%">
  <tr align="left">
    <td width="70%%">🏆 &nbsp;<b>Total Stars Earned</b></td>
    <td width="30%%" align="right"><b>{stars}</b></td>
  </tr>
  <tr align="left">
    <td>📦 &nbsp;<b>Public Repositories</b></td>
    <td align="right"><b>{repos}</b></td>
  </tr>
  <tr align="left">
    <td>🐛 &nbsp;<b>Issues Opened</b></td>
    <td align="right"><b>{issues}</b></td>
  </tr>
  <tr align="left">
    <td>🔄 &nbsp;<b>Pull Requests</b></td>
    <td align="right"><b>{prs}</b></td>
  </tr>
  <tr align="left">
    <td>💻 &nbsp;<b>Contributions (Last Year)</b></td>
    <td align="right"><b>{commits}</b></td>
  </tr>
</table>
"""

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

readme = re.sub(
    r'<!--STATS_START-->.*<!--STATS_END-->',
    f'<!--STATS_START-->\n{stats_md.strip()}\n  <!--STATS_END-->',
    readme,
    flags=re.DOTALL
)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme)
