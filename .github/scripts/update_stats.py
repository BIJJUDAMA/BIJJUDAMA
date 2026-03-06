import os
import json
import urllib.request
import datetime
import re
from collections import defaultdict

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
      nodes {{ 
        stargazerCount 
        languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
          edges {{
            size
            node {{
              name
              color
            }}
          }}
        }}
      }}
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

# Calculate top languages
langs = defaultdict(int)
lang_colors = {}
total_size = 0

for repo in data['repositories']['nodes']:
    for edge in repo['languages']['edges']:
        name = edge['node']['name']
        size = edge['size']
        color = edge['node']['color']
        
        langs[name] += size
        lang_colors[name] = color
        total_size += size

# Sort and get top 5 languages
sorted_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:5]

# Build the custom progress bar HTML
progress_bar = '<div style="display: flex; width: 100%; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 15px; margin-bottom: 15px;">\n'
lang_list = '<div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">\n'

# Only do language math if there's actually code
if total_size > 0:
    for name, size in sorted_langs:
        pct = (size / total_size) * 100
        # Ignore things under 1% to keep it clean
        if pct < 1: continue 
        
        color = lang_colors.get(name) or "#cccccc"
        progress_bar += f'  <div style="width: {pct}%; background-color: {color};" title="{name} {pct:.1f}%"></div>\n'
        lang_list += f'  <span style="font-size: 13px;"><b><span style="color: {color};">●</span> {name}</b> <span style="color: #888;">{pct:.1f}%</span></span>\n'

progress_bar += '</div>'
lang_list += '</div>'

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

  <br/>
  {progress_bar}
  {lang_list}
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
