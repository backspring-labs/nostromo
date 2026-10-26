"""Exercise the privileged updater with a virtual root filesystem and fake systemd only."""
import base64
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BIN = Path(__file__).resolve().parents[1] / 'infrastructure/spark/bin'


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), BIN / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def updater():
    return load('nostromo-deploy')


def envelope(updater, extra=None):
    files = {name: base64.b64encode(b'# source\n').decode() for name in updater.REQUIRED}
    files.update(extra or {})
    return {'version': 1, 'commit': 'a' * 40, 'requires': {'unit': 'pinned'}, 'files': files}


def decode(updater, value):
    raw = updater.canonical(value).encode()
    return updater.decode(raw, 'a' * 40, updater.sha(raw), {'unit': 'pinned'})


@pytest.mark.parametrize('name', [
    '/etc/sudoers', '../etc/sudoers', 'runtime/campaigns/../../escape.py',
    'runtime/campaigns/nested/code.py', 'runtime/campaigns/nostr_keys.py',
    'infrastructure/spark/bin/nostromo-deploy.py', 'crew/manifest.yaml',
    'infrastructure/spark/systemd/nostromo-campaign-broker.service'])
def test_release_cannot_write_outside_fixed_application_paths(updater, name):
    with pytest.raises(updater.Refused, match='allowlist'):
        decode(updater, envelope(updater, {name: base64.b64encode(b'bad').decode()}))


@pytest.mark.parametrize('fault', ['digest', 'commit', 'pins', 'missing', 'oversize', 'binary', 'duplicate'])
def test_malformed_or_incompatible_bundle_is_refused_before_mutation(updater, fault):
    value = envelope(updater)
    if fault == 'commit': value['commit'] = 'b' * 40
    if fault == 'pins': value['requires'] = {'unit': 'changed'}
    if fault == 'missing': value['files'].pop(next(iter(updater.REQUIRED)))
    if fault == 'oversize': value['files']['runtime/campaigns/core.py'] = base64.b64encode(b'x' * (updater.MAX_FILE + 1)).decode()
    if fault == 'binary': value['files']['runtime/campaigns/core.py'] = base64.b64encode(b'\x00').decode()
    raw = updater.canonical(value).encode()
    if fault == 'duplicate': raw = raw.replace(b'"version":1', b'"version":1,"version":1')
    checksum = '0' * 64 if fault == 'digest' else updater.sha(raw)
    with pytest.raises(updater.Refused):
        updater.decode(raw, 'a' * 40, checksum, {'unit': 'pinned'})


@pytest.fixture
def host(updater, tmp_path, monkeypatch):
    # Only this test's filesystem is made to look root-owned. Production has no test flag.
    original_stat = Path.lstat
    nonroot = set()
    def root_stat(path):
        values = list(original_stat(path))
        values[4] = 1000 if path in nonroot else 0
        if path != tmp_path and tmp_path not in path.parents:
            values[0] &= ~0o022  # Shared test-runner ancestors are outside this virtual host.
        return os.stat_result(values)
    monkeypatch.setattr(Path, 'lstat', root_stat)
    package, share, state = (tmp_path / name for name in ('package', 'share', 'state'))
    for path in (package, share, state): path.mkdir(mode=0o700)
    fixed = {name: (package if path.parent == updater.PACKAGE else share) / path.name
             for name, path in updater.FIXED.items()}
    monkeypatch.setattr(updater, 'PACKAGE', package)
    monkeypatch.setattr(updater, 'SHARE', share)
    monkeypatch.setattr(updater, 'STATE', state)
    monkeypatch.setattr(updater, 'FIXED', fixed)
    old = {name: b'# original code\n' for name in updater.REQUIRED}
    for name, raw in old.items(): updater.atomic(updater.destination(name), raw)
    updater.record('current.json', {'commit': 'b' * 40, 'checksum': None})
    states = {unit: 'inactive' for unit in updater.SERVICES}
    states.update({unit: 'active' for unit in updater.DAEMONS})
    states.update({unit: 'active' for unit in updater.TIMERS})
    states[updater.TIMERS[-1]] = 'inactive'  # Preserve a deliberately stopped timer.
    initial = dict(states)
    calls = []
    def control(action, *units):
        calls.append((action, units))
        assert all(unit in states for unit in units)
        for unit in units:
            if action in {'stop', 'start'}: states[unit] = 'active' if action == 'start' else 'inactive'
            else: raise AssertionError('unexpected privileged operation')
        return ''
    monkeypatch.setattr(updater, 'systemctl', control)
    monkeypatch.setattr(updater, 'properties', lambda unit: {'ActiveState': states[unit]})
    monkeypatch.setattr(updater, 'verify_pins', lambda config: None)
    monkeypatch.setattr(updater, 'health', lambda config: None)
    new = {name: b'# updated code\n' for name in old}
    new['runtime/campaigns/new_module.py'] = b"raise RuntimeError('must never be imported as root')\n"
    return updater, old, new, states, initial, calls, nonroot


