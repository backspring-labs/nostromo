#!/usr/bin/python3 -I
"""Deploy Nostromo on the Spark from merged main, as the supervisor account. No root, no sudo.

  nostromo-release.py status [--json]
  nostromo-release.py deploy [COMMIT] [--allow-unmerged REASON]
  nostromo-release.py stage  [COMMIT] [--allow-unmerged REASON]
  nostromo-release.py rollback [--allow-unmerged REASON]

A release is one commit, `git archive`d read-only into /opt/nostromo/releases/<sha>.
/opt/nostromo/current names the live release, and everything reads through it: the harness
launcher, prompts, personas, the manifest, crewctl, budget-watch, and (through root-owned links
under /usr/local, installed once by install-release-deploy.py) the campaign code and runbooks.
One commit is live for all of it, and `status` says which.

Only commits on GitHub main deploy. The repository is public, so the fetch needs no credential and
the supervisor still holds none. Root never runs release code; the supervisor restarts the units
that do through polkit (48-nostromo-release.rules). See docs/runbooks/deployment.md.
"""
import argparse
import fcntl
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import time
from pathlib import Path

GITHUB = 'https://github.com/backspring-labs/nostromo.git'
DAEMONS = ('nostromo-campaign-broker.service', 'nostromo-campaign-watch.service',
           'nostromo-budget-watch.service')
TIMERS = ('nostromo-campaign-window.timer', 'nostromo-campaign-advance.timer',
          'nostromo-campaign-launch.timer', 'nostromo-campaign-review@ripley.timer',
          'nostromo-campaign-review@dallas.timer')
WORKERS = tuple(timer.replace('.timer', '.service') for timer in TIMERS)
BUSY = {'active', 'activating', 'deactivating', 'reloading'}
SOCKET = '/run/nostromo-campaigns/control.sock'
# Present in every release, or it is not a Nostromo release.
REQUIRED = ('crew/manifest.yaml', 'infrastructure/spark/bin/launch-role.sh',
            'infrastructure/spark/bin/nostromo-release.py', 'runtime/campaigns/service.py')
KEEP = 5


class Refused(Exception):
    pass


class Spark:
    """Every side effect, so tests can replace systemd, the socket and the clock."""

    def __init__(self, root='/opt/nostromo', github=GITHUB, linked='/usr/local/lib/nostromo/campaigns'):
        self.root = Path(root)
        self.github = github
        self.linked = Path(linked)

    releases = property(lambda self: self.root / 'releases')
    current = property(lambda self: self.root / 'current')
    previous = property(lambda self: self.root / 'previous')
    bare = property(lambda self: self.root / 'nostromo-src.git')
    log = property(lambda self: self.root / 'state' / 'releases.jsonl')

    def git(self, *args, check=True, binary=False):
        result = subprocess.run(['git', '--git-dir', str(self.bare), *args], capture_output=True, timeout=120)
        if check and result.returncode:
            raise Refused(f'git {args[0]} failed: {result.stderr.decode().strip()[:300]}')
        return result if not check else (result.stdout if binary else result.stdout.decode().strip())

    def systemctl(self, *args):
        result = subprocess.run(['systemctl', '--no-ask-password', *args], capture_output=True, text=True, timeout=120)
        if result.returncode and args[0] in ('start', 'stop', 'restart'):
            raise Refused(f'systemctl {" ".join(args)}: {(result.stderr or result.stdout).strip()[:300]}')
        return result.stdout.strip()

    def state(self, unit):
        return self.systemctl('is-active', unit) or 'unknown'

    def started(self, unit):
        value = self.systemctl('show', '-P', 'ActiveEnterTimestamp', '--timestamp=unix', unit)
        return int(value[1:]) if value.startswith('@') else None

    def probe(self):
        """The broker answers a line of JSON. As the supervisor it says the caller is not admitted,
        which is an answer: the process is up, its modules loaded, and the socket handler ran."""
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(5)
            sock.connect(SOCKET)
            sock.sendall(b'{"command":"shared-ready","args":{}}\n')
            with sock.makefile('rb') as stream:
                return 'ok' in json.loads(stream.readline(65537))

    def harnesses(self):
        out = self.systemctl('list-units', 'nostromo@*', '--plain', '--no-legend', '--state=active')
        return [line.split()[0] for line in out.splitlines() if line.strip()]

    sleep = staticmethod(time.sleep)
    now = staticmethod(time.time)


