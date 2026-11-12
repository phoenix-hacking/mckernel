"""New paired-issuance adapter controls only, not an account/service operation.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Rejected worker01a1c48d/turn01a1ce01 collector request remains excluded.
Source/owner/goal input reads and synthetic in-memory fixture records only.
No current_account_snapshot(), controller state/ledger read, subprocess, native,
signal, flag, install, issue or resource-retirement operation is invoked.
"""
import ast,copy,datetime,hashlib,json,math,pathlib,sys,types
from decimal import Decimal,InvalidOperation
HERE=pathlib.Path(__file__).parent
BASE=HERE.parent/'normal-operation-1'
REPO=pathlib.Path('/home/holden/mckernel')
PINS={'preliminary': {'path': '/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/phase0-usage-correction-1/preliminary-current.ENVELOPE.PROPOSED.py', 'bytes': 42961, 'sha256': 'd19967a1e2f9fcffa1c1f857aadb632b0de461512a41c6daa4866e98f2da8dd2'}, 'issuer': {'path': '/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/phase0-usage-correction-1/ROOT-ISSUE-AND-EXECUTE-ONCE.ENVELOPE.PROPOSED.py', 'bytes': 14895, 'sha256': 'f7b27be4edd6d5cf1194ba1147ae6d3604d9719a375f773cdf844be48334845f'}, 'helper': {'path': '/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/normal-operation-1/current_account_snapshot.py', 'bytes': 7994, 'sha256': 'fe2c38a7d559e0066c45da9de0fd65b5597b61cebbd5249663c645cfe08c7fe6'}, 'owner': {'path': '/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/normal-operation-1/CURRENT-ACTUAL-OWNER.json', 'bytes': 706, 'sha256': 'a51ed92a2b11f7cb65d83189ee0eee80c13537d0c76f2b1b0351dc38293e09a1'}, 'goal': {'path': '/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/phase0-usage-correction-1/GOAL-IDENTITY.PRIVATE.json', 'bytes': 836, 'sha256': '81ff8ff8603fc57bda650ce1bd88f9d9b5b18ae597964e041d072fffd21d54cf'}, 'validator': {'path': '/home/holden/mckernel/scripts/run_os_goal.py', 'bytes': 157719, 'sha256': '7f8b14f23c0d87ed2614d90a7cf4dcd5edf106419f7e0e48715aebd418da191d'}, 'credits': {'path': '/home/holden/mckernel/scripts/os_goal_credits.py', 'bytes': 5178, 'sha256': 'adf5187240ed8199746eef3b59b79d4d38c4ae8ac5821c8d8324833926b21ec3'}}

def pinned(key):
    row=PINS[key];raw=pathlib.Path(row['path']).read_bytes()
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],key+' source pin'
    return raw

def project(raw,names,filename,namespace):
    tree=ast.parse(raw)
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes}==set(names),'exact actual function projection'
    exec(compile(ast.Module(body=nodes,type_ignores=[]),filename,'exec'),namespace)

helper_raw=pinned('helper');owner_raw=pinned('owner')
owner=json.loads(owner_raw)
goal=json.loads(pinned('goal'))['objective']
assert hashlib.sha256(json.dumps(goal,sort_keys=True,separators=(',',':')).encode()).hexdigest()==owner['goal_objective_sha256'],'saved goal identity'
validator_raw=pinned('validator');credits_raw=pinned('credits')
validator_module=types.ModuleType('run_os_goal')
validator_module.__file__=PINS['validator']['path']
validator_module.__dict__.update(math=math,hashlib=hashlib,json=json,Decimal=Decimal,InvalidOperation=InvalidOperation)
project(credits_raw,('amount','available_balance'),PINS['credits']['path'],validator_module.__dict__)
project(validator_raw,('_account_value_sha256','accepted_account_observation'),PINS['validator']['path'],validator_module.__dict__)
previous_module=sys.modules.get('run_os_goal')
sys.modules['run_os_goal']=validator_module
adapter_ns={'CURRENT':BASE,'hashlib':hashlib,'json':json}

def source_read_bound(path,maximum):
    # Substitute only static input retrieval. Exact source/owner SHA guards remain
    # in the actual adapter; all acceptance is the actual pinned pure validator.
    if path==BASE/'current_account_snapshot.py':raw=helper_raw
    elif path==BASE/'CURRENT-ACTUAL-OWNER.json':raw=owner_raw
    else:raise AssertionError('unexpected adapter input read')
    assert len(raw)<=maximum,'unchanged input envelope'
    return raw,{}