@pytest.mark.parametrize('fault', ['symlink', 'writable', 'owner', 'hardlink'])
def test_deployment_targets_reject_unsafe_files(host, tmp_path, fault):
    updater, _, _, _, _, _, nonroot = host
    target = updater.PACKAGE / 'core.py'
    if fault == 'symlink':
        target.unlink(); target.symlink_to(tmp_path / 'outside')
    if fault == 'writable': target.chmod(0o666)
    if fault == 'owner': nonroot.add(target)
    if fault == 'hardlink': os.link(target, tmp_path / 'alias')
    with pytest.raises(updater.Refused): updater.trusted(target)


def test_success_installs_data_preserves_timers_and_never_starts_a_review(host):
    updater, old, new, states, initial, calls, _ = host
    result = updater.deploy({}, new, 'a' * 40, 'c' * 64)
    assert updater.snapshot() == new and states == initial
    assert result['commit'] == 'a' * 40 and result['file_sha256']['runtime/campaigns/core.py'] == updater.sha(new['runtime/campaigns/core.py'])
    backup = updater.read_record('backup-' + 'c' * 64 + '.json')
    assert {name: base64.b64decode(raw) for name, raw in backup['files'].items()} == old
    assert not (updater.STATE / 'pending.json').exists()
    assert all(path.stat().st_mode & 0o077 == 0 for path in updater.STATE.glob('*.json'))
    assert all(set(units) <= set(updater.DAEMONS) | set(updater.TIMERS) for action, units in calls)
    calls.clear()
    assert updater.deploy({}, new, 'a' * 40, 'c' * 64)['unchanged'] is True
    assert calls == []


def test_busy_paid_worker_prevents_update_and_keeps_its_process_running(host):
    updater, old, new, states, initial, calls, _ = host
    unit = 'nostromo-campaign-review@ripley.service'
    states[unit] = initial[unit] = 'active'
    with pytest.raises(updater.Refused, match='worker is active'):
        updater.deploy({}, new, 'a' * 40, 'c' * 64)
    assert updater.snapshot() == old and states == initial
    assert all(unit not in units for action, units in calls)
    assert not (updater.STATE / 'pending.json').exists()


@pytest.mark.parametrize('fault', ['copy', 'health'])
def test_failed_update_restores_previous_code_and_timer_state(host, monkeypatch, fault):
    updater, old, new, states, initial, _, _ = host
    original = updater.atomic
    failed = []
    def atomic(path, raw, *args):
        if fault == 'copy' and path.name == 'core.py' and raw == new['runtime/campaigns/core.py'] and not failed:
            failed.append(True); raise OSError('injected interrupted copy')
        original(path, raw, *args)
    def health(config):
        if fault == 'health' and not failed:
            failed.append(True); raise updater.Refused('injected failed health check')
    monkeypatch.setattr(updater, 'atomic', atomic)
    monkeypatch.setattr(updater, 'health', health)
    with pytest.raises((OSError, updater.Refused)):
        updater.deploy({}, new, 'a' * 40, 'c' * 64)
    assert updater.snapshot() == old and states == initial
    assert updater.read_record('current.json')['commit'] == 'b' * 40
    assert updater.read_record('last-failure.json')['code_restored'] is True
    assert not (updater.STATE / 'pending.json').exists()


def test_interrupted_stop_is_durable_and_does_not_restart_unknown_work(host, monkeypatch):
    updater, old, new, states, _, _, _ = host
    original = updater.systemctl
    def interrupted(action, *units):
        original(action, *units)
        if action == 'stop' and tuple(units) == updater.DAEMONS:
            raise KeyboardInterrupt()
    monkeypatch.setattr(updater, 'systemctl', interrupted)
    with pytest.raises(KeyboardInterrupt): updater.deploy({}, new, 'a' * 40, 'c' * 64)
    assert updater.snapshot() == old
    assert updater.read_record('pending.json')['commit'] == 'a' * 40
    assert all(states[unit] == 'inactive' for unit in updater.TIMERS)
    with pytest.raises(updater.Refused, match='interrupted deployment'):
        updater.deploy({}, new, 'a' * 40, 'c' * 64)


