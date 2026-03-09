import os
import json
import urllib.request
import datetime
import math
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

current_year = datetime.datetime.now().year

# Query 1: Get User ID and basics
basic_query = f"""
query {{
  user(login: "{USERNAME}") {{
    id
    name
    company
    createdAt
    repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {{
      totalCount
    }}
    issues {{ totalCount }}
    pullRequests {{ totalCount }}
    contributionsCollection {{
      contributionCalendar {{
        totalContributions
        weeks {{
          contributionDays {{
            contributionCount
          }}
        }}
      }}
      restrictedContributionsCount
    }}
  }}
}}
"""
basic_data = run_query(basic_query)['user']
user_id = basic_data['id']
name = basic_data['name'] or USERNAME
company = basic_data['company'] or "Amrita Vishwa Vidyapeetham"
created_at = int(basic_data['createdAt'][:4])
joined_years = current_year - created_at
if joined_years == 0: joined_years = 1

issues = basic_data['issues']['totalCount']
prs = basic_data['pullRequests']['totalCount']
contrib_to = basic_data['repositoriesContributedTo']['totalCount']
current_commits = basic_data['contributionsCollection']['contributionCalendar']['totalContributions'] + \
                  basic_data['contributionsCollection']['restrictedContributionsCount']

# Area chart data
weeks = basic_data['contributionsCollection']['contributionCalendar']['weeks']
# flatten days
days = []
for w in weeks:
    for d in w['contributionDays']:
        days.append(d['contributionCount'])

weekly_contrib = [sum(d['contributionCount'] for d in w['contributionDays']) for w in weeks]
max_contrib = max(weekly_contrib) if weekly_contrib else 1

# Query 2: Repos for Languages and Stars
repo_query = f"""
query {{
  user(login: "{USERNAME}") {{
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {{
      totalCount
      nodes {{
        name
        stargazerCount
        defaultBranchRef {{
          target {{
            ... on Commit {{
              history(author: {{id: "{user_id}"}}) {{
                totalCount
              }}
            }}
          }}
        }}
        languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
          edges {{
            size
            node {{ name color }}
          }}
        }}
      }}
    }}
  }}
}}
"""
repo_data = run_query(repo_query)['user']['repositories']
repos_count = repo_data['totalCount']
stars = sum(node['stargazerCount'] for node in repo_data['nodes'])

langs_by_repo = defaultdict(int)
langs_by_commit = defaultdict(int)
lang_colors = {}

for repo in repo_data['nodes']:
    repo_commits = 0
    try:
        if repo['defaultBranchRef'] and repo['defaultBranchRef']['target']:
            repo_commits = repo['defaultBranchRef']['target']['history']['totalCount']
    except:
        pass
    
    total_size = sum(edge['size'] for edge in repo['languages']['edges'])
    for edge in repo['languages']['edges']:
        name_l = edge['node']['name']
        size = edge['size']
        color = edge['node']['color']
        lang_colors[name_l] = color
        
        langs_by_repo[name_l] += size
        if total_size > 0:
            langs_by_commit[name_l] += (size / total_size) * repo_commits

top_langs_repo = sorted(langs_by_repo.items(), key=lambda x: x[1], reverse=True)[:5]
top_langs_commit = sorted(langs_by_commit.items(), key=lambda x: x[1], reverse=True)[:5]

theme = {
    'bg': '#0d1117',
    'border': '#30363d',
    'title': '#58a6ff',
    'text': '#8b949e',
    'value': '#c9d1d9',
    'icon': '#58a6ff'
}