adapter_ns['read_bound']=source_read_bound
project(pinned('preliminary'),('strict_json','accepted_usage_receipt'),PINS['preliminary']['path'],adapter_ns)
adapter=adapter_ns['accepted_usage_receipt']
NOW_UTC_NS=1000000000000
NOW_MONO_NS=1000000000000

def account_hash(value):
    return validator_module._account_value_sha256(value)

def fixture():
    # Deliberately synthetic accounting/events. Real independent owner/goal pins
    # only select the validator context; none of these records is published.
    ledger={'schema_version':2,'id':owner['credit_run_id'],'budget':owner['credit_budget'],
            'initial_balance':'100','minimum_balance':'100','last_balance':'100',
            'spent':'0','remaining':owner['credit_budget'],'fixture_observation':'issued'}
    limits={'primary':{'usedPercent':1.0,'windowDurationMins':10080,'resetsAt':2000},
            'credits':{'hasCredits':True,'unlimited':False,'balance':'100'},
            'rateLimitReachedType':None,'spendControlReached':None}
    receipt={'schema_version':1,'source':'notification','method':'account/rateLimits/updated',
             'request_id':None,'received_utc_ns':NOW_UTC_NS-2000000000,
             'received_mono_ns':NOW_MONO_NS-2000000000,'sequence':1,
             'status':'ACCEPTED','owner':copy.deepcopy(owner),'server_pid':owner['server_pid'],
             'rate_limits_sha256':account_hash(limits),'credit_record_sha256':account_hash(ledger),
             'state_limits_and_credit_persisted':True}
    issued={key:copy.deepcopy(owner[key]) for key in ('log_dir','thread_id','worker_pid','server_pid',
            'worker_start','server_start','repo','guardian_run_id')}
    issued.update(phase='running',stop_reason=None,credit_budget_error=None,auth_mode='chatgpt',
                  goal={'status':'active','objective':goal,'threadId':owner['thread_id']},
                  last_rate_limits=limits,credit_budget=ledger,transport_failure={},
                  last_account_observation=receipt,last_account_notification=copy.deepcopy(receipt))
    usage={'at':datetime.datetime.fromtimestamp(receipt['received_utc_ns']/1000000000,datetime.timezone.utc).isoformat(),
           'source_kind':receipt['source'],'source_event':receipt['method'],
           'receipt_received_utc_ns':receipt['received_utc_ns'],'receipt_received_mono_ns':receipt['received_mono_ns'],
           'primary':copy.deepcopy(limits['primary']),'rateLimitReachedType':None,'spendControlReached':None,
           'credit_guard':copy.deepcopy(ledger),'credit_run_id':owner['credit_run_id'],'credit_budget':owner['credit_budget'],
           'receipt_state':copy.deepcopy(issued)}
    return issued,usage,copy.deepcopy(ledger)

def invoke(state,usage,ledger):
    return adapter(state,usage,ledger,NOW_UTC_NS/1000000000,NOW_MONO_NS/1000000000)

def newer(state,ledger,status='ACCEPTED'):
    row=copy.deepcopy(state['last_account_observation'])
    row.update(received_utc_ns=NOW_UTC_NS-1000000000,received_mono_ns=NOW_MONO_NS-1000000000,
               sequence=2,status=status,rate_limits_sha256=account_hash(state['last_rate_limits']),
               credit_record_sha256=account_hash(ledger))
    state['credit_budget']=copy.deepcopy(ledger)
    state['last_account_observation']=row
    state['last_account_notification']=copy.deepcopy(row)

results=[]
def passed(label):results.append({'case':label,'result':'PASS'})
def refuses(label,mutate,message):
    state,usage,ledger=fixture();mutate(state,usage,ledger)
    try:invoke(state,usage,ledger)
    except ValueError as error:
        assert message in str(error),label+' unexpected refusal category'
    else:raise AssertionError(label+' accepted invalid paired fixture')
    passed(label)

