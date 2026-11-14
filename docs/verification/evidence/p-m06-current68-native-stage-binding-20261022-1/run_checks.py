from pathlib import Path
import json,os,resource,subprocess,time
HERE=Path(__file__).resolve().parent
os.sched_setaffinity(0,{6});resource.setrlimit(resource.RLIMIT_AS,(512*2**20,512*2**20));resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(8*2**20,8*2**20))
cmd=['/usr/bin/python3','-B',str(HERE/'check_production_consumer.py')];start=time.monotonic()
with(HERE/'checks.stdout').open('xb')as out,(HERE/'checks.stderr').open('xb')as err:
 p=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True)
 try:rc=p.wait(timeout=30)
 except subprocess.TimeoutExpired:p.kill();rc=p.wait();raise
try:os.killpg(p.pid,0)
except ProcessLookupError:absent=True
else:absent=False
result=dict(argv=cmd,pid=p.pid,direct_join_returncode=rc,whole_group_absent=absent,wall_seconds=time.monotonic()-start,CPU=[6],jobs=1,ASbytes=512*2**20,CPU_seconds=30,wall_limit_seconds=30,output_cap_bytes=8*2**20,root_stage_archive_VM_compiler_operations=0)
(HERE/'checks-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
