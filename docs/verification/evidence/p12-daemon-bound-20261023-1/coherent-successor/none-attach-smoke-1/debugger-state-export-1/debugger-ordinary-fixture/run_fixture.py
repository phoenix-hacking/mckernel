"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Controlled own ordinary Python3.8 target/GDB interop; no root/live-owner/container.
"""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time,traceback
D=Path(__file__).resolve().parent;SRC=D.parent
assert sys.version_info[:2]==(3,8)
def pin(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
report=dict(scope=__doc__.splitlines()[0],python=sys.version,root=0,live_owner=0,Docker=0,child_source=pin(D/'child.py'),export_source=pin(SRC/'export_target_state.py'),gdb_source=pin(SRC/'export.gdb'))
p=None
try:
 with (D/'child.stdout').open('xb') as out,(D/'child.stderr').open('xb') as err:
  p=subprocess.Popen(['/usr/bin/python3','-I','-B',str(D/'child.py')],stdin=subprocess.DEVNULL,stdout=out,stderr=err)
  deadline=time.monotonic()+4
  while not (D/'ready.json').exists():
   assert p.poll() is None,'fixture child exited before ready'
   assert time.monotonic()<deadline,'fixture ready timeout'
   time.sleep(.02)
  ready=json.loads((D/'ready.json').read_text());assert ready['pid']==p.pid
  original_output=str(SRC/'TARGET-STATE.json');output=str(D/'TARGET-STATE.json')
  replacements=[('3502879',str(p.pid)),('52840595',str(ready['start'])),(original_output,output),('(27,4)','(%d,%d)'%(ready['lock_device'],ready['lock_inode']))]
  for name in ('export_target_state.py','export.gdb'):
   body=(SRC/name).read_text()
   for a,b in replacements:body=body.replace(a,b)
   (D/name).write_text(body)
  argv=['/usr/bin/gdb','-q','-nx','-nh','-batch','-iex','set auto-load off','-x',str(D/'export.gdb'),'-p',str(p.pid)]
  begin=time.monotonic()
  with (D/'gdb.stdout').open('xb') as go,(D/'gdb.stderr').open('xb') as ge:
   g=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=go,stderr=ge,timeout=60)
  report.update(gdb_argv=argv,gdb_returncode=g.returncode,gdb_seconds=time.monotonic()-begin,ready=ready,adapted_export=pin(D/'export_target_state.py'),adapted_gdb=pin(D/'export.gdb'),child_alive_after_detach=p.poll() is None)
  if (D/'TARGET-STATE.json').exists():
   raw=(D/'TARGET-STATE.json').read_bytes();report['exported_file']=pin(D/'TARGET-STATE.json')
   state=json.loads(raw);report['export_status']=state.get('status');report['exported_state']=state
  report['status']='PASS' if g.returncode==0 and report['child_alive_after_detach'] and report.get('export_status')=='DIAGNOSTIC_STATE_EXPORTED_NO_OWNER_METHODS_OR_FLAG_CHANGES' else 'FAIL_PRESERVED_FIRST_CANDIDATE'
except BaseException:
 report.update(status='FAIL_PRESERVED_FIRST_CANDIDATE',fixture_exception=traceback.format_exc())
finally:
 if p is not None:
  if p.poll() is None:p.terminate()
  try:report['fixture_child_returncode']=p.wait(timeout=5);report['fixture_child_joined']=True
  except BaseException:report['fixture_child_joined']=False
 (D/'RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
if report['status']!='PASS':raise SystemExit(1)
