#!/usr/bin/python3 -I
"""Root-owned routine updater. Never import or execute release content as root."""
import base64
import fcntl
import grp
import hashlib
import json
import os
import pwd
import re
import stat
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

CONFIG = Path('/etc/nostromo/deploy.json')
STATE = Path('/var/lib/nostromo-deploy')
PACKAGE = Path('/usr/local/lib/nostromo/campaigns')
SHARE = Path('/usr/local/share/nostromo')
MAX_BUNDLE = 8 * 1024 * 1024
MAX_FILE = 512 * 1024
MAX_TOTAL = 4 * 1024 * 1024
FIXED = {
    'infrastructure/buzz/bin/nostr_keys.py': PACKAGE / 'nostr_keys.py',
    'docs/runbooks/campaign-control.md': SHARE / 'campaign-control.md',
    'docs/runbooks/shared-inference.md': SHARE / 'shared-inference.md',
    'docs/runbooks/routine-deployment.md': SHARE / 'routine-deployment.md',
    'crew/personas/ripley.md': SHARE / 'campaign-ripley.md',
    'crew/personas/dallas.md': SHARE / 'campaign-dallas.md',
}
REQUIRED = set(FIXED) | {'runtime/campaigns/' + name for name in (
    '__init__.py', 'core.py', 'cli.py', 'service.py', 'watch.py', 'worker.py',
    'advance.py', 'host.py', 'launch_worker.py')}
SERVICES = {
    'nostromo-campaign-broker.service': 'nostromo-broker',
    'nostromo-campaign-watch.service': 'mother',
    'nostromo-campaign-review@ripley.service': 'ripley',
    'nostromo-campaign-review@dallas.service': 'dallas',
    'nostromo-campaign-advance.service': 'mother',
    'nostromo-campaign-launch.service': 'mother',
    'nostromo-campaign-window.service': 'nostromo-broker',
}
DAEMONS = ('nostromo-campaign-broker.service', 'nostromo-campaign-watch.service')
TIMERS = tuple(name.replace('.service', '.timer') for name in SERVICES if name not in DAEMONS)
GUARDS = {'nostromo@mother.service': 'mother', 'nostromo@brett.service': 'brett'}
IDENTITIES = {**SERVICES, **GUARDS}
STARTUP_DROPINS = {
    '/etc/systemd/system/nostromo@' + role + '.service.d/20-campaign-window.conf':
    'infrastructure/spark/systemd/20-campaign-window.conf' for role in ('mother', 'brett')}
ENTRYPOINTS = {
    'infrastructure/spark/bin/' + name: Path('/usr/local/lib/nostromo') / name
    for name in ('campaign-broker.py', 'campaign-watch.py', 'campaign-review.py',
                 'campaign-advance.py', 'campaign-launch.py', 'campaign-window.py', 'campaign-window-check.py')}
ENTRYPOINTS['infrastructure/spark/bin/campaignctl'] = Path('/usr/local/bin/campaignctl')
PROTECTED = {**ENTRYPOINTS, 'infrastructure/spark/systemd/50-nostromo-campaign-window.rules':
             Path('/etc/polkit-1/rules.d/50-nostromo-campaign-window.rules')}
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8', 'SYSTEMD_PAGER': '', 'SYSTEMD_COLORS': '0'}


class Refused(Exception):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refused('duplicate JSON field')
        result[key] = value
    return result


def trusted(path, directory=False):
    """Every component must be root-owned, non-symlink, and not group/other writable."""
    path = Path(path)
    if not path.is_absolute():
        raise Refused('trusted paths must be absolute')
    for item in reversed((path, *path.parents)):
        info = item.lstat()
        if info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode):
            raise Refused('unsafe ownership, permissions, or symlink in deployment path')
        want_directory = item != path or directory
        if not (stat.S_ISDIR(info.st_mode) if want_directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1):
            raise Refused('unexpected deployment path type')