def generate_donut(data, title):
    total = sum(d[1] for d in data)
    svg = f'''<svg width="300" height="150" viewBox="0 0 300 150" xmlns="http://www.w3.org/2000/svg">
    <style>
        .title {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; fill: {theme['title']}; font-size: 14px; font-weight: 600; }}
        .label {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; fill: {theme['value']}; font-size: 11px; }}
        .bg {{ fill: {theme['bg']}; stroke: {theme['border']}; stroke-width: 1; }}
    </style>
    <rect width="300" height="150" class="bg" rx="6" />
    <text x="25" y="25" class="title">{title}</text>
    '''
    
    cx, cy, radius, stroke_width = 220, 85, 40, 15
    current_angle = 0
    y_offset = 50
    for name_l, val in data:
        pct = (val / total) * 100 if total > 0 else 0
        angle = (val / total) * 360 if total > 0 else 0
        if angle > 359.9: angle = 359.9
        
        if angle > 0:
            start_rad = (current_angle - 90) * math.pi / 180.0
            end_rad = (current_angle + angle - 90) * math.pi / 180.0
            x1 = cx + radius * math.cos(start_rad)
            y1 = cy + radius * math.sin(start_rad)
            x2 = cx + radius * math.cos(end_rad)
            y2 = cy + radius * math.sin(end_rad)
            large_arc_flag = 1 if angle > 180 else 0
            
            path = f"M {x1} {y1} A {radius} {radius} 0 {large_arc_flag} 1 {x2} {y2}"
            svg += f'<path d="{path}" fill="none" stroke="{lang_colors.get(name_l, "#ccc")}" stroke-width="{stroke_width}" />'
            current_angle += angle
        
        svg += f'''
        <rect x="25" y="{y_offset - 8}" width="8" height="8" fill="{lang_colors.get(name_l, '#ccc')}" />
        <text x="40" y="{y_offset}" class="label">{name_l} {pct:.1f}%</text>
        '''
        y_offset += 16
        
    svg += '</svg>'
    return svg

# 1. Stats SVG
svg_stats = f'''<svg width="300" height="150" viewBox="0 0 300 150" xmlns="http://www.w3.org/2000/svg">
  <style>
      .title {{ font-family: -apple-system, sans-serif; fill: {theme['title']}; font-size: 14px; font-weight: 600; }}
      .label {{ font-family: -apple-system, sans-serif; fill: {theme['text']}; font-size: 12px; }}
      .value {{ font-family: -apple-system, sans-serif; fill: {theme['value']}; font-size: 12px; font-weight: 600; }}
      .bg {{ fill: {theme['bg']}; stroke: {theme['border']}; stroke-width: 1; }}
  </style>
  <rect width="300" height="150" class="bg" rx="6" />
  <text x="25" y="25" class="title">Stats</text>
  
  <text x="25" y="55" class="label">⭐ Total Stars: </text><text x="140" y="55" class="value">{stars}</text>
  <text x="25" y="75" class="label">⭕ Commits (Last Year): </text><text x="140" y="75" class="value">{current_commits}</text>
  <text x="25" y="95" class="label">🔄 Total PRs: </text><text x="140" y="95" class="value">{prs}</text>
  <text x="25" y="115" class="label">❗ Total Issues: </text><text x="140" y="115" class="value">{issues}</text>
  <text x="25" y="135" class="label">📦 Contributed to: </text><text x="140" y="135" class="value">{contrib_to}</text>
  
  <!-- GitHub Logo Silhouette -->
  <path d="M220 50 C200 50 185 65 185 85 C185 100 195 112 208 117 C210 117 211 116 211 114 C211 113 211 110 211 106 C201 108 199 101 199 101 C197 97 194 95 194 95 C190 92 194 92 194 92 C198 93 201 96 201 96 C204 102 210 101 213 100 C213 97 214 96 215 95 C206 94 196 90 196 75 C196 71 198 68 200 65 C200 64 198 60 201 55 C201 55 204 54 211 59 C214 58 217 58 220 58 C223 58 226 58 229 59 C236 54 240 55 240 55 C242 60 240 64 240 65 C242 68 244 71 244 75 C244 90 234 94 225 95 C227 96 228 99 228 103 C228 108 228 113 228 114 C228 116 229 117 232 117 C245 113 255 100 255 85 C255 65 240 50 220 50 Z" fill="#24292e" opacity="0.8"/>
</svg>'''

