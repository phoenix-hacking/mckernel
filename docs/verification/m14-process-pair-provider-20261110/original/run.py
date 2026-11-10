"""Root-admitted finite six-command compile/read/link/read operation only."""
from pathlib import Path
import hashlib
import json
import os
import resource
import subprocess
import sys
import traceback
import checks


def persist(path, value):
    with path.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    request = Path(sys.argv[1]).resolve()
    q = json.loads(request.read_text())
    root = request.parent
    records = []
    phase = 'source-and-retained-object-bindings'
    try:
        assert os.sched_getaffinity(0) == {7}, 'Root must admit this controller inside CPU7'
        assert resource.getrlimit(resource.RLIMIT_AS)[0] == 1073741824
        assert not Path(q['output_directory']).exists()
        assert not (root/'RESULT.json').exists() and not (root/'FIRST-FAILURE.json').exists()
        assert [c['label'] for c in q['commands']] == ['provider-compile','provider-nm','provider-elf','partial-link','joined-nm','joined-elf']
        binding = checks.bindings(q)
        persist(root/'BINDINGS-CHECK.json', binding)
        Path(q['output_directory']).mkdir(exist_ok=False)
        prejoin = None
        for command in q['commands']:
            phase = command['label']
            if phase == 'partial-link':
                prejoin = checks.prejoin(q)
                persist(root/'PREJOIN-CHECK.json', prejoin)
                assert prejoin['called_before_ld_r']
            record = dict(label=phase, argv=command['argv'], pid=None, birth_ticks=None,
                          launch_attempted=False, returncode=None, direct_wait_joined=False)
            records.append(record)
            persist(root/'COMMANDS.json', records)
            with Path(command['stdout_path']).open('xb') as stdout, Path(command['stderr_path']).open('xb') as stderr:
                record['launch_attempted'] = True
                persist(root/'COMMANDS.json', records)
                child = subprocess.Popen(command['argv'], cwd=q['cwd'], env=q['environment_replace'],
                                         stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
                record['pid'] = child.pid
                try:
                    try:
                        record['birth_ticks'] = Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
                    except OSError as error:
                        record['birth_observation_error'] = type(error).__name__
                    persist(root/'COMMANDS.json', records)
                finally:
                    status = child.wait()
                    record.update(returncode=status, direct_wait_joined=True)
                    persist(root/'COMMANDS.json', records)
            assert record['birth_ticks'] is not None, 'Unknown birth: preserve and stop; no retry'
            assert status == 0, (phase, status)
            diagnostic = Path(command['stderr_path']).read_bytes()
            if phase == 'provider-compile':
                assert diagnostic == Path(q['expected_compile_stderr']['path']).read_bytes(), 'Changed compiler diagnostic: preserve actual failure and review'
                assert Path(command['stdout_path']).read_bytes() == b''
            else:
                assert diagnostic == b'', (phase, 'unexpected diagnostics')
        phase = 'actual-owner-and-relocation-postjoin'
        result = checks.postjoin(q)
        capture = result.pop('capture')
        persist(root/'ACTUAL-JOINED-METADATA.json', capture)
        persist(root/'POSTJOIN-CHECK.json', result)
        result.update(request_sha256=hashlib.sha256(request.read_bytes()).hexdigest(), commands=records,
                      all6_direct_waits_joined=all(x['direct_wait_joined'] for x in records),
                      actual_prejoin_called_before_ld_r=True, actual_postjoin_called=True,
                      actual_provider_sha256=checks.sha(q['provider_object']), actual_source_manifest_sha256=checks.sha(q['source_manifest']),
                      scope='New finite genuine process-pair source/codegen/partial-link prerequisite only; no kernel function, old suite, native instruction, boot, C retirement or image/default acceptance.')
        persist(root/'RESULT.json', result)
        print(json.dumps({k: v for k, v in result.items() if k not in ['all_source_owners_preserved','normalized_source_relocations','commands']}, indent=2))
        return 0
    except BaseException as error:
        result = dict(status='FIRST_ACTUAL_FAILURE_STOP_REVIEW_NO_AUTOMATIC_RETRY', phase=phase,
                      error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(), commands=records,
                      all_started_direct_children_joined=all(x['pid'] is None or x['direct_wait_joined'] for x in records),
                      old_CPU0_UNKNOWN_released=False)
        persist(root/'FIRST-FAILURE.json', result)
        print(json.dumps(result, indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
