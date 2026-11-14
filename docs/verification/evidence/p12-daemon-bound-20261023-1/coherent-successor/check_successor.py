"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual private owner method bodies with controlled Docker observations; no daemon/workload.
"""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import copy, hashlib, importlib.util, json, os, resource, subprocess

D = Path(__file__).resolve().parent
assert os.sched_getaffinity(0) == {0}
assert resource.getrlimit(resource.RLIMIT_AS)[0] <= 512 * 2**20

def load(name):
    s = importlib.util.spec_from_file_location('private_successor_' + name, D/'source'/(name+'.py'))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

o, t = load('native_diagnostic_container_owner'), load('long_transport')
results = []

def check(name, assertion):
    assert assertion, name
    results.append(name)

def owner(long=True):
    i = object.__new__(o.DiagnosticOwner)
    i.long_requested = long; i.long_logs_issued = False; i.container = 'a'*64
    i.failure = None; i.secondary = []; i.secondary_omitted = 0
    return i

stopped = {'Id':'a'*64, 'HostConfig':{'RestartPolicy':{'Name':'no','MaximumRetryCount':0}}, 'State':dict(Status='exited', Running=False, Paused=False,
           Restarting=False, Dead=False, Pid=0)}
for label, change in [('running',dict(Running=True)), ('restart',dict(Restarting=True)),
                      ('paused',dict(Paused=True)), ('dead',dict(Dead=True)),
                      ('created',dict(Status='created')), ('missing-status',dict(Status=None)),
                      ('pid-live',dict(Pid=77)), ('bool-pid',dict(Pid=False)),
                      ('missing-pid',dict(Pid=None)), ('numeric-running',dict(Running=0))]:
    i=owner(); row=copy.deepcopy(stopped); row['State'].update(change)
    i._lookup=lambda row=row:row
    i._call=lambda *a,**k:(_ for _ in ()).throw(AssertionError('logs issued for '+label))
    try:i._capture_logs(timeout=1)
    except o.OwnerError:pass
    else:raise AssertionError('accepted '+label)
    check('gate refuses '+label, not i.long_logs_issued)

for policy in (None, {'Name':'always','MaximumRetryCount':0}, {'Name':'no','MaximumRetryCount':1}):
    i=owner(); row=copy.deepcopy(stopped);row['HostConfig']['RestartPolicy']=policy
    i._lookup=lambda row=row:row
    i._call=lambda *a,**k:(_ for _ in ()).throw(AssertionError('restart policy logs issued'))
    try:i._capture_logs(timeout=1)
    except o.OwnerError:pass
    else:raise AssertionError('restart policy accepted')
    check('gate refuses restart policy '+repr(policy), not i.long_logs_issued)

i=owner(); i._lookup=lambda:None
i._call=lambda *a,**k:(_ for _ in ()).throw(AssertionError('missing container logs'))
try:i._capture_logs(timeout=1)
except o.OwnerError:pass
else:raise AssertionError('missing container accepted')
check('gate refuses missing authenticated container',not i.long_logs_issued)

for timeout in (False,True):
    i=owner(); calls=[]; i._lookup=lambda:copy.deepcopy(stopped)
    def call(argv,**kw):
        calls.append((argv,kw))
        if timeout:raise o.OwnerError('simulated command timeout after publication')
        return NS(returncode=0,stdout=b'original logs',stderr=b'')
    i._call=call
    try:r=i._capture_logs(timeout=1)
    except o.OwnerError:assert timeout
    else:assert not timeout and r.stdout==b'original logs'
    i._lookup=lambda:(_ for _ in ()).throw(AssertionError('second lookup'))
    assert i._capture_logs(timeout=1) is None
    check('one log publication after '+('uncertain timeout' if timeout else 'success'),
          len(calls)==1 and calls[0][0]==['logs','--timestamps','a'*64])

i=owner(False); calls=[]; i._lookup=lambda:(_ for _ in ()).throw(AssertionError('SHORT lookup changed'))
i._call=lambda argv,**kw:calls.append(argv)
i._capture_logs(timeout=1); i._capture_logs(timeout=1)
check('SHORT preserves prior log requests',len(calls)==2)

# Preserve the actual _call nonzero-exit policy, not only request counts.
# Backend observations are fixtures; _capture_logs, _call and _cleanup run intact.
def command_owner(long):
    i=owner(long);i.sequence=0;i.command_deadline=None;i.cleaning=False
    i.evidence=Path('/fixture/evidence');i.retained=[]
    i._queue=lambda path,raw:i.retained.append((path,raw))
    i.clock=lambda:100.;i.create_issued=True;i.create_completed=False
    i.retirement_sequence=0
    removed=[False];calls=[]
    i._lookup=lambda:None if removed[0] else copy.deepcopy(stopped)
    children=NS(pending=set(),errors=[],retire_pending=lambda **k:None,
                peek_final_reap_records=lambda:[],ack_final_reap_records=lambda r:None)
    def call(argv,**kw):
        args=argv[len(o.PREFIX):];calls.append(args[0])
        if args[0]=='rm':removed[0]=True
        return subprocess.CompletedProcess(argv,17 if args[0]=='logs' else 0,
                                           b'partial retained log bytes' if args[0]=='logs' else b'',
                                           b'diagnostic log failure' if args[0]=='logs' else b'')
    i.backend=NS(children=children,call=call)
    return i,calls

for long in (False,True):
    i,calls=command_owner(long)
    assert i._cleanup() is True
    check(('LONG' if long else 'SHORT')+' actual cleanup accepts nonzero diagnostic logs',
          i.failure is None and calls.count('logs')==1 and calls[-1]=='rm' and i.absent)
    check(('LONG' if long else 'SHORT')+' retains nonzero stdout and stderr',
          any(raw==b'partial retained log bytes' for _,raw in i.retained) and
          any(raw==b'diagnostic log failure' for _,raw in i.retained))
    if long:assert i.long_logs_issued
    i,calls=command_owner(long)
    try:i._capture_logs(timeout=1)
    except o.OwnerError as e:assert str(e)=='docker command failed: logs'
    else:raise AssertionError('default nonzero logs silently accepted')
    check(('LONG' if long else 'SHORT')+' normal capture retains nonzero failure',calls==['logs'])
    if long:
        assert i.long_logs_issued and i._capture_logs(timeout=1,allow_failure=True) is None
        check('LONG uncertain nonzero request never duplicated',calls==['logs'])

# The full cleanup method must continue removal after failed stop/kill/wait,
# while the actual gate refuses a writer still observed as active.
for stop_fail, kill_fail, wait_fail, active in [(True,True,True,True),
                                               (True,False,False,False),
                                               (False,False,False,False)]:
    i=owner(); i.clock=lambda:100.; i.create_issued=True; i.create_completed=False
    i.retirement_sequence=0; i._save=lambda *a:None
    children=NS(pending=set(),errors=[],retire_pending=lambda **k:None,
                peek_final_reap_records=lambda:[],ack_final_reap_records=lambda r:None)
    i.backend=NS(children=children); calls=[]; removed=[False]
    row=copy.deepcopy(stopped)
    if active:row['State'].update(Status='running',Running=True,Pid=77)
    i._lookup=lambda:None if removed[0] else copy.deepcopy(row)
    def call(argv,**kw):
        calls.append(argv[0])
        if argv[0]=='rm':removed[0]=True
        failures={'stop':stop_fail,'kill':kill_fail,'wait':wait_fail}
        if failures.get(argv[0],False):raise o.OwnerError('simulated '+argv[0]+' timeout')
        return NS(returncode=0,stdout=b'logs',stderr=b'')
    i._call=call
    assert i._cleanup() is True
    check('actual cleanup stopfailure=%s active=%s'%(stop_fail,active),
          ('logs' in calls)==(not active) and calls[-1]=='rm' and i.absent)
    if active:assert i.failure is not None and not i.long_logs_issued

# Exercise run's actual finally block after an early owner-side failure.
i=owner(); i.parent=Path('/fixture/p'); i.attempt=i.parent/'attempt-fixture'
i.evidence=NS(mkdir=lambda **k:None,stat=lambda:NS(st_uid=os.geteuid(),st_mode=0o40700))
i._preflight=lambda:{}; i.lock=None; i.owner_queued=False; i.absent=False
i.may_exist=False; i.clock=lambda:100.; i.nonce='b'*32
i._acquire=lambda:setattr(i,'lock',object())
i._queue_owner=lambda:setattr(i,'owner_queued',True)
lookups=[0]; calls=[]
def lookup():
    lookups[0]+=1
    if lookups[0]==1:raise o.OwnerError('injected before native creation')
    r=copy.deepcopy(stopped);r['State'].update(Status='running',Running=True,Pid=77);return r
i._lookup=lookup
i._call=lambda argv,**kw:calls.append(argv[0])
i._cleanup=lambda:calls.append('cleanup')
with patch.object(o,'_long_transport',return_value=t),patch.object(o,'_outer_identity',return_value={}):
    try:i.run()
    except o.OwnerError:pass
    else:raise AssertionError('injected run failure lost')
check('actual run finally refuses active writer before cleanup',calls==['wait','inspect','cleanup'])

check('full external capture allowance',t.EXTERNAL_CAPTURE_BYTES==768*2**20)
check('metadata preserved',t.TRANSPORT['metadata_bytes']==32*2**20)
check('complete logical growth4GiB',t.TRANSPORT['logical_growth_bytes']==4*2**30)
check('LONG384MiB SHORT32MiB unchanged',t.file_limit(True)==384*2**20 and t.file_limit(False)==32*2**20)
a=dict(host_floor_bytes=16*2**30,scratch_floor_bytes=12*2**30,
       remaining_backing_growth_bytes=42*2**30,emergency_bytes=1,campaign_bytes=1,scratch_input_growth_bytes=0)
check('actual growth reader reserves4GiB',t.growth_requirements(a)['host_required_bytes']==62*2**30+2)
for binding in ('daemon','external'):
    with patch.object(t,'DAEMON_ALLOCATION_BINDING',None if binding=='daemon' else {'fixture':True}), \
         patch.object(t,'output_parent',side_effect=AssertionError('unbound release reached filesystem')):
        try:t.validate_release('/missing','a'*64,'/missing-manifest','b'*32,'/missing-parent')
        except ValueError as e:assert binding in str(e)
        else:raise AssertionError('unbound release accepted')
    check('unbound '+binding+' fails before filesystem access',True)

# Diagnostic/oracle consumer source bytes remain the original accepted cohort.
prior=json.loads((D.parents[1]/'p12-coupled-resource-review-20261023-1/COUPLED-SOURCE-COHORT.json').read_text())
for name in t.FILES:
    if name in ('long_transport.py','native_diagnostic_container_owner.py'):continue
    check('unchanged strict runtime '+name,
          hashlib.sha256((D/'source'/name).read_bytes()).hexdigest()==prior['runtime_files'][name]['sha256'])
report=dict(scope=__doc__.splitlines()[0],status='PASS_ACTUAL_PRIVATE_OWNER_AND_ACCOUNTING_BODIES',
            checks=results,count=len(results),root=0,docker=0,guests=0,builds=0,
            failed_candidates=0,bounded_corrections=1,review_findings=1,physical_allocation_bound_proved=False,
            runtime_release='NOT_RELEASED',native_credit=0)
(D/'ACTUAL-BODY-REGRESSION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],checks=len(results))))
