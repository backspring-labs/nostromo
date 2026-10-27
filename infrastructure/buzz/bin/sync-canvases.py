#!/usr/bin/python3 -I
"""Render the crew's channel canvases from their templates and live facts, and publish them as Mother.

Every crew/canvases/<name>.md is the canvas of the channel <name> in crew/channels.yaml. The
template holds the prose, changed by pull request. {{fact}} placeholders are filled from live
sources, and only the facts a template names are read:
- the SquadOps version, from the runtime API's /health;
- the engine and its health;
- the Spark mode;
- campaigns, through campaignctl as Mother;
- the crew's state, through crewctl;
- the live Nostromo release;
- the channel map;
- the installed runbooks.
No model is involved, and nothing here writes outside Buzz.

Runs ON the Spark, as mother: her key publishes, and she co-owns every crew channel. From the Mac:

  infrastructure/buzz/bin/sync-canvases.sh [--dry-run] [--only NAME]

deploy-spark.sh runs it after every deploy or rollback. A canvas is published only when its content
changed, not counting the as-of line, so its history records changes rather than runs.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SHARE = Path('/usr/local/share/nostromo')
MODE = Path('/opt/nostromo/state/spark-mode')
RUNTIME_HEALTH = 'http://127.0.0.1:8001/health'
CREWCTL = '/opt/nostromo/runtime/bin/crewctl'
BUDGET = 9000  # characters per canvas, about 2K tokens: every reader pays for the whole page
AS_OF = re.compile(r'^\*As of .*$', re.M)


class Refused(Exception):
    pass


def get_json(url, timeout=3):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read(65536))


def run(argv, stdin=None, env=None, timeout=30):
    result = subprocess.run(argv, input=stdin, capture_output=True, text=True, env=env, timeout=timeout)
    if result.returncode:
        raise Refused(f'{argv[0]} {argv[1] if len(argv) > 1 else ""} failed: {(result.stderr or result.stdout).strip()[:200]}')
    return result.stdout


class Facts:
    """Each fact is read on its own, and an unreadable one says so instead of failing the page."""

    def __init__(self, root=ROOT, share=SHARE, mode=MODE, get=get_json, run=run):
        self.root, self.share, self.mode, self.get, self.run = Path(root), Path(share), Path(mode), get, run
        self.manifest = yaml.safe_load((self.root / 'crew/manifest.yaml').read_text())
        self.budgets = yaml.safe_load((self.root / 'crew/budgets.yaml').read_text())['profiles']
        self.channels = yaml.safe_load((self.root / 'crew/channels.yaml').read_text())['channels']

    def squadops_version(self):
        try:
            return f"{self.get(RUNTIME_HEALTH)['version']}, runtime API healthy"
        except Exception:
            return 'unavailable: the runtime API did not answer'

    def engine(self):
        models = sorted({a['model'] for a in self.manifest['agents'].values() if a.get('provider') == 'tensorfold'})
        name = ', '.join(f'`{m}`' for m in models) or 'no TensorFold role in the manifest'
        try:
            state = 'healthy' if self.get(self.manifest['tensorfold']['health']).get('status') == 'ok' else 'not healthy'
        except Exception:
            state = 'not answering'
        return f'TensorFold {name}, {state}'

    def spark_mode(self):
        try:
            mode = self.mode.read_text().strip()
        except OSError:
            return 'unknown'
        return {'development': 'development: local crew roles may run',
                'counted': 'counted: local crew roles are stopped'}.get(mode, mode)

    def campaigns(self):
        try:
            tracked = json.loads(self.run(['campaignctl', 'tracked'], stdin='{}'))
            open_ = []
            for row in tracked:
                status = json.loads(self.run(['campaignctl', 'status'], stdin=json.dumps({'campaign': row['id']})))
                status = status.get('result', status)
                if status.get('state') != 'completed':
                    open_.append(f"`{row.get('definition', row['id'])}` ({status.get('state')})")
        except Exception:
            return 'unavailable: campaignctl did not answer'
        return f"{len(tracked)} tracked, " + (', '.join(open_) + ' open' if open_ else 'none open')

    def budget(self, role):
        profile = self.budgets.get(self.manifest['agents'][role].get('budget_profile'), {})
        return {'provider_hard_limit': f"${profile.get('amount_usd')} a month, hard limit",
                'fixed': f"${profile.get('amount_usd')} a month, subscription",
                'local_inference': 'local, no metered spend',
                'excluded_existing_subscription': 'existing subscription'}.get(profile.get('type'), 'unknown')

    def crew(self):
        try:
            units = {row['role']: row for row in json.loads(self.run([CREWCTL, '--json', 'status']))['crew']}
        except Exception:
            units = None
        rows = ['| Role | Status | Backing | Budget |', '|---|---|---|---|']
        for role, agent in self.manifest['agents'].items():
            unit = (units or {}).get(role)
            if units is None:
                status = 'unknown: crewctl did not answer'
            elif not unit or not unit.get('installed'):
                status = 'not installed'
            elif unit.get('paused_until') or unit.get('paused_for'):
                status = f"paused by budget-watch until {unit.get('paused_until') or 'its configuration changes'}"
            elif unit.get('active') == 'active':
                status = 'running'
            elif unit.get('enabled') == 'disabled':
                status = 'not running: unit disabled'
            else:
                status = f"not running: {unit.get('active')}"
            rows.append(f"| {agent.get('display_name', role.title())} | {status} | "
                        f"{agent.get('model_label', agent.get('model'))} | {self.budget(role)} |")
        return '\n'.join(rows)

    def release(self):
        try:
            info = json.loads((self.root / 'RELEASE.json').read_text())
        except (OSError, ValueError):
            return 'unreleased tree'
        return f"`{info['commit'][:12]}` {info['subject']}"

    def nostromo_commit(self):
        try:
            return json.loads((self.root / 'RELEASE.json').read_text())['commit'][:12]
        except (OSError, ValueError, KeyError):
            return 'unreleased'

    def channel_map(self):
        rows = ['| Channel | Id | For |', '|---|---|---|']
        for c in self.channels:
            rows.append(f"| `#{c['name']}` | `{c['id'] or 'not yet created'}` | {c['purpose']} |")
        return '\n'.join(rows)

    def runbooks(self):
        rows = []
        for path in sorted(self.share.glob('*.md')):
            role = re.fullmatch(r'campaign-(\w+)\.md', path.name)
            if role:
                title = f'the persona the campaign review worker runs as {role[1].title()}'
            else:
                try:
                    title = next((line[2:].strip() for line in path.read_text().splitlines() if line.startswith('# ')), '')
                except OSError:
                    title = ''
            rows.append(f'- `{path.name}`' + (f': {title}' if title else ''))
        return '\n'.join(rows) or '- none installed'

    def channel_id(self, name, required=True):
        found = next((c['id'] for c in self.channels if c['name'] == name), None)
        if not found and required:
            raise Refused(f'#{name} has no id in crew/channels.yaml')
        return found


def render(template, facts, channel, now=None):
    """Fill only the facts this template names, so one canvas never pays for another's reads."""
    sources = {
        'channel_id': lambda: facts.channel_id(channel, required=False) or 'not-yet-created',
        'squadops_version': facts.squadops_version, 'engine': facts.engine, 'spark_mode': facts.spark_mode,
        'campaigns': facts.campaigns, 'crew': facts.crew, 'nostromo_release': facts.release,
        'nostromo_commit': facts.nostromo_commit, 'channel_map': facts.channel_map, 'runbooks': facts.runbooks,
        'as_of': lambda: time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(now)),
    }
    named = set(re.findall(r'\{\{(\w+)\}\}', template))
    unknown = sorted(named - set(sources))
    if unknown:
        raise Refused(f'{channel}: the template names unknown facts: {", ".join(unknown)}')
    values = {name: sources[name]() for name in named}
    page = re.sub(r'\{\{(\w+)\}\}', lambda m: values[m[1]], template)
    if len(page) > BUDGET:
        raise Refused(f'{channel}: the page is {len(page)} characters, over its {BUDGET} budget: shorten the template')
    return page