def destination(name):
    if name in FIXED:
        return FIXED[name]
    match = re.fullmatch(r'runtime/campaigns/([a-z_][a-z0-9_]*\.py)', name)
    if match and match[1] != 'nostr_keys.py':
        return PACKAGE / match[1]
    raise Refused('release contains a path outside the application allowlist')


def privileged_sources():
    return set(PROTECTED) | {'crew/manifest.yaml', *STARTUP_DROPINS.values(),
        'infrastructure/spark/bin/nostromo-deploy.py', 'infrastructure/spark/bin/install-nostromo-deploy.py'} | {
        'infrastructure/spark/systemd/' + re.sub(r'@[^.]+\.', '@.', unit)
        for unit in (*IDENTITIES, *TIMERS)}


def decode(raw, commit, checksum, pins):
    if not re.fullmatch('[0-9a-f]{40}', commit) or not re.fullmatch('[0-9a-f]{64}', checksum):
        raise Refused('exact commit and SHA-256 are required')
    if len(raw) > MAX_BUNDLE or sha(raw) != checksum:
        raise Refused('release size or checksum mismatch')
    value = json.loads(raw, object_pairs_hook=unique)
    if (not isinstance(value, dict) or set(value) != {'version', 'commit', 'requires', 'files'} or
            type(value['version']) is not int or value['version'] != 1 or value['commit'] != commit):
        raise Refused('invalid release envelope')
    if value['requires'] != pins:
        raise Refused('privileged infrastructure differs; authenticated setup is required')
    files = value['files']
    if not isinstance(files, dict) or not REQUIRED <= files.keys() or len(files) > 64:
        raise Refused('release must contain a complete bounded application')
    decoded, total = {}, 0
    for name, encoded in files.items():
        destination(name)
        if not isinstance(encoded, str) or len(encoded) > (MAX_FILE + 2) // 3 * 4:
            raise Refused('release file exceeds its bound')
        content = base64.b64decode(encoded, validate=True)
        if len(content) > MAX_FILE or b'\x00' in content:
            raise Refused('release must contain bounded text files')
        content.decode('utf-8')
        total += len(content)
        decoded[name] = content
    if total > MAX_TOTAL:
        raise Refused('release exceeds its total content bound')
    return decoded


def command(args, **kwargs):
    result = subprocess.run(args, env=ENV, cwd='/', capture_output=True, timeout=30, **kwargs)
    if result.returncode:
        raise Refused('deployment command failed; inspect the fixed service journals')
    return result.stdout.decode().strip()


def systemctl(*args):
    return command(['/usr/bin/systemctl', *args])


def properties(unit):
    output = systemctl('show', unit, '--property=User,Group,SupplementaryGroups,FragmentPath,DropInPaths,ActiveState,NoNewPrivileges,AmbientCapabilities')
    return dict(line.split('=', 1) for line in output.splitlines())


def unit_files(owner_uid=None):
    result = {}
    for unit in (*IDENTITIES, *TIMERS):
        props = properties(unit)
        if unit in IDENTITIES and (props['User'] != IDENTITIES[unit] or
                props.get('NoNewPrivileges') != 'yes' or props.get('AmbientCapabilities')):
            raise Refused('campaign service identity differs from its admitted role')
        if unit in IDENTITIES:
            account = pwd.getpwnam(props['User'])
            groups = {grp.getgrgid(gid).gr_name for gid in os.getgrouplist(props['User'], account.pw_gid)}
            for group in (props.get('Group', '') + ' ' + props.get('SupplementaryGroups', '')).split():
                groups.add((grp.getgrgid(int(group)) if group.isdigit() else grp.getgrnam(group)).gr_name)
            if account.pw_uid in {0, owner_uid} or groups & {'root', 'sudo', 'docker', 'lxd', 'disk', 'adm'}:
                raise Refused('campaign deployment cannot target a privileged service account')
        paths = [props['FragmentPath'], *props['DropInPaths'].split()]
        if not paths[0]:
            raise Refused('campaign infrastructure must already be installed')
        for path in paths:
            trusted(path)
            raw = Path(path).read_bytes()
            if re.search(r'\\\s*\n', raw.decode()):
                raise Refused('continued service directives require authenticated review')
            # Never let application updates become privileged lifecycle hooks.
            for line in raw.decode().splitlines():
                if re.match(r'\s*(PermissionsStartOnly\s*=\s*(yes|true|1)|Exec\w+\s*=\s*[-:@]*[+!])', line):
                    raise Refused('privileged service hooks cannot consume deployable application code')
            result[path] = sha(raw)
    return result


