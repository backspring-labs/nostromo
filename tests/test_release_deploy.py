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
    def __init__(self, tmp, github, adopted=True, root=None):
        linked = tmp / 'usr-local-lib-nostromo-campaigns'
        if adopted:
            os.symlink(tmp / 'opt/current/runtime/campaigns', linked)
        root = root or tmp / 'opt'
        root.mkdir(parents=True)
        super().__init__(root=root, github=str(github), linked=linked)
        self.units = {unit: 'active' for unit in (*rel.DAEMONS, *rel.TIMERS)}
        self.units.update({unit: 'inactive' for unit in rel.WORKERS})
        self.calls, self.bad, self.clock, self.harness_start = [], set(), 1000.0, {}
        # Which release each running unit loaded (None: the pre-release layout), and units whose
        # next start fails once.
        self.loaded, self.fail_start = {}, set()
        self.fail_always, self.fail_stop, self.fail_reload = set(), set(), False

    def systemctl(self, *args):
        self.calls.append(args)
        verb, units = args[0], args[1:]
        if verb == 'daemon-reload' and self.fail_reload:
            raise rel.Refused('systemctl daemon-reload: injected failure')
        for unit in units:
            if verb in ('start', 'stop') and unit in (self.fail_always if verb == 'start' else self.fail_stop):
                raise rel.Refused(f'systemctl {verb} {unit}: injected persistent failure')
            if verb == 'stop':
                self.units[unit] = 'inactive'
            elif verb == 'start' and unit in self.fail_start:
                self.fail_start.discard(unit)
                raise rel.Refused(f'systemctl start {unit}: injected failure')
            # Like systemd: start on a running unit does nothing; restart always reloads it.
            elif verb == 'restart' or (verb == 'start' and self.units.get(unit) != 'active'):
                self.units[unit] = 'active'
                self.loaded[unit] = rel.live(self) if self.current.is_symlink() else None
        if verb == 'show':
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
    with pytest.raises(rel.Refused, match='install-release-deploy.py'):
        deploy(spark)


def test_rollback_returns_to_the_previous_release(spark, upstream):
    deploy(spark)
    upstream.commit({'runtime/campaigns/service.py': 'VALUE = 6\n'})
    deploy(spark)
    rel.main(['rollback'], spark=spark)
    assert rel.live(spark) == upstream.first
    assert records(spark)[-1]['reason'] == 'rollback'


def test_rollback_will_not_quietly_restore_an_unmerged_trial(spark, upstream):
    trial = upstream.commit({'notes.md': 'x\n'}, branch='feat/trial')
    deploy(spark, trial, '--allow-unmerged', 'idle-pool trial')
    later = upstream.commit({'runtime/campaigns/service.py': 'VALUE = 7\n'})
    deploy(spark)
    assert rel.live(spark, spark.previous) == trial
    with pytest.raises(rel.Refused, match='not on GitHub main'):
        rel.main(['rollback'], spark=spark)
    assert rel.live(spark) == later
    rel.main(['rollback', '--allow-unmerged', 'owner re-approved the trial'], spark=spark)
    assert rel.live(spark) == trial
    assert records(spark)[-1]['reason'] == 'rollback: owner re-approved the trial'


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


