"""Four fixed30 installer contract checks. Root review/admission precedes use.

Execute only whole pinned FunctionDef ASTs and their literal constants. Never
import a selected installer/phase/issuer/main. Filesystem/FD/UID/clock/account
effects below are finite data; no actual installer, account, nonce or native call.
"""
import ast
import copy
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import types

HERE = Path(__file__).resolve().parent
INPUTS = json.loads((HERE / 'INPUTS.json').read_text())
assert sys.version_info[:2] == (3, 8)
GIB = 1024 ** 3
NONCE = 'a' * 64


def canonical(value, newline=False):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + ('\n' if newline else '')).encode()


def sha(raw): return hashlib.sha256(raw).hexdigest()


def checked(row):
    raw = Path(row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
    return raw


def actual(role, functions, constants=(), **effects):
    """Whole source nodes only; no source imports, top-level calls or body edits."""
    row = INPUTS['sources'][role]; tree = ast.parse(checked(row), row['origin'])
    nodes = [n for n in tree.body if
             (isinstance(n, ast.FunctionDef) and n.name in functions) or
             (isinstance(n, ast.Assign) and len(n.targets) == 1 and
              isinstance(n.targets[0], ast.Name) and n.targets[0].id in constants)]
    assert {n.name for n in nodes if isinstance(n, ast.FunctionDef)} == set(functions)
    assert {n.targets[0].id for n in nodes if isinstance(n, ast.Assign)} == set(constants)
    namespace = dict(json=json, hashlib=hashlib, math=math, stat=stat,
                     Decimal=Decimal, InvalidOperation=InvalidOperation,
                     __file__=row['origin'], __name__='controlled_actual_' + role)
    namespace.update(effects)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), row['origin'], 'exec'), namespace)
    return namespace


def refusal(function, message):
    try: function()
    except (ValueError, TimeoutError, AssertionError) as error:
        assert message in str(error), (message, type(error).__name__, str(error))
        return str(error)
    raise AssertionError('required refusal absent: ' + message)


def catalogue_inputs():
    closure = json.loads(checked(INPUTS['closure']))
    payload = {name: checked(row) for name, row in INPUTS['payload'].items()}
    tree = ast.parse(payload['root_bootstrap.py'])
    entry = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'launch_named_native_from_registered_loader')
    names = next(ast.literal_eval(n.value) for n in entry.body if isinstance(n, ast.Assign) and
                 any(isinstance(t, ast.Name) and t.id == 'names' for t in n.targets))
    extras = [ast.literal_eval(n) for n in ast.walk(entry) if isinstance(n, ast.Tuple) and
              len(n.elts) == 4 and all(isinstance(x, ast.Str) and x.s.endswith('.py') for x in n.elts)]
    assert len(names) == 24 and len(extras) == 1
    expected_names = {n + '.py' for n in names} | set(extras[0]) | {'root_bootstrap.py', 'retained-scope-facts.json'}
    assert set(payload) == expected_names and len(expected_names) == 30
    rows = [dict(name=name, size=len(payload[name]), sha256=sha(payload[name])) for name in sorted(payload)]
    assert closure['files'] == rows and sum(name.endswith('.py') for name in payload) == 29
    assert sha(payload['retained-scope-facts.json']) == '7f7f4f58c733d6f42d631a1821241e3a632b823e981236038b03e675bdd4e362'
    return closure, payload


