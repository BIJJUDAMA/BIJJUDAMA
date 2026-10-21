from collections import defaultdict


def deduplicate_repositories(repositories):
    unique_repos = []
    seen = set()
    for repo in repositories:
        repo_key = repo.get("id") or repo.get("nameWithOwner") or repo.get("name")
        if not repo_key or repo_key in seen:
            continue
        seen.add(repo_key)
        unique_repos.append(repo)
    return unique_repos


def sort_languages(language_values, limit=5):
    sorted_languages = sorted(
        language_values.items(),
        key=lambda x: (-x[1], x[0].lower())
    )
    return sorted_languages[:limit]


def calculate_percentages(language_entries, total_value):
    if total_value <= 0:
        return {name: 0.0 for name, _ in language_entries}
    return {name: (value / total_value) * 100 for name, value in language_entries}


def aggregate_repo_languages(repositories):
    language_sizes = defaultdict(int)
    language_colors = {}

    for repo in deduplicate_repositories(repositories):
        edges = ((repo.get("languages") or {}).get("edges")) or []
        for edge in edges:
            node = edge.get("node") or {}
            language_name = node.get("name")
            size = edge.get("size") or 0
            if not language_name:
                continue
            language_sizes[language_name] += size
            color = node.get("color")
            if color and language_name not in language_colors:
                language_colors[language_name] = color

    return dict(language_sizes), language_colors


def aggregate_commit_languages(repositories):
    language_commit_sizes = defaultdict(float)

    for repo in deduplicate_repositories(repositories):
        repo_commits = 0
        try:
            default_ref = repo.get("defaultBranchRef")
            if default_ref and default_ref.get("target"):
                repo_commits = default_ref["target"]["history"]["totalCount"]
        except Exception:
            repo_commits = 0

        edges = ((repo.get("languages") or {}).get("edges")) or []
        repo_total_size = sum((edge.get("size") or 0) for edge in edges)
        if repo_total_size <= 0:
            continue

        for edge in edges:
            node = edge.get("node") or {}
            language_name = node.get("name")
            size = edge.get("size") or 0
            if not language_name or size <= 0:
                continue
            language_commit_sizes[language_name] += (size / repo_total_size) * repo_commits

    return dict(language_commit_sizes)


def build_donut_segments(language_entries, total_value=None):
    if total_value is None:
        total_value = sum(value for _, value in language_entries)
    segments = []
    for name, value in language_entries:
        if total_value > 0:
            percentage = (value / total_value) * 100
            angle = (value / total_value) * 360
        else:
            percentage = 0
            angle = 0
        segments.append((name, value, percentage, angle))
    return segments
