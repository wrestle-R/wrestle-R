"""Refresh only the latest-post block from Russel's public RSS feed."""
from datetime import datetime, timezone
from profile_cards import blog_svg, picture, save_variants
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

FEED = 'https://blogs.russeldanielpaul.is-a.dev/rss.xml'
START = '<!-- LATEST-BLOG:START -->'
END = '<!-- LATEST-BLOG:END -->'


def select_post(data):
    items = ET.fromstring(data).findall('./channel/item')
    now = datetime.now(timezone.utc)
    posts = []
    for item in items:
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()
        date = parsedate_to_datetime(item.findtext('pubDate') or '')
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        url = urlsplit(link)
        if (title and url.scheme == 'https'
                and url.hostname in {'blogs.russel.is-a.dev', 'blogs.russeldanielpaul.is-a.dev'}
                and url.path.startswith('/blog/') and date <= now):
            posts.append((date, title, link, (item.findtext('description') or '').strip()))
    if not posts:
        raise ValueError('No published blog posts found; keeping the existing README.')
    _, title, link, description = max(posts, key=lambda post: post[0])
    return {'title': title, 'link': link, 'description': description}


def latest_block(post):
    return (f'<a href="{escape(post["link"], quote=True)}">\n'
            + picture('latest-blog', post['title'] + ' — read the latest blog post')
            + '\n</a>')


def main():
    readme = Path(__file__).resolve().parents[1] / 'README.md'
    content = readme.read_text()
    if content.count(START) != 1 or content.count(END) != 1:
        raise ValueError('Expected exactly one latest-blog marker pair.')
    before, rest = content.split(START)
    _, after = rest.split(END)
    request = Request(FEED, headers={'User-Agent': 'wrestle-profile-readme/1.0'})
    with urlopen(request, timeout=30) as response:
        post = select_post(response.read(2_000_000))
    save_variants('latest-blog', post, blog_svg)
    block = latest_block(post)
    updated = before + START + '\n' + block + '\n' + END + after
    if updated != content:
        readme.write_text(updated)
        print('Updated latest blog post.')
    else:
        print('Latest blog post is already current.')


if __name__ == '__main__':
    main()
