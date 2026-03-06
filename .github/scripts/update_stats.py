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

# 1. Generate overview.svg (Glassmorphism style, White/Black text, Sharp)
svg_overview = f"""<svg width="600" height="250" viewBox="0 0 600 250" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&amp;display=swap');
      .box {{ fill: rgba(26, 27, 38, 0.4); stroke-width: 1.5px; stroke: rgba(255, 255, 255, 0.2); }}
      .text {{ font-family: 'Fira Code', monospace; fill: #ffffff; text-anchor: middle; }}
      .title {{ font-size: 13px; font-weight: 500; text-transform: uppercase; }}
      .value {{ font-size: 26px; font-weight: 600; }}
      
      @media (prefers-color-scheme: light) {{
        .text {{ fill: #000000; }}
        .box {{ fill: rgba(0, 0, 0, 0.05); stroke: rgba(0, 0, 0, 0.2); }}
      }}
    </style>
  </defs>

  <!-- Row 1 -->
  <rect x="0" y="20" width="280" height="60" class="box" />
  <text x="140" y="42" class="text title">TOTAL STARS EARNED</text>
  <text x="140" y="68" class="text value">{stars}</text>

  <rect x="320" y="20" width="280" height="60" class="box" />
  <text x="460" y="42" class="text title">PUBLIC REPOSITORIES</text>
  <text x="460" y="68" class="text value">{repos}</text>

  <!-- Row 2 -->
  <rect x="0" y="95" width="280" height="60" class="box" />
  <text x="140" y="117" class="text title">ISSUES OPENED</text>
  <text x="140" y="143" class="text value">{issues}</text>

  <rect x="320" y="95" width="280" height="60" class="box" />
  <text x="460" y="117" class="text title">PULL REQUESTS</text>
  <text x="460" y="143" class="text value">{prs}</text>

  <!-- Row 3 -->
  <rect x="160" y="170" width="280" height="60" class="box" />
  <text x="300" y="192" class="text title">ALL-TIME CONTRIBUTIONS</text>
  <text x="300" y="218" class="text value">{total_commits}</text>
</svg>"""

with open("overview.svg", "w", encoding="utf-8") as f:
    f.write(svg_overview)

# 2. Generate languages.svg (Left badges, right bars)
num_langs = min(5, sum(1 for n, s in sorted_langs if (s/total_size)*100 >= 1)) if total_size > 0 else 0
svg_height = max(40, num_langs * 40)

svg_langs = f"""<svg width="600" height="{svg_height}" viewBox="0 0 600 {svg_height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&amp;display=swap');
      .lang-text {{ font-family: 'Fira Code', monospace; font-size: 13px; font-weight: 500; }}
      .badge-text {{ fill: #000000; text-anchor: middle; font-weight: 600; text-transform: uppercase; }}
      .pct-text {{ fill: #ffffff; text-anchor: end; }}
      
      @media (prefers-color-scheme: light) {{
        .pct-text {{ fill: #000000; }}
      }}
    </style>
  </defs>
"""

y_offset = 0
if total_size > 0:
    for name, size in sorted_langs:
        pct = (size / total_size) * 100
        if pct < 1: continue 
        
        color = lang_colors.get(name, "#cccccc")
        
        filled = max(1, int(pct / 5))
        empty = 20 - filled
        bar = '█' * filled + '░' * empty
        
        svg_langs += f"""
  <!-- Badge (Left Aligned Sharp) -->
  <rect x="0" y="{y_offset + 5}" width="110" height="24" fill="{color}" />
  <text x="55" y="{y_offset + 22}" class="lang-text badge-text">{name}</text>
  
  <!-- Unicode Bar (After Badge) -->
  <text x="130" y="{y_offset + 22}" class="lang-text" fill="{color}" text-anchor="start">{bar}</text>
  
  <!-- Percentage Text (Right Aligned) -->
  <text x="590" y="{y_offset + 22}" class="lang-text pct-text">{pct:.1f}%</text>
"""
        y_offset += 40

svg_langs += "</svg>"

with open("languages.svg", "w", encoding="utf-8") as f:
    f.write(svg_langs)

plain_text_md = f"""
<div align="center">
  <br/>
  <img src="overview.svg" alt="GitHub Overview" style="max-width: 100%; height: auto;" />
</div>

<div align="left">
  <br/><br/>
  <h3 style="color: #bb9af7; margin-bottom: 5px;">Top Languages</h3>
</div>

<div align="center">
  <img src="languages.svg" alt="Top Languages" style="max-width: 100%; height: auto;" />
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
