"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded publication-only pure check with complete child streams/accounting.
"""
from pathlib import Path
import hashlib,json,os,resource,subprocess,time
D=Path(__file__).resolve().parent;O=D/'PURE-ROLE-CLOSURE-2'
O.mkdir()
def write(path,value):
    with path.open('x')as f:json.dump(value,f,indent=2);f.write('\n')
def ref(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
names=['publication_runtime_closure.py','prepare_publication_rows.py','test_publication_runtime_closure.py']
write(O/'SOURCE-BEFORE.json',[ref(D/name)for name in names])
argv=['/usr/bin/taskset','-c','0','/usr/bin/prlimit','--as=2147483648','--cpu=60','--',
      '/usr/bin/python3','-B','-m','unittest','-v','test_publication_runtime_closure.py']
started=time.monotonic();child=subprocess.Popen(argv,cwd=D,stdout=(O/'stdout').open('xb'),stderr=(O/'stderr').open('xb'))
birth=int(Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19])
write(O/'CHILD-STARTED.json',dict(pid=child.pid,birth=birth,argv=argv,scope=__doc__.splitlines()[0]))
pid,status,usage=os.wait4(child.pid,0);child.returncode=os.waitstatus_to_exitcode(status)
write(O/'PARENT-JOIN.json',dict(pid=pid,birth=birth,positive_direct_wait4_join=pid==child.pid,wait4_status=status,
      returncode=child.returncode,wall_seconds=time.monotonic()-started,CPU_seconds=usage.ru_utime+usage.ru_stime,
      max_RSS_KiB=usage.ru_maxrss,affinity=[0],jobs=1,AS_bytes=2147483648,actual_runtime_calls=0))
write(O/'SOURCE-AFTER.json',[ref(D/name)for name in names])
if child.returncode:raise SystemExit(child.returncode)
# This is the same collector exercised by the positive test, never a runtime
# validator/guard/observer/materializer call or source directory traversal.
import publication_runtime_closure as p
import test_publication_runtime_closure as t
rows=p.runtime_data_rows(t.BINDING,t.SELECTION,t.OPERATION)
write(O/'RUNTIME-DATA-ROWS.json',dict(scope=__doc__.splitlines()[0],runtime_authority=None,
      inputs=dict(typed=t.BINDING,selection=t.SELECTION,operation=t.OPERATION),rows=rows,
      dynamic_control_account_records_are_live_only=p.LIVE_CONTROL_READS,
      source_artifact_archive_hash_replay=False))
external=[row for row in rows if row['requires_explicit_fetched_alias']]
write(O/'EXTERNAL-ALIAS-REQUIREMENTS.json',dict(runtime_authority=None,rows=external))
write(O/'EXTERNAL-ALIASES.TEMPLATE.NOT-AUTHORITY.json',dict(author=None,runtime_authority=None,
      aliases={row['actual']['path']:None for row in external}))
print(json.dumps(dict(status='PASS_PUBLICATION_ONLY_CURRENT_ROOT_GRAPH_AND_6_PURE_GROUPS',rows=len(rows),
                      external_aliases=len(external),join=ref(O/'PARENT-JOIN.json'),graph=ref(O/'RUNTIME-DATA-ROWS.json'))))
