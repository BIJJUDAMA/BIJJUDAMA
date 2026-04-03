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

# Fetch Lifetime Contributions & Commits (Iterate Years)
lifetime_commits = 0
lifetime_contributions = 0
lifetime_weeks = []

for year in range(created_at, current_year + 1):
    start_date = f"{year}-01-01T00:00:00Z"
    end_date = f"{year}-12-31T23:59:59Z"
    
    yearly_query = f"""
    query {{
      user(login: "{USERNAME}") {{
        contributionsCollection(from: "{start_date}", to: "{end_date}") {{
          totalCommitContributions
          restrictedContributionsCount
          contributionCalendar {{
            totalContributions
            weeks {{
              contributionDays {{
                contributionCount
              }}
            }}
          }}
        }}
      }}
    }}
    """
    try:
        coll = run_query(yearly_query)['user']['contributionsCollection']
        
        # Add public commits
        lifetime_commits += coll['totalCommitContributions']
        # Add private/restricted commits (if token allows)
        lifetime_commits += coll.get('restrictedContributionsCount', 0)
        
        lifetime_contributions += coll['contributionCalendar']['totalContributions']
        lifetime_weeks.extend(coll['contributionCalendar']['weeks'])
    except Exception as e:
        print(f"Error fetching data for year {year}: {e}")

current_commits = lifetime_commits
current_contributions = lifetime_contributions
weekly_contrib = [sum(d['contributionCount'] for d in w['contributionDays']) for w in lifetime_weeks]
max_contrib = max(weekly_contrib) if weekly_contrib else 1

# Query 2: Repos for Languages and Stars (With Pagination)
all_repo_nodes = []
has_next_page = True
cursor = None
repos_count = 0

