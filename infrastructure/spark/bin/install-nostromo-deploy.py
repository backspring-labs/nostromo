#!/usr/bin/python3 -I
"""One authenticated root setup. Does not give any crew account deployment rights."""
import grp
import hashlib
import importlib.util
import importlib.machinery
import json
import os
import pwd
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


def owner_snapshot(path, uid):
    for item in reversed((path, *path.parents)):
        info = item.lstat()
        if info.st_uid not in {0, uid} or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode):
            raise SystemExit('setup must come from a private owner snapshot, not the shared checkout')
        if not (stat.S_ISREG(info.st_mode) if item == path else stat.S_ISDIR(info.st_mode)):
            raise SystemExit('unexpected bootstrap path type')


def main():
    if os.getuid() != 0 or os.geteuid() != 0 or len(sys.argv) != 1:
        raise SystemExit('run this setup with sudo and no arguments')
    os.umask(0o077)
    repo = Path(__file__).resolve().parents[3]
    owner_uid = int(os.environ.get('SUDO_UID', '-1'))
    if owner_uid < 1000:
        raise SystemExit('run setup through the existing human owner sudo login')
    owner_snapshot(Path(__file__).absolute(), owner_uid)
    helper = Path('/usr/local/sbin/nostromo-deploy')
    # Bootstrap is an explicitly authenticated installation of reviewed source. All routine
    # invocations subsequently execute only this root-owned copy, with Python isolated mode.
    source = repo / 'infrastructure/spark/bin/nostromo-deploy.py'
    owner_snapshot(source, owner_uid)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 65536:
        raise SystemExit('invalid deployment helper source')
    for parent in reversed((helper.parent, *helper.parent.parents)):
        info = parent.lstat()
        if parent.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
            raise SystemExit('unsafe deployment helper parent')
    if helper.exists() or helper.is_symlink():
        info = helper.lstat()
        if helper.is_symlink() or not helper.is_file() or info.st_uid != 0 or info.st_mode & 0o022 or info.st_nlink != 1:
            raise SystemExit('unsafe existing deployment helper')
    # Never import a helper from the owner-writable checkout as root after installation.
    with tempfile.NamedTemporaryFile(dir=helper.parent, prefix='.nostromo-deploy-', delete=False) as temp:
        temporary = Path(temp.name)
        temp.write(source.read_bytes()); temp.flush(); os.fsync(temp.fileno()); os.fchmod(temp.fileno(), 0o755)
    os.replace(temporary, helper)
    loader = importlib.machinery.SourceFileLoader('nostromo_deploy_bootstrap', str(helper))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    deploy = importlib.util.module_from_spec(spec)
    loader.exec_module(deploy)
    deploy.trusted(deploy.CONFIG.parent, directory=True)
    broker_path = Path('/etc/nostromo/campaign-broker.json')
    deploy.trusted(broker_path)
    broker = json.loads(broker_path.read_bytes())
    owners = [int(uid) for uid, role in broker['callers'].items() if role == 'owner']
    if len(owners) != 1 or owners[0] != owner_uid:
        raise SystemExit('expected one existing non-root broker owner')
    owner = pwd.getpwuid(owners[0])
    if not re.fullmatch('[a-z_][a-z0-9_-]*', owner.pw_name) or owner.pw_name in {
            'nostromo', 'nostromo-broker', 'mother', 'brett', 'ripley', 'dallas', 'parker', 'ash', 'lambert'}:
        raise SystemExit('deployment belongs to the human owner, never a crew account')
    if (deploy.STATE / 'pending.json').exists():
        raise SystemExit('resolve the interrupted deployment before reconfiguring the helper')
    deploy.STATE.mkdir(mode=0o700, exist_ok=True)
    deploy.trusted(deploy.STATE, directory=True)
    units = deploy.unit_files(owner.pw_uid)
    installed = {**units, str(helper): deploy.sha(helper.read_bytes())}
    requires = {name: deploy.sha((repo / name).read_bytes()) for name in (
        'infrastructure/spark/bin/nostromo-deploy.py', 'infrastructure/spark/bin/install-nostromo-deploy.py')}
    for source_name, installed_path in deploy.PROTECTED.items():
        deploy.trusted(installed_path)
        raw = installed_path.read_bytes()
        if (repo / source_name).read_bytes() != raw:
            raise SystemExit('privileged entry point or polkit rule differs; run the authenticated infrastructure installer first')
        installed[str(installed_path)] = deploy.sha(raw)
        requires[source_name] = deploy.sha(raw)
    for target, checksum in units.items():
        path = Path(target)
        if target in deploy.STARTUP_DROPINS:
            source_name = deploy.STARTUP_DROPINS[target]
        elif path.parent == Path('/etc/systemd/system'):
            source_name = 'infrastructure/spark/systemd/' + path.name
        else:
            raise SystemExit('unit drop-ins/custom locations need explicit bootstrap support')
        source_checksum = deploy.sha((repo / source_name).read_bytes())
        # Crew harnesses consume the startup check but are never deployment targets. Keep
        # their safe installed template as-is, even if an older exit-status rule is live.
        # Actual unit bytes and reviewed source bytes are pinned independently thereafter.
        guard_template = path.name == 'nostromo@.service' and path.parent == Path('/etc/systemd/system')
        if not guard_template and source_checksum != checksum:
            raise SystemExit('installed campaign units differ from the reviewed source')
        requires[source_name] = source_checksum
    # Manifest changes may require root config changes; do not silently skip them.
    requires['crew/manifest.yaml'] = hashlib.sha256((repo / 'crew/manifest.yaml').read_bytes()).hexdigest()
    config = {'owner': owner.pw_name, 'uid': owner.pw_uid, 'gid': owner.pw_gid,
              'socket_gid': grp.getgrnam('nostromo').gr_gid, 'units': units,
              'requires': requires, 'installed': installed}
    deploy.health(config)
    runbook = repo / 'docs/runbooks/routine-deployment.md'
    owner_snapshot(runbook, owner_uid)
    deploy.atomic(deploy.SHARE / 'routine-deployment.md', runbook.read_bytes())
    deploy.atomic(deploy.CONFIG, (deploy.canonical(config) + '\n').encode(), 0o600)
    if not (deploy.STATE / 'current.json').exists():
        files = deploy.snapshot()
        deploy.record('current.json', {'commit': None, 'checksum': None,
                                      'file_sha256': {name: deploy.sha(raw) for name, raw in files.items()}})
    lock = deploy.STATE / 'deploy.lock'
    if not lock.exists():
        deploy.atomic(lock, b'', 0o600)
    deploy.trusted(lock)
    rule = f'{owner.pw_name} ALL=(root) NOPASSWD: NOSETENV: /usr/local/sbin/nostromo-deploy\n'
    rules_dir = Path('/etc/sudoers.d')
    deploy.trusted(rules_dir, directory=True)
    with tempfile.NamedTemporaryFile(dir=rules_dir, prefix='.nostromo-deploy-', delete=False) as temp:
        candidate = Path(temp.name)
        temp.write(rule.encode()); temp.flush(); os.fsync(temp.fileno()); os.fchmod(temp.fileno(), 0o440)
    try:
        subprocess.run(['/usr/sbin/visudo', '-cf', str(candidate)], check=True, cwd='/', env=deploy.ENV)
        deploy.atomic(rules_dir / 'nostromo-deploy', candidate.read_bytes(), 0o440)
        subprocess.run(['/usr/sbin/visudo', '-c'], check=True, cwd='/', env=deploy.ENV)
    finally:
        candidate.unlink(missing_ok=True)
    print('Installed owner-only nostromo-deploy. Routine app updates need no password; infrastructure changes still use the authenticated installer.')


if __name__ == '__main__':
    main()
