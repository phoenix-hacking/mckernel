"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
In-memory fault injection. No subprocess, proc, guard, capture or file writes.
"""
from pathlib import Path
import importlib.util,types
p=Path(__file__).with_name('root_capture_parent.py');spec=importlib.util.spec_from_file_location('pure_parent_fixture',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Stream:
 def __init__(self):self.closed=False;self.contents=b''
 def __enter__(self):return self
 def __exit__(self,*args):self.closed=True
 def write(self,b):self.contents+=b
 def flush(self):pass
 def fileno(self):return 17
class FakePath:
 def __init__(self,*args):self.path='/'.join(str(a).strip('/') for a in args);self.name=self.path.rsplit('/',1)[-1]
 def __truediv__(self,x):return FakePath(self.path,x)
 def __str__(self):return '/'+self.path
 def mkdir(self,**kw):pass
 def open(self,*a,**kw):return Stream()
 def resolve(self):return self
 def iterdir(self):return []
 def with_name(self,name):return FakePath(self.path.rsplit('/',1)[0],name)
 @property
 def parent(self):return FakePath(self.path.rsplit('/',1)[0])
 def unlink(self):events.append('unlink-temp')

def run(mode):
 global events;events=[];records={};child=types.SimpleNamespace(pid=41,returncode=None)
 m.HERE=FakePath('/fixture');m.Path=FakePath
 m.reference=lambda path:dict(path=str(path),bytes=0,sha256='a'*64)
 def identity(pid):
  if pid==41 and mode=='identity-failure':raise FileNotFoundError('simulated disappeared child stat')
  return dict(pid=pid,birth=1000+pid,ppid=1,pgrp=pid,sid=pid)
 m.identity=identity
 def atomic(path,value):
  if path.name=='STARTED.ACTUAL.json' and mode=='evidence-failure':raise OSError('simulated started write failure')
  records[path.name]=value
 m.atomic_json=atomic
 def popen(*args,**kwargs):events.append('popen');return child
 def wait4(pid,flags):events.append(('wait4',pid,flags));return pid,0,types.SimpleNamespace(ru_utime=0,ru_stime=0,ru_maxrss=0)
 m.subprocess=types.SimpleNamespace(Popen=popen)
 m.os=types.SimpleNamespace(getpid=lambda:5,wait4=wait4,waitstatus_to_exitcode=lambda status:0)
 m.time=types.SimpleNamespace(time=lambda:100.,monotonic=lambda:50.)
 try:m.main()
 except SystemExit as e:status=e.code
 else:raise AssertionError('parent did not terminate with its status')
 result=records['DIRECT-PARENT-JOIN.ACTUAL.json'];assert events==['popen',('wait4',41,0)] and result['positive_wait4_join'] is True and result['streams_closed'] is True and result['current_free'] is False
 if mode=='success':assert status==0 and result['evidence_error'] is None and result['birth']==1041 and 'STARTED.ACTUAL.json' in records
 else:assert status==1 and result['evidence_error'] is not None
 if mode=='identity-failure':assert result['child'] is None and result['birth'] is None and result['pid']==41
 if mode=='evidence-failure':assert result['child']['birth']==1041 and result['birth']==1041
for mode in ('success','identity-failure','evidence-failure'):run(mode)
# Exercise the real atomic_json implementation through fake OS/path callbacks.
spec=importlib.util.spec_from_file_location('pure_atomic_fixture',p);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
events=[];target=FakePath('/fixture/final.json');collision=True
def link(src,dst,**kw):
 events.append(('link',str(src),str(dst),kw))
 if collision:raise FileExistsError('simulated destination appearing concurrently')
def fsync(fd):events.append(('fsync',fd))
a.os=types.SimpleNamespace(link=link,fsync=fsync,open=lambda *args:23,close=lambda fd:events.append(('close',fd)),O_RDONLY=1,O_DIRECTORY=2,O_CLOEXEC=4)
try:a.atomic_json(target,dict(test=True))
except FileExistsError:pass
else:raise AssertionError('concurrent destination overwrite accepted')
assert events[0]==('fsync',17) and events[1][0]=='link' and 'unlink-temp' not in events
collision=False;events=[];a.atomic_json(target,dict(test=True));assert events[0]==('fsync',17) and events[1][0]=='link' and events[2]==('fsync',23) and events[3]=='unlink-temp' and events[4]==('fsync',23) and events[5]==('close',23)
print('PASS in-memory owned-child success/identity-failure/evidence-failure each wait4 once and close streams; missing birth remains unknown; failed evidence refuses; atomic destination race cannot overwrite; no physical operations')