def exact_catalogue():
    closure, payload = catalogue_inputs()
    mutations = []
    def vector(name, mutate, error): mutations.append((name, mutate, error))
    vector('old23', lambda x: x.update(python_files=20, contract_files=3, files=x['files'][:23]), 'source closure shape')
    vector('missing-real-module', lambda x: x['files'].pop(0), 'source closure shape')
    vector('extra-python', lambda x: x['files'].append(dict(name='extra.py',size=1,sha256='0'*64)), 'source closure shape')
    vector('same-count-wrong-member', lambda x: x['files'][0].update(name='unexpected.py'), 'source closure membership')
    vector('changed-hash', lambda x: x['files'][0].update(sha256='0'*64), 'source closure membership')
    vector('changed-size', lambda x: x['files'][0].update(size=x['files'][0]['size']+1), 'source closure membership')
    vector('reordered', lambda x: x['files'].__setitem__(slice(0,2),list(reversed(x['files'][:2]))), 'source closure membership')
    vector('duplicate', lambda x: x['files'].__setitem__(1,copy.deepcopy(x['files'][0])), 'source row values')
    vector('nested', lambda x: x['files'][0].update(name='parser/file.py'), 'source row values')
    vector('traversal', lambda x: x['files'][0].update(name='..'), 'source row values')
    vector('bool-version', lambda x: x.update(version=True), 'source closure shape')
    vector('bool-count', lambda x: x.update(python_files=True), 'source closure shape')
    vector('bool-size', lambda x: x['files'][0].update(size=True), 'source row values')
    vector('changed-source-dir', lambda x: x.update(source_directory='/test-only/unselected'), 'source closure shape')
    vector('missing7f7-same-count', lambda x: next(r for r in x['files'] if r['name']=='retained-scope-facts.json').update(name='other.json'), 'source closure membership')
    reports = {}
    for role in ('installer', 'phase0', 'completion'):
        ns = actual(role, ['fixed_catalog'], ['SOURCE_DIR','FIXED_FILES'])
        accepted = ns['fixed_catalog'](copy.deepcopy(closure))
        assert accepted == closure['files']
        rejected = []
        for name, mutate, error in mutations:
            value = copy.deepcopy(closure); mutate(value)
            rejected.append(dict(id=name,diagnostic=refusal(lambda:ns['fixed_catalog'](value),error)))
        reports[role] = dict(accepted_rows=accepted,refusals=rejected)
    return reports


class ProofEffects:
    """Already-owned virtual FDs and installed metadata; no real OS fallback."""
    def __init__(self):
        self.closure, self.payload = catalogue_inputs(); self.held = []; self.opened = []
        self.files = {name: dict(raw=raw, inode=1000+i, uid=0, mode=0o444, flags=0x10, nlink=1)
                      for i,(name,raw) in enumerate(sorted(self.payload.items()))}
        self.directory = dict(inode=800, uid=0, mode=0o755, flags=0x10)
        self.journal_meta = dict(inode=700, uid=0, mode=0o600, nlink=1)
        self.records = [dict(state='CLAIMED',nonce=NONCE,release_sha256='b'*64,
                             closure_sha256=INPUTS['closure']['sha256']),
                        dict(state='DIRECTORY_CREATED',identity=self.ident(self.directory))]
        for row in self.closure['files']:
            identity = self.ident(self.files[row['name']])
            for state in ('BEFORE_CREATE','BEFORE_WRITER_CLOSE','WRITER_CLOSED','BEFORE_IMMUTABLE','FILE_HELD'):
                self.records.append(dict(state=state,name=row['name'],identity=identity,sha256=row['sha256']))
        self.records.extend([dict(state='BEFORE_DIRECTORY_IMMUTABLE',name='root',identity=self.ident(self.directory)),
                             dict(state='SOURCE_INSTALLED',nonce=NONCE,closure_sha256=INPUTS['closure']['sha256'],identity=self.ident(self.directory))])
        self.handles = {10:('root',None),11:('code',None),12:('closure',None)}; self.next_fd=100
        self.journal_newline = True

    @staticmethod
    def ident(row): return dict(device=77,inode=row['inode'])
    def journal_raw(self): return b'\n'.join(canonical(r) for r in self.records)+(b'\n' if self.journal_newline else b'')
    def held_open(self, held, name, flags, mode=0o777, dir_fd=None):
        if dir_fd==10 and name=='INSTALL-'+NONCE+'.jsonl': item=('journal',None)
        elif dir_fd==11 and name=='installed-source-'+NONCE: item=('directory',None)
        else:
            assert self.handles[dir_fd][0]=='directory' and name in self.files
            item=('file',name)
        fd=self.next_fd;self.next_fd+=1;self.handles[fd]=item;held.append(fd);self.opened.append(fd)
        return fd
    def raw(self, fd):
        kind,name=self.handles[fd]
        return checked(INPUTS['closure']) if kind=='closure' else self.journal_raw() if kind=='journal' else self.files[name]['raw']
    def fstat(self, fd):
        kind,name=self.handles[fd]
        row=self.directory if kind=='directory' else self.journal_meta if kind=='journal' else self.files[name]
        return types.SimpleNamespace(st_dev=77,st_ino=row['inode'],st_uid=row['uid'],st_gid=0,
              st_mode=(stat.S_IFDIR if kind=='directory' else stat.S_IFREG)|row['mode'],
              st_nlink=row.get('nlink',1),st_size=0 if kind=='directory' else len(self.raw(fd)))
    def flags(self, fd):
        kind,name=self.handles[fd]
        return self.directory['flags'] if kind=='directory' else self.files[name]['flags']
    def call(self):
        installer = actual('installer',['sha','unique','ident'],['SOURCE_DIR','CLOSURE_SHA256','MAX_SOURCE','IMMUTABLE'])
        install=types.SimpleNamespace(**installer)
        install.read_stable=lambda fd,limit:self.raw(fd) if len(self.raw(fd))<=limit else (_ for _ in ()).throw(ValueError('fake read bound'))
        install.flags=self.flags
        fake_os=types.SimpleNamespace(O_RDONLY=os.O_RDONLY,O_NOFOLLOW=os.O_NOFOLLOW,O_CLOEXEC=os.O_CLOEXEC,
                    O_DIRECTORY=os.O_DIRECTORY,fstat=self.fstat,listdir=lambda fd:sorted(self.files))
        fake_time=types.SimpleNamespace(CLOCK_BOOTTIME=7,clock_gettime_ns=lambda x:1000,monotonic_ns=lambda:1000,time_ns=lambda:1000)
        ns=actual('completion',['fixed_catalog','same_json','remaining','need_time','verify_writer_sequence','install_proof'],
                  ['SOURCE_DIR','FIXED_FILES','MAX_JOURNAL'],os=fake_os,time=fake_time,held_open=self.held_open)
        result=ns['install_proof'](install,10,11,12,NONCE,'b'*64,
                   dict(deadline_boot_ns=2000,deadline_mono_ns=2000,utc_cap_ns=2000),self.held)
        assert self.opened and set(self.opened)<=set(self.held), 'proof must retain already-owned FDs'
        return result


