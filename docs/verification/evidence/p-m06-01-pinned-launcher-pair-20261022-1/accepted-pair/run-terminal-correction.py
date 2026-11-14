from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('supervisor','/home/holden/mckernel/scripts/application-tests/supervisor.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
report=s.run_supervised(['/usr/bin/python3','-I','-B',str(R/'check-whole-terminal-consumer.py')],cwd=str(R),env={'PATH':'/usr/bin:/bin','HOME':str(R/'home'),'TMPDIR':str(R/'tmp'),'LC_ALL':'C'},attempt_dir=str(R/'terminal-capture-correction-1'),timeout_seconds=25,cleanup_timeout_seconds=3,stdout_limit_bytes=1048576,stderr_limit_bytes=1048576)
(R/'terminal-whole-correction-1.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['status']=='COMPLETED' and report['cleanup_complete'] and report['wait_status']=={'kind':'exited','code':0},report['wait_status']
assert (R/'terminal-capture-correction-1/stderr.bin').read_bytes()==b''
print('PASS wholeterminal9',report['elapsed_seconds'])
