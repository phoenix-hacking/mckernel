"""Exactly two admitted lower-IPI metadata reads and called source-object gate; no link."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
import ipi_lower_checks


def main():
    request = Path(sys.argv[1])
    q = json.loads(request.read_text())
    p = request.parent
    rows = []
    phase = 'bindings'
    receipt = {'request_path': str(request), 'request_sha256': hashlib.sha256(request.read_bytes()).hexdigest(), 'compiled_input': q['compiled_input'], 'controller_pid': os.getpid(), 'controller_birth_ticks': Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19], 'commands': rows}
    def save():
        with (p / 'METADATA-EXECUTION.json').open('w') as stream:
            json.dump(receipt, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
    try:
        for path, digest in q['inputs'].items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
        assert [row['label'] for row in q['commands']] == ['provider-symbols', 'provider-elf']
        assert hashlib.sha256(Path(q['compiled_input']['path']).read_bytes()).hexdigest() == q['compiled_input']['sha256']
        for command in q['commands']:
            phase = command['label']
            row = dict(label=phase, argv=command['argv'], stdout_path=command['stdout_path'], stderr_path=command['stderr_path'], environment_replace=q['environment_replace'], pid=None, birth_ticks_before_wait=None, direct_wait_joined=False, start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            rows.append(row)
            started = time.monotonic()
            with Path(command['stdout_path']).open('xb') as out, Path(command['stderr_path']).open('xb') as err:
                child = subprocess.Popen(command['argv'], cwd=q['cwd'], env=q['environment_replace'], stdin=subprocess.DEVNULL, stdout=out, stderr=err)
                row['pid'] = child.pid
                try:
                    row['birth_ticks_before_wait'] = Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
                    save()
                finally:
                    status = child.wait()
                    row.update(returncode=status, direct_wait_joined=True, wall_seconds=time.monotonic()-started)
                    save()
            row['stdout_sha256'] = hashlib.sha256(Path(command['stdout_path']).read_bytes()).hexdigest()
            row['stderr_sha256'] = hashlib.sha256(Path(command['stderr_path']).read_bytes()).hexdigest()
            save()
            assert status == 0, phase
            assert Path(command['stderr_path']).read_bytes() == b'', phase+' unexpected diagnostic'
        phase = 'called-finite-source-object-metadata-gate'
        decision = ipi_lower_checks.actual_object_gate(q)
        (p/'OBJECT-CHECK.json').write_text(json.dumps(decision,indent=2)+'\n')
        receipt.update(status='PASS_ACTUAL_IPI_LOWER_FOUR_FUNCTION_READ_SLOT_METADATA_READS_AND_CALLED_CONTENT_OWNER_GATE', object_gate_called=True, CPU6_released=True, all_started_children_joined=True, no_compile_link_runtime=True)
        save()
        print(json.dumps(receipt,indent=2))
        return 0
    except BaseException as error:
        receipt.update(status='FIRST_UNEXPECTED_FAILURE_STOP_NO_AUTOMATIC_RETRY', phase=phase, error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(), all_started_children_joined=all(row['pid'] is None or row['direct_wait_joined'] for row in rows))
        receipt['CPU6_released'] = receipt['all_started_children_joined']
        save()
        (p/'METADATA-FIRST-FAILURE.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt,indent=2))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
