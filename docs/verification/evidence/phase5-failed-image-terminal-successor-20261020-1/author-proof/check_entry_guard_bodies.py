"""Focused prior-state/fresh-entry vectors; no root, filesystem or real recovery."""
import ast,contextlib,copy,hashlib,io,json,os,stat
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'cleanup_failed_image.py'
BASE=HERE.parent.parent/'cleanup_failed_image.py'
TREE=ast.parse(SOURCE.read_bytes());OLD=ast.parse(BASE.read_bytes())
TX=next(n for n in TREE.body if isinstance(n,ast.ClassDef)and n.name=='Transaction')
OTX=next(n for n in OLD.body if isinstance(n,ast.ClassDef)and n.name=='Transaction')
methods={n.name:n for n in TX.body if isinstance(n,ast.FunctionDef)}
oldmethods={n.name:n for n in OTX.body if isinstance(n,ast.FunctionDef)}
assert set(methods)-set(oldmethods)=={'preflight_fresh'}
for name in oldmethods:
 if name!='run':assert ast.dump(methods[name],include_attributes=False)==ast.dump(oldmethods[name],include_attributes=False)
run=copy.deepcopy(methods['run']);del run.body[1]
assert ast.dump(run,include_attributes=False)==ast.dump(oldmethods['run'],include_attributes=False)
for name in ('capture_logs','recover','quarantine_wait','quarantine_diagnostic'):
 new=next(n for n in TREE.body if isinstance(n,ast.FunctionDef)and n.name==name)
 old=next(n for n in OLD.body if isinstance(n,ast.FunctionDef)and n.name==name)
 assert ast.dump(new,include_attributes=False)==ast.dump(old,include_attributes=False)
selected=[n for n in TREE.body if isinstance(n,ast.ClassDef)and n.name=='Refusal']
selected += [n for n in TREE.body if isinstance(n,ast.FunctionDef)and n.name in ('identity','digest','canonical','capture_logs','recover','quarantine_diagnostic','exists')]
selected += [methods[n]for n in ('run','lock','pristine','preflight_fresh')]
CODE=compile(ast.Module(body=selected,type_ignores=[]),str(SOURCE),'exec')
class Hold(BaseException):pass