def immutable_proof():
    base=ProofEffects(); proof=base.call()
    expected=[dict(name=r['name'],identity=base.ident(base.files[r['name']]),sha256=r['sha256']) for r in base.closure['files']]
    assert proof['files']==expected and len(expected)==30
    cases=[]
    def check(name, mutate, message):
        e=ProofEffects();mutate(e)
        diagnostic=refusal(e.call,message)
        assert set(e.opened)<=set(e.held), 'refusal cannot drop held FDs or infer retirement'
        cases.append(dict(id=name,diagnostic=diagnostic))
    check('directory-uid',lambda e:e.directory.update(uid=1000),'directory not immutable')
    check('directory-mode',lambda e:e.directory.update(mode=0o700),'directory not immutable')
    check('directory-mutable',lambda e:e.directory.update(flags=0),'directory not immutable')
    check('journal-uid',lambda e:e.journal_meta.update(uid=1000),'install journal identity')
    check('file-uid',lambda e:e.files['adapter.py'].update(uid=1000),'installed file identity')
    check('file-mode',lambda e:e.files['adapter.py'].update(mode=0o644),'installed file identity')
    check('file-mutable',lambda e:e.files['adapter.py'].update(flags=0),'installed file identity')
    check('file-inode',lambda e:e.files['adapter.py'].update(inode=9999),'installed file identity')
    check('file-content',lambda e:e.files['adapter.py'].update(raw=b'!'+e.files['adapter.py']['raw'][1:]),'installed file bytes')
    check('missing-writer-close',lambda e:e.records.__setitem__(slice(None),[r for r in e.records if not(r.get('name')=='adapter.py' and r['state']=='WRITER_CLOSED')]),'writer disposition sequence')
    check('writer-inode-mismatch',lambda e:next(r for r in e.records if r.get('name')=='adapter.py' and r['state']=='BEFORE_IMMUTABLE').update(identity=dict(device=77,inode=9999)),'writer identity sequence')
    check('unknown-writer',lambda e:e.records.insert(-1,dict(state='WRITER_CLOSURE_UNKNOWN')),'install terminal journal')
    check('29-physical-files',lambda e:e.files.pop('adapter.py'),'installed membership')
    check('same-count-wrong-member',lambda e:e.files.__setitem__('unexpected.py',e.files.pop('adapter.py')),'installed membership')
    check('extra-parser',lambda e:e.files.__setitem__('parser',dict(raw=b'',inode=2000,uid=0,mode=0o755,flags=0x10)),'installed membership')
    check('incomplete-journal',lambda e:setattr(e,'journal_newline',False),'incomplete install journal')
    return dict(proof=proof,refusals=cases,owned_fds_retained=True,actual_install=False)