def point(link, target):
    """Repoint a symlink atomically: a reader sees the old release or the new one, never neither."""
    temporary = link.with_name('.' + link.name + '.new')
    if temporary.is_symlink() or temporary.exists():
        temporary.unlink()
    os.symlink(target, temporary)
    os.replace(temporary, link)


def live(spark, link=None):
    link = link or spark.current
    return os.readlink(link).rsplit('/', 1)[-1] if link.is_symlink() else None


def resolve(spark, commit=None, allow_unmerged=None):
    if not spark.bare.is_dir():
        subprocess.run(['git', 'init', '--quiet', '--bare', str(spark.bare)], check=True)
    spark.git('fetch', '--quiet', '--prune', spark.github, '+refs/heads/*:refs/remotes/github/*')
    main = spark.git('rev-parse', 'refs/remotes/github/main^{commit}')
    if commit is None:
        sha = main
    else:
        # A bare name like "main" would resolve against whatever was last pushed here. Commits only.
        if not (7 <= len(commit) <= 40 and all(c in '0123456789abcdef' for c in commit)):
            raise Refused('name a commit by its hex id; branch names are not deployable')
        sha = spark.git('rev-parse', '--verify', '--quiet', commit + '^{commit}')
    merged = spark.git('merge-base', '--is-ancestor', sha, main, check=False).returncode == 0
    if not merged:
        if not allow_unmerged:
            raise Refused(f'{sha[:12]} is not on GitHub main. Merge its pull request, or pass '
                          '--allow-unmerged REASON for an owner-approved trial')
        if not spark.git('for-each-ref', '--contains', sha, 'refs/remotes/github'):
            raise Refused(f'{sha[:12]} is on no GitHub branch; push it first')
    return sha, merged, main


def freeze(path, writable=False):
    for directory, _dirs, files in os.walk(path):
        os.chmod(directory, 0o755 if writable else 0o555)
        for name in files:
            target = os.path.join(directory, name)
            if not os.path.islink(target):
                mode = os.stat(target).st_mode
                os.chmod(target, (0o755 if mode & 0o100 else 0o644) & (0o777 if writable else 0o555))


def remove(path):
    freeze(path, writable=True)
    shutil.rmtree(path)


def check(tree):
    """Refuse a release that cannot run, before anything points at it."""
    missing = [name for name in REQUIRED if not (tree / name).is_file()]
    if missing:
        raise Refused(f'release lacks {", ".join(missing)}')
    for path in sorted(tree.rglob('*')):
        if not path.is_file() or path.is_symlink():
            continue
        head = path.read_bytes()[:128]
        if path.suffix == '.py' or (head.startswith(b'#!') and b'python' in head.split(b'\n', 1)[0]):
            try:
                compile(path.read_bytes(), str(path), 'exec', dont_inherit=True)
            except SyntaxError as error:
                raise Refused(f'{path.relative_to(tree)}:{error.lineno}: {error.msg}') from None
        elif path.suffix == '.sh' or (head.startswith(b'#!') and b'bash' in head.split(b'\n', 1)[0]):
            result = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
            if result.returncode:
                raise Refused(f'{path.relative_to(tree)}: {result.stderr.strip()[:300]}')
    # Import every campaign module the way the services will, in a clean interpreter.
    modules = sorted(p.stem for p in (tree / 'runtime/campaigns').glob('*.py') if p.stem != '__init__')
    code = ('import importlib, sys; sys.path.insert(0, sys.argv[1])\n'
            'for name in sys.argv[2:]: importlib.import_module("campaigns." + name)')
    result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(tree / 'runtime'), *modules],
                            capture_output=True, text=True, cwd='/', timeout=60)
    if result.returncode:
        raise Refused('campaign modules do not import: ' + (result.stderr.strip().splitlines() or ['?'])[-1][:300])


