"""Release deploys: real Git repositories in a temporary directory, a fake systemd and socket."""
import importlib.util
import json
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / 'infrastructure/spark/bin'
SYSTEMD = ROOT / 'infrastructure/spark/systemd'


def load():
    spec = importlib.util.spec_from_file_location('nostromo_release', BIN / 'nostromo-release.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rel = load()

BASE = {
    'crew/manifest.yaml': 'agents:\n',
    'infrastructure/spark/bin/launch-role.sh': '#!/usr/bin/env bash\necho launch\n',
    'infrastructure/spark/bin/nostromo-release.py': '"""stand-in"""\n',
    'runtime/campaigns/__init__.py': '',
    'runtime/campaigns/service.py': 'VALUE = 1\n',
}


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@t', *args],
                          check=True, capture_output=True, text=True).stdout.strip()


class Upstream:
    """Stands in for GitHub: a bare repository the Spark fetches from, fed by a work tree."""

    def __init__(self, tmp):
        self.bare = tmp / 'github.git'
        self.work = tmp / 'work'
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(self.bare)], check=True)
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.work)], check=True)
        git(self.work, 'remote', 'add', 'origin', str(self.bare))

    def commit(self, files, message='change', branch='main'):
        if branch != 'main':
            git(self.work, 'checkout', '-q', '-B', branch)
        for name, content in files.items():
            path = self.work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        git(self.work, 'add', '-A')
        git(self.work, 'commit', '-q', '-m', message)
        git(self.work, 'push', '-q', 'origin', branch)
        sha = git(self.work, 'rev-parse', 'HEAD')
        if branch != 'main':
            git(self.work, 'checkout', '-q', 'main')
        return sha


class FakeSpark(rel.Spark):
    def __init__(self, tmp, github, adopted=True):
        linked = tmp / 'usr-local-lib-nostromo-campaigns'
        if adopted:
            os.symlink(tmp / 'opt/current/runtime/campaigns', linked)
        (tmp / 'opt').mkdir()
        super().__init__(root=tmp / 'opt', github=str(github), linked=linked)
        self.units = {unit: 'active' for unit in (*rel.DAEMONS, *rel.TIMERS)}
        self.units.update({unit: 'inactive' for unit in rel.WORKERS})
        self.calls, self.bad, self.clock, self.harness_start = [], set(), 1000.0, {}

    def systemctl(self, *args):
        self.calls.append(args)
        verb, unit = args[0], args[-1]
        if verb == 'stop':
            self.units[unit] = 'inactive'
        elif verb in ('start', 'restart'):
            self.units[unit] = 'active'
        elif verb == 'show':
            return '0'
        return ''

    def state(self, unit):
        return self.units.get(unit, 'inactive')

    def probe(self):
        return rel.live(self) not in self.bad

    def harnesses(self):
        return list(self.harness_start)

    def started(self, unit):
        return self.harness_start[unit]

    def sleep(self, seconds):
        self.clock += seconds

    def now(self):
        return self.clock


@pytest.fixture
def upstream(tmp_path):
    up = Upstream(tmp_path)
    up.first = up.commit(BASE, 'first')
    return up


@pytest.fixture
def spark(tmp_path, upstream):
    return FakeSpark(tmp_path, upstream.bare)


def deploy(spark, *argv):
    return rel.main(['deploy', *argv], spark=spark)


def records(spark):
    return [json.loads(line) for line in spark.log.read_text().splitlines()]


def test_deploys_the_head_of_main_read_only_and_records_it(spark, upstream):
    deploy(spark)
    assert rel.live(spark) == upstream.first
    release = spark.releases / upstream.first
    assert json.loads((release / 'RELEASE.json').read_text())['merged'] is True
    writable = [p for p in [release, *release.rglob('*')] if p.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)]
    assert writable == []
    assert records(spark)[-1]['result'] == 'live'
    assert all(('restart', unit) in spark.calls for unit in rel.DAEMONS)
    # Timers were paused for the switch and are running again.
    assert all(('stop', timer) in spark.calls and spark.units[timer] == 'active' for timer in rel.TIMERS)


def test_a_second_deploy_keeps_the_first_as_previous(spark, upstream):
    deploy(spark)
    second = upstream.commit({'runtime/campaigns/service.py': 'VALUE = 2\n'})
    deploy(spark)
    assert (rel.live(spark), rel.live(spark, spark.previous)) == (second, upstream.first)


def test_redeploying_the_live_release_changes_nothing(spark, upstream):
    deploy(spark)
    spark.calls.clear()
    deploy(spark)
    assert not any(call[0] in ('stop', 'restart') for call in spark.calls)


