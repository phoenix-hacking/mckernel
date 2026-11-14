#!/usr/bin/env python3
"""Compile a source-bound, independently reviewed packet in the native container.

This captures compiler inputs and native ELF/DSO identities; it never executes
an application, changes its oracle, or enables a runtime packet.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(path):
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(chunk)
            digest.update(chunk)
    return dict(path=str(path), size=size, sha256=digest.hexdigest())


def strict_json(path):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'duplicate JSON key: ' + key)
            value[key] = item
        return value

    def constant(value):
        raise ValueError('nonfinite JSON value: ' + value)

    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_constant=constant)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--attempt', type=Path, required=True)
    args = parser.parse_args()
    require(os.getuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5},
            'run through the pinned native container wrapper')
    require(args.attempt.is_absolute() and args.attempt.parent.resolve() == Path('/work'),
            'attempt must be a fresh direct child of /work')
    require(shutil.disk_usage('/work').free >= 3 * 1024**3, 'scratch reserve below 3 GiB')
    args.attempt.mkdir(mode=0o700)
    out, repo = args.attempt, Path('/workspace')
    (out / 'tmp').mkdir()
    build_environment = dict(PATH='/usr/local/bin:/usr/bin:/bin', LANG='C', LC_ALL='C',
                             TZ='UTC', TMPDIR=str(out / 'tmp'))
    record = dict(schema_version=1, status='RUNNING',
                  started_utc=datetime.now(timezone.utc).isoformat(), commands=[],
                  checked_inputs=[], cases=[], compiler_dependencies=[],
                  scope='independently reviewed fixture compilation and ELF inspection only',
                  linux_reference_executed=False, mckernel_application_executed=False,
                  application_acceptance=False, production_gate_credit=False)
    record['command_environment'] = build_environment
    record['isolation_authority'] = 'external pinned container-run.py wrapper and its retained invocation'
    record['ldd_scope'] = 'ELF loader dependency tracing only; no payload main/reference execution credit'

    def save():
        temporary = out / 'record.json.tmp'
        with temporary.open('w') as stream:
            json.dump(record, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(out / 'record.json')

    def check(row):
        path = Path(row['path'])
        if not path.is_absolute():
            path = repo / path
        require(path.resolve().is_relative_to(repo), 'reviewed input outside repository')
        actual = identity(path)
        require(actual['size'] == row['size'] and actual['sha256'] == row['sha256'],
                'reviewed input changed: ' + str(path))
        record['checked_inputs'].append(actual)
        return path

    def run(label, argv, timeout=60):
        record['phase'] = label
        entry = dict(label=label, argv=argv, cwd=str(out), timeout_seconds=timeout)
        record['commands'].append(entry)
        save()
        print('RUN', label, flush=True)
        with (out / (label + '.log')).open('xb') as stream:
            result = subprocess.run(argv, cwd=str(out), stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout, env=build_environment)
        entry['exit_code'] = result.returncode
        save()
        require(result.returncode == 0, 'command failed: ' + label)
        return (out / (label + '.log')).read_text()

    try:
        shutil.copyfile(__file__, out / 'helper.py')
        record['helper'] = identity(out / 'helper.py')
        packet_path, review_path = args.packet.resolve(), args.review.resolve()
        require(packet_path.is_relative_to(repo) and review_path.is_relative_to(repo),
                'packet and independent review must be repository artifacts')
        packet, review = strict_json(packet_path), strict_json(review_path)
        record['packet'] = identity(packet_path)
        record['independent_review'] = identity(review_path)
        require(review['compile_authorized'] is True, 'independent review has not authorized compilation')
        require(review['runtime_authorized'] is False and review['execution_enabled'] is False,
                'independent review must retain compile-only scope')
        require(check(review['reviewed_packet']) == packet_path, 'review binds a different packet')
        require(packet['execution_enabled'] is False and packet['mode'] == 'fixture-review-and-compile',
                'compile-only helper requires a compile-only packet')
        require(packet['active_cases_max'] == 3 and 1 <= len(packet['cases']) <= 3,
                'packet exceeds the three active-case limit')
        require(packet['case_ids'] == [case['case_id'] for case in packet['cases']]
                and len(set(packet['case_ids'])) == len(packet['case_ids']), 'case membership differs')
        catalog = strict_json(check(packet['catalog']))
        catalog_cases = {case['id']: case for case in catalog['cases']}
        check(packet['original_packet'])
        require(review['reviewed_sources'] == [case['source'] for case in packet['cases']]
                and review['reviewed_oracles'] == [case['oracle'] for case in packet['cases']],
                'independent source/oracle review membership differs')
        for row in review['current_launcher_sources']:
            check(row['current'])
        record['source_commit'] = run('source-commit', ['git', '-C', str(repo), 'rev-parse', 'HEAD']).strip()
        run('source-status', ['git', '-C', str(repo), 'status', '--porcelain'])
        run('source-diff', ['git', '-C', str(repo), 'diff', '--binary', 'HEAD'])
        run('source-diff-check', ['git', '-C', str(repo), 'diff', '--check'])
        record['compiler_version'] = run('compiler-version', ['cc', '--version'])
        record['compiler_tools'] = []
        for tool in ('cc', 'as', 'ld', 'readelf', 'objdump', 'ldd'):
            path = Path(shutil.which(tool, path=build_environment['PATH'])).resolve()
            record['compiler_tools'].append(identity(path))
        compiler_frontend = Path(run('compiler-frontend', ['cc', '-print-prog-name=cc1']).strip()).resolve()
        record['compiler_tools'].append(identity(compiler_frontend))
        for case in packet['cases']:
            case_id = case['case_id']
            require(re.fullmatch(r'[a-z0-9][a-z0-9.-]+', case_id) is not None, 'invalid case ID')
            original, oracle = check(case['source']), check(case['oracle'])
            require(original.suffix == '.c', 'this helper supports reviewed C fixtures only')
            case_out = out / case_id
            case_out.mkdir()
            source, executable = case_out / original.name, case_out / 'payload'
            shutil.copyfile(original, source)
            shutil.copyfile(oracle, case_out / 'oracle.json')
            for copied, expected in ((source, case['source']), (case_out / 'oracle.json', case['oracle'])):
                actual = identity(copied)
                require(actual['size'] == expected['size'] and actual['sha256'] == expected['sha256'],
                        'copied reviewed input differs: ' + str(copied))
            dependency_file = case_out / 'compiler.d'
            contract = catalog_cases[case_id]['payload_contract']
            require(contract['build_profile'] == 'ordinary-dynamic-etexec-c11', 'unsupported build profile')
            macros = contract['feature_test_macros']
            require(macros == ['_GNU_SOURCE'], 'unreviewed compiler feature macros')
            object_file = case_out / 'payload.o'
            run(case_id + '-compile', ['cc', '-std=c11', '-O2', '-g', '-Wall', '-Wextra', '-Werror',
                '-fno-pie', '-pthread', '-D_GNU_SOURCE', '-MD', '-MF', str(dependency_file),
                '-c', str(source), '-o', str(object_file)])
            run(case_id + '-link', ['cc', '-no-pie', '-pthread', '-Wl,-z,noexecstack',
                '-Wl,-Map,' + str(case_out / 'link.map'), str(object_file), '-o', str(executable)])
            elf = run(case_id + '-elf', ['readelf', '-h', '-l', '-d', str(executable)])
            require('ELF64' in elf and 'EXEC (Executable file)' in elf and 'INTERP' in elf,
                    'expected dynamic x86_64 ET_EXEC')
            require('Advanced Micro Devices X86-64' in elf, 'wrong machine')
            interpreter = re.findall(r'Requesting program interpreter: ([^\]]+)\]', elf)
            require(len(interpreter) == 1, 'expected one interpreter')
            run(case_id + '-disassembly', ['objdump', '-d', str(executable)])
            libraries = run(case_id + '-libraries', ['ldd', str(executable)])
            require('not found' not in libraries, 'unresolved runtime library')
            dependencies = sorted(set(re.findall(r'(/[^\s()]+)\s+\(0x[0-9a-f]+\)', libraries)))
            require(interpreter[0] in dependencies, 'interpreter missing from runtime captures')
            runtime = []
            for name in dependencies:
                path = Path(name)
                target = case_out / 'runtime' / name.lstrip('/')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                original_library, captured_library = identity(path), identity(target)
                require((original_library['size'], original_library['sha256']) ==
                        (captured_library['size'], captured_library['sha256']), 'copied DSO differs')
                runtime.append(dict(original=original_library, captured=captured_library))
            compiler_paths = set(dependency_file.read_text().replace('\\\n', ' ').split()[1:])
            compiler_paths.update(re.findall(r'^LOAD (/.+)$', (case_out / 'link.map').read_text(), re.M))
            for name in sorted(compiler_paths):
                path = Path(name)
                require(path.is_absolute() and path.is_file(), 'unresolved compiler input: ' + name)
                record['compiler_dependencies'].append(identity(path))
            record['cases'].append(dict(case_id=case_id, source=identity(source),
                executable=identity(executable), oracle=identity(case_out / 'oracle.json'),
                interpreter=interpreter[0], runtime_libraries=runtime,
                compile_status='PASS', runtime_status='NOT_RUN', acceptance_status='NOT_RUN'))
            save()
        for row in record['checked_inputs'] + record['compiler_tools'] + record['compiler_dependencies']:
            require(identity(Path(row['path'])) == row, 'input changed during compilation: ' + row['path'])
        for case in record['cases']:
            for library in case['runtime_libraries']:
                for row in (library['original'], library['captured']):
                    require(identity(Path(row['path'])) == row, 'runtime library changed during compilation')
        require(identity(review_path) == record['independent_review'], 'review changed during compilation')
        require(identity(packet_path) == record['packet'], 'packet changed during compilation')
        record.update(status='PASS', phase='complete')
    except BaseException as exc:
        record.update(status='FAIL', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        record['finished_utc'] = datetime.now(timezone.utc).isoformat()
        record['outputs'] = [identity(path) for path in sorted(out.rglob('*'))
                             if path.is_file() and path.name not in ('record.json', 'record.json.tmp')]
        save()
        print(record['status'], out, flush=True)


if __name__ == '__main__':
    main()
