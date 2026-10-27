#!/usr/bin/python3 -I
"""One authenticated step: put the Spark on release deploys, and retire the password-free helper.

The owner runs this as root, from a fresh root-owned clone of GitHub at the release's commit. Never
run it from /opt/nostromo: the supervisor owns that tree and could change a file between the owner
reading it and root running it. docs/runbooks/deployment.md has the exact command.

  1. Checks that /opt/nostromo/releases/<sha> is byte-identical to this clone, so what root links to
     is what the owner reviewed.
  2. Drains the campaign timers and stops the daemons.
  3. Points current at the release, and nostromo-src at current. The old working tree is kept.
  4. Replaces /usr/local/lib/nostromo, /usr/local/bin/campaignctl and /usr/local/share/nostromo with
     root-owned links into current.
  5. Installs 48-nostromo-release.rules and this release's nostromo@.service.
  6. Moves the nostromo-deploy helper, its sudoers rule, config and state to a backup.
  7. Starts the daemons, checks them, and resumes the timers.

A failure after the drain undoes every completed step in reverse, restarts the daemons that were
running, and resumes the timers it paused. Backups stay in /var/backups/nostromo-release-adopt-*.
"""
import importlib.util
import os
import pwd
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location('nostromo_release', Path(__file__).with_name('nostromo-release.py'))
rel = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rel)
Refused = rel.Refused

ENTRYPOINTS = ('campaign-broker.py', 'campaign-watch.py', 'campaign-window.py', 'campaign-window-check.py',
               'campaign-review.py', 'campaign-advance.py', 'campaign-launch.py')
RUNBOOKS = ('campaign-control.md', 'shared-inference.md', 'deployment.md')
PERSONAS = ('ripley', 'dallas')
RETIRED = ('usr/local/sbin/nostromo-deploy', 'etc/nostromo/deploy.json', 'var/lib/nostromo-deploy')
SUDOERS = 'etc/sudoers.d/nostromo-deploy'


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def tree(top, clone=False):
    """Relative path -> bytes for every regular file, without Git metadata or the release stamp.

    The clone gets bytecode caches the moment this script imports nostromo-release.py from it, so they
    are skipped there. They are not skipped in a release: a planted .pyc would run instead of the
    source, so one appearing there is a difference like any other."""
    out = {}
    for path in top.rglob('*'):
        rel_path = path.relative_to(top)
        if rel_path.parts[0] == '.git' or rel_path == Path('RELEASE.json'):
            continue
        if clone and '__pycache__' in rel_path.parts:
            continue
        if path.is_symlink():
            out[str(rel_path)] = b'link:' + os.readlink(path).encode()
        elif path.is_file():
            out[str(rel_path)] = path.read_bytes()
    return out


