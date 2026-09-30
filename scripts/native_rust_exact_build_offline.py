#!/usr/bin/env python3
"""Offline adaptation of only the exact-build job, with original validators.

The five named workflow bodies are consumed from the immutable candidate. Only
online acquisition and GitHub service provenance are replaced. Local execution
is explicitly not a GitHub run and never starts downstream capture/guest jobs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

WORKFLOW = '.github/workflows/native-rust-host-modules-exact-build.yml'
EXPECTED_IHK_HEAD = '3114d9e7101ad52030eb3effa849a5c108972a1f'
REVIEWED_IHK_HEAD = EXPECTED_IHK_HEAD
IHK_OVERLAY_PATH = 'test/ihklib/whitebox/src/driver/mckernel/syscall.c'
IHK_OVERLAY_ASSET = 'host-kernel/exact-build/ihk-clear-host-pte-overlay.patch'
IHK_OVERLAY_PATCH_SHA256 = 'cbaaec7b649608674747e4d88acdd1f0a005cff6ff696046b8d96ed959af49e7'
IHK_OVERLAY_BASE_SHA256 = '91fe5688f3282c1617a75f08c4b435a793200f2cf9beafe432cef7ad3ca0bd4c'
IHK_OVERLAY_RESULT_SHA256 = '7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77'
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
INPUT_SCHEMA = 'mckernel.native-exact-build-inputs.v1'
STEPS = (
    'Verify source-only contracts without claiming readiness',
    'Acquire, patch, and credit-forbidden-stage the exact source',
    'Resolve the evidence-only module configuration twice',
    'Compile the exact kernel and native Rust modules',
    'Validate built metadata and capture immutable diagnostics',
)
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
       'TZ': 'UTC', 'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1',
       'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0',
       'SOURCE_DATE_EPOCH': '1786434034', 'KBUILD_BUILD_HOST': 'rocky-10.2-x86_64',
       'KBUILD_BUILD_USER': 'mckernel', 'KBUILD_BUILD_VERSION': '1',
       'KBUILD_BUILD_TIMESTAMP': 'Tue, 11 Aug 2026 07:40:34 +0000',
       'NATIVE_KERNEL_LOCALVERSION': '-211.44.1.el10_2.mckernel1.x86_64',
       'EXPECTED_KERNEL_RELEASE': '6.12.0-211.44.1.el10_2.mckernel1.x86_64'}
ARTIFACTS = ('bzImage', 'ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko',
             'stage-lock.json', 'secondary-reset-build-supplement.lock',
             'kbuild-link-closure.json', 'kconfig-solver-matrix.json',
             'resolved.config', 'kernel.release', 'SHA256SUMS')


class BuildError(RuntimeError):
    pass


def safe_relative(raw):
    try:
        text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
        text.encode('utf-8')
    except (UnicodeError, AttributeError):
        raise BuildError('non-UTF-8 input path')
    if (not text or Path(text).is_absolute() or '\x00' in text or
            any(part in ('', '.', '..') for part in text.split('/'))):
        raise BuildError('path escapes checkout: ' + repr(text))
    return text


def git_rows(raw, tree=False):
    """Parse NUL-delimited plumbing output, retaining exact modes and OIDs."""
    if not isinstance(raw, bytes):
        raise BuildError('path-bearing Git output must be raw bytes')
    if raw and not raw.endswith(b'\0'):
        raise BuildError('unterminated git row')
    rows = {}
    for item in raw.split(b'\0')[:-1]:
        metadata, separator, raw_path = item.partition(b'\t')
        fields = metadata.split()
        if not separator or len(fields) != 3:
            raise BuildError('malformed git index/tree row')
        path = safe_relative(raw_path)
        if tree:
            mode, kind, object_id = fields
            if kind != (b'commit' if mode == b'160000' else b'blob'):
                raise BuildError('unsupported tree object type: ' + path)
        else:
            mode, object_id, stage = fields
            if stage != b'0':
                raise BuildError('non-stage-0 index row: ' + path)
        if (mode not in (b'100644', b'100755', b'120000', b'160000') or
                not re.fullmatch(b'[0-9a-f]{40}', object_id)):
            raise BuildError('unsupported mode or object ID: ' + path)
        if path in rows:
            raise BuildError('duplicate git index/tree row: ' + path)
        rows[path] = (mode.decode('ascii'), object_id.decode('ascii'))
    return rows


def git_head(raw):
    """Decode only a fixed scalar, requiring Git's exact single LF terminator."""
    if not isinstance(raw, bytes) or not re.fullmatch(b'[0-9a-f]{40}\n', raw):
        raise BuildError('malformed Git HEAD identity')
    return raw[:-1].decode('ascii')


