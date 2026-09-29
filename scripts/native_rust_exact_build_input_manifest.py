#!/usr/bin/env python3
"""Create the immutable input manifest for the offline exact-build driver."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid

if __package__:
    from . import native_rust_exact_build_offline as provenance
else:
    import native_rust_exact_build_offline as provenance

EXPECTED_IHK_HEAD = '3114d9e7101ad52030eb3effa849a5c108972a1f'
ARCHIVE = 'linux-6.12.0-211.44.1.el10_2.tar.xz'
BASELINE = 'kernel-x86_64-rhel.config'
SRPM = 'kernel-6.12.0-211.44.1.el10_2.src.rpm'
DEBRAND = '1000-debrand-some-messages.patch'
ASSET_HASHES = {
    ARCHIVE: '4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533',
    BASELINE: '5bbdda60ce822ec903c85d3d8ddda1bfc9493216bed86c6c432683aa50dcf50d',
    SRPM: '2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb',
    DEBRAND: '080bbc72a543eed6b71daee1b3236b59f3a0f8b3ad20815d962444d3b106b144',
}
_HEX40 = re.compile(r'^[0-9a-f]{40}$')


class ManifestError(Exception):
    pass


def _sha256(path, link_text=False):
    if link_text and path.is_symlink():
        data = os.fsencode(os.readlink(str(path)))
        return hashlib.sha256(data).hexdigest()
    if path.is_symlink() or not path.is_file():
        raise ManifestError('not a regular input: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(raw):
    try:
        return provenance.safe_relative(raw)
    except provenance.BuildError as error:
        raise ManifestError(str(error))


def _checked_input(root, relative):
    """Return a checkout input without allowing a symlinked parent to escape it."""
    try:
        return provenance.checked_input(root, relative)
    except provenance.BuildError as error:
        raise ManifestError(str(error))


def _check_output_parent(output):
    """Reject every existing symlink component before creating an output path."""
    parent = Path(os.path.abspath(str(output.parent)))
    current = Path(parent.anchor)
    for component in parent.parts[1:]:
        current /= component
        if current.is_symlink():
            raise ManifestError('output parent contains a symlink: ' + str(current))


def _git(root, *args):
    # Do not inherit caller-controlled Git locations or configuration.  The
    # candidate checkout's local configuration is still read by Git itself.
    env = {'PATH': os.defpath, 'LANG': 'C', 'LC_ALL': 'C',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
           'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0'}
    command = ['/usr/bin/git', '-c', 'safe.directory=' + str(root), '-c',
               'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-C',
               str(root)] + list(args)
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env, check=False)
    if result.returncode:
        raise ManifestError('git command failed: ' + result.stderr.decode('utf-8', 'replace'))
    return result.stdout


def _index_rows(root):
    try:
        rows = provenance.git_rows(_git(root, 'ls-files', '-s', '-z'))
        return [(path, mode, object_id) for path, (mode, object_id) in rows.items()]
    except provenance.BuildError as error:
        raise ManifestError(str(error))


def _validate_checkout_modes(repo):
    """Admit only worktree modes represented exactly by the Git index.

    Git records only 0644/0755 for regular files, but a candidate checkout
    must retain those complete permission bits: an umask-modified 0600/0700
    tree is not an exact source preimage.  lstat keeps links un-followed and
    checked_input applies the same parent/path confinement as inventory.
    """
    for root in (Path(repo), Path(repo) / 'ihk'):
        for relative, mode, unused_oid in _index_rows(root):
            if mode == '160000':
                continue
            path = _checked_input(root, relative)
            metadata = path.lstat()
            if mode == '120000':
                if not stat.S_ISLNK(metadata.st_mode):
                    raise ManifestError('indexed symlink type differs: ' + str(path))
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise ManifestError('indexed regular file type differs: ' + str(path))
            expected = 0o755 if mode == '100755' else 0o644
            if stat.S_IMODE(metadata.st_mode) != expected:
                raise ManifestError('indexed executable mode differs: ' + str(path))


def _head(root):
    try:
        return provenance.git_head(_git(root, 'rev-parse', 'HEAD'))
    except provenance.BuildError as error:
        raise ManifestError(str(error))


def _clean(root):
    if _git(root, 'ls-files', '--others', '--exclude-standard', '-z'):
        raise ManifestError('source checkout is dirty: ' + str(root))


def _inventory(repo):
    # Run both sides of inventory admission so a mode change during the
    # provenance walk cannot be self-blessed by a stale pre-check.
    _validate_checkout_modes(repo)
    try:
        result = provenance.source_inventory(repo, _git)
    except provenance.BuildError as error:
        raise ManifestError(str(error))
    _validate_checkout_modes(repo)
    return result


def generate(repo, assets, output, candidate_sha):
    repo = Path(repo).resolve()
    assets = Path(assets).resolve()
    output = Path(output)
    if not _HEX40.fullmatch(candidate_sha):
        raise ManifestError('invalid candidate SHA')
    if not repo.is_dir() or not assets.is_dir():
        raise ManifestError('repo/assets must be directories')
    if output.exists() or output.is_symlink():
        raise ManifestError('output already exists')
    _check_output_parent(output)
    if _head(repo) != candidate_sha:
        raise ManifestError('main HEAD differs from candidate')
    if _head(repo / 'ihk') != EXPECTED_IHK_HEAD:
        raise ManifestError('IHK HEAD differs')
    files, gitlinks = _inventory(repo)
    if gitlinks.get('ihk') != EXPECTED_IHK_HEAD:
        raise ManifestError('IHK gitlink differs')
    asset_rows = {}
    for name, expected in ASSET_HASHES.items():
        asset_rows[name] = _sha256(assets / name)
        if asset_rows[name] != expected:
            raise ManifestError('asset hash differs: ' + name)
    driver = repo / 'scripts' / 'native_rust_exact_build_offline.py'
    manifest = {'assets': asset_rows, 'candidate_sha': candidate_sha,
                'driver_sha256': _sha256(driver), 'gitlinks': gitlinks,
                'ihk_sha': EXPECTED_IHK_HEAD,
                'repository_files': files,
                'schema': provenance.INPUT_SCHEMA}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with temporary.open('x') as stream:
            json.dump(manifest, stream, sort_keys=True, separators=(',', ':'))
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        # link(2) atomically creates the destination only if absent. replace(2)
        # would silently destroy a competing writer's completed manifest.
        try:
            os.link(str(temporary), str(output))
        except FileExistsError:
            raise ManifestError('output already exists')
        temporary.unlink()
        directory = os.open(str(output.parent), os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--assets', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--candidate-sha', required=True)
    args = parser.parse_args(argv)
    try:
        generate(args.repo, args.assets, args.output, args.candidate_sha)
    except (ManifestError, OSError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    sys.exit(main())
