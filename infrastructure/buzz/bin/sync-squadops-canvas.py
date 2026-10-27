#!/usr/bin/python3 -I
"""Render the #squadops canvas from its template and live facts, and publish it as Mother.

Runs ON the Spark, as mother: her key publishes, and she co-owns the channel. From the Mac:

  infrastructure/buzz/bin/sync-squadops-canvas.sh [--dry-run]

deploy-spark.sh runs it after every successful deploy or rollback. It publishes only when the
content changed, not counting the as-of line, so the canvas history records changes rather than
runs. The prose is crew/canvases/squadops.md, changed by pull request. This adds only the facts:
- the SquadOps version, from the runtime API's /health;
- the engine and its health;
- the Spark mode;
- campaigns, through campaignctl as Mother;
- the live Nostromo release;
- the channel map, from crew/channels.yaml;
- the installed runbooks.
No model is involved, and nothing here writes outside Buzz.
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
BUDGET = 9000  # characters, about 2K tokens: every reader pays for the whole page
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

    def release(self):
        try:
            info = json.loads((self.root / 'RELEASE.json').read_text())
        except (OSError, ValueError):
            return 'unreleased tree', 'unreleased'
        return f"`{info['commit'][:12]}` {info['subject']}", info['commit'][:12]

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

    def channel_id(self, name='squadops', required=True):
        found = next((c['id'] for c in self.channels if c['name'] == name), None)
        if not found and required:
            raise Refused(f'#{name} has no id in crew/channels.yaml')
        return found


def render(template, facts, now=None):
    release, commit = facts.release()
    values = {
        'channel_id': facts.channel_id(required=False) or 'not-yet-created',
        'squadops_version': facts.squadops_version(),
        'engine': facts.engine(),
        'spark_mode': facts.spark_mode(),
        'campaigns': facts.campaigns(),
        'nostromo_release': release,
        'nostromo_commit': commit,
        'channel_map': facts.channel_map(),
        'runbooks': facts.runbooks(),
        'as_of': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(now)),
    }
    page = re.sub(r'\{\{(\w+)\}\}', lambda m: values.get(m[1], m[0]), template)
    unfilled = sorted(set(re.findall(r'\{\{(\w+)\}\}', page)))
    if unfilled:
        raise Refused(f'the template names unknown facts: {", ".join(unfilled)}')
    if len(page) > BUDGET:
        raise Refused(f'the page is {len(page)} characters, over its {BUDGET} budget: shorten the template')
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
    parser.add_argument('--dry-run', action='store_true', help='print the page; publish nothing')
    args = parser.parse_args(argv)
    facts = Facts()
    page = render((ROOT / 'crew/canvases/squadops.md').read_text(), facts)
    if args.dry_run:
        print(page)
        return 0
    result = publish(facts.channel_id(), page, buzz_env(facts.manifest))
    print(f'#squadops canvas {result} ({len(page)} characters)')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Refused as error:
        print(f'sync-squadops-canvas: {error}', file=sys.stderr)
        sys.exit(1)