def checked_input(root, relative, allow_missing=False):
    # A tracked path may be a link, but none of its parents may be links.
    root = Path(root)
    current = root
    if root.is_symlink() or not root.is_dir():
        raise BuildError('checkout is not a directory: ' + str(root))
    for part in Path(safe_relative(relative)).parts[:-1]:
        current /= part
        if allow_missing and not os.path.lexists(str(current)):
            continue
        if not stat.S_ISDIR(current.lstat().st_mode):
            raise BuildError('input parent is not a directory: ' + relative)
    return root / relative


def tracked_digest(path, mode, object_id, alternate_sha256=None):
    """Hash raw bytes ourselves: no Git filters, stat cache or index flags."""
    metadata = path.lstat()
    if mode == '120000':
        if not stat.S_ISLNK(metadata.st_mode):
            raise BuildError('indexed symlink type differs: ' + str(path))
        data = os.fsencode(os.readlink(str(path)))
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data)
        digest = hashlib.sha256(data)
    else:
        if not stat.S_ISREG(metadata.st_mode):
            raise BuildError('indexed regular file type differs: ' + str(path))
        # Git records regular inputs as exact 0644 or 0755 modes.  Checking
        # every permission bit rejects umask-drifted candidate preimages.
        expected_mode = 0o755 if mode == '100755' else 0o644
        if stat.S_IMODE(metadata.st_mode) != expected_mode:
            raise BuildError('indexed executable mode differs: ' + str(path))
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size) != (
                    metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_size):
                raise BuildError('input changed while opening: ' + str(path))
            blob = hashlib.sha1(b'blob ' + str(opened.st_size).encode('ascii') + b'\0')
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                blob.update(chunk)
                digest.update(chunk)
    digest_hex = digest.hexdigest()
    if blob.hexdigest() != object_id:
        if alternate_sha256 is None or digest_hex != alternate_sha256:
            raise BuildError('Git blob bytes differ: ' + str(path))
    return digest_hex


def source_inventory(repo, git, allow_ihk_overlay=False):
    """One provenance invariant for manifest production and consumption."""
    repo = Path(repo)
    inventories = []
    for root in (repo, repo / 'ihk'):
        index = git_rows(git(root, 'ls-files', '-s', '-z'))
        tree = git_rows(git(root, 'ls-tree', '-r', '-z', '--full-tree', 'HEAD'), tree=True)
        if index != tree:
            raise BuildError('index differs from HEAD tree: ' + str(root))
        inventories.append(index)
        untracked = git(root, 'ls-files', '--others', '--exclude-standard', '-z')
        if not isinstance(untracked, bytes):
            raise BuildError('path-bearing Git output must be raw bytes')
        if untracked:
            raise BuildError('source checkout is dirty: ' + str(root))
    main, ihk = inventories
    if any(p.startswith('ihk/') or p == 'ihk' and m != '160000'
           for p, (m, unused) in main.items()):
        raise BuildError('main/IHK inventory collision')
    files, gitlinks = {}, {}
    for root, rows, prefix in ((repo, main, ''), (repo / 'ihk', ihk, 'ihk/')):
        for relative, (mode, object_id) in rows.items():
            path = checked_input(root, relative, allow_missing=(mode == '160000'))
            if mode == '160000':
                if prefix:
                    raise BuildError('nested IHK gitlink is not a file: ' + relative)
                # Unconsumed submodules may be absent. A present object must
                # still be a real directory, never a symlink or ordinary file.
                if os.path.lexists(str(path)) and not stat.S_ISDIR(path.lstat().st_mode):
                    raise BuildError('indexed gitlink type differs: ' + relative)
                gitlinks[relative] = object_id
            else:
                if (allow_ihk_overlay and root == repo / 'ihk' and
                        relative == IHK_OVERLAY_PATH):
                    files[prefix + relative] = tracked_digest(
                        path, mode, object_id, alternate_sha256=IHK_OVERLAY_RESULT_SHA256)
                    continue
                files[prefix + relative] = tracked_digest(path, mode, object_id)
    return files, gitlinks


