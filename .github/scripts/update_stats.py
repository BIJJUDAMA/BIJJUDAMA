import os
import json
import urllib.request
import datetime
import re

TOKEN = os.environ.get("GH_TOKEN")
USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER") or "BIJJUDAMA"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}" if TOKEN else "",
    "Content-Type": "application/json"
}

def run_query(query):
    req = urllib.request.Request(
        'https://api.github.com/graphql',
        data=json.dumps({"query": query}).encode('utf-8'),
        headers=HEADERS
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))['data']

# Fetch user's creation date to get all-time contributions
creation_query = f"""
query {{
  user(login: "{USERNAME}") {{
    createdAt
  }}
}}
"""
created_at_str = run_query(creation_query)['user']['createdAt']
created_year = int(created_at_str[:4])
current_year = datetime.datetime.now().year

# Constructbatched query for all years
years_query = ""
for year in range(created_year, current_year + 1):
    years_query += f"""
    year__{year}: contributionsCollection(from: "{year}-01-01T00:00:00Z", to: "{year}-12-31T23:59:59Z") {{
      contributionCalendar {{ totalContributions }}
      restrictedContributionsCount
    }}
    """

main_query = f"""
query {{
  user(login: "{USERNAME}") {{
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {{
      totalCount
      nodes {{ stargazerCount }}
    }}
    issues {{ totalCount }}
    pullRequests {{ totalCount }}
    {years_query}
  }}
}}
"""

data = run_query(main_query)['user']

stars = sum(node['stargazerCount'] for node in data['repositories']['nodes'])
repos = data['repositories']['totalCount']
issues = data['issues']['totalCount']
prs = data['pullRequests']['totalCount']

total_commits = 0
for year in range(created_year, current_year + 1):
    col = data[f'year__{year}']
    total_commits += col['contributionCalendar']['totalContributions'] + col['restrictedContributionsCount']

plain_text_md = f"""
<div align="center">
  <h3>
    <span style="color: #70a5fd">Total Stars Earned:</span> <b>{stars}</b>
    &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
    <span style="color: #bb9af7">Public Repositories:</span> <b>{repos}</b>
    <br/><br/>
    <span style="color: #38bdae">Issues Opened:</span> <b>{issues}</b>
    &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
    <span style="color: #a9b1d6">Pull Requests:</span> <b>{prs}</b>
    &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
    <span style="color: #70a5fd">Total Contributions:</span> <b>{total_commits}</b>
  </h3>
</div>
"""

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

readme = re.sub(
    r'<!--STATS_START-->.*<!--STATS_END-->',
    f'<!--STATS_START-->\n{plain_text_md.strip()}\n  <!--STATS_END-->',
    readme,
    flags=re.DOTALL
)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme)