def same(old, new):
    """Equal apart from the as-of line, so a run that changes nothing publishes nothing."""
    return old is not None and AS_OF.sub('', old).strip() == AS_OF.sub('', new).strip()


def buzz_env(manifest):
    env = dict(os.environ)
    # An ssh command doesn't source the crew runtime's env.sh, which is where `buzz` lives.
    env['PATH'] = '/opt/nostromo/runtime/bin:' + env.get('PATH', '/usr/bin:/bin')
    env['BUZZ_RELAY_URL'] = manifest['relay']['url']
    env['BUZZ_PRIVATE_KEY'] = (Path.home() / '.config/nostromo/secrets/buzz.key').read_text().strip()
    return env


def publish(channel, page, env, run=run):
    current = run(['buzz', 'canvas', 'get', '--channel', channel], env=env).strip()
    current = None if current in ('', 'null') else current
    if same(current, page):
        return 'unchanged'
    run(['buzz', 'canvas', 'set', '--channel', channel, '--content', '-'], stdin=page, env=env)
    return 'published'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true', help='print the pages; publish nothing')
    parser.add_argument('--only', metavar='NAME', help='one canvas, by channel name')
    args = parser.parse_args(argv)
    facts = Facts()
    templates = sorted((ROOT / 'crew/canvases').glob('*.md'))
    if args.only:
        templates = [t for t in templates if t.stem == args.only]
        if not templates:
            raise Refused(f'no template crew/canvases/{args.only}.md')
    env = None if args.dry_run else buzz_env(facts.manifest)
    failed = False
    for template in templates:
        channel = template.stem
        try:
            page = render(template.read_text(), facts, channel)
            if args.dry_run:
                print(f'===== #{channel} ({len(page)} characters)\n{page}')
                continue
            result = publish(facts.channel_id(channel), page, env)
            print(f'#{channel} canvas {result} ({len(page)} characters)')
        except Refused as error:
            # One canvas failing never stops the others.
            print(f'sync-canvases: {error}', file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Refused as error:
        print(f'sync-canvases: {error}', file=sys.stderr)
        sys.exit(1)
