"""The #squadops canvas: rendered from crew/canvases/squadops.md and live facts, published as Mother."""
import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sync_canvas', ROOT / 'infrastructure/buzz/bin/sync-squadops-canvas.py')
canvas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(canvas)
TEMPLATE = (ROOT / 'crew/canvases/squadops.md').read_text()


def healthy_get(url, timeout=3):
    if url == canvas.RUNTIME_HEALTH:
        return {'status': 'healthy', 'version': '2.4.0'}
    return {'status': 'ok'}


def campaigns(states):
    def run(argv, stdin=None, env=None, timeout=30):
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
    page = canvas.render(TEMPLATE, facts, now=0)
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
    page = canvas.render(TEMPLATE, facts, now=0)
    assert 'unavailable: the runtime API did not answer' in page
    assert 'TensorFold `qwen3.8-27b-tf-nvfp4`, not answering' in page
    assert 'unavailable: campaignctl did not answer' in page
    assert '| Spark mode | unknown |' in page and '- none installed' in page


def test_an_unknown_placeholder_or_an_oversized_page_is_refused(facts):
    with pytest.raises(canvas.Refused, match='unknown facts: no_such_fact'):
        canvas.render(TEMPLATE + '{{no_such_fact}}', facts)
    with pytest.raises(canvas.Refused, match='over its'):
        canvas.render(TEMPLATE + 'x' * canvas.BUDGET, facts)


def test_a_run_that_changes_nothing_publishes_nothing(facts):
    calls = []

    def run(argv, stdin=None, env=None, timeout=30):
        calls.append((argv, stdin, env))
        return calls_page[0] if argv[2] == 'get' else ''
    first = canvas.render(TEMPLATE, facts, now=0)
    calls_page = [first]
    later = canvas.render(TEMPLATE, facts, now=3600)
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