while has_next_page:
    cursor_str = f', after: "{cursor}"' if cursor else ""
    repo_query = f"""
    query {{
      user(login: "{USERNAME}") {{
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false{cursor_str}) {{
          pageInfo {{
            hasNextPage
            endCursor
          }}
          totalCount
          nodes {{
            name
            isPrivate
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
    try:
        repo_data_paged = run_query(repo_query)['user']['repositories']
        all_repo_nodes.extend(repo_data_paged['nodes'])
        repos_count = repo_data_paged['totalCount']
        has_next_page = repo_data_paged['pageInfo']['hasNextPage']
        cursor = repo_data_paged['pageInfo']['endCursor']
    except Exception as e:
        print(f"Error fetching repositories: {e}")
        has_next_page = False

# Process Repo Data (Aggregating Totals)
public_repos_count = 0
stars = 0
langs_by_repo = defaultdict(int)
langs_by_commit = defaultdict(int)
lang_colors = {}

for repo in all_repo_nodes:
    if not repo['isPrivate']:
        public_repos_count += 1
    
    stars += repo['stargazerCount']
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
    'shadow': '#000000',
    'bg': '#0a0a0a',
    'surface': '#141414',
    'accent': '#ff0000',
    'border': '#333333',
    'muted': '#aaaaaa',
    'white': '#fafafa'
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
    'activity': '<path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm11.646-2.854a.5.5 0 00-.707 0L8 8.086 5.854 5.94a.5.5 0 00-.708 0l-2 2a.5.5 0 10.708.708L5.5 6.992l2.146 2.147a.5.5 0 00.708 0l3.5-3.5a.5.5 0 000-.707z"></path>',
    'github': '<path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>'
}


def generate_donut(data, title):
    total = sum(d[1] for d in data)
    w, h = 372, 170
    shadow_offset = 8
    canvas_w = w + shadow_offset
    canvas_h = h + shadow_offset
    
    svg = f'''<svg width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}" xmlns="http://www.w3.org/2000/svg">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&amp;family=JetBrains+Mono:wght@400;600&amp;display=swap');
        .title {{ font-family: 'Space Grotesk', system-ui; fill: {theme['white']}; font-size: 16px; font-weight: 700; letter-spacing: 0.05em; }}
        .label {{ font-family: 'JetBrains Mono', monospace; fill: {theme['muted']}; font-size: 12px; }}
        .value {{ font-family: 'JetBrains Mono', monospace; fill: {theme['white']}; font-size: 12px; font-weight: 600; }}
        .bg {{ fill: {theme['surface']}; stroke: {theme['border']}; stroke-width: 2; }}
        .shadow {{ fill: {theme['shadow']}; }}
    </style>
    <!-- Brutalist Shadow -->
    <rect x="{shadow_offset}" y="{shadow_offset}" width="{w}" height="{h}" class="shadow" />
    <!-- Foreground Background -->
    <rect width="{w}" height="{h}" class="bg" />
    
    <text x="30" y="35" class="title" fill="{theme['white']}">{title.upper()}</text>
    <line x1="30" y1="42" x2="160" y2="42" stroke="{theme['accent']}" stroke-width="2" />
    '''
    
    cx, cy, radius, stroke_width = 280, 100, 48, 14
    current_angle = 0
    y_offset = 70
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
        <text x="40" y="{y_offset}" class="label">{name_l} <tspan fill="{theme['white']}" class="value">{pct:.1f}%</tspan></text>
        '''
        y_offset += 16
        
    svg += '</svg>'
    return svg


# 1. Stats SVG
w, h = 372, 170
shadow_offset = 8
canvas_w = w + shadow_offset
canvas_h = h + shadow_offset
svg_stats = f'''<svg width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}" xmlns="http://www.w3.org/2000/svg">
  <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&amp;family=JetBrains+Mono:wght@400;600&amp;display=swap');
      .title {{ font-family: 'Space Grotesk', system-ui; fill: {theme['white']}; font-size: 16px; font-weight: 700; letter-spacing: 0.05em; }}
      .label {{ font-family: 'JetBrains Mono', monospace; fill: {theme['muted']}; font-size: 12px; }}
      .value {{ font-family: 'JetBrains Mono', monospace; fill: {theme['white']}; font-size: 12px; font-weight: 600; }}
      .bg {{ fill: {theme['surface']}; stroke: {theme['border']}; stroke-width: 2; }}
      .shadow {{ fill: {theme['shadow']}; }}
      .icon {{ fill: {theme['accent']}; }}
  </style>
  <rect x="{shadow_offset}" y="{shadow_offset}" width="{w}" height="{h}" class="shadow" />
  <rect width="{w}" height="{h}" class="bg" />
  
  <text x="30" y="35" class="title" fill="{theme['white']}">LIFETIME STATS</text>
  <line x1="30" y1="42" x2="160" y2="42" stroke="{theme['accent']}" stroke-width="2" />
  
  <g transform="translate(30, 65)">
    <g transform="translate(0, 0)">
        <g class="icon" transform="scale(0.9)">{icons['star']}</g>
        <text x="30" y="16" class="label" fill="{theme['muted']}">Stars: <tspan class="value" x="140" fill="{theme['white']}">{stars}</tspan></text>
    </g>
    <g transform="translate(0, 28)">
        <g class="icon" transform="scale(0.9)">{icons['commit']}</g>
        <text x="30" y="16" class="label" fill="{theme['muted']}">Commits: <tspan class="value" x="140" fill="{theme['white']}">{current_commits}</tspan></text>
    </g>
    <g transform="translate(0, 56)">
        <g class="icon" transform="scale(0.9)">{icons['pr']}</g>
        <text x="30" y="16" class="label" fill="{theme['muted']}">Pull Requests: <tspan class="value" x="140" fill="{theme['white']}">{prs}</tspan></text>
    </g>
    <g transform="translate(190, 0)">
        <g class="icon" transform="scale(0.9)">{icons['issue']}</g>
        <text x="30" y="16" class="label" fill="{theme['muted']}">Issues: <tspan class="value" x="110" fill="{theme['white']}">{issues}</tspan></text>
    </g>
    <g transform="translate(190, 28)">
        <g class="icon" transform="scale(0.9)">{icons['repo']}</g>
        <text x="30" y="16" class="label" fill="{theme['muted']}">Contributed: <tspan class="value" x="110" fill="{theme['white']}">{contrib_to}</tspan></text>
    </g>
  </g>
</svg>'''

with open("1-stats.svg", "w", encoding="utf-8") as f:
    f.write(svg_stats)

# 2. Languages Repo
with open("2-top-languages.svg", "w", encoding="utf-8") as f:
    f.write(generate_donut(top_langs_repo, "Top Languages by Repo"))

# 3. Top Languages (By Commit)
with open("3-top-languages-by-commit.svg", "w", encoding="utf-8") as f:
    f.write(generate_donut(top_langs_commit, "Top Languages by Commit"))

# --- Dynamic README Update (2x2 Grid with Clickable Badges) ---
try:
    with open("favorites.json", "r", encoding="utf-8") as f:
        favorites = json.load(f)
except Exception as e:
    print(f"Error loading favorites.json: {e}")
    favorites = []

# Function to generate individual repository badges
def generate_repo_badge(name, theme, icon_path):
    # Single-side red badge with left-aligned text and repo icon
    return f'''<svg width="372" height="40" viewBox="0 0 372 40" xmlns="http://www.w3.org/2000/svg">
  <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@700&amp;display=swap');
      .name {{ font-family: 'Space Grotesk', sans-serif; fill: {theme['white']}; font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }}
  </style>
  <rect width="372" height="40" rx="4" fill="{theme['accent']}" />
  <g transform="translate(20, 10) scale(0.85)" fill="{theme['white']}">
    {icon_path}
  </g>
  <text x="55" y="26" class="name" fill="{theme['white']}">{name}</text>
</svg>'''

# --- Dynamic README Update (2x2 Grid with Clickable Badges) ---
try:
    with open("favorites.json", "r", encoding="utf-8") as f:
        favorites = json.load(f)
except Exception as e:
    print(f"Error loading favorites.json: {e}")
    favorites = []

# Generate Badges and corresponding HTML
badges_html = ""
github_icon = icons['github'].replace('<path ', '<path fill="currentColor" ') # Ensure it inherits fill

for i, repo in enumerate(favorites[:3], 1):
    badge_content = generate_repo_badge(repo['name'], theme, github_icon)
    filename = f"fav-{i}.svg"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(badge_content)
    
    badges_html += f'<a href="{repo["url"]}"><img src="{filename}" width="372" /></a>'
    if i < 3: badges_html += "<br/>" 

new_stats_html = f"""<!--STATS_START-->
<div align="center">
  <br/>
  <table border="0" cellpadding="0" cellspacing="0" style="border: none; border-collapse: collapse;">
    <tr>
      <td align="center" style="border: none; padding: 0;"><img src="1-stats.svg" width="380" /></td>
      <td align="center" style="border: none; padding: 0;"><img src="2-top-languages.svg" width="380" /></td>
    </tr>
    <tr>
      <td align="center" style="border: none; padding: 0;"><img src="3-top-languages-by-commit.svg" width="380" /></td>
      <td align="center" style="border: none; padding: 0;" valign="middle">
        <div align="center">
          {badges_html}
        </div>
      </td>
    </tr>
  </table>
  <br/>
  <img src="0-profile-details.svg" alt="Profile Details" width="760" />