def stage(spark, sha, merged, reason=None):
    target = spark.releases / sha
    if target.is_dir():
        return target
    spark.releases.mkdir(mode=0o755, exist_ok=True)
    staging = spark.releases / f'.staging-{sha}-{os.getpid()}'
    staging.mkdir(mode=0o755)
    try:
        archive = spark.git('archive', '--format=tar', sha, binary=True)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(staging, filter='data')
        subject = spark.git('log', '-1', '--format=%s', sha)
        (staging / 'RELEASE.json').write_text(json.dumps(
            {'commit': sha, 'subject': subject, 'merged': merged, 'reason': reason,
             'staged_at': int(spark.now())}, indent=2) + '\n')
        check(staging)
        freeze(staging)
        os.rename(staging, target)
    except BaseException:
        remove(staging)
        raise
    return target


def record(spark, **entry):
    spark.log.parent.mkdir(exist_ok=True)
    with spark.log.open('a') as handle:
        handle.write(json.dumps({'at': int(spark.now()), **entry}, sort_keys=True) + '\n')


def healthy(spark, timeout=30):
    deadline = spark.now() + timeout
    while True:
        try:
            if all(spark.state(unit) == 'active' for unit in DAEMONS) and spark.probe():
                break
        except (OSError, ValueError):
            pass
        if spark.now() >= deadline:
            return False
        spark.sleep(1)
    # A daemon that crashes on its first request restarts; give it a moment to show that.
    before = {unit: spark.systemctl('show', '-P', 'NRestarts', unit) for unit in DAEMONS}
    spark.sleep(3)
    return all(spark.state(unit) == 'active' and spark.systemctl('show', '-P', 'NRestarts', unit) == before[unit]
               for unit in DAEMONS)


def restart(spark):
    try:
        for unit in DAEMONS:
            spark.systemctl('restart', unit)
    except Refused:
        return False
    return healthy(spark)


def drain(spark, timeout):
    """Pause the campaign timers and wait for any worker already running. Never kills one."""
    paused = [timer for timer in TIMERS if spark.state(timer) in BUSY]
    for timer in paused:
        spark.systemctl('stop', timer)
    deadline = spark.now() + timeout
    while busy := [unit for unit in WORKERS if spark.state(unit) in BUSY]:
        if spark.now() >= deadline:
            resume(spark, paused)
            raise Refused(f'{", ".join(busy)} still running after {timeout}s; nothing changed. Retry later')
        spark.sleep(2)
    return paused


def resume(spark, paused):
    """Start every paused timer, even after one fails; return the ones that did not start."""
    failed = []
    for timer in paused:
        try:
            spark.systemctl('start', timer)
        except Exception:  # any failure to start counts; keep starting the rest
            failed.append(timer)
    return failed


def switch(spark, sha, merged, reason, drain_timeout=120):
    if not spark.linked.is_symlink():
        raise Refused('this Spark is not on release deploys yet; run install-release-deploy.py once (docs/runbooks/deployment.md)')
    old = live(spark)
    if old == sha:
        return {'commit': sha, 'unchanged': True}
    paused = drain(spark, drain_timeout)
    stopped = []
    try:
        if old:
            point(spark.previous, f'releases/{old}')
        point(spark.current, f'releases/{sha}')
        if not restart(spark):
            restored = False
            if old:
                point(spark.current, f'releases/{old}')
                restored = restart(spark)
            record(spark, commit=sha, previous=old, merged=merged, reason=reason, result='rolled back' if restored else 'failed')
            raise Refused(f'{sha[:12]} failed its health check; ' + (
                f'{old[:12]} is live again' if restored else 'and the previous release did not recover: inspect journalctl -u nostromo-campaign-broker'))
    finally:
        stopped = resume(spark, paused)
    # A healthy release stays live; a timer that would not restart is recorded and reported, not hidden.
    record(spark, commit=sha, previous=old, merged=merged, reason=reason, result='live',
           **({'timers_not_restarted': stopped} if stopped else {}))
    if stopped:
        raise Refused(f'{sha[:12]} is live and healthy, but these timers did not restart: {", ".join(stopped)}. '
                      'Start them by hand (systemctl start), and inspect their journals')
    return {'commit': sha, 'previous': old, 'stale_harnesses': stale(spark)}


