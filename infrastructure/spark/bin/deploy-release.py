#!/usr/bin/python3 -I
"""Build a bounded release from an exact Git commit, as the unprivileged owner."""
import argparse
import base64
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location('nostromo_deploy_format', Path(__file__).with_name('nostromo-deploy.py'))
format = importlib.util.module_from_spec(spec)
spec.loader.exec_module(format)


def git(repo, *args):
    return subprocess.run(['/usr/bin/git', '-C', str(repo), *args], capture_output=True,
                          check=True, timeout=30).stdout


def bundle(repo, commit):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise format.Refused('supply an exact forty-character Git commit')
    if git(repo, 'rev-parse', commit + '^{commit}').decode().strip() != commit:
        raise format.Refused('Git did not resolve the exact requested commit')
    tree = {}
    for item in git(repo, 'ls-tree', '-rz', '--full-tree', commit).split(b'\x00'):
        if item:
            metadata, name = item.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            tree[name.decode()] = (mode, kind, oid)
    selected = set(format.FIXED) | {name for name in tree if name.startswith('runtime/campaigns/') and name.endswith('.py')}
    def read(name):
        mode, kind, oid = tree[name]
        if mode not in {'100644', '100755'} or kind != 'blob':
            raise format.Refused('release inputs must be regular tracked files')
        if int(git(repo, 'cat-file', '-s', oid)) > format.MAX_FILE:
            raise format.Refused('release input exceeds its bound')
        return git(repo, 'cat-file', 'blob', oid)
    value = {'version': 1, 'commit': commit,
             'requires': {name: format.sha(read(name)) for name in sorted(format.privileged_sources())},
             'files': {name: base64.b64encode(read(name)).decode() for name in sorted(selected)}}
    raw = (format.canonical(value) + '\n').encode()
    format.decode(raw, commit, format.sha(raw), value['requires'])
    return raw


def bootstrap(repo, commit, target):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise format.Refused('supply an exact forty-character Git commit')
    target.mkdir(mode=0o700)  # Refuse to reuse or merge with an existing directory.
    names = format.privileged_sources() | {
        'infrastructure/spark/bin/nostromo-deploy.py', 'infrastructure/spark/bin/install-nostromo-deploy.py',
        'docs/runbooks/routine-deployment.md'}
    for name in sorted(names):
        entry = git(repo, 'ls-tree', '-z', commit, '--', name).split(b'\x00')[0]
        metadata, actual = entry.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        if actual.decode() != name or mode not in {'100644', '100755'} or kind != 'blob':
            raise format.Refused('bootstrap inputs must be regular tracked files')
        if int(git(repo, 'cat-file', '-s', oid)) > format.MAX_FILE:
            raise format.Refused('bootstrap source exceeds its bound')
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(git(repo, 'cat-file', 'blob', oid))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--bootstrap-output', help='optional new private directory for the one-time setup snapshot')
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise SystemExit('build releases as the owner, never as root')
    repo = Path(__file__).resolve().parents[3]
    raw = bundle(repo, args.commit)
    target = Path(args.output)
    # Do not follow a pre-existing output link or overwrite another release by accident.
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as handle:
        handle.write(raw)
    if args.bootstrap_output:
        bootstrap(repo, args.commit, Path(args.bootstrap_output))
    print(format.canonical({'commit': args.commit, 'sha256': format.sha(raw), 'bytes': len(raw), 'file': str(target)}))


if __name__ == '__main__':
    main()