class Adopt:
    def __init__(self, sha, spark, root='/', source=HERE, supervisor='nostromo', run=subprocess.run, stamp=None):
        self.sha, self.spark, self.root, self.source, self.run = sha, spark, Path(root), Path(source), run
        account = pwd.getpwnam(supervisor)
        self.uid, self.gid = account.pw_uid, account.pw_gid
        self.stamp = stamp or time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
        self.backup = self.at(f'var/backups/nostromo-release-adopt-{self.stamp}')
        self.release = self.at('opt/nostromo/releases') / sha
        self.current = self.at('opt/nostromo/current')
        self.undo = []

    def at(self, path):
        return self.root / path

    def step(self, name):
        """Announce a step. Tests fail a named step here to prove the undo."""
        print(f'== {name}', flush=True)

    # Each change records how to reverse itself, so a failure can put back everything done so far.

    def aside(self, path):
        if not (path.exists() or path.is_symlink()):
            self.undo.append(lambda path=path: remove(path))
            return
        # Named by full path: /usr/local/lib/nostromo and /usr/local/share/nostromo must not collide.
        saved = self.backup / str(path.relative_to(self.root)).replace('/', '_')
        shutil.move(str(path), str(saved))
        self.undo.append(lambda path=path, saved=saved: (remove(path), shutil.move(str(saved), str(path))))

    def link(self, path, target, supervisor_owned=False):
        self.aside(path)
        os.symlink(target, path)
        if supervisor_owned:
            os.lchown(path, self.uid, self.gid)

    def links_dir(self, path, links):
        self.aside(path)
        path.mkdir(mode=0o755)
        for name, target in links.items():
            os.symlink(target, path / name)

    def install(self, source, path, mode=0o644):
        self.aside(path)
        shutil.copyfile(source, path)
        os.chmod(path, mode)

    def check(self):
        if not (len(self.sha) == 40 and all(c in '0123456789abcdef' for c in self.sha)):
            raise Refused('name the release by its full commit id')
        if self.release.is_symlink() or not self.release.is_dir():
            raise Refused(f'{self.release} is not staged; stage it as the supervisor first')
        if self.release.stat().st_uid != self.uid:
            raise Refused(f'{self.release} is not owned by the supervisor')
        if any(not p.is_symlink() and p.stat().st_mode & 0o022 for p in [self.release, *self.release.rglob('*')]):
            raise Refused(f'{self.release} is group- or other-writable')
        mine, staged = tree(self.source, clone=True), tree(self.release)
        if mine != staged:
            differs = sorted(set(mine) ^ set(staged)) or sorted(n for n in mine if mine[n] != staged[n])
            raise Refused(f'{self.release} differs from GitHub at {self.sha[:12]}, first at {differs[0]}; refusing')
        if self.current.exists() and not self.current.is_symlink():
            raise Refused(f'{self.current} exists and is not a link')

    def adopt(self):
        self.check()
        self.backup.mkdir(mode=0o700, parents=True)
        print(f'== release {self.sha}\n== backup  {self.backup}', flush=True)
        self.step('drain')
        paused = rel.drain(self.spark, 300)  # resumes and refuses by itself if a worker won't finish
        running = [unit for unit in rel.DAEMONS if self.spark.state(unit) == 'active']
        # Pushed first, so they run last: files back, then units reloaded, started and resumed. Starting
        # is best effort here; verify() below is what decides whether the units really came back.
        self.undo.append(lambda: rel.resume(self.spark, paused))
        self.undo.append(lambda: rel.resume(self.spark, running))
        self.undo.append(lambda: self.spark.systemctl('daemon-reload'))
        try:
            self.spark.systemctl('stop', *rel.DAEMONS)
            self.migrate()
            self.step('start')
            for unit in rel.DAEMONS:
                self.spark.systemctl('start', unit)
            if not rel.healthy(self.spark):
                raise Refused('the campaign daemons did not come up healthy on the new layout')
            # Resuming is part of adoption: a timer that will not start undoes it like any other step.
            self.step('resume timers')
            failed = rel.resume(self.spark, paused)
            if failed:
                raise Refused(f'these timers would not start on the new layout: {", ".join(failed)}')
        except BaseException:
            errors = self.quiesce(paused) + self.rollback() + self.verify(running, paused)
            if errors:
                print(f'== adoption failed, and restoring it is INCOMPLETE. Inspect {self.backup}:', file=sys.stderr)
                for error in errors:
                    print(f'   - {error}', file=sys.stderr)
            else:
                print('== adoption failed; every file was put back, and every unit is running as before', file=sys.stderr)
            raise
        self.undo.clear()

    def migrate(self):
        opt = self.at('opt/nostromo')
        current = '/opt/nostromo/current'
        self.step('current and nostromo-src')
        self.link(self.current, f'releases/{self.sha}', supervisor_owned=True)
        source = opt / 'nostromo-src'
        if source.is_dir() and not source.is_symlink():
            saved = opt / 'backups' / f'nostromo-src-pre-release-{self.stamp}'
            shutil.move(str(source), str(saved))
            self.undo.append(lambda: (remove(source), shutil.move(str(saved), str(source))))
        else:
            self.aside(source)
        os.symlink('current', source)
        os.lchown(source, self.uid, self.gid)

        self.step('/usr/local links')
        self.links_dir(self.at('usr/local/lib/nostromo'), {
            'campaigns': f'{current}/runtime/campaigns',
            **{name: f'{current}/infrastructure/spark/bin/{name}' for name in ENTRYPOINTS}})
        self.link(self.at('usr/local/bin/campaignctl'), f'{current}/infrastructure/spark/bin/campaignctl')
        self.links_dir(self.at('usr/local/share/nostromo'), {
            **{name: f'{current}/docs/runbooks/{name}' for name in RUNBOOKS},
            **{f'campaign-{role}.md': f'{current}/crew/personas/{role}.md' for role in PERSONAS}})

        self.step('polkit rule and crew unit')
        self.install(self.source / 'infrastructure/spark/systemd/48-nostromo-release.rules',
                     self.at('etc/polkit-1/rules.d/48-nostromo-release.rules'))
        self.install(self.source / 'infrastructure/spark/systemd/nostromo@.service',
                     self.at('etc/systemd/system/nostromo@.service'))
        self.spark.systemctl('daemon-reload')

        self.step('retire nostromo-deploy')
        sudoers = self.at(SUDOERS)
        if sudoers.exists():
            self.aside(sudoers)
            if self.run(['visudo', '-c'], capture_output=True).returncode:
                raise Refused('visudo -c failed after removing the rule')
        for name in RETIRED:
            path = self.at(name)
            if path.exists() or path.is_symlink():
                self.aside(path)

    def quiesce(self, paused):
        """Stop what may be running the new layout: after the files go back it would keep the new code,
        and `systemctl start` on a running unit does nothing."""
        errors = []
        for unit in (*paused, *rel.DAEMONS):
            try:
                self.spark.systemctl('stop', unit)
            except Exception as error:
                errors.append(f'could not stop {unit} before restoring ({error}); '
                              + ('it may still be running the new release' if unit in rel.DAEMONS else 'it may fire during the restore'))
        return errors

    def verify(self, running, paused):
        """The units' final state, read back rather than assumed."""
        return [f'{unit} is {self.spark.state(unit)}, not active as it was before adoption'
                for unit in (*running, *paused) if self.spark.state(unit) != 'active']

    def rollback(self):
        errors = []
        for action in reversed(self.undo):
            try:
                action()
            except Exception as error:  # Keep restoring; report what could not be.
                errors.append(f'{type(error).__name__}: {error}')
        self.undo.clear()
        return errors


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise Refused('usage: install-release-deploy.py <full commit id>')
    sha = argv[0]
    if os.geteuid() != 0:
        raise Refused('run as root, from a fresh root-owned clone (docs/runbooks/deployment.md)')
    info = HERE.stat()
    if info.st_uid != 0 or info.st_mode & 0o077:
        raise Refused(f'{HERE} must be a private root-owned clone, not a shared tree')
    head = subprocess.run(['git', '-C', str(HERE), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    if head != sha:
        raise Refused(f'this clone is at {head[:12] or "?"}, not {sha[:12]}')
    Adopt(sha, rel.Spark()).adopt()
    print()
    subprocess.run(['runuser', '-u', 'nostromo', '--', '/usr/bin/python3', '-I',
                    '/opt/nostromo/current/infrastructure/spark/bin/nostromo-release.py', 'status'], cwd='/')
    print('\nDone. Crew harnesses keep the persona they launched with: restart them from the Mac with rollout.sh.')


if __name__ == '__main__':
    try:
        main()
    except Refused as error:
        print(f'install-release-deploy: {error}', file=sys.stderr)
        sys.exit(1)
