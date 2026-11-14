"""Mocked actual bodies and disposable ordinary fixtures; no privileged effects."""
from pathlib import Path
import contextlib,copy,errno,hashlib,importlib.util,json,os,stat,sys,tempfile,types,unittest
from unittest import mock
BASE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('new_regular_recovery_tests',BASE/'terminal_recovery.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def row(pid, ppid=1, start='1', pgid=None, sid=None):
    return dict(pid=pid, ppid=ppid, pgid=pid if pgid is None else pgid,
                sid=pid if sid is None else sid, starttime=start, state='S',
                uid=1000, exe='/bin/sleep', argv=['sleep'])

def process_case():
    packet = dict(client_roots=[1033294, 1033157], protected_pids=[m.WAITER],
                  owner_argv=['python', 'owner.py'], owner_exe='/python',
                  waiter_argv=['python','-B','-'], waiter_exe='/python')
    owner = row(m.OWNER, ppid=m.WAITER, start=m.START)
    owner.update(exe=packet['owner_exe'], argv=packet['owner_argv'])
    waiter = row(m.WAITER,start=m.WAITER_START)
    waiter.update(exe=packet['waiter_exe'], argv=packet['waiter_argv'])
    rows=[row(1,ppid=0),row(os.getpid()),waiter,owner]
    return packet,[copy.deepcopy(rows),copy.deepcopy(rows)]

class ProcessTests(unittest.TestCase):
    def test_exact_owner_waiter_clients_pass(self):
        p,r=process_case();m.validate_processes(r,p,True)
    def test_reused_owner_refuses(self):
        p,r=process_case();r[0][-1]['starttime']='bad'
        with self.assertRaises(m.Refusal):m.validate_processes(r,p,True)
    def test_reused_waiter_refuses(self):
        p,r=process_case();r[0][-2]['starttime']='bad'
        with self.assertRaisesRegex(m.Refusal,'waiter'):m.validate_processes(r,p,True)
    def test_waiter_relation_refuses(self):
        p,r=process_case();r[0][-1]['ppid']=1
        with self.assertRaisesRegex(m.Refusal,'waiter'):m.validate_processes(r,p,True)
    def test_old_client_group_refuses(self):
        p,r=process_case();r[1].append(row(999999,pgid=1033294))
        with self.assertRaisesRegex(m.Refusal,'group/session'):m.validate_processes(r,p,True)
    def test_old_client_session_refuses(self):
        p,r=process_case();r[1].append(row(999999,sid=1033294))
        with self.assertRaisesRegex(m.Refusal,'group/session'):m.validate_processes(r,p,True)
    def test_numeric_client_reuse_refuses(self):
        p,r=process_case();r[1].append(row(1033294,start='reused'))
        with self.assertRaisesRegex(m.Refusal,'reused PID'):m.validate_processes(r,p,True)
    def test_owner_descendant_refuses(self):
        p,r=process_case();r[1].append(row(999999,ppid=m.OWNER))
        with self.assertRaisesRegex(m.Refusal,'descendant'):m.validate_processes(r,p,True)
    def test_post_retirement_waiter_still_present_refuses(self):
        p,r=process_case();[rows.pop() for rows in r]
        with self.assertRaisesRegex(m.Refusal,'owner/waiter'):m.validate_processes(r,p,False)
    def test_post_retirement_both_gone_passes(self):
        p,r=process_case();r=[rows[:-2] for rows in r];m.validate_processes(r,p,False)
    def test_old_observation_packet_refuses(self):
        self.assertFalse(m.observation_packet_join({'packet_sha256':'old'},{},'new'))
    def test_mounts_order_only_normalized(self):
        rows=[{'Destination':'/b','RW':False},{'Destination':'/a','RW':True}]
        self.assertEqual(m.mount_rows(rows),m.mount_rows(list(reversed(rows))))
        changed=copy.deepcopy(rows);changed[0]['RW']=True
        self.assertNotEqual(m.mount_rows(rows),m.mount_rows(changed))
    def test_mount_duplicate_refuses(self):
        with self.assertRaises(m.Refusal):m.mount_rows([{'Destination':'/a'},{'Destination':'/a'}])

class Census(unittest.TestCase):
 def scenario(self,errors):
  captured=[];calls=[]
  def once(progress):
   calls.append(len(calls));progress['enumerated_pids']=[1,44];progress['observed_rows']=[{'pid':1}]
   error=errors.pop(0)
   if error:raise error
   return [{'pid':1},{'pid':44}]
  with mock.patch.object(m,'process_snapshot_once',once),mock.patch.object(m,'create',lambda p,raw:captured.append((p,json.loads(raw)))):
   try:result=m.process_snapshot_retry(BASE,'test',clock=lambda:0);error=None
   except BaseException as exc:result=None;error=exc
  return calls,captured,result,error
 def test_whole_restart_retains_partial_and_uses_only_complete(self):
  calls,capture,rows,error=self.scenario([FileNotFoundError(errno.ENOENT,'gone','/proc/44/stat'),None])
  self.assertIsNone(error);self.assertEqual(len(calls),2);self.assertEqual(len(capture),2);self.assertEqual(len(capture[0][1]['observed_rows']),1);self.assertEqual(len(rows),2)
 def test_three_disappearances_fail_closed(self):
  calls,capture,rows,error=self.scenario([FileNotFoundError(errno.ENOENT,'gone','/proc/44/stat') for _ in range(3)])
  self.assertEqual(len(calls),3);self.assertEqual(len(capture),3);self.assertIsInstance(error,m.Refusal);self.assertIsNone(rows)
 def test_permission_parse_identity_and_nonproc_absence_never_retry(self):
  for error in [PermissionError(errno.EACCES,'denied','/proc/44/stat'),ValueError('parse'),m.Refusal('proc row raced'),FileNotFoundError(errno.ENOENT,'gone','/other/file')]:
   with self.subTest(error=error):
    calls,capture,rows,got=self.scenario([error]);self.assertIs(got,error);self.assertEqual(len(calls),1);self.assertEqual(len(capture),1)
 def test_wall_deadline_refuses_before_retry(self):
  clock=iter([0,4]);failure=FileNotFoundError(errno.ENOENT,'gone','/proc/44/exe')
  with mock.patch.object(m,'process_snapshot_once',side_effect=failure),mock.patch.object(m,'create') as create:
   with self.assertRaisesRegex(m.Refusal,'budget'):m.process_snapshot_retry(BASE,'test',clock=lambda:next(clock))
   self.assertEqual(create.call_count,1)
 def test_actual_census_body_does_not_skip_missing_row(self):
  ns=m.process_snapshot_once.__globals__
  fakeos=types.SimpleNamespace(geteuid=lambda:0,listdir=lambda _:['1','44'],getpid=lambda:1)
  def statrow(pid):
   if pid==44:raise FileNotFoundError(errno.ENOENT,'gone','/proc/44/stat')
   return {'pid':pid,'ppid':0,'pgid':1,'sid':1,'starttime':'1'}
  class P:
   def __init__(self,p):self.p=p
   def read_bytes(self):return b''
   def stat(self):return types.SimpleNamespace(st_uid=0)
  progress={}
  with mock.patch.dict(ns,{'os':fakeos,'statrow':statrow,'Path':P}):
   with self.assertRaises(FileNotFoundError):m.process_snapshot_once(progress)
  self.assertEqual(progress['enumerated_pids'],[1,44]);self.assertEqual(len(progress['observed_rows']),1)

class RegularTransaction(unittest.TestCase):
 def setUp(self):m.STOP_REQUEST=None;m.STOP_COUNT=0
 def fixture(self,stop=None,drift=None,short=False):
  # Actual exchange/regular snapshot/plan/journal bodies in disposable UID1000 tree.
  # Guard root UID is adapted ONLY by this test shim; production remains root0.
  with tempfile.TemporaryDirectory(prefix='regular-test-',dir=BASE) as tmp:
   root=Path(tmp);e=root/'e';e.mkdir();records=tuple(root/('record%d'%i) for i in range(3))
   for i,p in enumerate(records):p.write_bytes(('original%d'%i).encode())
   packet={'files':[m.snapshot(p)[0] for p in records]};events=[];boundaries=[0];realwrite=os.write;realstat=os.stat;realopen=os.open;realfstat=os.fstat;released=[];exchanges=[]
   def guard(parent,name,row):
    st=os.stat(name,dir_fd=parent,follow_symlinks=False)
    m.need(stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode)==0o700 and st.st_uid==os.getuid() and st.st_gid==os.getgid() and st.st_nlink==2 and (st.st_dev,st.st_ino)==(row['dev'],row['ino']),'test guard generation/metadata')
    fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
    try:m.need(not os.listdir(fd) and m.metadata(os.fstat(fd))==m.metadata(st),'test guard fd raced')
    finally:os.close(fd)
   def boundary():
    boundaries[0]+=1;events.append(('boundary',boundaries[0]))
    if stop==boundaries[0]:raise m.Refusal('injected boundary')
    if drift==boundaries[0]:
     # Replace guard generation before an exchange/release; no raw unlink.
     target=root/(m.ARCHIVE_PREFIX+'.record-0.sentinel') if boundaries[0]<=7 else records[0]
     if target.exists():target.rename(root/'retained-replaced-guard');target.mkdir(mode=0o700)
   def write(fd,data):return realwrite(fd,data[:min(2,len(data))]) if short else realwrite(fd,data)
   realexchange=m.exchange
   def exchange(parent,a,b):exchanges.append(a);return realexchange(parent,a,b)
   with mock.patch.object(m,'ROOT',root),mock.patch.object(m,'RECORDS',records),mock.patch.object(m,'guard',side_effect=guard),mock.patch.object(m.os,'fchown'),mock.patch.object(m.os,'write',side_effect=write),mock.patch.object(m,'exchange',side_effect=exchange):
    try:m.claim_records(packet,e,boundary);error=None
    except BaseException as exc:error=exc
   journal=[json.loads(x) for x in (e/'journal.jsonl').read_bytes().splitlines()] if (e/'journal.jsonl').exists() else []
   current=[(p.exists(),p.is_dir()) for p in records]
   archived=[m.snapshot(root/(m.ARCHIVE_PREFIX+'.record-%d.sentinel'%i))[1] for i in range(len(exchanges))]
   return {'error':error,'journal':journal,'current':current,'archived':archived,'complete':(e/'complete.json').exists(),'release':(e/'release-authorized.json').exists(),'exchanges':len(exchanges),'boundaries':boundaries[0]}
 def test_full_three_regular_records_actual_exchange_and_short_journal_writes(self):
  x=self.fixture(short=True);self.assertIsNone(x['error']);self.assertTrue(x['complete']);self.assertEqual(x['current'],[(False,False)]*3);self.assertEqual(x['archived'],[b'original0',b'original1',b'original2'])
  self.assertEqual(x['journal'],[{'stage':s,'index':i} for i in range(3) for s in ['exchange-intent','exchange-complete']]+[{'stage':s,'index':i} for i in range(3) for s in ['release-intent','release-complete']])
 def test_crash_before_each_exchange_and_release_preserves_unreleased_names(self):
  for boundary in range(5,11):
   with self.subTest(boundary=boundary):
    x=self.fixture(stop=boundary);self.assertIsInstance(x['error'],m.Refusal);self.assertFalse(x['complete'])
    exchanged=min(3,boundary-5);released=max(0,boundary-8)
    self.assertEqual(x['exchanges'],exchanged)
    for i in range(released,3):self.assertTrue(x['current'][i][0])
 def test_guard_generation_substitution_blocks_first_exchange(self):
  x=self.fixture(drift=5);self.assertIsInstance(x['error'],m.Refusal);self.assertEqual(x['exchanges'],0);self.assertFalse(x['complete'])
 def test_guard_generation_substitution_blocks_release(self):
  x=self.fixture(drift=8);self.assertIsInstance(x['error'],m.Refusal);self.assertEqual(x['exchanges'],3);self.assertTrue(all(p[0] for p in x['current']));self.assertFalse(x['complete'])
 def test_journal_zero_progress_and_error_fail_closed(self):
  for result in [0,-1,None,1000]:
   with self.subTest(result=result),mock.patch.object(m.os,'write',return_value=result),mock.patch.object(m.os,'fsync'):
    with self.assertRaises(m.Refusal):m.journal_row(44,{'stage':'x'})
 def test_real_guard_rejects_uid_mode_nonempty_and_generation(self):
  expected={'dev':1828,'ino':99};st=types.SimpleNamespace(st_mode=stat.S_IFDIR|0o700,st_uid=0,st_gid=0,st_nlink=2,st_dev=1828,st_ino=99)
  for field,value in [('st_uid',1000),('st_gid',1000),('st_mode',stat.S_IFDIR|0o755),('st_ino',98),('st_nlink',3)]:
   changed=types.SimpleNamespace(**vars(st));setattr(changed,field,value)
   with mock.patch.object(m.os,'stat',return_value=changed):
    with self.assertRaises(m.Refusal):m.guard(1,'guard',expected)

