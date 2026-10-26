"""Snapshot public GitHub activity; errors preserve the last successful card."""
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from profile_cards import ASSETS, picture, save_variants, stats_svg

ROOT = Path(__file__).resolve().parents[1]
QUERY = '''query($cursor:String) {
 user(login:"wrestle-R") {
  createdAt
  followers { totalCount }
  repositories(first:100, after:$cursor, ownerAffiliations:OWNER, privacy:PUBLIC) {
   nodes { isFork stargazerCount } pageInfo { hasNextPage endCursor } totalCount
  }
  contributionsCollection {
   contributionCalendar {
    totalContributions
    weeks { contributionDays { date contributionCount contributionLevel weekday } }
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
    calendar = user['contributionsCollection']['contributionCalendar']
    return {'calendar': calendar, 'stars': stars, 'prs': data['opened']['issueCount'],
            'merged_prs': data['merged']['issueCount'],
            'commits': fetch_all_time_commits(user['createdAt']),
            'repos': repos['totalCount'], 'followers': user['followers']['totalCount']}


def fetch_all_time_commits(created_at):
    # GitHub accepts at most one year per contributionsCollection request.
    # Sum public commit contributions across non-overlapping calendar years.
    now = datetime.now(timezone.utc)
    total = 0
    query = '''query($from:DateTime!,$to:DateTime!) {
      user(login:"wrestle-R") {
        contributionsCollection(from:$from,to:$to) {
          commitContributionsByRepository(maxRepositories:100) {
            repository { isPrivate } contributions { totalCount }
          }
        }
      }
    }'''
    for year in range(int(created_at[:4]), now.year+1):
        start = f'{year}-01-01T00:00:00Z'
        end = (f'{year}-12-31T23:59:59Z' if year < now.year
               else now.strftime('%Y-%m-%dT%H:%M:%SZ'))
        result = json.loads(subprocess.check_output([
            'gh', 'api', 'graphql', '-f', 'query='+query,
            '-f', 'from='+start, '-f', 'to='+end], text=True))
        if result.get('errors'):
            raise ValueError('GitHub returned incomplete all-time commit counts.')
        repos = result['data']['user']['contributionsCollection']['commitContributionsByRepository']
        if len(repos) == 100:
            raise ValueError(f'Commit repository limit reached in {year}; refusing a partial count.')
        total += sum(repo['contributions']['totalCount'] for repo in repos
                     if not repo['repository']['isPrivate'])
    return total


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
        'commits': 'Public GitHub contribution-calendar commits, summed across every calendar year since account creation',
        'repos': 'Owned public repositories, including forks',
        'followers': 'Current followers'}}
    (ASSETS / 'account-stats.json').write_text(json.dumps(snapshot, indent=2)+'\n')
    alt = (f'{stats["calendar"]["totalContributions"]} contributions in the past year; {stats["stars"]} stars earned; {stats["prs"]} public PRs; '
           f'{stats["merged_prs"]} merged PRs; {stats["commits"]} public commits all time; '
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