def test_an_unmerged_commit_is_refused(spark, upstream):
    trial = upstream.commit({'notes.md': 'x\n'}, branch='feat/trial')
    with pytest.raises(rel.Refused, match='not on GitHub main'):
        deploy(spark, trial)
    assert rel.live(spark) is None


def test_an_owner_approved_trial_deploys_and_says_so(spark, upstream):
    trial = upstream.commit({'notes.md': 'x\n'}, branch='feat/trial')
    deploy(spark, trial, '--allow-unmerged', 'idle-pool trial')
    assert rel.live(spark) == trial
    info = rel.status(spark)
    assert (info['merged'], info['reason']) == (False, 'idle-pool trial')
    assert records(spark)[-1]['merged'] is False


@pytest.mark.parametrize('name', ['main', 'HEAD', 'feat/trial', 'origin/main'])
def test_branch_names_are_not_deployable(spark, upstream, name):
    with pytest.raises(rel.Refused, match='hex id'):
        deploy(spark, name)


def test_a_commit_github_does_not_have_is_refused(spark, upstream):
    with pytest.raises(rel.Refused):
        deploy(spark, 'deadbeef' * 5)


@pytest.mark.parametrize('files,match', [
    ({'runtime/campaigns/broken.py': 'def (:\n'}, 'broken.py'),
    ({'infrastructure/spark/bin/tool': '#!/usr/bin/python3\nif True print(1)\n'}, 'tool'),
    ({'infrastructure/spark/bin/run.sh': '#!/usr/bin/env bash\nif then fi\n'}, 'run.sh'),
    ({'runtime/campaigns/needs.py': 'import nostromo_module_that_does_not_exist\n'}, 'do not import'),
])
def test_a_release_that_cannot_run_never_goes_live(spark, upstream, files, match):
    deploy(spark)
    upstream.commit(files)
    with pytest.raises(rel.Refused, match=match):
        deploy(spark)
    assert rel.live(spark) == upstream.first
    assert [p.name for p in spark.releases.iterdir()] == [upstream.first]


def test_a_release_missing_its_launcher_is_refused(spark, upstream):
    subprocess.run(['git', '-C', str(upstream.work), 'rm', '-q', 'infrastructure/spark/bin/launch-role.sh'], check=True)
    upstream.commit({}, 'drop launcher')
    with pytest.raises(rel.Refused, match='launch-role.sh'):
        deploy(spark)


def test_an_unhealthy_release_rolls_back_and_resumes_timers(spark, upstream):
    deploy(spark)
    bad = upstream.commit({'runtime/campaigns/service.py': 'VALUE = 3\n'})
    spark.bad.add(bad)
    with pytest.raises(rel.Refused, match='is live again'):
        deploy(spark)
    assert rel.live(spark) == upstream.first
    assert records(spark)[-1] == {**records(spark)[-1], 'commit': bad, 'result': 'rolled back'}
    assert all(spark.units[timer] == 'active' for timer in rel.TIMERS)


def test_a_failed_restart_rolls_back_too(spark, upstream):
    deploy(spark)
    upstream.commit({'runtime/campaigns/service.py': 'VALUE = 4\n'})
    original = spark.systemctl

    def systemctl(*args):
        if args[0] == 'restart' and rel.live(spark) != upstream.first:
            raise rel.Refused('polkit said no')
        return original(*args)
    spark.systemctl = systemctl
    with pytest.raises(rel.Refused, match='is live again'):
        deploy(spark)
    assert rel.live(spark) == upstream.first


def test_a_running_worker_is_waited_for_never_killed(spark, upstream):
    deploy(spark)
    upstream.commit({'runtime/campaigns/service.py': 'VALUE = 5\n'})
    spark.units['nostromo-campaign-review@ripley.service'] = 'activating'
    with pytest.raises(rel.Refused, match='still running'):
        deploy(spark)
    assert rel.live(spark) == upstream.first
    assert ('stop', 'nostromo-campaign-review@ripley.service') not in spark.calls
    assert all(spark.units[timer] == 'active' for timer in rel.TIMERS)


def test_a_spark_not_yet_adopted_stages_but_will_not_switch(tmp_path, upstream):
    spark = FakeSpark(tmp_path, upstream.bare, adopted=False)
    assert rel.main(['stage'], spark=spark) == 0
    assert (spark.releases / upstream.first / 'RELEASE.json').is_file()
    with pytest.raises(rel.Refused, match='install-release-deploy.sh'):
        deploy(spark)


