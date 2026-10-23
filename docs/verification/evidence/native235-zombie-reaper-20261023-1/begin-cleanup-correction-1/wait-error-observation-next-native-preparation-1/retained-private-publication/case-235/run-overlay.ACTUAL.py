from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('supervisor','/home/holden/mckernel/scripts/application-tests/supervisor.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
argv=json.loads((R/'OVERLAY-ARGV.ACTUAL.json').read_text())
report=s.run_supervised(argv,cwd=str(R),env={'PATH':'/usr/bin:/bin','HOME':str(R),'TMPDIR':str(R),'LC_ALL':'C'},attempt_dir=str(R/'actual-v3-overlay-capture-1'),timeout_seconds=30,cleanup_timeout_seconds=3,stdout_limit_bytes=8388608,stderr_limit_bytes=8388608)
with (R/'ACTUAL-V3-OVERLAY-CAPTURE-RESULT.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
assert report['status']=='COMPLETED' and report['cleanup_complete'] and report['wait_status']=={'kind':'exited','code':0},report
print('PASS ordinary V3 235 overlay collection',report['elapsed_seconds'])