def credit_namespace():
    return actual('preliminary',['amount','credit_record_checks','publication_evidence_checks'],
                  ['EXPECTED_ACTORS','MANUAL_INVOCATION','CREDIT_RUN_ID','CREDIT_BUDGET','CREDIT_INITIAL','BOOT_ID'])


def current_inputs(ns, percent=6):
    record=dict(schema_version=2,id=ns['CREDIT_RUN_ID'],budget=ns['CREDIT_BUDGET'],
                initial_balance=ns['CREDIT_INITIAL'],minimum_balance='50000',last_balance='50000',
                spent='2079.801105',remaining='50000')
    primary=dict(usedPercent=percent,windowDurationMins=10080,resetsAt=2000)
    limits=dict(primary=primary,credits=dict(hasCredits=True,unlimited=False,balance='50000'),
                rateLimitReachedType=None,spendControlReached=False)
    usage=dict(source_event='account/rateLimits/updated',at=datetime.fromtimestamp(990,timezone.utc).isoformat(),
               primary=primary,rateLimitReachedType=None,spendControlReached=False,
               credit_run_id=ns['CREDIT_RUN_ID'],credit_budget=ns['CREDIT_BUDGET'],
               credit_guard=dict(id=ns['CREDIT_RUN_ID'],budget=ns['CREDIT_BUDGET'],
                                 initial_balance=ns['CREDIT_INITIAL'],spent='2000'))
    bindings={k:dict(pid=v[0],ppid=v[1],start=v[2]) for k,v in ns['EXPECTED_ACTORS'].items()}
    h=lambda text:sha(('test-only '+text).encode())
    cap=dict(version=1,record_type='ROOT_PUBLICATION_ONE_SHOT_CAP_V1',scope='ROOT_CODE_INSTALL_ONLY',
       manual_invocation=ns['MANUAL_INVOCATION'],owner_pid=ns['EXPECTED_ACTORS']['server'][0],
       owner_birth=ns['EXPECTED_ACTORS']['server'][2],boot_id=ns['BOOT_ID'],nonce=NONCE,
       preliminary_sha256=INPUTS['sources']['preliminary']['sha256'],profile_sha256=h('profile'),
       parent_manifest_sha256=h('parent'),child_manifest_sha256=h('child'),driver_sha256=h('driver'),
       independent_review_sha256=h('review'),native_release=False,native_currentfree=None,
       issued_utc_ns=999000000000,expiry_utc_ns=1120000000000,
       issued_boot_ns=1999000000000,expiry_boot_ns=2120000000000,
       issued_mono_ns=2999000000000,expiry_mono_ns=3120000000000)
    caps=dict(deadline=1120,boot_deadline=2120,monotonic_deadline=3120,boot_id=ns['BOOT_ID'])
    common=dict(scope='ROOT_CODE_INSTALL_ONLY',thread_id='01a18bc3-e072-7810-9426-75101b0856c0',
        native_release=False,native_currentfree=None,nonce=NONCE,binding=bindings,caps=caps,
        credit_run_id=ns['CREDIT_RUN_ID'],credit_budget=ns['CREDIT_BUDGET'])
    controls=dict(common,usage_sha256=sha(canonical(usage)),owner_cap=cap,owner_cap_sha256=sha(canonical(cap,True)))
    capacity=dict(common,billing_mode='included_first_same_durable_credit_budget',same_thread=True,
       generic_c_request_still_held=True,native_reservation_bytes=12*GIB,dfd_unknown_bytes=4*GIB,
       v2_unknown_bytes=2*GIB,publication_max_bytes=2*GIB,planning_ceiling_bytes=4*GIB,
       non_additive=False,native_workloads_barred=True,other_host_compilation_barred=True,
       shared_overhead_bytes=2*GIB,owner_cap_sha256=controls['owner_cap_sha256'],
       independent_review_sha256=cap['independent_review_sha256'],independent_review_status='PASS_ACTUAL_INSTALL_ONLY',
       scratch_mount_id=11,scratch_mount_device='8:1',scratch_mount_source='/test-only/device')
    state=dict(thread_id=common['thread_id'],phase='running',stop_reason=None,weekly_usage_error=None,
       weekly_confirmation_pending=False,credit_budget_error=None,auth_mode='chatgpt',goal=dict(status='active'),
       server_pid=ns['EXPECTED_ACTORS']['server'][0],server_start=ns['EXPECTED_ACTORS']['server'][2],
       worker_pid=ns['EXPECTED_ACTORS']['worker'][0],worker_start=ns['EXPECTED_ACTORS']['worker'][2],
       resume_instruction=dict(invocation=ns['MANUAL_INVOCATION']),last_rate_limits=limits,credit_budget=copy.deepcopy(record))
    actor_rows={v[0]:dict(pid=v[0],ppid=v[1],birth=v[2],uid=1000) for v in ns['EXPECTED_ACTORS'].values()}
    return dict(controls=controls,capacity=capacity,state=state,usage=usage,record=record,actor_rows=actor_rows,
                source_sha=INPUTS['sources']['preliminary']['sha256'])


