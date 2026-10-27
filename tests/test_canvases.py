"""The crew's canvases: crew/canvases/<channel>.md rendered with live facts, published as Mother."""
import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sync_canvases', ROOT / 'infrastructure/buzz/bin/sync-canvases.py')
canvas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(canvas)
TEMPLATE = (ROOT / 'crew/canvases/squadops.md').read_text()
NOSTROMO = (ROOT / 'crew/canvases/nostromo.md').read_text()


def healthy_get(url, timeout=3):
    if url == canvas.RUNTIME_HEALTH:
        return {'status': 'healthy', 'version': '2.4.0'}
    return {'status': 'ok'}


CREW = {'crew': [
    {'role': 'mother', 'installed': True, 'enabled': 'enabled', 'active': 'active', 'paused_until': None},
    {'role': 'ripley', 'installed': True, 'enabled': 'enabled', 'active': 'inactive', 'paused_until': '2026-11-01'},
    {'role': 'lambert', 'installed': True, 'enabled': 'disabled', 'active': 'inactive', 'paused_until': None},
]}


def campaigns(states, calls=None):
    def run(argv, stdin=None, env=None, timeout=30):
        if calls is not None:
            calls.append(argv)
        if argv[0] == canvas.CREWCTL:
            return json.dumps(CREW)
        if argv[1] == 'tracked':
            return json.dumps([{'id': cid, 'definition': f'def-{cid}'} for cid in states])
        return json.dumps({'result': {'state': states[json.loads(stdin)['campaign']]}})
    return run


@pytest.fixture
def facts(tmp_path):
    share = tmp_path / 'share'
    share.mkdir()
    (share / 'deployment.md').write_text('# Deploying Nostromo to the Spark\n')
    (share / 'campaign-ripley.md').write_text('# Ripley\n')
    mode = tmp_path / 'spark-mode'
    mode.write_text('development\n')
    return canvas.Facts(root=ROOT, share=share, mode=mode, get=healthy_get,
                        run=campaigns({'cmp_a': 'completed', 'cmp_b': 'executing'}))


def test_the_page_fills_every_fact_and_fits_its_budget(facts):
    page = canvas.render(TEMPLATE, facts, 'squadops', now=0)
    assert '{{' not in page and len(page) <= canvas.BUDGET
    assert '| SquadOps | 2.4.0, runtime API healthy |' in page
    assert 'TensorFold `qwen3.8-27b-tf-nvfp4`, healthy' in page
    assert '2 tracked, `def-cmp_b` (executing) open' in page
    assert '`deployment.md`: Deploying Nostromo to the Spark' in page
    assert '`campaign-ripley.md`: the persona the campaign review worker runs as Ripley' in page
    assert '*As of 1970-01-01 00:00 UTC.*' in page


def test_an_unreadable_fact_says_so_and_the_page_still_renders(tmp_path):
    def down(*_a, **_k):
        raise OSError('connection refused')
    facts = canvas.Facts(root=ROOT, share=tmp_path, mode=tmp_path / 'missing', get=down, run=down)
    page = canvas.render(TEMPLATE, facts, 'squadops', now=0)
    assert 'unavailable: the runtime API did not answer' in page
    assert 'TensorFold `qwen3.8-27b-tf-nvfp4`, not answering' in page
    assert 'unavailable: campaignctl did not answer' in page
    assert '| Spark mode | unknown |' in page and '- none installed' in page


def test_an_unknown_placeholder_or_an_oversized_page_is_refused(facts):
    with pytest.raises(canvas.Refused, match='unknown facts: no_such_fact'):
        canvas.render(TEMPLATE + '{{no_such_fact}}', facts, 'squadops')
    with pytest.raises(canvas.Refused, match='over its'):
        canvas.render(TEMPLATE + 'x' * canvas.BUDGET, facts, 'squadops')


def test_a_run_that_changes_nothing_publishes_nothing(facts):
    calls = []

    def run(argv, stdin=None, env=None, timeout=30):
        calls.append((argv, stdin, env))
        return calls_page[0] if argv[2] == 'get' else ''
    first = canvas.render(TEMPLATE, facts, 'squadops', now=0)
    calls_page = [first]
    later = canvas.render(TEMPLATE, facts, 'squadops', now=3600)
    assert first != later  # only the as-of line moved
    assert canvas.publish('chan', later, {'BUZZ_PRIVATE_KEY': 'k'}, run=run) == 'unchanged'
    assert [c[0][2] for c in calls] == ['get']
    calls_page[0] = 'null'
    assert canvas.publish('chan', later, {'BUZZ_PRIVATE_KEY': 'k'}, run=run) == 'published'
    argv, stdin, env = calls[-1]
    assert argv == ['buzz', 'canvas', 'set', '--channel', 'chan', '--content', '-'] and stdin == later
    assert all('k' not in arg for arg in argv), 'the key travels in the environment, never argv'


