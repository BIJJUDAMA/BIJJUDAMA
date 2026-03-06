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

# 1. Generate overview.svg (Glassmorphism style)
svg = f"""<svg width="600" height="250" viewBox="0 0 600 250" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&amp;display=swap');
      .box {{ fill: rgba(26, 27, 38, 0.4); rx: 12px; stroke-width: 1.5px; }}
      .box-blue {{ stroke: rgba(112, 165, 253, 0.6); }}
      .box-purple {{ stroke: rgba(187, 154, 247, 0.6); }}
      .box-green {{ stroke: rgba(56, 189, 174, 0.6); }}
      .box-cyan {{ stroke: rgba(169, 177, 214, 0.6); }}
      
      .title {{ font-family: 'Fira Code', monospace; font-size: 13px; font-weight: 500; text-anchor: middle; }}
      .title-blue {{ fill: #70a5fd; }}
      .title-purple {{ fill: #bb9af7; }}
      .title-green {{ fill: #38bdae; }}
      .title-cyan {{ fill: #a9b1d6; }}
      
      .value {{ font-family: 'Fira Code', monospace; fill: #ffffff; font-size: 26px; font-weight: 600; text-anchor: middle; }}
      
      @media (prefers-color-scheme: light) {{
        .value {{ fill: #1a1b26; }}
        .box {{ fill: rgba(255, 255, 255, 0.6); }}
      }}
    </style>
  </defs>

  <!-- Row 1 -->
  <rect x="50" y="20" width="240" height="60" class="box box-blue" />
  <text x="170" y="42" class="title title-blue">TOTAL STARS EARNED</text>
  <text x="170" y="68" class="value">{stars}</text>

  <rect x="310" y="20" width="240" height="60" class="box box-purple" />
  <text x="430" y="42" class="title title-purple">PUBLIC REPOSITORIES</text>
  <text x="430" y="68" class="value">{repos}</text>

  <!-- Row 2 -->
  <rect x="50" y="95" width="240" height="60" class="box box-green" />
  <text x="170" y="117" class="title title-green">ISSUES OPENED</text>
  <text x="170" y="143" class="value">{issues}</text>

  <rect x="310" y="95" width="240" height="60" class="box box-cyan" />
  <text x="430" y="117" class="title title-cyan">PULL REQUESTS</text>
  <text x="430" y="143" class="value">{prs}</text>

  <!-- Row 3 -->
  <rect x="180" y="170" width="240" height="60" class="box box-blue" />
  <text x="300" y="192" class="title title-blue">ALL-TIME CONTRIBUTIONS</text>
  <text x="300" y="218" class="value">{total_commits}</text>
</svg>"""

with open("overview.svg", "w", encoding="utf-8") as f:
    f.write(svg)

# 2. Generate Top Languages hybrid badges
import urllib.parse
lang_list = '<div align="center">\n'

if total_size > 0:
    for name, size in sorted_langs:
        pct = (size / total_size) * 100
        if pct < 1: continue 
        
        color = lang_colors.get(name) or "#cccccc"
        color_clean = color.replace('#', '')
        
        filled = max(1, int(pct / 10))
        empty = 10 - filled
        bar = '█' * filled + '░' * empty
        
        # Shields.io needs - and _ to be duplicated
        raw_name = name.replace('-', '--').replace('_', '__')
        name_enc = urllib.parse.quote(raw_name)
        
        raw_msg = f"{bar} {pct:.1f}%".replace('-', '--').replace('_', '__')
        msg_enc = urllib.parse.quote(raw_msg)
        
        logo = urllib.parse.quote(name.lower())
        
        url = f"https://img.shields.io/badge/{name_enc}-{msg_enc}-{color_clean}?style=for-the-badge&logo={logo}&logoColor=white"
        lang_list += f'  <img src="{url}" alt="{name}" style="margin-bottom: 8px;"/><br/>\n'

lang_list += '</div>\n'

plain_text_md = f"""
<div align="center">
  <br/>
  <h3 style="color: #70a5fd; margin-bottom: 5px;">GitHub Overview</h3>
  <hr style="width: 40%; border: 1px solid #292e42; margin-bottom: 25px;">
  
  <img src="overview.svg" alt="GitHub Overview" style="max-width: 100%; height: auto;" />

  <br/><br/><br/>
  <h3 style="color: #bb9af7; margin-bottom: 5px;">Top Languages</h3>
  <hr style="width: 40%; border: 1px solid #292e42; margin-bottom: 25px;">
  
{lang_list}
  <br/>
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
