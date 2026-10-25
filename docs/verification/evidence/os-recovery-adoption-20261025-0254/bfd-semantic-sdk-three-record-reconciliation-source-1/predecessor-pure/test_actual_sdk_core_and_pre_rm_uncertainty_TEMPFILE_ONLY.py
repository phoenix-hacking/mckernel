"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual adapted SDK AST + actual main exception/finally controls on disposable
files/mocked clients only. No real cleanup records, root flock, sudo or Docker.
"""
from pathlib import Path
import ast,hashlib,json,os,stat,tempfile,types
D=Path(__file__).parent
SOURCE=D/'reconcile_exact_sdk_stopped_container_and_three_records.py'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='81b592f51c6aa6ee16bd9de3d52c6d1bab1f90b0301d68e0e92d40943acfd8fb'
profile=json.loads((D/'EXACT-OWNED-SDK-THREE-RECORD-RECONCILIATION-PROFILE.json').read_text())
TREE=ast.parse(SOURCE.read_bytes());SDK=Path(profile['sdk_owner_source']['path']);raw=SDK.read_bytes();assert hashlib.sha256(raw).hexdigest()==profile['sdk_owner_source']['sha256'];SDKT=ast.parse(raw)
LOOP=next(n for n in TREE.body if isinstance(n,ast.For) and isinstance(n.iter,ast.Name) and n.iter.id=='sdk_units')
MAIN=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=='main')
SDKUNITS=[n for n in SDKT.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ('safe_path','ExternalDocker','positive_clients','record_snapshot','release_owned_records')]
OUTROOT=D/'actual-pure-core-output-1';OUTROOT.mkdir(mode=0o700)
results=[]
def need(ok,message):
    if not ok:raise RuntimeError(message)
def pairs(items):
    out={}
    for k,v in items:need(k not in out,'duplicate');out[k]=v
    return out
class ProxyOS:
    def __init__(self,root,out,originals,trace):self.root,self.out,self.originals,self.trace=root,out,originals,trace
    def __getattr__(self,key):return getattr(os,key)
    def unlink(self,name,*,dir_fd):
        a=os.fstat(dir_fd);b=self.root.stat();assert (a.st_dev,a.st_ino)==(b.st_dev,b.st_ino)
        assert name in {p.name for p in self.originals}
        for path,raw in self.originals.items():
            which='lease' if path.name=='lease' else 'common' if path.name=='common' else 'shared'
            assert (self.out/(which+'.record.raw')).read_bytes()==raw,'all three exact archives before ANY unlink'
        assert (self.out/'ownership-archive.json').is_file() and (self.out/'record-release-authorized.json').is_file()
        self.trace.append(name);os.unlink(name,dir_fd=dir_fd)
def core_case(name,change=None,proof_key=None):
    with tempfile.TemporaryDirectory(dir=OUTROOT,prefix='three-record-') as tmp:
        root=Path(tmp);out=root/'new-evidence';out.mkdir(mode=0o700)
        paths=[root/'lease',root/'common',root/'shared'];records={};originals={}
        for key,path in zip(('lease','common','shared'),paths):
            value=dict(next(v for k,v in profile['record_values'].items() if ('lease.json' in k if key=='lease' else 'operational-exclusion' in k if key=='common' else k.endswith('mckernel-heavy-operation.lock'))))
            path.write_bytes(b'initial');path.chmod(0o600);meta=path.stat()
            if 'inode' in value:value['inode']=meta.st_ino;value['dev' if 'dev' in value else 'device']=meta.st_dev
            if change=='wrong_pid' and key=='common':value['pid']=635881
            if change=='wrong_start' and key=='common':value['starttime']='71676756'
            if change=='wrong_inode' and key=='common':value['inode']+=1
            blob=json.dumps(value,sort_keys=True).encode();path.write_bytes(blob);records[path]=value;originals[path]=blob
        trace=[];g={};proxy=ProxyOS(root,out,originals,trace)
        def safety():
            for path,before in originals.items():
                if str(path) not in g['RELEASED_RECORDS']:need(path.read_bytes()==before,'fixture exact record drift')
                else:need(not path.exists(),'released fixture record exists')
        def new(path,blob,mode=0o600):
            assert path.parent==out
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
            with os.fdopen(fd,'wb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        def write(path,value):
            new(path,(json.dumps(value,sort_keys=True)+'\n').encode())
            if change=='after_archive_drift' and path.name=='ownership-archive.json':paths[1].write_bytes(b'{"changed":true}')
        guard=types.SimpleNamespace(_duplicates=pairs,_write_new=new,_write_json=write)
        host=types.SimpleNamespace(Docker=object,digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest())
        g.update(Path=Path,os=proxy,stat=stat,json=json,hashlib=hashlib,need=need,Refusal=RuntimeError,guard=guard,host=host,ROOT=root,LEASE=paths[0],COMMON=paths[1],shared=types.SimpleNamespace(SHARED_HEAVY_LOCK_PATH=str(paths[2])),sha=lambda b:hashlib.sha256(b).hexdigest(),current_safety=safety,RELEASED_RECORDS=set(),sdk_units=SDKUNITS,p=profile,ast=ast)
        exec(compile(ast.Module(body=[LOOP],type_ignores=[]),str(SOURCE),'exec'),g)
        selected=dict(records)
        if change=='missing_shared':del selected[paths[2]]
        if change=='archive_collision':(out/'shared.record.raw').write_bytes(b'preserved existing capture')
        proof={'container_absent':True,'all_clients_reaped':True}
        if proof_key:proof[proof_key]=False
        error=None
        try:g['release_owned_records']({'nonce':'fixture-only'},selected,out,proof,{'request':{'fixture':True},'source_sha256':{'fixture':'0'*64}})
        except (RuntimeError,OSError,ValueError) as exc:error=exc
        positive=change is None and proof_key is None
        assert (error is None)==positive,(name,str(error))
        if positive:
            assert trace==['lease','common','shared'] and g['RELEASED_RECORDS']=={str(p) for p in paths}
            assert all(not p.exists() for p in paths) and (out/'record-release-complete.json').exists()
        else:assert trace==[] and all(p.exists() for p in paths),(name,'refusal released original record')
        results.append(dict(name=name,passed=True,positive=positive,exact_archive_before_first_release=positive,no_production_paths=True))
core_case('actual adapted three-record full archive/release positive')
for c in ('wrong_pid','wrong_start','wrong_inode','missing_shared','archive_collision','after_archive_drift'):core_case(c,c)
core_case('container absence proof false',proof_key='container_absent')
core_case('client closure proof false',proof_key='all_clients_reaped')
# Execute the REAL main exception/finally AST. Only root/client operations are
# simulated; this catches the exact pre-rm FD surrender previously identified.
def main_case(name,unproven,fail_at,hold_expected):
    with tempfile.TemporaryDirectory(dir=OUTROOT,prefix='actual-main-') as tmp:
        root=Path(tmp);out=root/'fresh';log=root/'container.log';log.write_bytes(b'fixture log')
        closed=[];held=[];handlers=[];written=[]
        class Parser:
            def add_argument(self,*a,**kw):pass
            def parse_args(self):return types.SimpleNamespace(execute=True,release=root/'fixture-release',release_sha256='0'*64)
        class Client:
            client_retirement_unproven=False
            def __init__(self,*a,**kw):pass
            def call(self,args,**kw):
                if args[0]==fail_at:
                    self.client_retirement_unproven=unproven;raise RuntimeError('synthetic fresh-client failure')
                return types.SimpleNamespace(stdout='fixture log',stderr='')
        fake_signal=types.SimpleNamespace(SIG_BLOCK=0,SIG_SETMASK=1,pthread_sigmask=lambda *a:set(),signal=lambda *a:(handlers.append(a) or 'old-handler'))
        fake_m=types.SimpleNamespace(DEFERRED_SIGNALS={1,2,3,15},acquire_root_lock=lambda:73,quarantine_hold=lambda fd:held.append(fd))
        fake_os=types.SimpleNamespace(close=lambda fd:closed.append(fd))
        g=dict(argparse=types.SimpleNamespace(ArgumentParser=lambda **kw:Parser()),Path=Path,validate_release=lambda *a:{'fixture':True},need=need,signal=fake_signal,m=fake_m,LOCKFD=None,MUTATED=False,COMPLETE=False,REQUESTED=[],OUT=out,current_safety=lambda:None,normal=types.SimpleNamespace(census=lambda:True),FixedDocker=Client,CleaningSignals=lambda:None,os=fake_os,p={'protected_inputs':[{'path':str(log)}],'postjoin_acceptance':{'fixture':True},'record_values':{'fixture':True}},CID='fixture-cid',__doc__=__doc__,write_json=lambda *a:written.append(a))
        exec(compile(ast.Module(body=[MAIN],type_ignores=[]),str(SOURCE),'exec'),g)
        try:g['main']()
        except RuntimeError as exc:assert str(exc)=='synthetic fresh-client failure'
        else:raise AssertionError('expected client failure not propagated')
        assert held==([73] if hold_expected else []),(name,held)
        assert closed==([] if hold_expected else [73]),(name,closed)
        assert g['LOCKFD']==(73 if hold_expected else None)
        assert g['MUTATED']==(fail_at=='rm')
        assert len(handlers)==(4 if hold_expected else 8),(name,'handler preservation')
        results.append(dict(name=name,passed=True,quarantine_selected=hold_expected,permanent_fd_retained=hold_expected,client_simulated=True,actual_main_ast=True))
main_case('failed logs unproven BEFORE MUTATED must hold',True,'logs',True)
main_case('benign logs refusal with proven client closes normally',False,'logs',False)
main_case('failed rm AFTER MUTATED must hold even without latch',False,'rm',True)
record=dict(scope=__doc__,status='PASS',tests=len(results),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),controls=results,actual_root_mutex=False,actual_Docker=False,production_record_mutation=False)
(OUTROOT/'RESULT.json').open('x').write(json.dumps(record,sort_keys=True,indent=2)+'\n');print(json.dumps(record,sort_keys=True))
