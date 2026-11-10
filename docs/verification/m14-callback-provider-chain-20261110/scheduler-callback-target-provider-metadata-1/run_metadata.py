"""Two literal admitted target5 metadata readbacks and called object gate; no link."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import traceback
import metadata_checks


def persist(path, value):
    with path.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    request = Path(sys.argv[1])
    q = json.loads(request.read_text())
    root = request.parent
    rows = []
    receipt = dict(request_path=str(request), request_sha256=hashlib.sha256(request.read_bytes()).hexdigest(),
                   controller_pid=os.getpid(), controller_birth=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19], commands=rows)
    phase = 'bindings'
    try:
        assert os.sched_getaffinity(0) == {6}, 'Root must bind controller/gate overhead CPU6'
        for path, digest in q['inputs'].items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
        assert [row['label'] for row in q['commands']] == ['provider-symbols','provider-elf']
        for command in q['commands']:
            phase = command['label']
            row = dict(label=phase, argv=command['argv'], pid=None, birth_before_wait=None, direct_wait_joined=False)
            rows.append(row)
            with Path(command['stdout_path']).open('xb') as out, Path(command['stderr_path']).open('xb') as err:
                child = subprocess.Popen(command['argv'], cwd=q['cwd'], env=q['environment_replace'],
                                         stdin=subprocess.DEVNULL, stdout=out, stderr=err)
                row['pid'] = child.pid
                try:
                    try:
                        row['birth_before_wait'] = Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
                    except OSError as error:
                        row['birth_observation_error'] = type(error).__name__
                    persist(root/'METADATA-EXECUTION.json', receipt)
                finally:
                    status = child.wait()
                    row.update(returncode=status, direct_wait_joined=True)
                    persist(root/'METADATA-EXECUTION.json', receipt)
            row.update(stdout_sha256=hashlib.sha256(Path(command['stdout_path']).read_bytes()).hexdigest(),
                       stderr_sha256=hashlib.sha256(Path(command['stderr_path']).read_bytes()).hexdigest())
            persist(root/'METADATA-EXECUTION.json', receipt)
            assert row['birth_before_wait'] is not None, 'Missing birth remains UNKNOWN; stop without replay'
            assert status == 0 and Path(command['stderr_path']).read_bytes() == b'', phase
        phase = 'called-actual-five-target-rdmsr-object-gate'
        decision = metadata_checks.actual_object_gate(q)
        persist(root/'OBJECT-CHECK.json', decision)
        receipt.update(status='PASS_TWO_TARGET5_READBACKS_AND_CALLED_OBJECT_GATE', object_gate_called=True,
                       object_sha256=decision['object_sha256'], all_started_children_joined=True, CPU6_released=True,
                       no_compiler_link_function_runtime=True)
        persist(root/'METADATA-EXECUTION.json', receipt)
        print(json.dumps(receipt, indent=2))
        return 0
    except BaseException as error:
        receipt.update(status='FIRST_UNEXPECTED_FAILURE_STOP_NO_AUTOMATIC_RETRY', phase=phase,
                       error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(),
                       all_started_children_joined=all(row['pid'] is None or row['direct_wait_joined'] for row in rows))
        receipt['CPU6_released'] = receipt['all_started_children_joined']
        persist(root/'METADATA-EXECUTION.json', receipt)
        persist(root/'METADATA-FIRST-FAILURE.json', receipt)
        print(json.dumps(receipt, indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
