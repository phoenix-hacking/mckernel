#!/usr/bin/env python3
"""Inside-container diagnostic final-step reuse; never a fresh-build PASS.

The separately owned container mounts frozen candidate /src and retained /out
read-only, the reviewed lifecycle checker read-only over its original path,
old evidence at /prior read-only, and an empty executable /capture writable.
This payload neither creates containers nor grants execution authority.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat

CANDIDATE = '942c927b1ec93cc31284ff498455909d9bb2d0fc'
CHECKER_SHA256 = '89e11f815960ba0159190c398e8292947b2491bcafdbf1713525a824e28ee437'
SOURCE = Path('/src')
OUTPUT = Path('/out')
SEEDS = ('module-targets.txt', 'kconfig-solver-matrix.json')
EXPORTS = frozenset(('NATIVE_SRPM', 'NATIVE_SOURCE_ROOT', 'NATIVE_BASELINE_CONFIG', 'NATIVE_BUILD_DIR'))


class RevalidationError(RuntimeError):
    pass


def read_regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 8 * 1024 * 1024:
            raise RevalidationError('not a bounded regular input: ' + str(path))
        with os.fdopen(os.dup(fd), 'rb') as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_nlink', 'st_uid',
                  'st_gid', 'st_mtime_ns', 'st_ctime_ns')
        if any(getattr(after, key) != getattr(before, key) for key in fields) or len(raw) != before.st_size:
            raise RevalidationError('input changed: ' + str(path))
        return raw
    finally:
        os.close(fd)


def phase_environment(raw, driver, capture):
    values = {}
    for line in raw.decode('utf-8').splitlines():
        key, separator, value = line.partition('=')
        if not separator or key not in EXPORTS or key in values or not value:
            raise RevalidationError('unexpected retained phase environment')
        values[key] = value
    if set(values) != EXPORTS:
        raise RevalidationError('incomplete retained phase environment')
    if (values['NATIVE_SOURCE_ROOT'] != str(OUTPUT / 'source/linux-6.12.0-211.44.1.el10_2') or
            values['NATIVE_BUILD_DIR'] != str(OUTPUT / 'build')):
        raise RevalidationError('retained original /out path binding differs')
    return dict(driver.ENV, **values, GITHUB_WORKSPACE=str(SOURCE),
                EXPECTED_HEAD_SHA=CANDIDATE, BUILD_DIR=str(OUTPUT/'build'),
                SOURCE_PARENT=str(OUTPUT/'source'), GITHUB_ENV=str(capture/'phase.env'),
                GITHUB_PATH=str(capture/'phase.path'),
                **{key: str(capture) for key in ('RUNNER_TEMP', 'TMPDIR', 'TMP', 'TEMP')})


def load_driver():
    spec = importlib.util.spec_from_file_location('_retained_exact_driver', SOURCE/'scripts/native_rust_exact_build_offline.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(*, prior=Path('/prior'), capture=Path('/capture'), driver=None, runner=None):
    prior, capture = Path(prior), Path(capture)
    for path in (SOURCE, OUTPUT, prior, capture):
        if not path.is_absolute() or path.resolve(strict=True) != path or not path.is_dir():
            raise RevalidationError('canonical existing directory required: ' + str(path))
    roots = (SOURCE, OUTPUT, prior, capture)
    if any(a == b or a in b.parents or b in a.parents for i, a in enumerate(roots) for b in roots[i+1:]):
        raise RevalidationError('capture/input roots overlap')
    if any(capture.iterdir()):
        raise RevalidationError('capture is not fresh/empty')
    checker = read_regular(SOURCE/'scripts/ihk_native_lifecycle_check.py')
    if hashlib.sha256(checker).hexdigest() != CHECKER_SHA256:
        raise RevalidationError('reviewed diagnostic checker overlay differs')
    driver = driver or load_driver()
    environment = phase_environment(read_regular(prior/'phase.env'), driver, capture)
    body = driver.workflow_bodies((SOURCE/driver.WORKFLOW).read_text())[driver.STEPS[4]]
    evidence = capture/'native-rust-build-evidence'
    evidence.mkdir()
    for name in SEEDS:
        with (evidence/name).open('xb') as stream:
            stream.write(read_regular(prior/'native-rust-build-evidence'/name))
    for name in ('phase.env', 'phase.path'):
        (capture/name).touch(exist_ok=False)
    script = capture/'phase-4.sh'
    with script.open('x') as stream:
        stream.write(body)
    result = {'candidate_sha': CANDIDATE, 'checker_overlay_sha256': CHECKER_SHA256,
              'status': 'FAIL', 'scope': 'retained-artifact diagnostic final checks only',
              'strict_fresh_build_pass': False, 'runtime_or_acceptance_credit': False}
    try:
        result['exit_code'] = (runner or driver.Runner()).phase(script, SOURCE, environment, capture/'driver.log')
        if result['exit_code']:
            raise RevalidationError('original final step failed; retained /out must remain read-only')
        if (evidence/'commit.sha').read_text().strip() != CANDIDATE:
            raise RevalidationError('original final-step candidate identity differs')
        driver.verify_artifacts(evidence)
        result['status'] = 'PASS_DIAGNOSTIC_FINAL_CHECKS'
        return result
    except BaseException as error:
        result['error'] = str(error)
        raise
    finally:
        with (capture/'result.json').open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior-evidence', type=Path, default=Path('/prior'))
    parser.add_argument('--capture', type=Path, default=Path('/capture'))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run(prior=args.prior_evidence, capture=args.capture), sort_keys=True))
    except (RevalidationError, OSError, ValueError) as error:
        parser.exit(1, str(error)+'\n')


if __name__ == '__main__':
    main()
