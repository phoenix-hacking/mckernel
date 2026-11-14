"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Straight accepted supervisor caller for finite source prep and nine authority fixtures.
No compiler, archive, stage, root, Docker or native execution. CPU6 grant required.
"""
from pathlib import Path
import importlib.util,json
E=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('accepted_source_supervisor','/home/holden/mckernel/scripts/application-tests/supervisor.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
prefix=['/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=60:60','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B']
rows=[]
for name in ['correct_outer_interpreter','prepare_restoration_successor','test_restoration_authority']:
 argv=prefix+[str(E/(name+'.py'))]
 report=s.run_supervised(argv,cwd=str(E),env={'PATH':'/usr/bin:/bin','HOME':str(E),'TMPDIR':str(E),'LC_ALL':'C'},attempt_dir=str(E/('actual-'+name+'-1')),timeout_seconds=90,cleanup_timeout_seconds=6,stdout_limit_bytes=8388608,stderr_limit_bytes=8388608)
 rows.append(dict(name=name,argv=argv,report=report))
 with(E/('ACTUAL-'+name+'-CAPTURE.json')).open('x')as f:json.dump(rows[-1],f,sort_keys=True,indent=2);f.write('\n')
 assert report['status']=='COMPLETED'and report['cleanup_complete']and report['wait_status']=={'kind':'exited','code':0},rows[-1]
 for stream in report['streams'].values():assert stream['eof']and not stream['truncated']and stream['discarded_observed_bytes']==0
print(json.dumps(dict(scope=__doc__.splitlines()[0],status='PASS_FINITE_BEGIN_RESTORATION_SOURCE_PREPARATION_AND_9_AUTHORITY_FIXTURES',operations=[dict(name=r['name'],elapsed_seconds=r['report']['elapsed_seconds'])for r in rows],root_compiler_archive_stage_guest_operations=0)))