try:
    # Exercise the exact two inserted/main enrichment AST statements, serialize
    # through the unchanged actual canonical function, and check bounded roundtrip.
    issuer_raw=pinned('issuer');tree=ast.parse(issuer_raw)
    main=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main')
    def literal_slice(node):
        selected=node.slice
        if isinstance(selected,ast.Index):selected=selected.value
        return selected.value if isinstance(selected,ast.Constant) else None
    pair=[node for node in main.body if isinstance(node,ast.Assign) and
          any(isinstance(x,ast.Subscript) and isinstance(x.value,ast.Name) and x.value.id=='usage' and
              literal_slice(x)=='receipt_state' for x in node.targets)]
    enrich=[node for node in main.body if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and
            isinstance(node.value.func,ast.Attribute) and isinstance(node.value.func.value,ast.Name) and
            node.value.func.value.id=='usage' and node.value.func.attr=='update']
    assert len(pair)==len(enrich)==1 and pair[0].lineno<enrich[0].lineno,'paired insertion ordering'
    state,usage,ledger=fixture();usage.pop('receipt_state');scope={'state':state,'usage':usage,'credit':ledger}
    scope['json']=json
    project(issuer_raw,('canonical',),PINS['issuer']['path'],scope)
    exec(compile(ast.Module(body=pair+enrich,type_ignores=[]),PINS['issuer']['path'],'exec'),scope)
    raw=scope['canonical'](usage)
    assert len(raw)<=65536 and json.loads(raw)['receipt_state']==state,'private bounded pair roundtrip'
    passed('issuer_pair_roundtrip')
    state,usage,ledger=fixture();assert invoke(state,usage,ledger)['sequence']==1
    passed('same_pair_accept')
    state,usage,ledger=fixture();ledger['fixture_observation']='current';newer(state,ledger)
    actual=invoke(state,usage,ledger)
    assert actual['sequence']==2 and actual['received_mono_ns']!=usage['receipt_received_mono_ns'],'return newest genuine fixture receipt'
    passed('later_identical_notification_accept')
    def newest_hold(state,usage,ledger,status):
        newer(state,ledger,status);usage.pop('receipt_state')
    refuses('newest_rejected_veto_first',lambda s,u,l:newest_hold(s,u,l,'REJECTED'),'newest account observation not accepted')
    refuses('newest_pending_veto_first',lambda s,u,l:newest_hold(s,u,l,'PENDING'),'newest account observation not accepted')
    for field,value,label in [('source_kind','read','saved_source_kind_refuse'),
                              ('source_event','account/rateLimits/read','saved_method_refuse'),
                              ('receipt_received_utc_ns',NOW_UTC_NS-2000000000+1,'saved_utc_refuse'),
                              ('receipt_received_mono_ns',NOW_MONO_NS-2000000000+1,'saved_mono_refuse')]:
        refuses(label,lambda s,u,l,k=field,v=value:u.__setitem__(k,v),'saved usage differs from actual accepted account receipt')
    refuses('missing_pair_refuse',lambda s,u,l:u.pop('receipt_state'),'paired issued account snapshot required')
    def order_bad(state,usage,ledger):
        newer(usage['receipt_state'],usage['credit_guard'])
        row=usage['receipt_state']['last_account_observation']
        usage.update(receipt_received_utc_ns=row['received_utc_ns'],receipt_received_mono_ns=row['received_mono_ns'])
    refuses('issued_newer_order_refuse',order_bad,'issued account receipt is newer than live state')
    def issued_stale(state,usage,ledger,key):
        for field in ('last_account_observation','last_account_notification'):
            usage['receipt_state'][field][key]=(NOW_UTC_NS if key=='received_utc_ns' else NOW_MONO_NS)-25000000000
        usage['receipt_'+key]=usage['receipt_state']['last_account_observation'][key]
    refuses('issued_utc_exact25_refuse',lambda s,u,l:issued_stale(s,u,l,'received_utc_ns'),'account observation stale')
    refuses('issued_mono_exact25_refuse',lambda s,u,l:issued_stale(s,u,l,'received_mono_ns'),'account observation stale')
    refuses('issued_credit_pair_refuse',lambda s,u,l:u['credit_guard'].__setitem__('fixture_observation','drift'),'account durable credit snapshot mismatch')
    refuses('issued_limits_hash_refuse',lambda s,u,l:u['receipt_state']['last_rate_limits'].__setitem__('fixture_extra','drift'),'account observation limits mismatch')
    def full_current_changed(state,usage,ledger):
        state['last_rate_limits']['fixture_extra']='different';newer(state,ledger)
    refuses('current_full_limits_difference_refuse',full_current_changed,'issued and current full account limits differ')
    assert len(results)==16,'exact focused control count'
    print(json.dumps({'kind':'mckernel-phase0-paired-issuance-new-controls-v1','scope':'synthetic in-memory fixtures only; no account/service/issue/native authority',
                      'source_preliminary_sha256':PINS['preliminary']['sha256'],'source_issuer_sha256':PINS['issuer']['sha256'],
                      'cases':results,'count':len(results),'passing_original_receipt_suite_replayed':False},sort_keys=True))
finally:
    if previous_module is None:sys.modules.pop('run_os_goal',None)
    else:sys.modules['run_os_goal']=previous_module