def publication(ns,x):
    return ns['publication_evidence_checks'](x['controls'],x['capacity'],x['state'],x['usage'],
       sha(canonical(x['usage'])),x['source_sha'],1000,2000,3000,
       lambda pid:x['actor_rows'][pid],x['record'])


def rehash_cap(x):
    digest=sha(canonical(x['controls']['owner_cap'],True))
    x['controls']['owner_cap_sha256']=digest;x['capacity']['owner_cap_sha256']=digest


def current_credit_caps():
    ns=credit_namespace();positives=[];failures=[]
    for percent in (6,100):
        x=current_inputs(ns,percent);before=canonical(x)
        result=publication(ns,x);assert result==x['controls']['caps'] and canonical(x)==before
        assert ns['credit_record_checks'](x['record'],x['state']['last_rate_limits'])==Decimal('50000')
        positives.append(dict(included_percent=percent,remaining_credit='50000',caps=result))
    def record_case(name,mutate,message):
        x=current_inputs(ns);mutate(x)
        failures.append(dict(id=name,diagnostic=refusal(lambda:publication(ns,x),message)))
    record_case('stop',lambda x:x['state'].update(stop_reason='test-only user stop'),'launcher paused or accounting unknown')
    record_case('auth',lambda x:x['state'].update(auth_mode='api'),'launcher paused or accounting unknown')
    record_case('unknown-account',lambda x:x['state'].update(weekly_usage_error='unknown'),'launcher paused or accounting unknown')
    record_case('old-actor',lambda x:x['state'].update(server_pid=22545),'launcher owner differs')
    record_case('changed-actor-birth',lambda x:x['actor_rows'][ns['EXPECTED_ACTORS']['server'][0]].update(birth='0'),'current owner role changed')
    record_case('changed-actor-uid',lambda x:x['actor_rows'][ns['EXPECTED_ACTORS']['server'][0]].update(uid=0),'current owner role changed')
    record_case('closed-nonce',lambda x:(x['controls'].update(nonce='c9e9624d1bada62e9635a740aba6e30e8432b47d0b560844911a54a2c36d95b5'),x['capacity'].update(nonce='c9e9624d1bada62e9635a740aba6e30e8432b47d0b560844911a54a2c36d95b5')),'publication nonce differs')
    record_case('different-credit-id',lambda x:x['record'].update(id='0'*32),'persisted credit guard differs')
    record_case('state-ledger-diff',lambda x:x['state']['credit_budget'].update(last_balance='49999'),'persisted credit guard differs')
    record_case('spend-hold',lambda x:x['state']['last_rate_limits'].update(spendControlReached=True),'current account service hold')
    record_case('service-hold',lambda x:x['state']['last_rate_limits'].update(rateLimitReachedType='actual-hold'),'current account service hold')
    def stale_account(x):
        x['usage']['at']=datetime.fromtimestamp(969,timezone.utc).isoformat()
        x['controls']['usage_sha256']=sha(canonical(x['usage']))
    record_case('stale-account',stale_account,'usage observation stale or held')
    record_case('source-pin-mismatch',lambda x:x.update(source_sha='0'*64),'owner cap actual admission binding')
    record_case('owner-cap-digest',lambda x:x['controls'].update(owner_cap_sha256='0'*64),'owner cap actual admission binding')
    def invalid_cap(x):x['controls']['owner_cap']['profile_sha256']='bad';rehash_cap(x)
    record_case('unbound-profile-sha',invalid_cap,'owner cap actual admission binding')
    def overlong(x):x['controls']['owner_cap']['expiry_boot_ns']=x['controls']['owner_cap']['issued_boot_ns']+180000000001;rehash_cap(x)
    record_case('over180-cap',overlong,'current one-shot publication cutoff')
    def expired(x):x['controls']['owner_cap']['expiry_mono_ns']=3000000000000;rehash_cap(x)
    record_case('expired-cap',expired,'current one-shot publication cutoff')
    record_case('native-release',lambda x:x['capacity'].update(native_release=True),'current publication binding differs')
    record_case('borrowed12-profile',lambda x:x['capacity'].update(planning_ceiling_bytes=12*GIB),'publication resource reservation differs')
    def credit_case(name,mutate,message):
        x=current_inputs(ns);mutate(x)
        failures.append(dict(id=name,diagnostic=refusal(lambda:ns['credit_record_checks'](x['record'],x['state']['last_rate_limits']),message)))
    credit_case('schema-bool',lambda x:x['record'].update(schema_version=True),'current credit-run binding')
    credit_case('credit-id',lambda x:x['record'].update(id='0'*32),'current credit-run binding')
    credit_case('credit-budget',lambda x:x['record'].update(budget='60000'),'current credit-run binding')
    credit_case('reset-initial',lambda x:x['record'].update(initial_balance='60000'),'current credit-run accounting')
    credit_case('inconsistent-spent',lambda x:x['record'].update(spent='1',remaining='52078.801105'),'current credit-run accounting')
    credit_case('exhausted',lambda x:x['record'].update(spent=ns['CREDIT_BUDGET'],remaining='0'),'current credit-run accounting')
    credit_case('unknown-finite-balance',lambda x:x['state']['last_rate_limits']['credits'].update(balance=None),'Credit amount must be a finite number')
    credit_case('unlimited',lambda x:x['state']['last_rate_limits']['credits'].update(unlimited=True),'current signed-in finite balance differs')
    for value,message in [(True,'finite number'),('-1','outside the supported range'),('NaN','outside the supported range'),('0','positive')]:
        failures.append(dict(id='amount-'+str(value),diagnostic=refusal(lambda:ns['amount'](value,positive=True),message)))
    return dict(positives=positives,refusals=failures,ledger_mutation=False,actual_account_call=False)