def test_rollback_returns_to_the_previous_release(spark, upstream):
    deploy(spark)
    upstream.commit({'runtime/campaigns/service.py': 'VALUE = 6\n'})
    deploy(spark)
    rel.main(['rollback'], spark=spark)
    assert rel.live(spark) == upstream.first
    assert records(spark)[-1]['reason'] == 'rollback'


def test_prune_keeps_live_previous_and_the_newest(spark, upstream):
    shas = [upstream.first]
    for n in range(7):
        shas.append(upstream.commit({'runtime/campaigns/service.py': f'VALUE = {10 + n}\n'}))
    for sha in shas:
        rel.main(['stage', sha], spark=spark)
    for age, sha in enumerate(shas):
        os.utime(spark.releases / sha, (2_000_000_000 + age, 2_000_000_000 + age))
    rel.point(spark.current, f'releases/{shas[0]}')
    rel.point(spark.previous, f'releases/{shas[1]}')
    rel.prune(spark)
    assert {p.name for p in spark.releases.iterdir()} == set(shas[-rel.KEEP:]) | {shas[0], shas[1]}


def test_status_names_harnesses_older_than_the_live_release(spark, upstream):
    deploy(spark)
    switched = spark.current.lstat().st_mtime
    spark.harness_start = {'nostromo@ripley.service': int(switched) - 60, 'nostromo@mother.service': int(switched) + 60}
    info = rel.status(spark)
    assert info['stale_harnesses'] == ['nostromo@ripley.service']
    assert (info['live'], info['behind_main'], info['adopted']) == (upstream.first, 0, True)


def test_the_supervisor_runs_it_never_root(spark, monkeypatch):
    monkeypatch.setattr(os, 'geteuid', lambda: 0)
    with pytest.raises(rel.Refused, match='never as root'):
        rel.main(['status'], spark=spark)


# The infrastructure around the tool must agree with it.

def test_polkit_lets_the_supervisor_restart_exactly_the_units_it_deploys():
    rule = (SYSTEMD / '48-nostromo-release.rules').read_text()
    listed = set(re.findall(r'"(nostromo-[^"]+\.(?:service|timer))"', rule))
    assert listed == set(rel.DAEMONS) | set(rel.TIMERS)
    assert 'subject.user !== "nostromo"' in rule and 'isInGroup' not in rule


def unit_files():
    return sorted(SYSTEMD.glob('*.service')) + sorted(SYSTEMD.glob('*.conf'))


def test_no_unit_runs_release_code_as_root():
    for path in unit_files():
        text = path.read_text()
        if path.suffix == '.conf':
            continue  # drop-ins inherit User= from the nostromo@ template, checked below
        if re.search(r'^Exec\w+=.*(/opt/nostromo|/usr/local/lib/nostromo)', text, re.M):
            user = re.search(r'^User=(\S+)', text, re.M)
            assert user and user[1] != 'root', path.name
            assert not re.search(r'^Exec\w+=[-@:]*[+!]', text, re.M), path.name


def test_the_installer_links_everything_the_units_and_crew_read():
    installer = (BIN / 'install-release-deploy.sh').read_text()
    entrypoints = set(re.search(r'ENTRYPOINTS=\(([^)]*)\)', installer)[1].split())
    runbooks = set(re.search(r'RUNBOOKS=\(([^)]*)\)', installer)[1].split())
    used = set()
    for path in unit_files():
        used |= set(re.findall(r'/usr/local/lib/nostromo/([\w-]+\.py)', path.read_text()))
    assert used and used <= entrypoints
    assert all((BIN / name).is_file() for name in entrypoints)
    assert all((ROOT / 'docs/runbooks' / name).is_file() for name in runbooks)
    shared = set()
    for path in [*ROOT.glob('crew/**/*.md'), ROOT / 'instructions.md', *BIN.glob('*')]:
        if path.is_file():
            shared |= set(re.findall(r'/usr/local/share/nostromo/([\w.-]+\.md)', path.read_text(errors='ignore')))
    assert shared <= runbooks | {'campaign-ripley.md', 'campaign-dallas.md'}, shared
    assert rel.DAEMONS == tuple(re.search(r'DAEMONS=\(([^)]*)\)', installer)[1].split())
    assert rel.TIMERS == tuple(re.search(r'TIMERS=\(([^)]*)\)', installer)[1].split())


def test_the_campaign_installer_no_longer_copies_code():
    installer = (BIN / 'install-campaign-control.sh').read_text()
    assert 'runtime/campaigns/*.py' not in installer
    assert not re.search(r'install .*/usr/local/(lib|share)/nostromo|install .*/usr/local/bin/campaignctl', installer)
