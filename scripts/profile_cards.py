"""Code-native SVG cards, with explicit phone and light/dark variants."""
from html import escape
from pathlib import Path
import textwrap
from datetime import date
import math

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets' / 'generated'
PALETTES = {
    'dark': ('#0d1117', '#30363d', '#e6edf3', '#8b949e', '#4493f8'),
    'light': ('#ffffff', '#d1d9e0', '#1f2328', '#59636e', '#0969da'),
}


def text(x, y, value, size, color, weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(str(value))}</text>'


def frame(width, height, theme, label, parts):
    bg, border, _, _, _ = PALETTES[theme]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label, quote=True)}">'
            f'<title>{escape(label)}</title><rect x="1" y="1" width="{width-2}" height="{height-2}" rx="6" fill="{bg}" stroke="{border}"/>'
            '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif">'+''.join(parts)+'</g></svg>\n')


def wrapped(value, columns, maximum):
    return textwrap.wrap(' '.join(value.split()), width=columns,
                         max_lines=maximum, placeholder='…')


def blog_svg(post, theme, mobile=False):
    width = 360 if mobile else 780
    _, _, ink, _, _ = PALETTES[theme]
    titles = wrapped(post['title'], 23 if mobile else 44, 3 if mobile else 2)
    height = 44+(len(titles)-1)*29+24
    parts = [text(20, 44+i*29, line, 23 if mobile else 27, ink, 650)
             for i, line in enumerate(titles)]
    return frame(width, height, theme, post['title'], parts)


def stats_svg(stats, theme, mobile=False):
    width, height = (360, 470) if mobile else (780, 348)
    _, border, ink, muted, _ = PALETTES[theme]
    green = '#3fb950' if theme == 'dark' else '#1a7f37'
    total = stats['calendar']['totalContributions']
    parts = [text(24, 32, f'{total:,} contributions'+('' if mobile else ' in the last year'), 17, ink, 600),
             text(24, 53, 'Weekly contributions · past 12 months', 12, muted)]
    weeks = stats['calendar']['weeks']
    values = [sum(day['contributionCount'] for day in week['contributionDays']) for week in weeks]
    if not values:
        raise ValueError('Contribution calendar is empty.')
    left, right, top, bottom = 44, width-24, 82, 218
    maximum = max(values)
    raw_tick = max(maximum/5, 1)
    magnitude = 10**math.floor(math.log10(raw_tick))
    tick = next(step*magnitude for step in (1, 2, 5, 10) if step*magnitude >= raw_tick)
    intervals = max(1, math.ceil(maximum/tick))
    ceiling = tick*intervals
    for i in range(intervals+1):
        y = bottom-(bottom-top)*i/intervals
        parts.extend([f'<path d="M{left} {y:.1f}H{right}" stroke="{border}" stroke-dasharray="3 4"/>',
                      text(8 if mobile else 12, y+4, i*tick, 10, muted)])
    points = [(left+(right-left)*i/max(len(values)-1, 1), bottom-(bottom-top)*v/ceiling) for i,v in enumerate(values)]
    area = f'M{left},{bottom} '+ ' '.join(f'L{x:.2f},{y:.2f}' for x,y in points)+f' L{right},{bottom}Z'
    parts.append(f'<path d="{area}" fill="{green}" fill-opacity="0.07"/>')
    line = ' '.join(f'{x:.2f},{y:.2f}' for x,y in points)
    parts.append(f'<polyline points="{line}" fill="none" stroke="{green}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
    # A point title gives each weekly aggregate an inspectable date and exact count.
    for (x,y),week,value in zip(points,weeks,values):
        when = week['contributionDays'][0]['date']
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2" fill="{green}"><title>Week of {when}: {value} contributions</title></circle>')
    previous_month = None
    last_label = -100
    for i,week in enumerate(weeks):
        month = date.fromisoformat(week['contributionDays'][0]['date']).strftime('%b')
        spacing = 7 if mobile else 3
        if month != previous_month and i-last_label >= spacing:
            x = points[i][0]
            parts.append(text(x-5, bottom+18, month, 10, muted))
            last_label = i
        previous_month = month
    divider = 255 if mobile else 252
    parts.append(f'<path d="M24 {divider}H{width-24}" stroke="{border}"/>')
    metrics = [(stats['stars'], 'Stars earned'), (stats['prs'], 'Pull requests'),
               (stats['merged_prs'], 'Merged PRs'), (stats['commits'], 'Commits · all time'),
               (stats['repos'], 'Public repos'), (stats['followers'], 'Followers')]
    columns = 2 if mobile else 6
    cell = (width-48)/columns
    for i, (value, label) in enumerate(metrics):
        x, y = 24+(i % columns)*cell, (290 if mobile else 286)+(i//columns)*57
        parts.extend([text(x, y, f'{value:,}', 23, ink, 600),
                      text(x, y+20, label, 12 if mobile else 11, muted)])
    parts.append(text(24, height-15, 'Public GitHub activity · updated daily', 11, muted))
    return frame(width, height, theme, 'Weekly GitHub contributions and account summary', parts)


def save_variants(name, data, renderer):
    ASSETS.mkdir(parents=True, exist_ok=True)
    for theme in PALETTES:
        for mobile in (False, True):
            suffix = '-mobile' if mobile else ''
            path = ASSETS / f'{name}-{theme}{suffix}.svg'
            value = renderer(data, theme, mobile)
            if not path.exists() or path.read_text() != value:
                path.write_text(value)


def picture(name, alt):
    return '\n'.join([
        '<picture>',
        f'  <source media="(max-width: 480px) and (prefers-color-scheme: dark)" srcset="assets/generated/{name}-dark-mobile.svg" />',
        f'  <source media="(max-width: 480px)" srcset="assets/generated/{name}-light-mobile.svg" />',
        f'  <source media="(prefers-color-scheme: dark)" srcset="assets/generated/{name}-dark.svg" />',
        f'  <img src="assets/generated/{name}-light.svg" alt="{escape(alt, quote=True)}" width="100%" />',
        '</picture>',
    ])
