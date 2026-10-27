"""Functional OS one-shot bridge pure mocks; no actual guard/clock/Popen/filesystem mutation."""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import io
import json
import math
from types import SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('bridge_mocked_only',HERE/'root_once_startup_entry.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
static=json.loads((HERE/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.CANDIDATE.json').read_bytes())  # Immutable prepared data only.
helper=ast.parse((HERE/'run_native_startup_capture.py').read_bytes())
nodes=[n for n in helper.body if (isinstance(n,ast.FunctionDef) and n.name in ('entry_clamps','cutoff_triplet')) or
       (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='AUTHORIZED_FIXED_LIMITS' for t in n.targets))]
ns={'math':math};exec(compile(ast.Module(body=nodes,type_ignores=[]),'PURE_UNCHANGED_ENTRY_CLAMPS','exec'),ns)
rows=[]

def fixture():
    docs={}
    special={}
    events=[]
    state=dict(age=1.,review_visible=True,claim_collision=False,popens=0,sleeps=0)
    def digest(value):return hashlib.sha256(m.encoded(value)).hexdigest()
    def ref(path):
        path=Path(path)
        if path in special:return special[path]
        value=docs.get(path,{})
        raw=value if isinstance(value,bytes) else m.encoded(value)
        return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    docs[m.STATIC]=copy.deepcopy(static)
    special[m.STATIC]=dict(path=str(m.STATIC),bytes=123,sha256=m.STATIC_SHA)
    special[Path(m.__file__)]=dict(path=m.__file__,bytes=1,sha256='bridge-source')
    for r in static['capture_sources'].values():special[Path(r['path'])]=r
    for key in ('source_authority','case_capability','stage_map_acceptance','root_ledger35','manifest','scratch_manifest_stage','artifact_acceptance'):
        r=static[key];special[Path(r['path'])]=r;docs[Path(r['path'])]={}
    docs[m.RESOURCE]=dict(observed_clocks=[100.,100.,100.],fixed_cutoffs=[1793165769.,947874.5689514667,963213.6959701729],
        root_ledger35=static['root_ledger35'],actual_latest_operation_postjoin_acceptance=static['latest_serial_operation_physical_acceptance'],no_existing_heavy=True,pids_current=0)
    docs[m.PUBLICATION]=dict(status='PASS_ACTUAL_PUSH_FETCH_AND_EXACT_NATIVE_STATIC_BLOBS',files=[ref(m.STATIC)]+list(static['capture_sources'].values()))
    packet={k:copy.deepcopy(static[k]) for k in ('exact_argv','profile','capture_sources','source_authority','case_capability',
        'stage_map_acceptance','root_ledger35','manifest','scratch_manifest_stage','artifact_acceptance')}
    packet.update(decision='PENDING_ONE_EXACT_NATIVE_M15_STARTUP_RELEASE',nonce=m.NONCE,expected_case=m.CASE,maximum_invocations=1,
        static_bindings=ref(m.STATIC),fresh_resource_physical=ref(m.RESOURCE),source_publication=ref(m.PUBLICATION),fixed_cutoffs=docs[m.RESOURCE]['fixed_cutoffs'])
    docs[m.PENDING]=packet
    docs[m.REVIEW]=dict(decision='PASS_EXECUTION',reviewer=m.REVIEWER,implementation_ownership=False,maximum_invocations=1,
        nonce=m.NONCE,payload_sha256=ref(m.PENDING)['sha256'],pending_execution_packet=ref(m.PENDING),exact_argv=packet['exact_argv'],
        static_bindings=ref(m.STATIC),fresh_resource_physical=ref(m.RESOURCE),source_publication=ref(m.PUBLICATION),manifest=packet['manifest'],
        root_ledger35=packet['root_ledger35'],source_authority=packet['source_authority'])
    docs[m.AUTH]=dict(decision='CONDITIONALLY_AUTHORIZE_ONE_EXACT_ORIGINAL_STARTUP_ENTRY_AFTER_PASS',authorized=True,authorized_by='/root',
        maximum_invocations=1,reviewer=m.REVIEWER,nonce=m.NONCE,case=m.CASE,bridge_sha256='bridge-source',static_bindings=ref(m.STATIC),
        exact_argv=static['exact_argv'],profile_sha256=m.PROFILE_SHA)
    def exists(path):return Path(path) in docs and (Path(path)!=m.REVIEW or state['review_visible'])
    def durable(path,value):
        if Path(path) in docs or (path==m.CLAIM and state['claim_collision']):raise FileExistsError(str(path))
        docs[Path(path)]=copy.deepcopy(value);events.extend([('exclusive-create',path),('file-fsync',path),('parent-fsync',path)])
    def guard():
        events.append(('guard',state['age']))
        return [100.+state['age']]*3,tuple(docs[m.RESOURCE]['fixed_cutoffs'])
    def sleep(_):state['sleeps']+=1;state['age']+=.25
    class Stream(io.BytesIO):
        def __init__(self,path):super().__init__();self.path=path
        def fileno(self):return 91
        def close(self):docs[self.path]=self.getvalue();super().close()
    def opened(path,mode):
        assert mode=='xb' and not exists(path);docs[Path(path)]=b'';return Stream(Path(path))
    def popen(argv,**kwargs):
        assert argv==m.HELPER_ARGV
        assert m.CLAIM in docs and m.GRANT in docs
        assert events.index(('parent-fsync',m.CLAIM))<len(events)
        state['popens']+=1;events.append(('Popen',tuple(argv)))
        def wait():events.append(('positive-wait',444));return 0
        return SimpleNamespace(pid=444,wait=wait)
    return SimpleNamespace(docs=docs,special=special,events=events,state=state,ref=ref,exists=exists,durable=durable,guard=guard,sleep=sleep,opened=opened,popen=popen)

def run(label,mutate=None,accept=False,again=False):
    f=fixture()
    if mutate:mutate(f)
    auth_sha=f.ref(m.AUTH)['sha256']
    with patch.object(m,'file_ref',f.ref),patch.object(m,'load_json',lambda p:copy.deepcopy(f.docs[Path(p)])),\
         patch.object(m,'durable_create',f.durable),patch.object(m,'guard_now',f.guard),\
         patch.object(m,'_entry_clamps',ns['entry_clamps']),patch.object(m.os,'getuid',lambda:1000),\
         patch.object(m.os,'geteuid',lambda:1000),patch.object(m.os,'getpid',lambda:333),\
         patch.object(Path,'exists',f.exists),patch.object(Path,'open',f.opened),\
         patch.object(m.time,'sleep',f.sleep),patch.object(m.subprocess,'Popen',f.popen),patch.object(m.os,'fsync',lambda fd:None):
        try:rc=m.enter_once(auth_sha)
        except (ValueError,KeyError,FileExistsError,TypeError):actual=False
        else:actual=rc==0
        assert actual==accept,label
        if again:
            try:m.enter_once(auth_sha)
            except ValueError:pass
            else:raise AssertionError('second entry accepted')
    assert f.state['popens']==(1 if accept else 0),label
    if accept:
        assert f.docs[m.GRANT]['execution_review']==f.ref(m.REVIEW)
        assert f.docs[m.JOINED]['direct_child_joined'] and f.docs[m.JOINED]['native_helper_pid']==444
        assert f.events.index(('parent-fsync',m.CLAIM))<f.events.index(('Popen',tuple(m.HELPER_ARGV)))
    rows.append(dict(case=label,result='PASS',native_helper_Popens=f.state['popens']))

run('exact PASS durable claim/grant one normal Popen and second invocation refuses',accept=True,again=True)
run('O_EXCL claim race refuses',lambda f:f.state.update(claim_collision=True))
run('existing claim refuses',lambda f:f.docs.update({m.CLAIM:{}}))
run('age exactly120 refuses',lambda f:f.state.update(age=120.))
run('no PASS waits only remaining freshness then refuses',lambda f:f.state.update(age=119.9,review_visible=False))
run('wrong authorization nonce refuses',lambda f:f.docs[m.AUTH].update(nonce='wrong'))
run('wrong static source hash refuses',lambda f:f.special[m.STATIC].update(sha256='wrong'))
run('wrong exact profile refuses',lambda f:f.docs[m.AUTH].update(profile_sha256='wrong'))
run('wrong resource binding refuses',lambda f:f.special.update({m.RESOURCE:dict(path=str(m.RESOURCE),bytes=1,sha256='wrong')}))
run('wrong source publication binding refuses',lambda f:f.docs[m.PUBLICATION].update(status='wrong'))
run('wrong PASS decision refuses',lambda f:f.docs[m.REVIEW].update(decision='FAIL'))
run('wrong independent reviewer refuses',lambda f:f.docs[m.REVIEW].update(reviewer='/root'))
run('wrong PASS payload hash refuses',lambda f:f.docs[m.REVIEW].update(payload_sha256='wrong'))
run('wrong PASS nonce refuses',lambda f:f.docs[m.REVIEW].update(nonce='wrong'))
run('wrong PASS resource reference refuses',lambda f:f.docs[m.REVIEW].update(fresh_resource_physical={}))
run('wrong pending case refuses',lambda f:f.docs[m.PENDING].update(expected_case='wrong'))
run('conditional authorization remains false refuses',lambda f:f.docs[m.AUTH].update(authorized=False))
run('changed five-helper source refuses',lambda f:f.special[m.HELPER].update(sha256='wrong'))

# Independently exercise real durability helper against mocked OS calls.
events=[]
class DurableStream(io.BytesIO):
    def fileno(self):return 71
def opened(path,flags,*mode):
    events.append(('open',path,flags));return 72 if flags&m.os.O_DIRECTORY else 71
with patch.object(m.os,'open',opened),patch.object(m.os,'fdopen',lambda *a:DurableStream()),\
     patch.object(m.os,'fsync',lambda fd:events.append(('fsync',fd))),patch.object(m.os,'close',lambda fd:events.append(('close',fd))):
    m.durable_create(m.CLAIM,{'pure':'mock'})
assert events[0][2]&m.os.O_EXCL and events[0][2]&m.os.O_CREAT
assert events.index(('fsync',71))<events.index(('fsync',72))
rows.append(dict(case='real durable helper O_EXCL plus file and parent fsync ordering mocked',result='PASS'))
(HERE/'PURE-MOCK-RESULT.json').write_text(json.dumps(dict(scope=__doc__,status='PASS_MOCKED_ROOT_ONCE_ONLY',count=len(rows),cases=rows,
    actual_guard_clock_resource_Docker_native_calls=0),indent=2)+'\n')
print(json.dumps(dict(status='PASS_MOCKED_ROOT_ONCE_ONLY',count=len(rows))))