def test_failed_rollback_keeps_pending_marker_and_timers_stopped(host, monkeypatch):
    updater, old, new, states, _, _, _ = host
    def unhealthy(config): raise updater.Refused('unhealthy')
    monkeypatch.setattr(updater, 'health', unhealthy)
    with pytest.raises(updater.Refused): updater.deploy({}, new, 'a' * 40, 'c' * 64)
    assert updater.snapshot() == old and (updater.STATE / 'pending.json').exists()
    assert all(states[unit] == 'inactive' for unit in updater.TIMERS)


def test_timer_restoration_failure_remains_visible_as_an_interrupted_deployment(host, monkeypatch):
    updater, _, new, _, _, _, _ = host
    original = updater.systemctl
    def failed(action, *units):
        if action == 'start' and units == (updater.TIMERS[0],):
            raise updater.Refused('timer could not be restored')
        return original(action, *units)
    monkeypatch.setattr(updater, 'systemctl', failed)
    with pytest.raises(updater.Refused, match='timer could not be restored'):
        updater.deploy({}, new, 'a' * 40, 'c' * 64)
    assert updater.read_record('current.json')['commit'] == 'a' * 40
    assert (updater.STATE / 'pending.json').exists()


def test_changed_unit_pin_blocks_deployment(updater, monkeypatch):
    monkeypatch.setattr(updater, 'unit_files', lambda uid: {'/etc/systemd/system/example.service': 'changed'})
    with pytest.raises(updater.Refused, match='unit definitions changed'):
        updater.verify_pins({'uid': 1000, 'units': {'/etc/systemd/system/example.service': 'approved'}})


def test_health_probe_drops_to_owner_uid_and_uses_only_fixed_read_command(updater, monkeypatch):
    calls = []
    monkeypatch.setattr(updater, 'systemctl', lambda *args: None)
    monkeypatch.setattr(updater, 'command', lambda args, **kwargs: calls.append((args, kwargs)))
    updater.probe_health({'uid': 1000, 'gid': 1000, 'socket_gid': 1001})
    args, options = calls[0]
    assert args[:3] == ['/usr/bin/python3', '-I', '-c']
    assert options == {'user': 1000, 'group': 1000, 'extra_groups': [1001]}
    assert 'shared-ready' in args[3]
    compile(args[3], '<fixed health probe>', 'exec')


def test_only_configured_owner_can_use_the_installed_helper(host, tmp_path, monkeypatch):
    updater = host[0]
    config = tmp_path / 'config.json'
    updater.atomic(config, json.dumps({'owner': 'jladd', 'uid': 1000}).encode(), 0o600)
    monkeypatch.setattr(updater, 'CONFIG', config)
    monkeypatch.setattr(os, 'getuid', lambda: 0)
    monkeypatch.setattr(os, 'geteuid', lambda: 0)
    monkeypatch.setattr(sys, 'argv', ['nostromo-deploy', 'status'])
    monkeypatch.setenv('SUDO_USER', 'mother'); monkeypatch.setenv('SUDO_UID', '1000')
    with pytest.raises(updater.Refused, match='configured owner'): updater.main()
    monkeypatch.setenv('SUDO_USER', 'jladd'); monkeypatch.setenv('SUDO_UID', '1001')
    with pytest.raises(updater.Refused, match='configured owner'): updater.main()
    monkeypatch.setenv('SUDO_UID', '1000')
    monkeypatch.setattr(sys, 'argv', ['nostromo-deploy', '--bootstrap'])
    with pytest.raises(updater.Refused, match='usage:'): updater.main()


def test_owner_status_reports_actual_code_and_service_states(host, tmp_path, monkeypatch, capsys):
    updater, _, new, states, _, _, _ = host
    updater.deploy({}, new, 'a' * 40, 'c' * 64)
    config = tmp_path / 'config.json'
    updater.atomic(config, json.dumps({'owner': 'jladd', 'uid': 1000}).encode(), 0o600)
    monkeypatch.setattr(updater, 'CONFIG', config)
    monkeypatch.setattr(os, 'getuid', lambda: 0); monkeypatch.setattr(os, 'geteuid', lambda: 0)
    monkeypatch.setenv('SUDO_USER', 'jladd'); monkeypatch.setenv('SUDO_UID', '1000')
    monkeypatch.setattr(sys, 'argv', ['nostromo-deploy', 'status'])
    updater.main()
    result = json.loads(capsys.readouterr().out)
    assert result['files_match'] is True and result['interrupted'] is False and result['services'] == states


