from pathlib import Path
import importlib.util,json,runpy
OLD=Path('/home/holden/mckernel-work/host-preparation/M07-current-profile-next-observation-preparation-20261021-1/collector-diagnostic-normalization-runtime-preparation-1/coupled-sourcegraph-correction-1/runtime-construction-source-4/bound-runtime-source-1')
D=Path('/home/holden/mckernel-work/host-preparation/M07-current-profile-next-observation-preparation-20261021-1/collector-diagnostic-normalization-runtime-preparation-1/coupled-sourcegraph-correction-1/runtime-construction-source-4/normalization-capture-facts-compatibility-1/bound-runtime-source-1')
s=importlib.util.spec_from_file_location('actual_original_source4_snapshot',OLD/'root_manual_snapshot_threads.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);b=json.loads((OLD/'fresh-snapshot-bindings.json').read_bytes())
try:m.static_joins(b)
except KeyError as e:assert e.args==('process_group_absent',),e.args
else:raise AssertionError('original actual raw-capture field mismatch did not refuse')
runpy.run_path(str(D/'check_current_whole_caller.py'),run_name='__main__')