def exercise(case):
 events=[];files={};ns={'__file__':str(SOURCE),'json':json,'hashlib':hashlib,'stat':stat}
 exec(CODE,ns);Refusal=ns['Refusal']
 root=Path('/no-effects/root');namespace=Path('/no-effects/namespace')
 paths={k:root/(k.lower()+'.fixture')for k in ('MUTEX','PLAN','JOURNAL','CAPTURE','QUARANTINE')}
 attempt=namespace/'attempt.json';shared=root/'shared.json';archives=('attempt.archive','shared.archive')
 if case.startswith('prior-'):
  key=case.removeprefix('prior-').upper()
  if key=='SENTINEL':files[archives[0]]=b''
  else:files[paths[key].name]=b'logs'if key=='CAPTURE'else b''
 class FakeOS:
  O_RDWR=os.O_RDWR;O_CREAT=os.O_CREAT;O_EXCL=os.O_EXCL;O_NOFOLLOW=os.O_NOFOLLOW
  O_RDONLY=os.O_RDONLY;O_NONBLOCK=os.O_NONBLOCK
  path=SimpleNamespace(lexists=lambda path:Path(path).name in files)
  def open(self,name,flags,mode=None,**kwargs):
   if flags&os.O_CREAT:
    if name in files:raise FileExistsError(name)
    files[name]=b'';events.append('create-mutex')
   elif name not in files:raise FileNotFoundError(name)
   return 101
  def stat(self,name,**kwargs):
   if Path(name).name not in files:raise FileNotFoundError(name)
   return self.fstat(101)
  def fstat(self,fd):return SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_dev=27,st_ino=4,st_size=0,st_nlink=1,st_uid=1000,st_gid=1000)
  def fchown(self,*args):events.append('fchown-fixture')
  def fsync(self,*args):events.append('fsync-fixture')
  def close(self,*args):events.append('close-fd-fixture')
 protect_count=0
 def protected_files():
  nonlocal protect_count
  protect_count+=1;events.append('protected-'+str(protect_count))
  if case=='fresh-refusal' or (case=='postlock-refusal'and protect_count==2):
   raise Refusal('fixture-protection-refusal')
 def census():events.append('census');return True
 def read_bounded(path,**kwargs):events.append('retained-log-read');return b'logs'
 def read_at_path(path,expected):assert files[path.name]==expected;events.append('validate-capture')
 def logs(args):events.append('live-logs-read-only');return b'logs'
 def create_at(fd,name,data,on_created=None):
  assert name==paths['CAPTURE'].name and name not in files
  files[name]=data;events.append('create-capture')
  assert on_created is not None;on_created()
 def sigmask(which,mask):events.append('mask-'+which);return ('old-fixture-mask',)
 def hold():events.append('quarantine-hold');raise Hold()
 class Transaction:
  def __setattr__(self,name,value):
   object.__setattr__(self,name,value)
   if name=='mutation_started'and value is True:events.append('mutation-latch')
  def __init__(self):self.fd=71;self.mfd=None;self.rfd=72;self.root_locked=True;self.mutation_started=False
  def pinned(self):assert self.root_locked;events.append('pinned')
  def preserved(self):events.append('preserved')
  def parent_fd(self,path):return 2 if path==attempt else 71
  def lock(self,execute):events.append('lock-'+str(execute));return ns['lock'](self,execute)
  def preflight_fresh(self):events.append('preflight');return ns['preflight_fresh'](self)
  def load_plan(self):events.append('load-prior-plan');raise Refusal('fixture-original-prior-plan-validation')
  def prepare(self):events.append('original-prepare');raise Refusal('fixture-stop-before-plan-effects')
  def close(self):events.append('fixture-final-close')
  def create(self,name,raw):
   assert name==paths['QUARANTINE'].name and self.mutation_started
   assert name not in files;files[name]=raw;events.append('quarantine-marker')
 Transaction.run=ns['run'];Transaction.pristine=ns['pristine']
 ns.update(paths,Transaction=Transaction,ROOT=root,ATTEMPT=attempt,SHARED=shared,ARCHIVE_NAMES=archives,
  DEVICE=27,UID=1000,GID=1000,RECORDS={attempt:None,shared:None},path_device=lambda p:27,
  read_at=lambda *args,**kw:(b'record',None),protected_files=protected_files,census=census,
  EVIDENCE=namespace/'evidence',PROTECTED_LIMIT=1024,ROOT_LOCK_BINDING={},
  read_bounded=read_bounded,read_at_path=read_at_path,run_privileged_large=logs,
  directory=lambda p:(71,[]),create_at=create_at,CONTAINER='fixture-CID',
  os=FakeOS(),fcntl=SimpleNamespace(flock=lambda *args:events.append('flock-fixture'),LOCK_EX=1,LOCK_NB=2),
  signal=SimpleNamespace(pthread_sigmask=sigmask,SIG_BLOCK='block',SIG_SETMASK='restore'),
  DEFERRED_SIGNALS=('fixture-signal',),RELEASE={'fixture_only':True},quarantine_wait=hold)
 with contextlib.redirect_stdout(io.StringIO()):
  try:ns['recover'](execute=True)
  except(Hold,Refusal):pass
  else:raise AssertionError('expected bounded fixture refusal')
 if case.startswith('prior-'):
  assert 'preflight'not in events and 'lock-False'not in events
  assert 'lock-True'in events and 'create-mutex'in events
  assert 'mutation-latch'in events and 'quarantine-marker'in events and 'quarantine-hold'in events
  if case=='prior-plan':assert 'load-prior-plan'in events
  elif case in ('prior-journal','prior-sentinel'):assert 'preserved'in events
  else:assert 'validate-capture'in events and 'original-prepare'in events
 elif case=='fresh-refusal':
  assert 'preflight'in events and 'lock-False'in events and 'lock-True'not in events
  assert not files and 'quarantine-marker'not in events and 'mutation-latch'not in events
 elif case=='postlock-refusal':
  assert events.index('protected-1')<events.index('lock-True')<events.index('protected-2')
  assert 'live-logs-read-only'in events and 'create-capture'not in events
  assert 'quarantine-marker'in events and 'mutation-latch'in events
 else:
  assert protect_count==2 and events.count('census')==2 and events.count('live-logs-read-only')==2
  assert events.index('create-mutex')<events.index('create-capture')<events.index('original-prepare')
  assert events.count('mutation-latch')==2 and 'quarantine-marker'in events
 return {'case':case,'preflight_called':'preflight'in events,'mutated_mutex':'create-mutex'in events,
         'quarantined':'quarantine-marker'in events,'events':events}

cases=[exercise(c)for c in ('prior-plan','prior-journal','prior-sentinel','prior-capture','fresh-refusal','postlock-refusal','both-latches')]
(HERE/'entry-guard-body-result-1.json').write_text(json.dumps(dict(status='PASS_NO_EFFECT_FRESH_ENTRY_AND_PRIOR_STATE_CASES',cases=cases,
 real_effects=0,actual_bodies=['recover','Transaction.run','Transaction.lock','Transaction.pristine','Transaction.preflight_fresh','capture_logs','exists'],
 adapters=['in-memory filesystem/fd/stat/ownership model','alreadyheldrootlock fixture; no realroot lock','signal/quarantine-hold sentinel, protectedinventory andDocker-log adapters','prior-plan loader/plan-prepare refusal adapters; no realrecords'],
 original_postlock_tail_AST_equal=True,both_latches_original_AST_equal=True,deployment_allowed=False),indent=2)+'\n')
print(json.dumps({'cases_passed':len(cases),'real_effects':0}))