def literal_assignments(raw):
    result={}
    for node in ast.parse(raw).body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            try:result[node.targets[0].id]=ast.literal_eval(node.value)
            except (ValueError,TypeError):pass
    return result


def static_boundaries():
    child=json.loads(checked(INPUTS['child_manifest']));parent=json.loads(checked(INPUTS['parent_manifest']))
    profile=json.loads(checked(INPUTS['installer_profile']));spec=INPUTS['static_spec']
    def check_child(doc):
        assert doc['source_paths']==spec['child_paths'],'selected source path drift'
        assert doc['source_sha256']==spec['child_hashes'],'selected source hash drift'
        assert doc['source_closure_sha256']==INPUTS['closure']['sha256'],'closure pin drift'
    check_child(child)
    assert parent['child_manifest_sha256']==INPUTS['child_manifest']['sha256']
    assert parent['source_paths']==spec['parent_paths'] and parent['files']==spec['parent_hashes']
    prefix=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','6','/usr/bin/prlimit',
            '--as=1073741824:1073741824','--cpu=60:60','--fsize=33554432:33554432',
            '--nofile=256:256','--core=0:0','--','/usr/bin/python3','-I','-B','-c']
    def check_profile(doc):
        assert doc['argv'][:16]==prefix,'privilege argv drift'
        assert doc['argv'][16].encode()==checked(INPUTS['sources']['bootstrap']),'bootstrap source drift'
        assert doc['operation_family_reserve_bytes']==doc['controller_overhead_reserve_bytes']==2*GIB
        assert doc['aggregate_HOST_bytes']==4*GIB and doc['planning_only_native_reservation_unchanged'] is True
        assert doc['scope']=='ROOT_CODE_INSTALL_ONLY' and doc['credit_run_id']==spec['credit_run_id']
    check_profile(profile)
    for role,row in INPUTS['sources'].items():
        assignments=literal_assignments(checked(row))
        for name,value in spec['literal_pins'].get(role,{}).items():assert assignments[name]==value
    wait=checked(INPUTS['wait']);assert wait==checked(INPUTS['old_wait'])
    assert child['source_sha256']['WAIT-INSTALL-CODE.py']==sha(wait)
    assert literal_assignments(checked(INPUTS['sources']['direct_entry']))['WAIT_SHA']==sha(wait)
    assert child['ipc_sha256']==INPUTS['ipc']['sha256'] and sha(checked(INPUTS['ipc']))==child['ipc_sha256']
    new=ast.parse(checked(INPUTS['sources']['root_parent']));old=ast.parse(checked(INPUTS['old_root_parent']))
    class ActorOnly(ast.NodeTransformer):
        def __init__(self):self.changed=0
        def visit_FunctionDef(self,node):
            if node.name!='run':return node
            return self.generic_visit(node)
        def visit_Set(self,node):
            try:value=ast.literal_eval(node)
            except (ValueError,TypeError):return node
            if len(value)==3 and all(type(x) is int for x in value):
                self.changed+=1;return ast.copy_location(ast.Constant(value='EXACT_ACTOR_SET'),node)
            return node
    a=ActorOnly();b=ActorOnly();new=a.visit(new);old=b.visit(old)
    assert a.changed==b.changed==1 and ast.dump(new,include_attributes=False)==ast.dump(old,include_attributes=False)
    rejected=[]
    bad=copy.deepcopy(child);bad['source_sha256']['install_completion.py']='0'*64
    rejected.append(refusal(lambda:check_child(bad),'selected source hash drift'))
    bad=copy.deepcopy(child);bad['source_paths']['phase0.py']='/test-only/unselected.py'
    rejected.append(refusal(lambda:check_child(bad),'selected source path drift'))
    bad=copy.deepcopy(profile);bad['argv'][0]='/bin/sh'
    rejected.append(refusal(lambda:check_profile(bad),'privilege argv drift'))
    return dict(source_paths_and_hashes=True,fixed30_closure=True,normal_privilege_argv=True,
                root_parent_actor_only=True,unchanged_wait_sha256=sha(wait),unchanged_ipc_sha256=child['ipc_sha256'],
                drift_refusals=rejected,installer_or_issuer_executed=False)


FAMILIES={'exact-fixed-catalogue':exact_catalogue,'root-immutable-proof':immutable_proof,
          'current-root-credit-caps':current_credit_caps,'dependent-pins-boundary':static_boundaries}
if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in FAMILIES
    family=sys.argv[1];result=FAMILIES[family]()
    print(canonical(dict(status='PASS',family=family,result=result,
          real_install=False,real_nonce=False,real_account=False,real_root_or_native=False,
          unchanged_wait_IPC_executed=False,controller1961_rerun=False)).decode())
