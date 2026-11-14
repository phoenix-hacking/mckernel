"""Functional owned fixture debug-info regression only; no security testing.
Never attaches/signals the real quarantined actor. No group signals anywhere.
"""
import hashlib,json,os,select,subprocess,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PYTHON='/home/holden/anaconda3/bin/python3.9'
GDB='/usr/bin/gdb'
release=ROOT/('fixture-release-'+uuid.uuid4().hex)
fixture=subprocess.Popen([PYTHON,'-I','-B',str(ROOT/'owned_fixture.py'),str(release)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
result={}
try:
 ready,_,_=select.select([fixture.stdout],[],[],5);assert ready,'fixture startup timeout'
 line=fixture.stdout.readline();identity=json.loads(line);assert identity['pid']==fixture.pid and identity['ready'] is True
 stat=Path('/proc/'+str(fixture.pid)+'/stat').read_bytes();birth=stat.rpartition(b') ')[2].split()[19].decode()
 assert os.readlink('/proc/'+str(fixture.pid)+'/exe')==PYTHON
 commands=['set pagination off','set confirm off','set may-call-functions off','set may-write-registers off','set may-write-memory off','set may-insert-breakpoints off','set may-insert-fast-tracepoints off','file '+PYTHON,'attach '+str(fixture.pid),'source '+str(ROOT/'read_exact_recover_error.gdb.py'),'read-exact-recover-error '+str(ROOT/'FIXTURE-ONLY-EXACT-CO-FILENAME.py')+' RuntimeError','detach']
 argv=[GDB,'-nx','-nh','-batch','-q','-iex','set auto-load off']
 for command in commands:argv.extend(['-ex',command])
 (ROOT/'fixture-gdb-command.json').write_text(json.dumps(argv,indent=2)+'\n')
 gdb=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,check=False)
 (ROOT/'gdb.stdout').write_bytes(gdb.stdout);(ROOT/'gdb.stderr').write_bytes(gdb.stderr)
 assert gdb.returncode==0, 'gdb failed; see retained output'
 answers=[json.loads(line) for line in gdb.stdout.decode().splitlines() if line.startswith('{')]
 assert len(answers)==1 and answers[0]['status']=='PASS_EXACT_RECOVER_ERROR_READ'
 assert answers[0]['error_argument']=='MCKERNEL_OWNED_FIXTURE_EXACT_ERROR_20261026'
 assert fixture.poll() is None,'fixture must remain alive after detach'
 after=Path('/proc/'+str(fixture.pid)+'/stat').read_bytes().rpartition(b') ')[2].split()
 assert after[19].decode()==birth and after[0] not in (b'Z',b'T',b't'),'fixture birth/liveness state after detach'
 result=dict(status='PASS_OWNED_FIXTURE_EXCEPTION_READ_ONLY',fixture_pid=fixture.pid,fixture_starttime=birth,gdb_exit=gdb.returncode,fixture_alive_after_detach=True,extraction=answers[0],actual_quarantine_actor_attached=False)
finally:
 release.write_bytes(b'fixture own normal release\n')
 stdout,stderr=fixture.communicate(timeout=5)
 (ROOT/'fixture.stdout').write_bytes(line+stdout if 'line' in locals() else stdout)
 (ROOT/'fixture.stderr').write_bytes(stderr)
 result['fixture_normal_exit']=fixture.returncode
 (ROOT/'FIXTURE-RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
assert fixture.returncode==0
print(json.dumps(result,indent=2))