def load_installer():
    spec = importlib.util.spec_from_file_location('install_release_deploy', BIN / 'install-release-deploy.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adopt = load_installer()


def test_the_installer_links_everything_the_units_and_crew_read():
    used = set()
    for path in unit_files():
        used |= set(re.findall(r'/usr/local/lib/nostromo/([\w-]+\.py)', path.read_text()))
    assert used and used <= set(adopt.ENTRYPOINTS)
    assert all((BIN / name).is_file() for name in adopt.ENTRYPOINTS)
    assert all((ROOT / 'docs/runbooks' / name).is_file() for name in adopt.RUNBOOKS)
    shared = set()
    for path in [*ROOT.glob('crew/**/*.md'), ROOT / 'instructions.md', *BIN.glob('*')]:
        if path.is_file():
            shared |= set(re.findall(r'/usr/local/share/nostromo/([\w.-]+\.md)', path.read_text(errors='ignore')))
    assert shared <= set(adopt.RUNBOOKS) | {f'campaign-{role}.md' for role in adopt.PERSONAS}, shared


def test_the_campaign_installer_no_longer_copies_code():
    installer = (BIN / 'install-campaign-control.sh').read_text()
    assert 'runtime/campaigns/*.py' not in installer
    assert not re.search(r'install .*/usr/local/(lib|share)/nostromo|install .*/usr/local/bin/campaignctl', installer)


# The one-time adoption, against a fake filesystem root, the same fake systemd, and a real staged release.

import pwd  # noqa: E402

UNIT_FILES = {
    'infrastructure/spark/systemd/48-nostromo-release.rules': '// rule\n',
    'infrastructure/spark/systemd/nostromo@.service': '[Service]\nUser=%i\nSuccessExitStatus=75\n',
}
OLD = {
    'opt/nostromo/nostromo-src/old-tree.txt': 'working tree\n',
    'usr/local/lib/nostromo/campaigns/core.py': 'old copy\n',
    'usr/local/lib/nostromo/campaign-broker.py': 'old entry point\n',
    'usr/local/bin/campaignctl': 'old client\n',
    'usr/local/share/nostromo/campaign-control.md': 'old runbook\n',
    'etc/systemd/system/nostromo@.service': '[Service]\nUser=%i\n',
    'etc/sudoers.d/nostromo-deploy': 'jladd ALL=(root) NOPASSWD: /usr/local/sbin/nostromo-deploy\n',
    'usr/local/sbin/nostromo-deploy': 'helper\n',
    'etc/nostromo/deploy.json': '{}\n',
    'var/lib/nostromo-deploy/current.json': '{}\n',
}


def snapshot(top):
    """Everything outside the backups and the release store, so a rollback can be compared exactly."""
    out = {}
    for path in sorted(top.rglob('*')):
        name = str(path.relative_to(top))
        if name.startswith(('var/backups', 'opt/nostromo/backups/', 'opt/nostromo/releases')):
            continue
        out[name] = ('link', os.readlink(path)) if path.is_symlink() else (
            ('file', path.read_bytes()) if path.is_file() else 'dir')
    return out


@pytest.fixture
def site(tmp_path, upstream):
    sha = upstream.commit(UNIT_FILES, 'units')
    fs = tmp_path / 'fs'
    spark = FakeSpark(tmp_path, upstream.bare, adopted=False, root=fs / 'opt/nostromo')
    rel.main(['stage'], spark=spark)
    for name, content in OLD.items():
        (fs / name).parent.mkdir(parents=True, exist_ok=True)
        (fs / name).write_text(content)
    for name in ('opt/nostromo/backups', 'etc/polkit-1/rules.d', 'var/backups'):
        (fs / name).mkdir(parents=True, exist_ok=True)
    visudo, status = [], {'visudo': 0}

    def run(argv, **_):
        visudo.append(argv)
        return subprocess.CompletedProcess(argv, status['visudo'])
    me = pwd.getpwuid(os.getuid()).pw_name
    make = lambda cls=adopt.Adopt: cls(sha, spark, root=fs, source=upstream.work, supervisor=me, run=run, stamp='T')
    return type('Site', (), {'sha': sha, 'fs': fs, 'spark': spark, 'make': staticmethod(make), 'visudo': visudo,
                            'status': status})


def test_adoption_links_everything_into_current_and_retires_the_helper(site):
    site.make().adopt()
    fs, opt = site.fs, site.fs / 'opt/nostromo'
    assert os.readlink(opt / 'current') == f'releases/{site.sha}'
    assert os.readlink(opt / 'nostromo-src') == 'current'
    assert (opt / 'backups/nostromo-src-pre-release-T/old-tree.txt').read_text() == 'working tree\n'
    assert os.readlink(fs / 'usr/local/lib/nostromo/campaigns') == '/opt/nostromo/current/runtime/campaigns'
    assert os.readlink(fs / 'usr/local/lib/nostromo/campaign-broker.py') == '/opt/nostromo/current/infrastructure/spark/bin/campaign-broker.py'
    assert os.readlink(fs / 'usr/local/bin/campaignctl') == '/opt/nostromo/current/infrastructure/spark/bin/campaignctl'
    assert os.readlink(fs / 'usr/local/share/nostromo/campaign-ripley.md') == '/opt/nostromo/current/crew/personas/ripley.md'
    assert (fs / 'etc/systemd/system/nostromo@.service').read_text() == UNIT_FILES['infrastructure/spark/systemd/nostromo@.service']
    assert (fs / 'etc/polkit-1/rules.d/48-nostromo-release.rules').is_file()
    assert not any((fs / name).exists() for name in ('etc/sudoers.d/nostromo-deploy', *adopt.RETIRED))
    assert (fs / 'var/backups/nostromo-release-adopt-T/etc_sudoers.d_nostromo-deploy').is_file()
    assert site.visudo == [['visudo', '-c']]
    assert all(site.spark.units[unit] == 'active' for unit in (*rel.DAEMONS, *rel.TIMERS))


@pytest.mark.parametrize('failing', ['current and nostromo-src', '/usr/local links', 'polkit rule and crew unit',
                                     'retire nostromo-deploy', 'start', 'resume timers'])
def test_a_failure_after_the_drain_puts_everything_back(site, failing):
    before = snapshot(site.fs)

    class Failing(adopt.Adopt):
        def step(self, name):
            if name == failing:
                raise RuntimeError(f'injected failure at {name}')

    with pytest.raises(RuntimeError, match='injected'):
        site.make(Failing).adopt()
    assert snapshot(site.fs) == before
    assert all(site.spark.units[unit] == 'active' for unit in (*rel.DAEMONS, *rel.TIMERS))


def test_a_failed_sudoers_check_puts_everything_back(site):
    before = snapshot(site.fs)
    site.status['visudo'] = 1
    with pytest.raises(adopt.Refused, match='visudo'):
        site.make().adopt()
    assert snapshot(site.fs) == before
    assert all(site.spark.units[unit] == 'active' for unit in (*rel.DAEMONS, *rel.TIMERS))


def test_unhealthy_daemons_on_the_new_layout_put_everything_back(site):
    before = snapshot(site.fs)
    site.spark.bad.add(site.sha)
    with pytest.raises(adopt.Refused, match='healthy'):
        site.make().adopt()
    assert snapshot(site.fs) == before
    assert all(site.spark.units[unit] == 'active' for unit in (*rel.DAEMONS, *rel.TIMERS))


def test_a_staged_release_that_differs_from_github_is_refused_before_anything_stops(site):
    target = site.fs / 'opt/nostromo/releases' / site.sha / 'crew/manifest.yaml'
    target.chmod(0o644)
    target.write_text('agents: {tampered: true}\n')
    target.chmod(0o444)
    with pytest.raises(adopt.Refused, match='differs from GitHub'):
        site.make().adopt()
    assert not any(call[0] == 'stop' for call in site.spark.calls)


def test_a_running_worker_stops_adoption_before_anything_changes(site):
    before = snapshot(site.fs)
    site.spark.units['nostromo-campaign-launch.service'] = 'activating'
    with pytest.raises(adopt.Refused, match='still running'):
        site.make().adopt()
    assert snapshot(site.fs) == before
    assert all(site.spark.units[timer] == 'active' for timer in rel.TIMERS)


def test_bytecode_in_the_clone_is_ignored_but_planted_bytecode_in_a_release_is_not(site, upstream):
    cache = upstream.work / 'infrastructure/spark/bin/__pycache__'
    cache.mkdir(parents=True)
    (cache / 'nostromo-release.cpython-312.pyc').write_bytes(b'from importing the installer')
    site.make().check()
    planted = site.fs / 'opt/nostromo/releases' / site.sha / 'runtime/campaigns'
    planted.chmod(0o755)
    (planted / '__pycache__').mkdir()
    (planted / '__pycache__/service.cpython-312.pyc').write_bytes(b'not the reviewed source')
    planted.chmod(0o555)
    with pytest.raises(adopt.Refused, match='differs from GitHub'):
        site.make().check()


def restored(site, before):
    assert snapshot(site.fs) == before
    assert all(site.spark.units[unit] == 'active' for unit in (*rel.DAEMONS, *rel.TIMERS))
    # Running again on the old layout, not still holding the new release's code.
    assert all(site.spark.loaded.get(unit) is None for unit in rel.DAEMONS)


def test_a_timer_that_will_not_resume_undoes_the_adoption(site):
    before = snapshot(site.fs)
    site.spark.fail_start.add('nostromo-campaign-advance.timer')
    with pytest.raises(adopt.Refused, match='would not start'):
        site.make().adopt()
    restored(site, before)


def test_daemons_that_started_on_the_new_layout_are_restarted_on_the_old(site):
    before = snapshot(site.fs)
    site.spark.bad.add(site.sha)
    with pytest.raises(adopt.Refused, match='healthy'):
        site.make().adopt()
    restored(site, before)


def test_a_successful_adoption_leaves_the_daemons_on_the_release(site):
    site.make().adopt()
    assert all(site.spark.loaded[unit] == site.sha for unit in rel.DAEMONS)


def test_a_timer_that_will_not_restart_after_a_healthy_deploy_is_recorded_and_reported(spark, upstream):
    deploy(spark)
    second = upstream.commit({'runtime/campaigns/service.py': 'VALUE = 8\n'})
    spark.fail_start.add('nostromo-campaign-launch.timer')
    with pytest.raises(rel.Refused, match='live and healthy. These timers did not restart and are stopped: nostromo-campaign-launch.timer'):
        deploy(spark)
    assert rel.live(spark) == second
    assert records(spark)[-1]['timers_not_restarted'] == ['nostromo-campaign-launch.timer']
    # Every other paused timer was still started.
    assert all(spark.units[t] == 'active' for t in rel.TIMERS if t != 'nostromo-campaign-launch.timer')



# Every recovery path reports what it could not restore; none claims success it did not verify.

def test_a_timer_that_never_restarts_makes_adoption_recovery_say_it_is_incomplete(site, capsys):
    site.spark.fail_always.add('nostromo-campaign-advance.timer')
    with pytest.raises(adopt.Refused, match='would not start'):
        site.make().adopt()
    err = capsys.readouterr().err
    assert 'INCOMPLETE' in err and 'nostromo-campaign-advance.timer is inactive' in err
    assert 'every unit is running as before' not in err


def test_a_daemon_that_will_not_stop_is_reported_as_maybe_running_the_new_release(site, capsys):
    site.spark.bad.add(site.sha)
    original = site.spark.systemctl

    def systemctl(*args):
        # Stops succeed during the drain; the broker refuses to stop once the new layout is up.
        if args[0] == 'stop' and 'nostromo-campaign-broker.service' in args and site.spark.current.is_symlink():
            raise rel.Refused('systemctl stop nostromo-campaign-broker.service: injected')
        return original(*args)
    site.spark.systemctl = systemctl
    with pytest.raises(adopt.Refused, match='healthy'):
        site.make().adopt()
    err = capsys.readouterr().err
    assert 'INCOMPLETE' in err and 'may still be running the new release' in err


def test_a_failed_daemon_reload_during_recovery_is_reported(site, capsys):
    class Failing(adopt.Adopt):
        def step(self, name):
            if name == 'retire nostromo-deploy':
                self.spark.fail_reload = True
                raise RuntimeError('injected')
    with pytest.raises(RuntimeError):
        site.make(Failing).adopt()
    err = capsys.readouterr().err
    assert 'INCOMPLETE' in err and 'daemon-reload' in err


def test_a_clean_recovery_says_so(site, capsys):
    site.spark.bad.add(site.sha)
    with pytest.raises(adopt.Refused):
        site.make().adopt()
    assert 'every unit is running as before' in capsys.readouterr().err


def test_a_timer_that_will_not_stop_during_the_drain_restarts_the_ones_already_stopped(spark, upstream):
    deploy(spark)
    upstream.commit({'runtime/campaigns/service.py': 'VALUE = 9\n'})
    spark.fail_stop.add(rel.TIMERS[2])
    with pytest.raises(rel.Refused, match='nothing changed'):
        deploy(spark)
    assert rel.live(spark) == upstream.first
    assert all(spark.units[timer] == 'active' for timer in rel.TIMERS)


def test_a_drain_timeout_names_a_timer_that_would_not_restart(spark, upstream):
    deploy(spark)
    upstream.commit({'runtime/campaigns/service.py': 'VALUE = 10\n'})
    spark.units['nostromo-campaign-review@dallas.service'] = 'activating'
    spark.fail_always.add('nostromo-campaign-window.timer')
    with pytest.raises(rel.Refused, match='still running.*did not restart and are stopped: nostromo-campaign-window.timer'):
        deploy(spark)


def test_an_unhealthy_deploy_still_reports_timers_that_would_not_restart(spark, upstream):
    deploy(spark)
    bad = upstream.commit({'runtime/campaigns/service.py': 'VALUE = 11\n'})
    spark.bad.add(bad)
    spark.fail_always.add('nostromo-campaign-launch.timer')
    with pytest.raises(rel.Refused, match='is live again. These timers did not restart and are stopped: nostromo-campaign-launch.timer'):
        deploy(spark)
    assert records(spark)[-1]['result'] == 'rolled back'
    assert records(spark)[-1]['timers_not_restarted'] == ['nostromo-campaign-launch.timer']


def test_an_unexpected_error_mid_switch_restarts_timers_and_says_what_is_live(spark, upstream, monkeypatch):
    deploy(spark)
    upstream.commit({'runtime/campaigns/service.py': 'VALUE = 12\n'})
    monkeypatch.setattr(rel, 'point', lambda *a: (_ for _ in ()).throw(OSError(28, 'No space left on device')))
    with pytest.raises(rel.Refused, match=f'stopped by OSError.*Live now: {upstream.first[:12]}'):
        deploy(spark)
    assert all(spark.units[timer] == 'active' for timer in rel.TIMERS)
    assert records(spark)[-1]['result'] == 'error: OSError'


def test_a_release_that_cannot_be_pruned_does_not_fail_a_good_deploy(spark, upstream, monkeypatch, capsys):
    for n in range(rel.KEEP + 2):
        upstream.commit({'runtime/campaigns/service.py': f'VALUE = {100 + n}\n'})
        rel.main(['stage'], spark=spark)
    monkeypatch.setattr(rel, 'remove', lambda path: (_ for _ in ()).throw(PermissionError(13, 'Permission denied')))
    assert deploy(spark) == 0
    assert 'prune_problems' in json.loads(capsys.readouterr().out.strip().splitlines()[-1])
