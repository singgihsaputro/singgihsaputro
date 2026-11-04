#!/usr/bin/env python3
"""Rewrite the two generated blocks of README.md:

- between the RECENT markers, the highlighted projects: curated rather than
  most-recent, because the nightly agent published a repository most days and
  would otherwise bury the work worth showing;
- between the ALL markers, every public repository, grouped. Forks, private
  repositories and this profile repository are left out.

Metadata is fetched live, so languages, stars and descriptions stay true. On any
failure the file is left alone. --offline FILE renders the ALL block from a JSON
list instead (the shape of data/all-repos.json on the site), for trying it out.
"""
import json
import os
import pathlib
import re
import sys
import urllib.request

USER = 'singgihsaputro'
RECENT = ('<!-- RECENT:START -->', '<!-- RECENT:END -->')
ALL = ('<!-- ALL:START -->', '<!-- ALL:END -->')

# name, and an optional blurb where the repository's own description reads poorly
HIGHLIGHTS = [
    ('erp', None),
    ('pokemon-kotlin-multiplatform-mobile',
     'Kotlin Multiplatform sample sharing business logic across Android and iOS'),
    ('android-pomodoro-timer', None),
    ('ios-habit-tracker', None),
    ('backend-expense-splitter', None),
    ('WebChat-BottlePython', 'Web chat built on Bottle, Python\u2019s micro web framework'),
]

# Same rules as data/repo-groups.mjs in singgihsaputro/singgihsaputro.github.io:
# a name prefix decides the group, otherwise the year it was created.
GROUPS = [
    ('projects', 'Projects', False, []),
    ('android', 'Android apps', True, ['android-']),
    ('androidlib', 'Android libraries', True, ['androidlib-']),
    ('ios', 'iOS apps', True, ['ios-']),
    ('kmp', 'Kotlin Multiplatform', True, ['kmp-', 'kmpfullstack-']),
    ('web', 'Web apps', True, ['web-']),
    ('backend', 'Backends', True, ['backend-']),
    ('freelance', 'Freelance web apps', True, ['freelance-']),
    ('flutter', 'Flutter samples', False, ['flutter_']),
    ('early', 'Early work, 2016\u20132019', False, []),
]
HIDDEN = {USER}
# GitHub counts generated platform code (C++, Makefiles); these are all Flutter.
GROUP_LANGUAGE = {'flutter': 'Dart'}


def group_of(name, created):
    for gid, _, _, prefixes in GROUPS:
        if any(name.startswith(p) for p in prefixes):
            return gid
    return 'early' if created < '2020' else 'projects'


def get(url):
    headers = {'User-Agent': 'profile-readme', 'Accept': 'application/vnd.github+json'}
    token = os.environ.get('GITHUB_TOKEN')
    if token:  # in Actions the workflow token lifts the anonymous rate limit
        headers['Authorization'] = f'Bearer {token}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return json.load(r)


def fetch_highlights():
    out = []
    for name, blurb in HIGHLIGHTS:
        d = get(f'https://api.github.com/repos/{USER}/{name}')
        d['_blurb'] = blurb or d.get('description') or '—'
        out.append(d)
    if len(out) != len(HIGHLIGHTS):
        raise SystemExit('not every highlight resolved — leaving the table alone')
    return out


def fetch_all():
    repos, page = [], 1
    while True:
        batch = get(f'https://api.github.com/users/{USER}/repos?type=owner&sort=created&direction=desc&per_page=100&page={page}')
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    return [
        {
            'name': r['name'],
            'description': r.get('description') or '',
            'language': r.get('language') or '',
            'stars': r['stargazers_count'],
            'archived': r.get('archived', False),
            'created': r['created_at'][:10],
        }
        for r in repos
        if not r['fork'] and not r.get('private') and r['name'] not in HIDDEN
    ]


def cell(s):
    return (s or '—').replace('|', '\\|').replace('\n', ' ')


def render_highlights(repos):
    rows = ['| Project | What it is | Language |', '|---|---|---|']
    for r in repos:
        stars = f" ⭐{r['stargazers_count']}" if r['stargazers_count'] else ''
        rows.append(f"| [{r['name']}](https://github.com/{USER}/{r['name']}){stars} | {cell(r['_blurb'])} | {r['language'] or '—'} |")
    return '\n'.join(rows)


def render_all(repos):
    # a near-empty answer is a GitHub hiccup, not a deleted account
    if len(repos) < 10:
        raise SystemExit(f'only {len(repos)} repositories came back — leaving the list alone')
    for r in repos:
        r['group'] = group_of(r['name'], r['created'])
    nightly = sum(1 for r in repos if any(g[0] == r['group'] and g[2] for g in GROUPS))
    parts = [
        f'{len(repos)} public repositories, grouped and refreshed every day. {nightly} of them are mini '
        'projects a scheduled agent built one a night; the newest, [erp](https://github.com/singgihsaputro/erp), '
        'grows by a feature a night.',
    ]
    for gid, label, is_nightly, _ in GROUPS:
        # newest first, then by name — the same order as the site
        members = sorted(sorted((r for r in repos if r['group'] == gid), key=lambda r: r['name']), key=lambda r: r['created'], reverse=True)
        if not members:
            continue
        note = ' · built one a night by a scheduled agent' if is_nightly else ''
        rows = ['| Project | What it is | Language | Year |', '|---|---|---|---|']
        for r in members:
            stars = f" ⭐{r['stars']}" if r['stars'] else ''
            archived = ' *(archived)*' if r.get('archived') else ''
            language = GROUP_LANGUAGE.get(gid) or r['language'] or '—'
            rows.append(
                f"| [{r['name']}](https://github.com/{USER}/{r['name']}){stars}{archived} | {cell(r['description'])} "
                f"| {language} | {r['created'][:4]} |"
            )
        parts.append(
            f"<details{' open' if gid == 'projects' else ''}>\n"
            f"<summary><b>{label}</b> · {len(members)}{note}</summary>\n\n" + '\n'.join(rows) + '\n\n</details>'
        )
    return '\n\n'.join(parts)


def replace_block(text, markers, body):
    start, end = markers
    if start not in text or end not in text:
        raise SystemExit(f'markers {start} … {end} are missing from README.md')
    block = f'{start}\n\n{body}\n\n{end}'
    return re.sub(re.escape(start) + r'.*?' + re.escape(end), lambda _: block, text, flags=re.S)


def main():
    p = pathlib.Path(__file__).resolve().parent.parent / 'README.md'
    s = p.read_text()
    if len(sys.argv) == 3 and sys.argv[1] == '--offline':
        new = replace_block(s, ALL, render_all(json.loads(pathlib.Path(sys.argv[2]).read_text())))
    else:
        new = replace_block(s, RECENT, render_highlights(fetch_highlights()))
        new = replace_block(new, ALL, render_all(fetch_all()))
    if new == s:
        print('no change')
        return
    p.write_text(new)
    print('updated README.md')


if __name__ == '__main__':
    main()
