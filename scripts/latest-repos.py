#!/usr/bin/env python3
"""Rewrite the block between the RECENT markers in README.md with the five most
recently pushed public repositories. Leaves the file alone on any failure."""
import json
import pathlib
import re
import urllib.request

USER = 'singgihsaputro'
COUNT = 5
START, END = '<!-- RECENT:START -->', '<!-- RECENT:END -->'


def fetch():
    req = urllib.request.Request(
        f'https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed',
        headers={'User-Agent': 'profile-readme', 'Accept': 'application/vnd.github+json'},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        repos = json.load(r)

    keep = [
        x for x in repos
        if not x['fork'] and not x.get('archived')
        and x['name'] not in (USER, f'{USER}.github.io')
    ]
    keep.sort(key=lambda x: x['pushed_at'], reverse=True)
    return keep[:COUNT]


def main():
    repos = fetch()
    if not repos:
        raise SystemExit('no repositories returned — refusing to blank the section')

    rows = ['| Repository | What it is | Language | Updated |', '|---|---|---|---|']
    for r in repos:
        desc = (r['description'] or '—').replace('|', '\\|')
        rows.append(
            f"| [{r['name']}](https://github.com/{USER}/{r['name']}) | {desc} "
            f"| {r['language'] or '—'} | {r['pushed_at'][:10]} |"
        )

    p = pathlib.Path(__file__).resolve().parent.parent / 'README.md'
    s = p.read_text()
    block = f"{START}\n\n" + '\n'.join(rows) + f"\n\n{END}"
    new = re.sub(re.escape(START) + r'.*?' + re.escape(END), block, s, flags=re.S)
    if new == s:
        print('no change')
        return
    p.write_text(new)
    print('updated:', ', '.join(r['name'] for r in repos))


if __name__ == '__main__':
    main()
