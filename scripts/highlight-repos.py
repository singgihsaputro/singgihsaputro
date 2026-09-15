#!/usr/bin/env python3
"""Rewrite the block between the RECENT markers in README.md with the highlighted
projects.

The selection is curated rather than most-recent: the nightly agent publishes a
repository most days and would otherwise bury the work worth showing. Metadata is
still fetched live, so languages and stars stay true. Leaves the file alone on
any failure."""
import json
import pathlib
import re
import urllib.request

USER = 'singgihsaputro'
START, END = '<!-- RECENT:START -->', '<!-- RECENT:END -->'

# name, and an optional blurb where the repository's own description reads poorly
HIGHLIGHTS = [
    ('pokemon-kotlin-multiplatform-mobile',
     'Kotlin Multiplatform sample sharing business logic across Android and iOS'),
    ('android-pomodoro-timer', None),
    ('ios-habit-tracker', None),
    ('backend-expense-splitter', None),
    ('WebChat-BottlePython', 'Web chat built on Bottle, Python\u2019s micro web framework'),
]


def fetch():
    out = []
    for name, blurb in HIGHLIGHTS:
        req = urllib.request.Request(
            f'https://api.github.com/repos/{USER}/{name}',
            headers={'User-Agent': 'profile-readme', 'Accept': 'application/vnd.github+json'},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        d['_blurb'] = blurb or d.get('description') or '—'
        out.append(d)
    if len(out) != len(HIGHLIGHTS):
        raise SystemExit('not every highlight resolved — leaving the table alone')
    return out


def main():
    repos = fetch()
    if not repos:
        raise SystemExit('no repositories returned — refusing to blank the section')

    rows = ['| Project | What it is | Language |', '|---|---|---|']
    for r in repos:
        desc = r['_blurb'].replace('|', '\\|')
        stars = f" ⭐{r['stargazers_count']}" if r['stargazers_count'] else ''
        rows.append(
            f"| [{r['name']}](https://github.com/{USER}/{r['name']}){stars} | {desc} "
            f"| {r['language'] or '—'} |"
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