class ActualCli(unittest.TestCase):
 def pipeline(self,fail=None,vanish=False,repeat=False):
  # Real main -> authorize -> observe -> separate release -> recover. Mock only
  # privileged boundaries and process/container facts; never mock authorize/main.
  with tempfile.TemporaryDirectory(prefix='cli-test-',dir=BASE) as tmp:
   root=Path(tmp);packet=json.loads((BASE/'packet.json').read_bytes());p=root/'packet.json';p.write_bytes(m.canonical(packet));(root/'terminal_recovery.py').write_bytes((BASE/'terminal_recovery.py').read_bytes());(root/'test_terminal_recovery.py').write_bytes((BASE/'test_terminal_recovery.py').read_bytes());lock=root/'root-lock';lock.write_bytes(b'fixture')
   alive=[True];events=[];fds={};calls=[0];realopen=os.open;realfstat=os.fstat
   def rows():
    rows=[row(1,0),row(os.getpid())]
    if alive[0]:
     owner=row(m.OWNER,ppid=m.WAITER,start=m.START);owner.update(argv=packet['owner_argv'],exe=packet['owner_exe']);outer=row(m.WAITER,start=m.WAITER_START);outer.update(argv=packet['waiter_argv'],exe=packet['waiter_exe']);rows += [owner,outer]
    return rows
   def once(progress):
    calls[0]+=1;progress.update(enumerated_pids=[1,44],observed_rows=[{'pid':1}])
    if vanish and calls[0]==1:raise FileNotFoundError(errno.ENOENT,'gone','/proc/44/stat')
    return rows()
   def bound(pid,start):
    self.assertIn((pid,start),[(m.OWNER,m.START),(m.WAITER,m.WAITER_START)]);fd=realopen(lock,os.O_RDONLY);fds[fd]=pid;return fd
   def fstat(fd):
    st=realfstat(fd)
    if st.st_ino==lock.stat().st_ino:return types.SimpleNamespace(st_dev=27,st_ino=4)
    return st
   def send(fd,number):
    self.assertEqual(fds[fd],m.OWNER);self.assertEqual(number,m.signal.SIGKILL);events.append(('signal',fds[fd]));alive[0]=False
    if fail=='after-signal':m.termination_latch(m.signal.SIGTERM,None)
   def select(r,w,e,t):return ([r[0]],[],[]) if not alive[0] else ([],[],[])
   def quarantine(e,fd,error,acquired=True):
    events.append(('quarantine',acquired));self.assertIsNotNone(fd)
    if repeat:
     before=m.STOP_REQUEST;m.termination_latch(m.signal.SIGHUP,None);m.termination_latch(m.signal.SIGQUIT,None);self.assertEqual(m.STOP_REQUEST,before);self.assertGreaterEqual(m.STOP_COUNT,3)
    raise m.Refusal('fixture retained quarantine')
   def statrow(pid):
    if pid in [m.OWNER,m.WAITER]:raise FileNotFoundError()
    return {'starttime':'new-controller'}
   def claim(packet,e,boundary):
    boundary();events.append(('claim',));m.create(e/'complete.json',m.canonical({'status':'MOCK_COMPLETE'}))
    if fail=='finalization':m.termination_latch(m.signal.SIGTERM,None)
   class Docker:
    def __init__(self,e):self.evidence=e;self.unproven=False
    def call(self,args):events.append(('docker',args));return b''
   def release(mode,observation=None):
    doc={'status':'PASS_REGULAR_READ_ONLY_OBSERVATION_RELEASE' if mode=='observe' else 'PASS_EXACT_REGULAR_RECOVERY_RELEASE','author':'fixture-author','reviewer':'fixture-reviewer','execution_count':1,'sources':m.source_bindings(),'boot_id':m.BOOT,'no_concurrent_publishers':True,'owner':packet['owner'],'outer':packet['waiter'],'read_only':True}
    if mode=='recover':doc.update(pidfd_sigkill_only=[m.BOOT,m.OWNER,m.START],signal_parent_launcher_server=False,remove_exact_stopped_container=m.CID,archive_release_exact_three_regular_records=True,positive_natural_outer_join=[m.WAITER,m.WAITER_START],root_observation={'path':str(observation),'sha256':m.sha(observation.read_bytes())})
    p=root/(mode+'-release.json');p.write_bytes(m.canonical(doc));return p
   def cli(mode,p):
    with mock.patch.object(sys,'argv',['terminal_recovery.py',mode,'--release',str(p),'--release-sha256',m.sha(p.read_bytes())]):m.main()
   def container(d,p):events.append(('container',));return packet['container']
   lockobj=types.SimpleNamespace(lstat=lambda:types.SimpleNamespace(st_dev=27,st_ino=4))
   with contextlib.ExitStack() as stack:
    patches=[mock.patch.object(m,'BASE',root),mock.patch.object(m,'PACKET',p),mock.patch.object(m,'ROOT_LOCK',lockobj),mock.patch.object(m.resource,'setrlimit'),mock.patch.object(m.os,'getuid',return_value=0),mock.patch.object(m.os,'geteuid',return_value=0),mock.patch.object(m.os,'fchown'),mock.patch.object(m.os,'chown'),mock.patch.object(m.signal,'signal',side_effect=lambda *a:None),mock.patch.object(m,'pins'),mock.patch.object(m,'mount',return_value=packet['scratch']),mock.patch.object(m,'resources',return_value={}),mock.patch.object(m,'owner_lock',return_value={}),mock.patch.object(m,'process_snapshot_once',side_effect=once),mock.patch.object(m,'bound_pidfd',side_effect=bound),mock.patch.object(m,'pidfd_signal',side_effect=send),mock.patch.object(m.os,'fstat',side_effect=fstat),mock.patch.object(m.select,'select',side_effect=select),mock.patch.object(m,'acquire_root_mutex',side_effect=lambda fd:events.append(('acquire',))),mock.patch.object(m,'statrow',side_effect=statrow),mock.patch.object(m,'hold_quarantine',side_effect=quarantine),mock.patch.object(m,'Docker',Docker),mock.patch.object(m,'container',side_effect=container),mock.patch.object(m,'archive_failure_files',side_effect=lambda p,e:events.append(('archive',))),mock.patch.object(m,'claim_records',side_effect=claim),mock.patch.object(m.fcntl,'flock')]
    # Root-lock open is the only synthetic FD; original snapshot opens remain real.
    original_directory=m.directory
    def openpath(path,*a,**kw):return realopen(lock,*a,**kw) if path is lockobj else realopen(path,*a,**kw)
    patches.append(mock.patch.object(m.os,'open',side_effect=openpath))
    for patch in patches:stack.enter_context(patch)
    cli('observe',release('observe'));observation=root/'observe-evidence/root-observation.json';self.assertTrue(observation.exists())
    if fail:
     with self.assertRaisesRegex(m.Refusal,'fixture retained quarantine'):cli('recover',release('recover',observation))
     if fail=='after-signal':self.assertTrue(json.loads((root/'recover-evidence/handoff-unproven.json').read_bytes())['owner_signal_sent'])
     self.assertTrue((root/'recover-evidence/failure.json').exists());self.assertEqual((root/'recover-evidence/complete.json').exists(),fail=='finalization');self.assertIn(('quarantine',fail!='after-signal'),events)
    else:cli('recover',release('recover',observation));self.assertTrue((root/'recover-evidence/complete.json').exists())
    self.assertEqual([x for x in events if x[0]=='signal'],[('signal',m.OWNER)])
    if not fail:
     self.assertLess(events.index(('archive',)),events.index(('docker',['rm','--',m.CID])));self.assertLess(events.index(('docker',['rm','--',m.CID])),events.index(('claim',)))
    if vanish:self.assertEqual(json.loads((root/'observe-evidence/observe-before-before-0.json').read_bytes())['status'],'FAILED_WHOLE_CENSUS_DISCARDED')
 def test_actual_main_authorize_observe_then_separate_recovery_release(self):self.pipeline()
 def test_actual_main_whole_census_retry(self):self.pipeline(vanish=True)
 def test_actual_main_postsignal_repeated_signals_hold_quarantine(self):self.pipeline(fail='after-signal',repeat=True)
 def test_actual_main_finalization_repeated_signals_hold_root(self):self.pipeline(fail='finalization',repeat=True)

