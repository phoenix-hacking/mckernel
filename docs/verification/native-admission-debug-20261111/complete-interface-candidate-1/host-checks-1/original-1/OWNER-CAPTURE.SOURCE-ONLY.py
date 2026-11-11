"""Thin existing-Owner batch body, invoked only inside Root's admitted capture.

This function performs no resource/account/native admission. Root must first
bind the independent review, actual shared profile, source/input pins and fresh
exclusive output. It is source only and has no CLI execution entry point.
"""
import hashlib
import importlib.util
import json
from pathlib import Path


def run_after_root_admission(request, capture_root):
    capture_root = Path(capture_root)
    assert capture_root.is_dir()
    helper = request['ownership']['helper']
    raw = Path(helper['path']).read_bytes()
    assert len(raw) == helper['bytes'] and hashlib.sha256(raw).hexdigest() == helper['sha256']
    spec = importlib.util.spec_from_file_location('exact_owned_process', helper['path'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    owner = module.Owner(capture_root)
    rows = []
    try:
        for index, command in enumerate(request['commands']):
            result = owner.run(command['argv'], env={}, cwd=request['cwd'],
                timeout=command['wall_seconds'], label=request['ownership']['labels'][index])
            record = owner.records[-1]
            assert int(record['leader']) > 0 and int(record['leader_birth']) > 0
            assert record['status'] == result.returncode == command['expected_exit'] == 0
            assert record['leader_parent_joined'] and record['whole_descendants_joined'] and record['streams_closed']
            assert not record['timed_out'] and not record['leader_group_signalled']
            assert record['adopted_reaps'] == record['adopted_kills'] == record['remaining_direct_children'] == []
            assert record['error'] is None and result.stderr == b''
            assert json.loads(result.stdout) == command['required_stdout_json']
            rows.append(dict(id=command['id'], argv=command['argv'], cwd=request['cwd'],
                             exit=result.returncode, ownership=record))
            (capture_root / 'PARTIAL.json').write_text(json.dumps(rows, indent=2, sort_keys=True) + '\n')
        assert len(owner.records) == len(rows) == 4
        return rows
    except BaseException:
        (capture_root / 'FAILED-OWNERSHIP.json').write_text(json.dumps(owner.records, indent=2, sort_keys=True) + '\n')
        raise


if __name__ == '__main__':
    raise RuntimeError('No CLI: Root must use its existing fresh admission/full tool capture')