with open("1-stats.svg", "w", encoding="utf-8") as f:
    f.write(svg_stats)

# 2. Languages Repo
with open("2-top-languages.svg", "w", encoding="utf-8") as f:
    f.write(generate_donut(top_langs_repo, "Top Languages by Repo"))

# 3. Languages Commit
with open("3-top-languages-by-commit.svg", "w", encoding="utf-8") as f:
    f.write(generate_donut(top_langs_commit, "Top Languages by Commit"))

# 4. Profile Details SVG
points = []
chart_w, chart_h = 450, 80
x_start = 380
y_start = 180

if len(weekly_contrib) > 0:
    for i, val in enumerate(weekly_contrib):
        x = x_start + (i / max(1, len(weekly_contrib) - 1)) * chart_w
        y = y_start - (val / max(1, max_contrib)) * chart_h
        points.append(f"{x},{y}")
        
    path_d = f"M {x_start},{y_start} " + " ".join([f"L {p}" for p in points]) + f" L {x_start+chart_w},{y_start} Z"
else:
    path_d = ""

svg_profile = f'''<svg width="900" height="250" viewBox="0 0 900 250" xmlns="http://www.w3.org/2000/svg">
  <style>
      .title {{ font-family: -apple-system, sans-serif; fill: {theme['title']}; font-size: 24px; font-weight: 500; }}
      .label {{ font-family: -apple-system, sans-serif; fill: {theme['text']}; font-size: 16px; }}
      .bg {{ fill: {theme['bg']}; stroke: {theme['border']}; stroke-width: 1; }}
      .chart-fill {{ fill: #3fb950; opacity: 0.8; }}
      .axis {{ stroke: #30363d; stroke-width: 1; }}
      .axis-label {{ font-family: -apple-system, sans-serif; fill: {theme['text']}; font-size: 10px; }}
  </style>
  <rect width="900" height="250" class="bg" rx="6" />
  
  <text x="30" y="50" class="title">{USERNAME} ({name})</text>
  
  <text x="50" y="110" class="label">🏢 {current_commits} contributions in last year</text>
  <text x="50" y="145" class="label">📦 {repos_count} Public Repos</text>
  <text x="50" y="180" class="label">🕒 Joined GitHub {joined_years} years ago</text>
  <text x="50" y="215" class="label">🎓 {company}</text>
  
  <text x="650" y="45" class="axis-label" text-anchor="middle">contributions in the last year</text>
  
  <path d="{path_d}" class="chart-fill"/>
  <line x1="{x_start}" y1="{y_start}" x2="{x_start+chart_w}" y2="{y_start}" class="axis" />
  
  <line x1="{x_start+chart_w}" y1="{y_start}" x2="{x_start+chart_w}" y2="{y_start-chart_h}" class="axis" />
  <text x="{x_start+chart_w+10}" y="{y_start}" class="axis-label">0</text>
  <text x="{x_start+chart_w+10}" y="{y_start - chart_h/2}" class="axis-label">{max_contrib//2}</text>
  <text x="{x_start+chart_w+10}" y="{y_start - chart_h}" class="axis-label">{max_contrib}</text>
</svg>'''

with open("0-profile-details.svg", "w", encoding="utf-8") as f:
    f.write(svg_profile)