def verify_ihk_overlay(repo, git, applied):
    """Admit only the reviewed one-file IHK working-tree overlay.

    The IHK gitlink remains pinned to EXPECTED_IHK_HEAD.  Preparation applies
    this patch after the pristine checkout, so the ordinary Git blob check is
    intentionally replaced for this one path by a base/result byte check.
    """
    repo = Path(repo)
    asset = regular(repo / IHK_OVERLAY_ASSET)
    if sha256(asset) != IHK_OVERLAY_PATCH_SHA256:
        raise BuildError('IHK overlay patch asset differs')
    raw = git(repo / 'ihk', 'show', 'HEAD:' + IHK_OVERLAY_PATH)
    if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != IHK_OVERLAY_BASE_SHA256:
        raise BuildError('IHK overlay base differs')
    current = regular(repo / 'ihk' / IHK_OVERLAY_PATH)
    expected = IHK_OVERLAY_RESULT_SHA256 if applied else IHK_OVERLAY_BASE_SHA256
    if sha256(current) != expected:
        state = 'applied' if applied else 'pristine'
        raise BuildError('IHK overlay ' + state + ' bytes differ')
    ihk = repo / 'ihk'
    status = git(ihk, 'status', '--porcelain=1', '--untracked-files=all', '-z')
    expected_status = (b' M ' + IHK_OVERLAY_PATH.encode('utf-8') + b'\0') if applied else b''
    if status != expected_status:
        raise BuildError('IHK overlay worktree has unexpected changes')
    diff = git(ihk, 'diff', '--no-ext-diff', '--binary', 'HEAD', '--', IHK_OVERLAY_PATH)
    expected_diff = IHK_OVERLAY_PATCH_SHA256 if applied else hashlib.sha256(b'').hexdigest()
    if hashlib.sha256(diff).hexdigest() != expected_diff:
        raise BuildError('IHK overlay diff differs')


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic(path, data):
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    with temporary.open('x') as stream:
        json.dump(data, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def regular(path):
    if path.is_symlink() or not path.is_file():
        raise BuildError('not a regular file: ' + str(path))
    return path


def bound_files(root, rows, links=False):
    if not isinstance(rows, dict) or not rows:
        raise BuildError('empty input manifest')
    for relative, expected in rows.items():
        p = Path(relative)
        if p.is_absolute() or '..' in p.parts or not re.fullmatch('[0-9a-f]{64}', expected):
            raise BuildError('invalid input manifest row')
        resolved = root / p
        if links and resolved.is_symlink():
            # Git hashes link text, not a dereferenced (possibly absent) target.
            observed = hashlib.sha256(os.fsencode(os.readlink(resolved))).hexdigest()
        else:
            if root.resolve() not in resolved.resolve().parents:
                raise BuildError('input path escapes root: ' + relative)
            observed = sha256(regular(resolved))
        if observed != expected:
            raise BuildError('input bytes differ: ' + relative)


class Runner:
    def bytes(self, argv, cwd):
        # NUL-delimited Git paths may contain CR and CRLF. Text-mode pipes
        # normalize those bytes and can redirect provenance checks to a decoy.
        result = subprocess.run(argv, cwd=cwd, env=ENV,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode:
            raise BuildError('identity command failed: ' + json.dumps(argv) + ': ' +
                             result.stderr.decode('utf-8', 'replace'))
        return result.stdout

    def phase(self, script, cwd, env, log):
        # File-backed stdout is visible during a long build, including SIGKILL.
        with log.open('ab', buffering=0) as stream:
            return subprocess.run(['/usr/bin/bash', '--noprofile', '--norc', '-p',
                                   '-e', '-o', 'pipefail', str(script)], cwd=cwd,
                                  env=env, stdout=stream, stderr=subprocess.STDOUT,
                                  check=False).returncode


def verify_inputs(repo, candidate, assets, manifest, runner):
    if (not isinstance(manifest, dict) or manifest.get('schema') != INPUT_SCHEMA or
            manifest.get('ihk_sha') != EXPECTED_IHK_HEAD):
        raise BuildError('input schema or IHK identity differs')
    if not re.fullmatch('[0-9a-f]{40}', candidate) or manifest.get('candidate_sha') != candidate:
        raise BuildError('candidate identity differs')
    def git(root, *args):
        return runner.bytes(['/usr/bin/git', '-c', 'safe.directory=' + str(root),
                            '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
                            '-C', str(root), *args], repo)
    if git_head(git(repo, 'rev-parse', 'HEAD')) != candidate:
        raise BuildError('HEAD differs')
    if git_head(git(repo / 'ihk', 'rev-parse', 'HEAD')) != EXPECTED_IHK_HEAD:
        raise BuildError('submodule identity differs')
    # The production candidate is prepared from pristine IHK and then has the
    # single reviewed overlay applied.  Test fixtures may substitute another
    # IHK identity; those retain the historical pristine-only contract.
    production_overlay = EXPECTED_IHK_HEAD == REVIEWED_IHK_HEAD
    overlay = manifest.get('ihk_overlay')
    if production_overlay:
        expected_overlay = {
            'asset': IHK_OVERLAY_ASSET,
            'path': IHK_OVERLAY_PATH,
            'patch_sha256': IHK_OVERLAY_PATCH_SHA256,
            'base_sha256': IHK_OVERLAY_BASE_SHA256,
            'result_sha256': IHK_OVERLAY_RESULT_SHA256,
        }
        if overlay != expected_overlay:
            raise BuildError('IHK overlay contract differs')
    elif overlay is not None:
        raise BuildError('unexpected IHK overlay contract')
    files, gitlinks = source_inventory(repo, git, allow_ihk_overlay=production_overlay)
    if manifest.get('gitlinks') != gitlinks or gitlinks.get('ihk') != EXPECTED_IHK_HEAD:
        raise BuildError('gitlink inventory differs')
    # Manifest must cover every ordinary tracked file, not a convenient subset.
    if set(manifest.get('repository_files', {})) != set(files):
        raise BuildError('consumed source inventory incomplete')
    if manifest['repository_files'] != files:
        raise BuildError('input bytes differ from manifest')
    if production_overlay:
        verify_ihk_overlay(repo, git, applied=True)
    if set(manifest.get('assets', {})) != {ARCHIVE, BASELINE, SRPM, DEBRAND}:
        raise BuildError('asset inventory incomplete')
    for name, expected_hash in ASSET_HASHES.items():
        if manifest['assets'][name] != expected_hash:
            raise BuildError('unpinned source asset: ' + name)
    bound_files(assets, manifest['assets'])
    if sha256(regular(Path(__file__))) != manifest.get('driver_sha256'):
        raise BuildError('executed driver identity differs')


def workflow_bodies(text):
    """Strictly read literal blocks; do not interpret actions, expressions or jobs."""
    job = text.split('\n  exact-build:\n', 1)
    if len(job) != 2:
        raise BuildError('exact-build job missing')
    job = re.split(r'\n  [a-zA-Z0-9_-]+:\n', job[1], maxsplit=1)[0]
    result = {}
    for chunk in job.split('      - name: ')[1:]:
        name, _, tail = chunk.partition('\n')
        if name not in STEPS:
            continue
        if name in result or '        run: |\n' not in tail:
            raise BuildError('ambiguous workflow step: ' + name)
        lines = tail.split('        run: |\n', 1)[1].splitlines()
        body = []
        for line in lines:
            if line and not line.startswith('          '):
                break
            body.append(line[10:] if line else '')
        result[name] = '\n'.join(body).rstrip() + '\n'
    if tuple(result) != STEPS:
        raise BuildError('workflow phase set/order differs')
    phase2 = result[STEPS[2]]
    merge_group = '''"${kbuild_environment[@]}" /usr/bin/bash --noprofile --norc -p \\
  "$NATIVE_SOURCE_ROOT/scripts/kconfig/merge_config.sh" -m -O "$BUILD_DIR" \\
  "$BUILD_DIR/.config" \\
  "$GITHUB_WORKSPACE/host-kernel/rocky/configs/rust-minimal.config" \\
  "$GITHUB_WORKSPACE/host-kernel/rocky/configs/native-rust-evidence.config"
'''
    if phase2.count(merge_group) != 1:
        raise BuildError('merge_config adaptation anchor changed')
    adapted_merge_group = '''(
  cd "$BUILD_DIR"
  ''' + merge_group + ''')
'''
    phase2 = phase2.replace(merge_group, adapted_merge_group, 1)
    if phase2.count('cd "$BUILD_DIR"') != 1:
        raise BuildError('merge_config writable-build adaptation differs')
    result[STEPS[2]] = phase2
    acquisition = result[STEPS[1]]
    marker = 'archive="$SOURCE_ASSETS/' + ARCHIVE + '"\n'
    if acquisition.count(marker) != 1:
        raise BuildError('acquisition adaptation anchor changed')
    # SRPM is independently hash-bound. Extract its debrand object into disposable
    # space and compare before accepting the separately mounted debrand bytes.
    prefix = '''set -euo pipefail
github_env_file="$GITHUB_ENV"
github_path_file="$GITHUB_PATH"
unset GITHUB_ENV GITHUB_PATH
srpm="$SOURCE_ASSETS/kernel-6.12.0-211.44.1.el10_2.src.rpm"
mkdir -p "$SOURCE_PARENT" "$RUNNER_TEMP/srpm-check"
(cd "$RUNNER_TEMP/srpm-check" && rpm2cpio "$srpm" | cpio -idm --quiet --no-absolute-filenames 1000-debrand-some-messages.patch)
cmp "$RUNNER_TEMP/srpm-check/1000-debrand-some-messages.patch" "$SOURCE_ASSETS/1000-debrand-some-messages.patch"
'''
    result[STEPS[1]] = prefix + marker + acquisition.split(marker, 1)[1]
    validation = result[STEPS[4]]
    start = 'EVIDENCE_DIR="$EVIDENCE_DIR" /usr/bin/python3 -E -s <<\'PY\'\n'
    end = 'PY\n# Preserve the exact binaries'
    if validation.count(start) != 1 or validation.count(end) != 1:
        raise BuildError('GitHub provenance adaptation anchor changed')
    before, remainder = validation.split(start, 1)
    _, after = remainder.split(end, 1)
    result[STEPS[4]] = before + '# Local provenance is retained by the offline owner.\n# Preserve the exact binaries' + after
    return result


def verify_artifacts(root):
    for name in ARTIFACTS:
        if regular(root / name).stat().st_size == 0:
            raise BuildError('empty required artifact: ' + name)
    rows = {}
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([^/\x00]+)', line)
        if not match or match[2] in rows or match[2] in ('.', '..', 'SHA256SUMS'):
            raise BuildError('invalid checksum inventory')
        rows[match[2]] = match[1]
    actual = {p.name for p in root.iterdir() if p.is_file() and p.name != 'SHA256SUMS'}
    if set(rows) != actual:
        raise BuildError('checksum inventory incomplete')
    bound_files(root, rows)


def temporary_environment(root, evidence_root):
    """Bind every phase's temporary files to the reviewed executable mount.

    Do not resolve links before checking them: a lexical evidence path must not
    silently redirect fixture executables outside the retained build evidence.
    Mount execution policy remains part of the separately reviewed container
    profile; directory search permission alone cannot prove a mount is exec.
    """
    root, evidence_root = Path(root), Path(evidence_root)
    if any(not p.is_absolute() or '..' in p.parts for p in (root, evidence_root)):
        raise BuildError('temporary root must be absolute without traversal')
    try:
        root.relative_to(evidence_root)
    except ValueError:
        raise BuildError('temporary root escapes evidence build root')
    try:
        for path in reversed((root,) + tuple(root.parents)):
            if not stat.S_ISDIR(path.lstat().st_mode):
                raise BuildError('temporary root component is not a real directory: ' + str(path))
        mode = root.lstat().st_mode
        if (not mode & 0o222 or not mode & 0o111 or
                not os.access(str(root), os.W_OK | os.X_OK)):
            raise BuildError('temporary root is not writable/searchable: ' + str(root))
    except OSError as exc:
        raise BuildError('temporary root is unavailable: ' + str(root) + ': ' + str(exc))
    return {key: str(root) for key in ('RUNNER_TEMP', 'TMPDIR', 'TMP', 'TEMP')}


def run(repo, candidate, assets, output, evidence, manifest, runner=None):
    repo, assets, output = [Path(p).resolve() for p in (repo, assets, output)]
    evidence = Path(evidence)
    # Validate existing ancestors before creating a fresh evidence directory.
    temporary_environment(evidence.parent, evidence.parent)
    evidence.mkdir(parents=True, exist_ok=False)
    runner = runner or Runner()
    receipt = {'status': 'FAIL', 'candidate_sha': candidate, 'phase': 'identity',
               'scope': 'local exact-build only; no application/production acceptance',
               'commands': [], 'started_at': time.time()}
    try:
        temporary_env = temporary_environment(evidence, evidence)
        if any(output.iterdir()):
            raise BuildError('output is not fresh')
        for i, path in enumerate((repo, assets, output, evidence)):
            for other in (repo, assets, output, evidence)[i + 1:]:
                if path == other or path in other.parents or other in path.parents:
                    raise BuildError('roots overlap')
        inputs = json.loads(regular(Path(manifest)).read_text())
        verify_inputs(repo, candidate, assets, inputs, runner)
        bodies = workflow_bodies(regular(repo / WORKFLOW).read_text())
        env = dict(ENV, GITHUB_WORKSPACE=str(repo), EXPECTED_HEAD_SHA=candidate,
                   SOURCE_ASSETS=str(assets),
                   SOURCE_PARENT=str(output / 'source'), BUILD_DIR=str(output / 'build'),
                   GITHUB_ENV=str(evidence / 'phase.env'), GITHUB_PATH=str(evidence / 'phase.path'))
        # Runner.phase execs a fresh shell, and workflow Python commands start
        # fresh interpreters. Thus tempfile's cached parent-process choice does
        # not override this environment (including under Python -E -s).
        env.update(temporary_env)
        (evidence / 'phase.env').touch()
        (evidence / 'phase.path').touch()
        atomic(evidence / 'local-provenance.json', {
            'candidate_sha': candidate, 'ihk_sha': EXPECTED_IHK_HEAD,
            'manifest_sha256': sha256(Path(manifest)), 'driver_sha256': sha256(Path(__file__)),
            'workflow_sha256': sha256(repo / WORKFLOW), 'github_run': False})
        for index, name in enumerate(STEPS):
            receipt['phase'] = name
            script = evidence / ('phase-%d.sh' % index)
            script.write_text(bodies[name])
            row = {'name': name, 'script_sha256': sha256(script), 'exit_code': None}
            receipt['commands'].append(row)
            atomic(evidence / 'receipt.json', receipt)
            row['exit_code'] = runner.phase(script, repo, env, evidence / 'driver.log')
            atomic(evidence / 'receipt.json', receipt)
            if row['exit_code']:
                raise BuildError('workflow phase failed: ' + name)
            for line in (evidence / 'phase.env').read_text().splitlines():
                key, separator, value = line.partition('=')
                if not separator or key not in ('NATIVE_SRPM', 'NATIVE_SOURCE_ROOT', 'NATIVE_BASELINE_CONFIG', 'NATIVE_BUILD_DIR'):
                    raise BuildError('unexpected workflow environment export')
                env[key] = value
        receipt['phase'] = 'artifact-verification'
        verify_artifacts(evidence / 'native-rust-build-evidence')
        # Verify input bytes again before promotion (mounts are read-only but the
        # host owner may still be able to mutate its underlying directories).
        verify_inputs(repo, candidate, assets, inputs, runner)
        receipt['status'] = 'PASS'
        receipt['phase'] = 'complete'
    except BaseException as exc:
        receipt['error'] = str(exc)
    finally:
        receipt['finished_at'] = time.time()
        receipt['inventory'] = {
            str(p.relative_to(evidence)): {'sha256': sha256(p), 'size': p.stat().st_size}
            for p in sorted(evidence.rglob('*')) if p.is_file() and not p.is_symlink()
            and p.name != 'receipt.json'}
        receipt['partial_outputs'] = {
            str(p.relative_to(output)): {'sha256': sha256(p), 'size': p.stat().st_size}
            for p in sorted(output.rglob('*')) if p.is_file() and not p.is_symlink()}
        atomic(evidence / 'receipt.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    for name in ('repo', 'candidate', 'assets', 'output', 'evidence', 'manifest'):
        parser.add_argument('--' + name, required=True)
    result = run(**vars(parser.parse_args()))
    print(json.dumps(result))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