def test_the_channel_map_is_consistent_with_the_manifest():
    manifest = yaml.safe_load((ROOT / 'crew/manifest.yaml').read_text())
    channels = yaml.safe_load((ROOT / 'crew/channels.yaml').read_text())['channels']
    roles = set(manifest['agents']) | {'owner'}
    ids = [c['id'] for c in channels if c['id']]
    assert len(ids) == len(set(ids))
    for c in channels:
        assert set(c['members']) <= roles, c['name']
        assert c['id'] is None or re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', c['id']), c['name']


def test_the_constitution_points_at_the_canvas_by_id():
    squadops = next(c for c in yaml.safe_load((ROOT / 'crew/channels.yaml').read_text())['channels']
                    if c['name'] == 'squadops')
    if squadops['id']:
        assert squadops['id'] in (ROOT / 'instructions.md').read_text()


def test_the_nostromo_canvas_shows_each_roles_live_state_and_budget(facts):
    page = canvas.render(NOSTROMO, facts, 'nostromo', now=0)
    assert '{{' not in page and len(page) <= canvas.BUDGET
    assert '| Mother | running | Local Qwen 3.8 27B (TensorFold) | local, no metered spend |' in page
    assert '| Ripley | paused by budget-watch until 2026-11-01 | OpenAI GPT-5.6 Sol | $25 a month, hard limit |' in page
    assert '| Lambert | not running: unit disabled |' in page
    assert '| Parker | not installed |' in page  # absent from crewctl's answer
    assert '| Ash | not installed | OpenAI GPT-6 Astra (subscription) | $20 a month, subscription |' in page


def test_a_canvas_reads_only_the_facts_it_names(tmp_path):
    calls = []
    facts = canvas.Facts(root=ROOT, share=tmp_path, mode=tmp_path / 'm', get=healthy_get,
                         run=campaigns({'cmp_a': 'completed'}, calls))
    canvas.render(NOSTROMO, facts, 'nostromo', now=0)
    assert [c[0] for c in calls] == [canvas.CREWCTL], 'the #nostromo page never queries campaigns'


def test_an_unanswering_crewctl_marks_every_role_unknown(tmp_path):
    def down(*_a, **_k):
        raise OSError('no crewctl')
    facts = canvas.Facts(root=ROOT, share=tmp_path, mode=tmp_path / 'm', get=healthy_get, run=down)
    page = canvas.render(NOSTROMO, facts, 'nostromo', now=0)
    assert page.count('unknown: crewctl did not answer') == len(facts.manifest['agents'])


def test_every_template_names_a_channel_with_an_id():
    channels = {c['name']: c['id'] for c in yaml.safe_load((ROOT / 'crew/channels.yaml').read_text())['channels']}
    for template in (ROOT / 'crew/canvases').glob('*.md'):
        assert channels.get(template.stem), f'{template.name} has no channel id in crew/channels.yaml'


def test_the_mac_wrapper_passes_no_empty_argument(tmp_path):
    """printf '%q ' with no arguments emits '', which the script rejected on 2026-10-27's first deploy."""
    import os, subprocess
    fake = tmp_path / 'ssh'
    fake.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$CAPTURE"\n')
    fake.chmod(0o755)
    env = {**os.environ, 'PATH': f"{tmp_path}:{os.environ['PATH']}", 'CAPTURE': str(tmp_path / 'argv')}
    wrapper = ROOT / 'infrastructure/buzz/bin/sync-canvases.sh'
    subprocess.run([str(wrapper)], env=env, check=True)
    assert (tmp_path / 'argv').read_text().splitlines()[-1].endswith('sync-canvases.py')
    subprocess.run([str(wrapper), '--only', 'nostromo'], env=env, check=True)
    assert (tmp_path / 'argv').read_text().splitlines()[-1].endswith('sync-canvases.py --only nostromo ')