def verify_pins(config):
    if unit_files(config['uid']) != config['units']:
        raise Refused('installed unit definitions changed; authenticated setup is required')
    for target, expected in config['installed'].items():
        trusted(target)
        actual = sha(target.read_bytes())
        if actual != expected:
            raise Refused(f'installed pin changed: {target} (expected {expected}, found {actual})')


def snapshot():
    trusted(PACKAGE, directory=True)
    trusted(SHARE, directory=True)
    cache = PACKAGE / '__pycache__'
    if cache.exists() or cache.is_symlink():
        trusted(cache, directory=True)
        for path in cache.glob('*.pyc'):
            trusted(path)
    paths = dict(FIXED)
    for path in PACKAGE.glob('*.py'):
        if path.name != 'nostr_keys.py':
            name = 'runtime/campaigns/' + path.name
            destination(name)
            paths[name] = path
    result = {}
    for name, path in paths.items():
        trusted(path)
        if path.stat().st_size > MAX_FILE:
            raise Refused('installed application exceeds the backup file bound')
        result[name] = path.read_bytes()
    if len(result) > 64 or sum(map(len, result.values())) > MAX_TOTAL:
        raise Refused('installed application exceeds the backup bound')
    return result


def atomic(path, raw, mode=0o644):
    trusted(path.parent, directory=True)
    if path.exists() or path.is_symlink():
        trusted(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.deploy-', delete=False) as handle:
        temporary = Path(handle.name)
        try:
            os.fchmod(handle.fileno(), mode)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def install_files(files):
    previous = snapshot()
    for name, raw in files.items():
        atomic(destination(name), raw)
    for name in previous.keys() - files.keys():
        destination(name).unlink()
    cache = PACKAGE / '__pycache__'
    if cache.exists() or cache.is_symlink():
        trusted(cache, directory=True)
        for path in cache.glob('*.pyc'):
            trusted(path)
            path.unlink()


def probe_health(config):
    for unit in DAEMONS:
        systemctl('is-active', '--quiet', unit)
    # Authenticate the socket probe as its existing owner UID, never as root or a crew role.
    probe = '''import json,socket
with socket.socket(socket.AF_UNIX) as s:
 s.settimeout(5); s.connect('/run/nostromo-campaigns/control.sock')
 s.sendall(b'{"command":"shared-ready","args":{}}\\n')
 with s.makefile('rb') as stream: raw=stream.readline(65537)
 value=json.loads(raw)
 assert value.get('ok') is True and value['result']['contract']==1
'''
    command(['/usr/bin/python3', '-I', '-c', probe], user=config['uid'], group=config['gid'],
            extra_groups=[config['socket_gid']])


def health(config):
    deadline = time.monotonic() + 15
    while True:
        try:
            probe_health(config)
            return
        except (Refused, OSError, subprocess.TimeoutExpired):
            if time.monotonic() >= deadline:
                raise Refused('campaign health check failed') from None
            time.sleep(0.2)


def record(name, value):
    atomic(STATE / name, (canonical(value) + '\n').encode(), 0o600)


def read_record(name):
    path = STATE / name
    trusted(path)
    if path.stat().st_size > MAX_BUNDLE:
        raise Refused('deployment state exceeds its bound')
    return json.loads(path.read_bytes(), object_pairs_hook=unique)


def deploy(config, files, commit, checksum):
    if (STATE / 'pending.json').exists():
        raise Refused('interrupted deployment requires authenticated recovery; workers were left stopped')
    verify_pins(config)
    for unit in DAEMONS:
        if properties(unit)['ActiveState'] != 'active':
            raise Refused('campaign daemons must be healthy before a routine deployment')
    previous = snapshot()
    current = read_record('current.json')
    if current.get('checksum') == checksum and previous == files:
        health(config)
        return {**current, 'unchanged': True}
    active = [unit for unit in TIMERS if properties(unit)['ActiveState'] == 'active']
    backup = {'files': {name: base64.b64encode(raw).decode() for name, raw in previous.items()}, 'current': current,
              'attempt': {'commit': commit, 'checksum': checksum, 'at_ns': time.time_ns()}}
    record('backup-' + checksum + '.json', backup)
    record('pending.json', {'commit': commit, 'checksum': checksum, 'backup': 'backup-' + checksum + '.json', 'timers': active})
    restore_timers = True
    try:
        for unit in active:
            systemctl('stop', unit)
        for unit in SERVICES:
            if unit not in DAEMONS and properties(unit)['ActiveState'] not in {'inactive', 'failed'}:
                raise Refused('a campaign worker is active; wait for completion before deploying')
        restore_timers = False
        systemctl('stop', *DAEMONS)
        try:
            install_files(files)
            systemctl('start', *DAEMONS)
            health(config)
        except BaseException:
            systemctl('stop', *DAEMONS)
            install_files(previous)
            systemctl('start', *DAEMONS)
            health(config)
            record('last-failure.json', {'commit': commit, 'checksum': checksum, 'code_restored': True})
            restore_timers = True
            raise
        result = {'commit': commit, 'checksum': checksum, 'deployed_at_ns': time.time_ns(),
                  'file_sha256': {name: sha(raw) for name, raw in files.items()}}
        record('current.json', result)
        restore_timers = True
        return result
    finally:
        # A killed process/failed rollback leaves pending.json and timers off for inspection.
        if restore_timers:
            for unit in active:
                systemctl('start', unit)
            (STATE / 'pending.json').unlink()


def main():
    os.umask(0o077)
    if os.getuid() != 0 or os.geteuid() != 0:
        raise Refused('deployment requires the installed owner-only sudo command')
    trusted(CONFIG)
    trusted(STATE, directory=True)
    config = json.loads(CONFIG.read_bytes(), object_pairs_hook=unique)
    if os.environ.get('SUDO_UID') != str(config['uid']) or os.environ.get('SUDO_USER') != config['owner']:
        raise Refused('only the configured owner may invoke this deployment command')
    if sys.argv[1:] == ['status']:
        current = read_record('current.json')
        current['interrupted'] = (STATE / 'pending.json').exists()
        current['files_match'] = current['file_sha256'] == {name: sha(raw) for name, raw in snapshot().items()}
        current['services'] = {unit: properties(unit)['ActiveState'] for unit in (*SERVICES, *TIMERS)}
        print(canonical(current))
        return
    if len(sys.argv) != 4 or sys.argv[1] != 'apply':
        raise Refused('usage: nostromo-deploy status | apply COMMIT SHA256 < release.json')
    files = decode(sys.stdin.buffer.read(MAX_BUNDLE + 1), sys.argv[2], sys.argv[3], config['requires'])
    lock = STATE / 'deploy.lock'
    trusted(lock)
    with lock.open('rb') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(canonical(deploy(config, files, sys.argv[2], sys.argv[3])))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        # No child output, payload contents, or credential-bearing exception bodies.
        frames = traceback.extract_tb(error.__traceback__)
        location = [{'file': Path(frame.filename).name, 'function': frame.name, 'line': frame.lineno}
                    for frame in frames[-6:]]
        print(canonical({'ok': False, 'error': str(error) if isinstance(error, Refused) else type(error).__name__,
                         'where': location}), file=sys.stderr)
        sys.exit(1)