class ReleaseContract(unittest.TestCase):
 def test_actual_authorizer_rejects_old_mode_owner_sources_and_bool_count(self):
  with tempfile.TemporaryDirectory(prefix='release-test-',dir=BASE) as tmp:
   root=Path(tmp);packet=json.loads((BASE/'packet.json').read_bytes());(root/'packet.json').write_bytes(m.canonical(packet))
   for name in ['terminal_recovery.py','test_terminal_recovery.py']:(root/name).write_bytes((BASE/name).read_bytes())
   with mock.patch.object(m,'BASE',root),mock.patch.object(m,'PACKET',root/'packet.json'):
    release={'status':'PASS_REGULAR_READ_ONLY_OBSERVATION_RELEASE','author':'author','reviewer':'independent','execution_count':1,'sources':m.source_bindings(),'boot_id':m.BOOT,'no_concurrent_publishers':True,'owner':packet['owner'],'outer':packet['waiter'],'read_only':True}
    path=root/'release.json'
    def call(doc):
     path.write_bytes(m.canonical(doc));return m.authorize(path,m.sha(path.read_bytes()),'observe')
    self.assertEqual(call(release)[0]['client_roots'],packet['client_roots'])
    for field,value in [('status','PASS_TERMINAL_RECOVERY_RELEASE'),('execution_count',True),('sources',{}),('owner',dict(packet['owner'],pid=1033154)),('outer',dict(packet['waiter'],pid=1033153)),('reviewer','author'),('read_only',False)]:
     bad=copy.deepcopy(release);bad[field]=value
     with self.subTest(field=field):
      with self.assertRaises(m.Refusal):call(bad)