# 5. About Terminal SVG
advanced_svg = """<svg width="600" height="230" viewBox="0 0 600 230" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .prompt { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size: 14px; fill: #3fb950; }
      .cmd { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size: 14px; fill: #58a6ff; }
      .file { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size: 14px; fill: #d2a8ff; }
      .output { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size: 14px; fill: #8b949e; }
      .bold { font-weight: 600; fill: #e6edf3; font-size: 14px; }
      .bg { fill: #0d1117; }
      .border { fill: none; stroke: #30363d; stroke-width: 1; }

      .cursor { fill: #c9d1d9; font-family: ui-monospace, SFMono-Regular, monospace; font-size: 14px; animation: blink 1s step-end infinite; }
      @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

      .type-mask { fill: #0d1117; animation: slide 1.5s steps(40, end) forwards; }
      .type-mask-1 { animation-delay: 0.5s; }
      .type-mask-2 { animation-delay: 1.5s; }
      .type-mask-3 { animation-delay: 2.0s; }
      .type-mask-4 { animation-delay: 3.0s; }
      .type-mask-5 { animation-delay: 3.2s; }
      .type-mask-6 { animation-delay: 4.5s; }
      .type-mask-7 { animation-delay: 5.5s; }
      
      @keyframes slide { to { transform: translateX(550px); } }
      
      .hide { opacity: 0; animation: fadein 0.1s forwards; }
      .delay-1 { animation-delay: 0s; }
      .delay-2 { animation-delay: 1.5s; }
      .delay-3 { animation-delay: 2.0s; }
      .delay-4 { animation-delay: 3.0s; }
      .delay-6 { animation-delay: 4.5s; }
      .delay-7 { animation-delay: 5.5s; }
      .delay-8 { animation-delay: 7.0s; }
      @keyframes fadein { to { opacity: 1; } }
    </style>
  </defs>

  <rect width="600" height="230" class="bg" rx="6" />
  <rect width="600" height="230" class="border" rx="6" />

  <circle cx="20" cy="16" r="5" fill="#ff5f57" />
  <circle cx="38" cy="16" r="5" fill="#febc2e" />
  <circle cx="56" cy="16" r="5" fill="#28c840" />

  <!-- Block 1 -->
  <g class="hide delay-1">
    <text y="50" x="20">
      <tspan class="prompt">$</tspan>
      <tspan class="cmd"> cat</tspan>
      <tspan class="file"> education.txt</tspan>
    </text>
    <rect x="35" y="35" width="550" height="20" class="type-mask type-mask-1" />
  </g>
  
  <g class="hide delay-2">
    <text y="70" x="20" class="output">&gt; CS Undergrad @ <tspan class="bold">Amrita Vishwa Vidyapeetham</tspan>, Coimbatore</text>
  </g>

  <!-- Block 2 -->
  <g class="hide delay-3">
    <text y="105" x="20">
      <tspan class="prompt">$</tspan>
      <tspan class="cmd"> cat</tspan>
      <tspan class="file"> experience.txt</tspan>
    </text>
    <rect x="35" y="90" width="550" height="20" class="type-mask type-mask-3" />
  </g>
  
  <g class="hide delay-4">
    <text y="125" x="20" class="output">&gt; <tspan class="bold">Website Development Head</tspan> @ Init Club,</text>
    <text y="145" x="20" class="output">&gt; Previously worked with <tspan class="bold">InCTF</tspan> &amp; <tspan class="bold">Station-S</tspan></text>
  </g>

  <!-- Block 3 -->
  <g class="hide delay-6">
    <text y="180" x="20">
      <tspan class="prompt">$</tspan>
      <tspan class="cmd"> cat</tspan>
      <tspan class="file"> interests.txt</tspan>
    </text>
    <rect x="35" y="165" width="550" height="20" class="type-mask type-mask-6" />
  </g>

  <g class="hide delay-7">
    <text y="200" x="20" class="output">&gt; <tspan class="bold">Full-Stack Engineering</tspan> &amp; <tspan class="bold">AI/ML</tspan></text>
  </g>

  <g class="hide delay-8">
     <text y="225" x="20" class="prompt">$ <tspan class="cursor">█</tspan></text>
  </g>
</svg>"""

with open("about.svg", "w", encoding="utf-8") as f:
    f.write(advanced_svg)
