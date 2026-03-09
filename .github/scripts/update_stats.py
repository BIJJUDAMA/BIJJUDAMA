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

icons = {
    'star': '<path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path>',
    'commit': '<path fill-rule="evenodd" d="M10.5 7.75a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zm1.43.75a4.002 4.002 0 01-7.86 0H.75a.75.75 0 110-1.5h3.32a4.001 4.001 0 017.86 0h3.32a.75.75 0 110 1.5h-3.32z"></path>',
    'pr': '<path fill-rule="evenodd" d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z"></path>',
    'issue': '<path d="M8 9.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z"></path><path fill-rule="evenodd" d="M8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z"></path>',
    'repo': '<path fill-rule="evenodd" d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z"></path>',
    'institution': '<path d="M2.5 1.75A.75.75 0 013.25 1h9.5a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75H3.25a.75.75 0 01-.75-.75V1.75zM3.5 2v11.5h9V2h-9zM5 4h5v1H5V4zm0 2h5v1H5V6zm0 2h5v1H5V8zm0 2h5v1H5v-1z"></path>',
    'briefcase': '<path fill-rule="evenodd" d="M3.75 3A1.75 1.75 0 015.5 1.25h5A1.75 1.75 0 0112.25 3v1h1A1.75 1.75 0 0115 5.75v7.5A1.75 1.75 0 0113.25 15H2.75A1.75 1.75 0 011 13.25v-7.5A1.75 1.75 0 012.75 4h1V3zm1.75-.25a.25.25 0 00-.25.25v1h5V3a.25.25 0 00-.25-.25h-5zM2.5 5.75v7.5c0 .138.112.25.25.25h10.5a.25.25 0 00.25-.25v-7.5a.25.25 0 00-.25-.25H2.75a.25.25 0 00-.25.25z"></path>',
    'heart': '<path fill-rule="evenodd" d="M11.204 2.27c-1.396-1.03-3.056-.51-3.954.59L7 3.09l-.25-.23c-.898-1.1-2.558-1.62-3.954-.59-1.428 1.05-1.921 2.9-.844 4.5 1.144 1.7 3.313 3.65 4.808 5.16l.24.25.24-.25c1.495-1.51 3.664-3.46 4.808-5.16 1.077-1.6.584-3.45-.844-4.5zM7.172 13.268C5.636 11.704 3.328 9.61 2.056 7.72c-1.253-1.85-.698-4.04 1.15-5.39.99-.73 2.18-.5 2.9.22l.53.5.53-.5c.72-.72 1.91-.95 2.9-.22 1.848 1.35 2.403 3.54 1.15 5.39-1.272 1.89-3.58 3.984-5.116 5.548A1 1 0 017.172 13.268z"></path>',
    'clock': '<path fill-rule="evenodd" d="M1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0zM8 0a8 8 0 100 16A8 8 0 008 0zm.5 4.75a.75.75 0 00-1.5 0v3.5a.75.75 0 00.471.696l2.5 1a.75.75 0 00.557-1.392L8.5 7.742V4.75z"></path>',
    'activity': '<path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm11.646-2.854a.5.5 0 00-.707 0L8 8.086 5.854 5.94a.5.5 0 00-.708 0l-2 2a.5.5 0 10.708.708L5.5 6.992l2.146 2.147a.5.5 0 00.708 0l3.5-3.5a.5.5 0 000-.707z"></path>'
}


def generate_donut(data, title):
    total = sum(d[1] for d in data)
    svg = f'''<svg width="300" height="150" viewBox="0 0 300 150" xmlns="http://www.w3.org/2000/svg">
    <style>
        .title {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; fill: {theme['title']}; font-size: 14px; font-weight: 600; }}
        .label {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; fill: {theme['value']}; font-size: 12px; }}
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
      .label {{ font-family: -apple-system, sans-serif; fill: {theme['text']}; font-size: 13px; }}
      .value {{ font-family: -apple-system, sans-serif; fill: {theme['value']}; font-size: 13px; font-weight: 600; }}
      .bg {{ fill: {theme['bg']}; stroke: {theme['border']}; stroke-width: 1; }}
      .icon {{ fill: {theme['icon']}; }}
  </style>
  <rect width="300" height="150" class="bg" rx="6" />
  <text x="25" y="25" class="title">Stats</text>
  
  <g transform="translate(25, 45)"><g class="icon">{icons['star']}</g></g>
  <text x="50" y="56" class="label">Total Stars: </text><text x="175" y="56" class="value">{stars}</text>

  <g transform="translate(25, 65)"><g class="icon">{icons['commit']}</g></g>
  <text x="50" y="76" class="label">Commits (Last Year): </text><text x="175" y="76" class="value">{current_commits}</text>

  <g transform="translate(25, 85)"><g class="icon">{icons['pr']}</g></g>
  <text x="50" y="96" class="label">Total PRs: </text><text x="175" y="96" class="value">{prs}</text>

  <g transform="translate(25, 105)"><g class="icon">{icons['issue']}</g></g>
  <text x="50" y="116" class="label">Total Issues: </text><text x="175" y="116" class="value">{issues}</text>

  <g transform="translate(25, 125)"><g class="icon">{icons['repo']}</g></g>
  <text x="50" y="136" class="label">Contributed to: </text><text x="175" y="136" class="value">{contrib_to}</text>
  
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
      .axis-label {{ font-family: -apple-system, sans-serif; fill: {theme['text']}; font-size: 14px; font-weight: 500; }}
      .icon {{ fill: {theme['text']}; }}
  </style>
  <rect width="900" height="250" class="bg" rx="6" />
  
  <text x="30" y="50" class="title">{USERNAME} ({name})</text>
  
  <g transform="translate(30, 95)"><g class="icon">{icons['activity']}</g></g>
  <text x="55" y="108" class="label">{current_commits} contributions in the last year</text>

  <g transform="translate(30, 130)"><g class="icon">{icons['repo']}</g></g>
  <text x="55" y="143" class="label">{repos_count} Public Repos</text>

  <g transform="translate(30, 165)"><g class="icon">{icons['clock']}</g></g>
  <text x="55" y="178" class="label">Joined GitHub {joined_years} years ago</text>

  <g transform="translate(30, 200)"><g class="icon">{icons['institution']}</g></g>
  <text x="55" y="213" class="label">{company}</text>
  
  <text x="605" y="55" class="axis-label" text-anchor="middle">Contributions in the Last Year</text>
  
  <path d="{path_d}" class="chart-fill"/>
  <line x1="{x_start}" y1="{y_start}" x2="{x_start+chart_w}" y2="{y_start}" class="axis" />
  
  <line x1="{x_start+chart_w}" y1="{y_start}" x2="{x_start+chart_w}" y2="{y_start-chart_h}" class="axis" />
  <text x="{x_start+chart_w+10}" y="{y_start}" class="axis-label" fill="{theme['text']}">0</text>
  <text x="{x_start+chart_w+10}" y="{y_start - chart_h/2}" class="axis-label" fill="{theme['text']}">{max_contrib//2}</text>
  <text x="{x_start+chart_w+10}" y="{y_start - chart_h}" class="axis-label" fill="{theme['text']}">{max_contrib}</text>
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