def test_setup_rejects_group_writable_or_other_account_bootstrap_paths(host, tmp_path):
    installer = load('install-nostromo-deploy')
    directory = tmp_path / 'bootstrap'; directory.mkdir(mode=0o700)
    script = directory / 'setup.py'; script.write_text('# reviewed setup\n')
    installer.owner_snapshot(script, 1000)
    directory.chmod(0o775)
    with pytest.raises(SystemExit, match='private owner snapshot'):
        installer.owner_snapshot(script, 1000)
    directory.chmod(0o700)
    host[-1].add(script)  # Virtual UID 1000; somebody else's bootstrap is not trusted.
    with pytest.raises(SystemExit, match='private owner snapshot'):
        installer.owner_snapshot(script, 1002)


def test_pinned_units_refuse_root_hooks_and_wrong_role(host, tmp_path, monkeypatch):
    updater = host[0]
    fragment = tmp_path / 'unit.service'
    fragment.write_text('[Service]\nUser=mother\nNoNewPrivileges=yes\nExecStart=+/bin/sh\n')
    props = {'FragmentPath': str(fragment), 'DropInPaths': '', 'NoNewPrivileges': 'yes', 'AmbientCapabilities': ''}
    monkeypatch.setattr(updater.pwd, 'getpwnam', lambda user: SimpleNamespace(pw_uid=1001, pw_gid=1001))
    monkeypatch.setattr(updater.os, 'getgrouplist', lambda user, gid: [gid])
    monkeypatch.setattr(updater.grp, 'getgrgid', lambda gid: SimpleNamespace(gr_name='nostromo'))
    monkeypatch.setattr(updater.grp, 'getgrnam', lambda group: SimpleNamespace(gr_name=group))
    monkeypatch.setattr(updater, 'properties', lambda unit: {**props, 'User': updater.SERVICES.get(unit, '')})
    with pytest.raises(updater.Refused, match='privileged service hooks'): updater.unit_files()
    fragment.write_text('[Service]\nExecStart=\\\n +/bin/sh\n')
    with pytest.raises(updater.Refused, match='continued service directives'): updater.unit_files()
    fragment.write_text('[Service]\nExecStart=/usr/bin/python3 -I /fixed.py\n')
    monkeypatch.setattr(updater, 'properties', lambda unit: {**props, 'User': 'root'})
    with pytest.raises(updater.Refused, match='service identity'): updater.unit_files()
    monkeypatch.setattr(updater, 'properties', lambda unit: {**props, 'User': updater.SERVICES.get(unit, ''), 'Group': 'docker'})
    with pytest.raises(updater.Refused, match='privileged service account'): updater.unit_files()


def test_release_packaging_reads_exact_git_commit_and_refuses_tracked_symlinks(tmp_path):
    packer = load('deploy-release')
    repo = tmp_path / 'repo'; repo.mkdir()
    def git(*args): return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True).stdout.decode().strip()
    git('init', '-q')
    bootstrap_scripts = {'infrastructure/spark/bin/nostromo-deploy.py', 'infrastructure/spark/bin/install-nostromo-deploy.py'}
    for name in packer.format.REQUIRED | packer.format.privileged_sources() | bootstrap_scripts:
        path = repo / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('# committed\n')
    git('add', '.')
    git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture')
    commit = git('rev-parse', 'HEAD')
    core = repo / 'runtime/campaigns/core.py'
    core.write_text('# uncommitted must not travel\n')
    result = json.loads(packer.bundle(repo, commit))
    assert base64.b64decode(result['files']['runtime/campaigns/core.py']) == b'# committed\n'
    private = tmp_path / 'bootstrap'
    (repo / 'infrastructure/spark/bin/nostromo-deploy.py').write_text('# uncommitted\n')
    packer.bootstrap(repo, commit, private)
    assert (private / 'infrastructure/spark/bin/nostromo-deploy.py').read_bytes() == b'# committed\n'
    assert private.stat().st_mode & 0o077 == 0
    assert all(path.stat().st_mode & 0o077 == 0 for path in private.rglob('*') if path.is_file())
    with pytest.raises(FileExistsError): packer.bootstrap(repo, commit, private)
    core.unlink(); core.symlink_to(tmp_path / 'outside')
    git('add', '.')
    git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'symlink fixture')
    with pytest.raises(packer.format.Refused, match='regular tracked files'):
        packer.bundle(repo, git('rev-parse', 'HEAD'))
