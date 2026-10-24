"""Snapshot public GitHub activity; errors preserve the last successful card."""
import json
from pathlib import Path
import subprocess
from profile_cards import ASSETS, picture, save_variants, stats_svg

ROOT = Path(__file__).resolve().parents[1]
QUERY = '''query($cursor:String) {
 user(login:"wrestle-R") {
  followers { totalCount }
  repositories(first:100, after:$cursor, ownerAffiliations:OWNER, privacy:PUBLIC) {
   nodes { isFork stargazerCount } pageInfo { hasNextPage endCursor } totalCount
  }
  contributionsCollection {
   contributionCalendar {
    totalContributions
    weeks { contributionDays { date contributionCount contributionLevel weekday } }
   }
   commitContributionsByRepository(maxRepositories:100) {
    repository { isPrivate } contributions { totalCount }
   }
  }
 }
 opened:search(query:"author:wrestle-R type:pr is:public",type:ISSUE,first:1){issueCount}
 merged:search(query:"author:wrestle-R type:pr is:merged is:public",type:ISSUE,first:1){issueCount}
}'''


def fetch_stats():
    cursor = None
    stars = 0
    while True:
        args = ['gh', 'api', 'graphql', '-f', 'query='+QUERY]
        if cursor:
            args += ['-f', 'cursor='+cursor]
        result = json.loads(subprocess.check_output(args, text=True))
        if result.get('errors'):
            raise ValueError('GitHub returned incomplete statistics.')
        data = result['data']
        user = data['user']
        repos = user['repositories']
        stars += sum(repo['stargazerCount'] for repo in repos['nodes'] if not repo['isFork'])
        if not repos['pageInfo']['hasNextPage']:
            break
        cursor = repos['pageInfo']['endCursor']
    commits = user['contributionsCollection']['commitContributionsByRepository']
    if len(commits) == 100:
        raise ValueError('Commit repository limit reached; refusing to publish a partial count.')
    calendar = user['contributionsCollection']['contributionCalendar']
    return {'calendar': calendar, 'stars': stars, 'prs': data['opened']['issueCount'],
            'merged_prs': data['merged']['issueCount'],
            'commits': sum(repo['contributions']['totalCount'] for repo in commits if not repo['repository']['isPrivate']),
            'repos': repos['totalCount'], 'followers': user['followers']['totalCount']}


def main():
    path = ROOT / 'README.md'
    content = path.read_text()
    start, end = '<!-- ACCOUNT-STATS:START -->', '<!-- ACCOUNT-STATS:END -->'
    if content.count(start) != 1 or content.count(end) != 1:
        raise ValueError('Expected exactly one statistics marker pair.')
    stats = fetch_stats()
    save_variants('account-stats', stats, stats_svg)
    snapshot = {'counts': {k:v for k,v in stats.items() if k != 'calendar'}, 'calendar': stats['calendar'], 'scope': {
        'stars': 'Stars earned by owned public non-fork repositories',
        'prs': 'Public pull requests authored, all time',
        'merged_prs': 'Public authored pull requests merged, all time',
        'commits': 'Public GitHub contribution-calendar commits, past 12 months',
        'repos': 'Owned public repositories, including forks',
        'followers': 'Current followers'}}
    (ASSETS / 'account-stats.json').write_text(json.dumps(snapshot, indent=2)+'\n')
    alt = (f'{stats["calendar"]["totalContributions"]} contributions in the past year; {stats["stars"]} stars earned; {stats["prs"]} public PRs; '
           f'{stats["merged_prs"]} merged PRs; {stats["commits"]} public commits in the past year; '
           f'{stats["repos"]} public repos; {stats["followers"]} followers. Refreshed daily.')
    block = '<a href="https://github.com/wrestle-R">\n'+picture('account-stats', alt)+'\n</a>'
    before, rest = content.split(start)
    _, after = rest.split(end)
    updated = before+start+'\n'+block+'\n'+end+after
    if content != updated:
        path.write_text(updated)
    print('Public account summary refreshed.')


if __name__ == '__main__':
    main()