def stale(spark):
    """Crew harnesses that started before the live release. They keep the persona they launched
    with until restarted; rollout.sh restarts them with a canary."""
    switched = (spark.current.lstat().st_mtime if spark.current.is_symlink() else 0)
    return [unit for unit in spark.harnesses() if (spark.started(unit) or 0) < switched]


def prune(spark):
    keep = {live(spark), live(spark, spark.previous)}
    kept = sorted((p for p in spark.releases.iterdir() if p.is_dir() and len(p.name) == 40),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    for path in kept[KEEP:]:
        if path.name not in keep:
            remove(path)
    for path in spark.releases.glob('.staging-*'):
        remove(path)


def status(spark):
    sha = live(spark)
    info = {'live': sha, 'previous': live(spark, spark.previous), 'adopted': spark.linked.is_symlink()}
    if sha:
        info.update(json.loads((spark.releases / sha / 'RELEASE.json').read_text()))
        main = spark.git('rev-parse', 'refs/remotes/github/main', check=False)
        if main.returncode == 0:
            main = main.stdout.decode().strip()
            info['github_main'] = main
            info['behind_main'] = int(spark.git('rev-list', '--count', f'{sha}..{main}'))
            # Merged since it was staged as a trial, or not: ask Git, not the stamp.
            info['merged'] = spark.git('merge-base', '--is-ancestor', sha, main, check=False).returncode == 0
    info['units'] = {unit: spark.state(unit) for unit in (*DAEMONS, *TIMERS)}
    info['stale_harnesses'] = stale(spark) if sha else []
    if spark.log.exists():
        info['recent'] = [json.loads(line) for line in spark.log.read_text().splitlines()[-3:]]
    return info


def show(info):
    sha = info['live']
    print(f"live      {sha[:12] if sha else '-'}  {info.get('subject', '')}")
    if not info.get('merged', True):
        print(f"          UNMERGED trial: {info.get('reason')}")
    if 'behind_main' in info:
        print(f"main      {info['github_main'][:12]}  " + (
            'up to date' if not info['behind_main'] else f"{info['behind_main']} commit(s) ahead of live, as last fetched"))
    print(f"previous  {(info['previous'] or '-')[:12]}")
    print(f"adopted   {'yes' if info['adopted'] else 'no: run install-release-deploy.py once'}")
    for unit, state in info['units'].items():
        print(f"  {state:<10} {unit}")
    if info['stale_harnesses']:
        print('started before this release (restart with rollout.sh from the Mac): ' + ', '.join(info['stale_harnesses']))


def main(argv=None, spark=None):
    os.umask(0o022)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('status', 'stage', 'deploy', 'rollback'))
    parser.add_argument('commit', nargs='?')
    parser.add_argument('--allow-unmerged', metavar='REASON')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    spark = spark or Spark()
    if os.geteuid() == 0:
        raise Refused('run as the supervisor (nostromo), never as root')
    if args.command == 'status':
        info = status(spark)
        print(json.dumps(info, indent=2)) if args.json else show(info)
        return 0
    spark.root.joinpath('state').mkdir(exist_ok=True)
    with open(spark.root / 'state' / 'release.lock', 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refused('another deploy is running') from None
        if args.command == 'rollback':
            sha = live(spark, spark.previous)
            if not sha:
                raise Refused('there is no previous release')
            # The previous release passes the same gate as any deploy, against main as it is now: a
            # trial that was once approved needs approving again, never a silent return to production.
            sha, merged, _main = resolve(spark, sha, args.allow_unmerged)
            reason = 'rollback' + (f': {args.allow_unmerged}' if args.allow_unmerged else '')
            result = switch(spark, sha, merged, reason)
        else:
            sha, merged, _main = resolve(spark, args.commit, args.allow_unmerged)
            path = stage(spark, sha, merged, args.allow_unmerged)
            if args.command == 'stage':
                print(path)
                return 0
            result = switch(spark, sha, merged, args.allow_unmerged)
        prune(spark)
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Refused as error:
        print(f'nostromo-release: {error}', file=sys.stderr)
        sys.exit(1)