class DockerOwnership(unittest.TestCase):
 class Held(RuntimeError):pass
 def scenario(self,started_failure=False,pidfd_failure=False,signal_failure=False,join_timeout=False,failure_evidence_failure=False,natural_exit=False,group_survivor=False,identity_mismatch=False):
  events=[];captures={};held=[];primary=OSError(errno.ENOSPC,'injected started fsync failure')
  pid=765432;identity={'pid':pid,'ppid':os.getpid(),'pgid':pid,'sid':pid,'starttime':'fixture-start','state':'S'}
  class Proc:
   def __init__(self):self.pid=pid;self.returncode=None;self.calls=0
   def communicate(self,timeout):
    self.calls+=1;events.append(('communicate',timeout))
    if join_timeout or (pidfd_failure and not natural_exit):raise m.subprocess.TimeoutExpired('owned-client',timeout)
    self.returncode=0 if natural_exit or self.calls==1 and not started_failure else -9
    return b'original-output',b''
  proc=Proc()
  statcalls=[0]
  def statrow(p):
   statcalls[0]+=1
   return dict(identity,starttime='different') if identity_mismatch and statcalls[0]==2 else dict(identity)
  def spawn(*a,**kw):events.append(('spawn',));return proc
  def pidfd(p):
   events.append(('pidfd',p))
   if pidfd_failure:raise OSError(errno.EMFILE,'injected pidfd acquisition')
   return 77
  def signal(fd,number):
   events.append(('signal',fd,number))
   if signal_failure:raise OSError(errno.EPERM,'injected signal failure')
  def create(path,raw):
   events.append(('write',path.suffix));captures[path.name]=bytes(raw)
   if path.name.endswith('.started.json') and started_failure:raise primary
   if path.name.endswith('.failure-status.json') and failure_evidence_failure:raise OSError(errno.ENOSPC,'injected exception evidence write')
  def pair(evidence,stem):
   events.append(('census',stem))
   return [[{'pid':999,'pgid':pid,'sid':999}],[{'pid':999,'pgid':pid,'sid':999}]] if group_survivor else [[],[]]
  def hold(stem,status,owned,fd):
   held.append(copy.deepcopy(status));self.assertIs(owned,proc);self.assertEqual(fd,None if pidfd_failure else 77)
   events.append(('held',));raise self.Held('fixture retains caller stack')
  d=m.Docker(BASE)
  with mock.patch.object(m.subprocess,'Popen',side_effect=spawn),mock.patch.object(m,'statrow',side_effect=statrow),mock.patch.object(m,'pidfd_open',side_effect=pidfd),mock.patch.object(m,'pidfd_signal',side_effect=signal),mock.patch.object(m,'create',side_effect=create),mock.patch.object(m,'process_pair_retry',side_effect=pair),mock.patch.object(m,'hold_client_quarantine',side_effect=hold),mock.patch.object(m.os,'close',side_effect=lambda fd:events.append(('close',fd))),mock.patch.object(m.os,'kill',side_effect=AssertionError('numeric signal forbidden')):
   try:value=d.call(['ps']);error=None
   except BaseException as exc:value=None;error=exc
  return d,events,captures,held,value,error,primary
 def failure_status(self,captures):return json.loads(captures['client-01.failure-status.json'])
 def test_started_record_fsync_failure_still_signals_joins_and_proves_group_before_raise(self):
  d,e,c,h,value,error,primary=self.scenario(started_failure=True)
  self.assertIs(error,primary);self.assertTrue(d.unproven);self.assertIsNone(value);self.assertFalse(h)
  self.assertLess(e.index(('pidfd',765432)),e.index(('write','.json')));self.assertIn(('signal',77,m.signal.SIGKILL),e);self.assertIn(('communicate',5),e)
  status=self.failure_status(c);self.assertFalse(status['root_group_retired']);self.assertTrue(status['cleanup']['direct_joined']);self.assertTrue(status['cleanup']['complete_group_absence'])
 def test_pidfd_acquisition_failure_retains_known_identity_and_holds_without_numeric_signal(self):
  d,e,c,h,value,error,_=self.scenario(pidfd_failure=True)
  self.assertIsInstance(error,self.Held);self.assertTrue(d.unproven);self.assertEqual(h[0]['identity']['starttime'],'fixture-start');self.assertFalse(any(x[0]=='signal' for x in e));self.assertFalse(h[0]['cleanup']['direct_joined']);self.assertFalse(h[0]['root_group_retired'])
 def test_pidfd_failure_natural_direct_join_and_group_proof_remains_failed_command(self):
  d,e,c,h,value,error,_=self.scenario(pidfd_failure=True,natural_exit=True)
  self.assertIsInstance(error,OSError);self.assertFalse(h);self.assertIsNone(value);self.assertTrue(d.unproven);self.assertFalse(any(x[0]=='signal' for x in e));self.assertTrue(self.failure_status(c)['cleanup']['complete_group_absence'])
 def test_cleanup_signal_failure_and_wait_timeout_hold_before_fd_close(self):
  d,e,c,h,value,error,_=self.scenario(started_failure=True,signal_failure=True,join_timeout=True)
  self.assertIsInstance(error,self.Held);self.assertTrue(d.unproven);self.assertLess(e.index(('held',)),e.index(('close',77)));self.assertEqual(h[0]['cleanup']['errors'][0]['stage'],'pidfd-signal');self.assertFalse(h[0]['cleanup']['signal_sent'])
 def test_communicate_timeout_attempts_pidfd_cleanup_then_holds(self):
  d,e,c,h,value,error,_=self.scenario(join_timeout=True)
  self.assertIsInstance(error,self.Held);self.assertIn(('communicate',30),e);self.assertIn(('communicate',5),e);self.assertIn(('signal',77,m.signal.SIGKILL),e);self.assertFalse(h[0]['cleanup']['complete_group_absence'])
 def test_exception_evidence_failure_cannot_bypass_cleanup_or_mask_primary_error(self):
  d,e,c,h,value,error,primary=self.scenario(started_failure=True,failure_evidence_failure=True)
  self.assertIs(error,primary);self.assertTrue(d.unproven);self.assertIn(('communicate',5),e);self.assertTrue(any(x[0]=='census' for x in e));self.assertFalse(h)
 def test_joined_child_with_surviving_group_holds_and_never_signals_reaped_pidfd(self):
  d,e,c,h,value,error,_=self.scenario(group_survivor=True)
  self.assertIsInstance(error,self.Held);self.assertTrue(h[0]['cleanup']['direct_joined']);self.assertFalse(h[0]['cleanup']['complete_group_absence']);self.assertFalse(any(x[0]=='signal' for x in e));self.assertIsNone(value)
 def test_unproven_pidfd_start_binding_never_authorizes_signal(self):
  d,e,c,h,value,error,_=self.scenario(identity_mismatch=True)
  self.assertIsInstance(error,m.Refusal);self.assertTrue(d.unproven);self.assertFalse(any(x[0]=='signal' for x in e));self.assertFalse(self.failure_status(c)['cleanup']['pidfd_start_bound'])
 def test_success_owns_pidfd_before_evidence_and_returns_only_after_group_closure(self):
  d,e,c,h,value,error,_=self.scenario()
  self.assertIsNone(error);self.assertEqual(value,b'original-output');self.assertFalse(d.unproven);self.assertFalse(h);self.assertFalse(any(x[0]=='signal' for x in e));self.assertEqual(e[-1],('close',77));self.assertTrue(json.loads(c['client-01.status.json'])['root_group_retired'])

if __name__=='__main__':unittest.main(verbosity=2)
