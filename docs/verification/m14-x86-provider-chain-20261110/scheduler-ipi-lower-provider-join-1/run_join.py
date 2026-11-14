"""Three literal new two-operand partial-link/readback commands; persisted prejoin before any Popen."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import traceback
import ipi_lower_join_checks


def persist(path, value):
    with path.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    request = Path(sys.argv[1])
    q = json.loads(request.read_text())
    p = request.parent
    rows = []
    phase = 'bindings'
    prejoin_passed = False
    try:
        assert os.sched_getaffinity(0) == {6}, 'Root admission must bind controller/predicate overhead to CPU6'
        assert [row['label'] for row in q['commands']] == ['partial-link','joined-symbols','joined-elf']
        assert not Path(q['joined_object']).exists()
        phase = 'called-exact-two-operand-source-owner-prejoin'
        decision = ipi_lower_join_checks.prejoin(q)
        persist(p/'JOIN-PREJOIN-CHECK.json', decision)
        prejoin_passed = True
        Path(q['output_directory']).mkdir(exist_ok=False)
        for command in q['commands']:
            phase = command['label']
            if phase == 'partial-link':
                assert prejoin_passed and (p/'JOIN-PREJOIN-CHECK.json').is_file()
            row = dict(label=phase, argv=command['argv'], pid=None, birth_ticks_before_wait=None,
                       returncode=None, direct_wait_joined=False)
            rows.append(row)
            with Path(command['stdout_path']).open('xb') as stdout, Path(command['stderr_path']).open('xb') as stderr:
                child = subprocess.Popen(command['argv'], cwd=q['cwd'], env=q['environment_replace'],
                                         stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
                row['pid'] = child.pid
                try:
                    try:
                        row['birth_ticks_before_wait'] = Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
                    except OSError as error:
                        row['birth_observation_error'] = type(error).__name__
                    persist(p/'JOIN-COMMANDS.json', rows)
                finally:
                    status = child.wait()
                    row.update(returncode=status, direct_wait_joined=True)
                    persist(p/'JOIN-COMMANDS.json', rows)
            assert row['birth_ticks_before_wait'] is not None, 'Preserve unknown birth and stop, no retry'
            assert status == 0, phase
            assert Path(command['stderr_path']).read_bytes() == b'', phase+' unexpected diagnostics'
        phase = 'called-actual-two-operand-postjoin'
        decision = ipi_lower_join_checks.postjoin(q)
        persist(p/'POSTJOIN-CHECK.json', decision)
        result = dict(status='PASS_CURRENT112_PLUS_GENUINE_IPI_LOWER_PARTIAL',
                      request_sha256=hashlib.sha256(request.read_bytes()).hexdigest(),
                      actual_inputs=q['object_inputs'],
                      actual_joined_object_sha256=hashlib.sha256(Path(q['joined_object']).read_bytes()).hexdigest(),
                      actual_prejoin_called_persisted_before_ld_r=prejoin_passed, actual_postjoin_called=True,
                      all3_direct_waits_joined=True, CPU6_released=True, commands=rows,
                      global_owners=decision['global_strong'], global_T=decision['global_T'], global_data=decision['global_data'],
                      actual_remaining_genuine_U=decision['actual_remaining_genuine_U'],
                      no_compiler_provider_metadata_replay_function_IRQ_boot_native_default_Cretirement_or_score=True)
        persist(p/'JOIN-RESULT.json', result)
        print(json.dumps(result,indent=2))
        return 0
    except BaseException as error:
        result = dict(status='FIRST_ACTUAL_FAILURE_STOP_FOCUSED_REVIEW_NO_AUTOMATIC_RETRY', phase=phase,
                      error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(), commands=rows,
                      all_started_children_joined=all(row['pid'] is None or row['direct_wait_joined'] for row in rows))
        result['CPU6_released'] = result['all_started_children_joined']
        persist(p/'JOIN-FIRST-FAILURE.json', result)
        print(json.dumps(result,indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