</div>
<!--STATS_END-->"""

try:
    with open("README.md", "r", encoding="utf-8") as f:
        readme_content = f.read()

    import re
    # Replace content between STATS markers
    updated_readme = re.sub(
        r"<!--STATS_START-->.*?<!--STATS_END-->",
        new_stats_html,
        readme_content,
        flags=re.DOTALL
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated_readme)
    print("README.md updated successfully with 2x2 grid.")
except Exception as e:
    print(f"Error updating README.md: {e}")


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

svg_profile = f'''<svg width="908" height="258" viewBox="0 0 908 258" xmlns="http://www.w3.org/2000/svg">
  <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&amp;family=JetBrains+Mono:wght@400;600&amp;display=swap');
      .title {{ font-family: 'Space Grotesk', sans-serif; fill: {theme['white']}; font-size: 24px; font-weight: 700; letter-spacing: 0.05em; }}
      .label {{ font-family: 'JetBrains Mono', sans-serif; fill: {theme['muted']}; font-size: 13px; }}
      .value {{ font-family: 'JetBrains Mono', sans-serif; fill: {theme['white']}; font-size: 13px; font-weight: 600; }}
      .bg {{ fill: {theme['surface']}; stroke: {theme['border']}; stroke-width: 2; }}
      .shadow {{ fill: {theme['shadow']}; }}
      .chart-fill {{ fill: {theme['accent']}; opacity: 0.15; stroke: {theme['accent']}; stroke-width: 2; }}
      .axis {{ stroke: {theme['border']}; stroke-width: 1; stroke-dasharray: 2 2; }}
      .axis-label {{ font-family: 'JetBrains Mono', sans-serif; fill: {theme['muted']}; font-size: 12px; }}
      .icon {{ fill: {theme['accent']}; }}
  </style>
  <rect x="8" y="8" width="900" height="250" class="shadow" />
  <rect width="900" height="250" class="bg" />
  
  <text x="30" y="50" class="title">{USERNAME} ({name})</text>
  <line x1="30" y1="60" x2="300" y2="60" stroke="{theme['accent']}" stroke-width="2" />
  
  <g transform="translate(30, 95)"><g class="icon" transform="scale(0.9)">{icons['activity']}</g></g>
  <text x="55" y="108" class="label">Lifetime Contributions: <tspan class="value">{current_contributions}</tspan></text>

  <g transform="translate(30, 130)"><g class="icon" transform="scale(0.9)">{icons['repo']}</g></g>
  <text x="55" y="143" class="label">Public Repos: <tspan class="value">{public_repos_count}</tspan></text>

  <g transform="translate(30, 165)"><g class="icon" transform="scale(0.9)">{icons['clock']}</g></g>
  <text x="55" y="178" class="label">Joined GitHub: <tspan class="value">{joined_years} years ago</tspan></text>

  <g transform="translate(30, 200)"><g class="icon" transform="scale(0.9)">{icons['institution']}</g></g>
  <text x="55" y="213" class="label">Studying At: <tspan class="value">{company}</tspan></text>
  
  <text x="605" y="45" class="axis-label" text-anchor="middle" fill="{theme['white']}">LIFETIME CONTRIBUTIONS ACTIVITY</text>
  
  <path d="{path_d}" class="chart-fill"/>
  <line x1="{x_start}" y1="{y_start}" x2="{x_start+chart_w}" y2="{y_start}" class="axis" />
  
  <line x1="{x_start+chart_w}" y1="{y_start}" x2="{x_start+chart_w}" y2="{y_start-chart_h}" class="axis" />
  <text x="{x_start+chart_w+10}" y="{y_start}" class="axis-label" fill="{theme['muted']}">{0}</text>
  <text x="{x_start+chart_w+10}" y="{y_start - chart_h/2}" class="axis-label" fill="{theme['muted']}">{max_contrib//2}</text>
  <text x="{x_start+chart_w+10}" y="{y_start - chart_h}" class="axis-label" fill="{theme['muted']}">{max_contrib}</text>
</svg>'''

with open("0-profile-details.svg", "w", encoding="utf-8") as f:
    f.write(svg_profile)

# 5. About Terminal SVG
advanced_svg = f"""<svg width="608" height="238" viewBox="0 0 608 238" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&amp;display=swap');
      .prompt {{ font-family: 'JetBrains Mono', monospace; font-size: 14px; fill: {theme['accent']}; font-weight: 600; }}
      .cmd {{ font-family: 'JetBrains Mono', monospace; font-size: 14px; fill: {theme['white']}; }}
      .file {{ font-family: 'JetBrains Mono', monospace; font-size: 14px; fill: {theme['muted']}; }}
      .output {{ font-family: 'JetBrains Mono', monospace; font-size: 14px; fill: {theme['white']}; opacity: 0.85; }}
      .bold {{ font-weight: 600; fill: {theme['white']}; font-size: 14px; }}
      .bg {{ fill: {theme['surface']}; }}
      .border {{ fill: none; stroke: {theme['border']}; stroke-width: 2; }}
      .shadow {{ fill: {theme['shadow']}; }}

      .cursor {{ fill: {theme['white']}; font-family: 'JetBrains Mono', monospace; font-size: 14px; animation: blink 1s step-end infinite; }}
      @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}

      .type-mask {{ fill: {theme['surface']}; animation: slide 1.5s steps(40, end) forwards; }}
      .type-mask-1 {{ animation-delay: 0.5s; }}
      .type-mask-2 {{ animation-delay: 1.5s; }}
      .type-mask-3 {{ animation-delay: 2.0s; }}
      .type-mask-4 {{ animation-delay: 3.0s; }}
      .type-mask-5 {{ animation-delay: 3.2s; }}
      .type-mask-6 {{ animation-delay: 4.5s; }}
      .type-mask-7 {{ animation-delay: 5.5s; }}
      
      @keyframes slide {{ to {{ transform: translateX(550px); }} }}
      
      .hide {{ opacity: 0; animation: fadein 0.1s forwards; }}
      .delay-1 {{ animation-delay: 0s; }}
      .delay-2 {{ animation-delay: 1.5s; }}
      .delay-3 {{ animation-delay: 2.0s; }}
      .delay-4 {{ animation-delay: 3.0s; }}
      .delay-6 {{ animation-delay: 4.5s; }}
      .delay-7 {{ animation-delay: 5.5s; }}
      .delay-8 {{ animation-delay: 7.0s; }}
      @keyframes fadein {{ to {{ opacity: 1; }} }}
    </style>
  </defs>

  <!-- Shadow -->
  <rect x="8" y="8" width="600" height="230" class="shadow" />
  <!-- Main -->
  <rect width="600" height="230" class="bg" fill="{theme['surface']}" />
  <rect width="600" height="230" class="border" />

  <g transform="translate(10, 10)">
    <circle cx="10" cy="6" r="5" fill="#ff5f57" />
    <circle cx="28" cy="6" r="5" fill="#febc2e" />
    <circle cx="46" cy="6" r="5" fill="#28c840" />
  </g>

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

# 6. Output to JSON
total_repo_size = sum(d[1] for d in top_langs_repo)
total_commit_val = sum(d[1] for d in top_langs_commit)

stats_data = {
    "user": {
        "login": USERNAME,
        "name": name,
        "company": company,
        "joined_years_ago": joined_years
    },
    "stats": {
        "stars": stars,
        "commits": current_commits,
        "contributions": current_contributions,
        "prs": prs,
        "issues": issues,
        "contributed_to": contrib_to,
        "public_repos": public_repos_count
    },
    "languages": {
        "by_repo_size": {lang: round((size / total_repo_size) * 100, 1) if total_repo_size > 0 else 0 for lang, size in top_langs_repo},
        "by_commits": {lang: round((val / total_commit_val) * 100, 1) if total_commit_val > 0 else 0 for lang, val in top_langs_commit}
    },
    "generated_at": datetime.datetime.now().isoformat()
}

with open("stats.json", "w", encoding="utf-8") as f:
    json.dump(stats_data, f, indent=2)


