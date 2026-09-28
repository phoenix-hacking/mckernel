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
import subprocess
import sys
import time
import uuid

WORKFLOW = '.github/workflows/native-rust-host-modules-exact-build.yml'
EXPECTED_IHK_HEAD = '3114d9e7101ad52030eb3effa849a5c108972a1f'
ARCHIVE = 'linux-6.12.0-211.44.1.el10_2.tar.xz'
BASELINE = 'kernel-x86_64-rhel.config'
SRPM = 'kernel-6.12.0-211.44.1.el10_2.src.rpm'
DEBRAND = '1000-debrand-some-messages.patch'
ASSET_HASHES = {
    ARCHIVE: '4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533',
    BASELINE: '5bbdda60ce822ec903c85d3d8ddda1bfc9493216bed86c6c432683aa50dcf50d',
    SRPM: '2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb',
}
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
    def text(self, argv, cwd):
        result = subprocess.run(argv, cwd=cwd, env=ENV, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode:
            raise BuildError('identity command failed: ' + json.dumps(argv) + ': ' + result.stderr)
        return result.stdout

    def phase(self, script, cwd, env, log):
        # File-backed stdout is visible during a long build, including SIGKILL.
        with log.open('ab', buffering=0) as stream:
            return subprocess.run(['/usr/bin/bash', '--noprofile', '--norc', '-p',
                                   '-e', '-o', 'pipefail', str(script)], cwd=cwd,
                                  env=env, stdout=stream, stderr=subprocess.STDOUT,
                                  check=False).returncode


def verify_inputs(repo, candidate, assets, manifest, runner):
    if not re.fullmatch('[0-9a-f]{40}', candidate) or manifest.get('candidate_sha') != candidate:
        raise BuildError('candidate identity differs')
    def git(root, *args):
        return runner.text(['/usr/bin/git', '-c', 'safe.directory=' + str(root),
                            '-C', str(root), *args], repo)
    if git(repo, 'rev-parse', 'HEAD').strip() != candidate:
        raise BuildError('HEAD differs')
    if git(repo / 'ihk', 'rev-parse', 'HEAD').strip() != EXPECTED_IHK_HEAD:
        raise BuildError('submodule identity differs')
    for root in (repo, repo / 'ihk'):
        if git(root, 'status', '--porcelain', '--untracked-files=all').strip():
            raise BuildError('source checkout is dirty')
    # Bind gitlinks as Git object identities.  Only ihk is consumed by this job,
    # so its checked-out files are additionally covered below; unrelated
    # submodules need not be materialized merely to prove their exact gitlinks.
    gitlinks = {}
    for row in git(repo, 'ls-files', '-s', '-z').split('\0'):
        if not row:
            continue
        metadata, separator, path = row.partition('\t')
        fields = metadata.split()
        if not separator or len(fields) != 3:
            raise BuildError('malformed git index row')
        mode, object_id, stage = fields
        if mode == '160000':
            if stage != '0' or not re.fullmatch('[0-9a-f]{40}', object_id):
                raise BuildError('malformed gitlink identity')
            gitlinks[path] = object_id
    if manifest.get('gitlinks') != gitlinks or gitlinks.get('ihk') != EXPECTED_IHK_HEAD:
        raise BuildError('gitlink inventory differs')
    # Manifest must cover every ordinary tracked file, not a convenient subset.
    expected = set(git(repo, 'ls-files', '-z').split('\0')) - {''} - set(gitlinks)
    expected |= {'ihk/' + p for p in git(repo / 'ihk', 'ls-files', '-z').split('\0') if p}
    if set(manifest.get('repository_files', {})) != expected:
        raise BuildError('consumed source inventory incomplete')
    bound_files(repo, manifest['repository_files'], links=True)
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


def run(repo, candidate, assets, output, evidence, manifest, runner=None):
    repo, assets, output, evidence = [Path(p).resolve() for p in (repo, assets, output, evidence)]
    evidence.mkdir(parents=True, exist_ok=False)
    runner = runner or Runner()
    receipt = {'status': 'FAIL', 'candidate_sha': candidate, 'phase': 'identity',
               'scope': 'local exact-build only; no application/production acceptance',
               'commands': [], 'started_at': time.time()}
    try:
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
                   RUNNER_TEMP=str(evidence), SOURCE_ASSETS=str(assets),
                   SOURCE_PARENT=str(output / 'source'), BUILD_DIR=str(output / 'build'),
                   GITHUB_ENV=str(evidence / 'phase.env'), GITHUB_PATH=str(evidence / 'phase.path'))
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
