"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure cap regression using actual query receipts; historical physical fields and one
explicit fixture BOOTTIME are used because the failed capture did not persist its
in-memory history/guard clocks. This is not an actual capture replay or clearance.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,math
D=Path(__file__).resolve().parent;S=D.parent/'EXPERT-CONSUMED-ROUTING-CORRECTION-1';C=S/'actual-postjoin-capture-quota-expert-root1';P=json.loads((D/'INPUTS.json').read_bytes())
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=load(P['base_source']['path'],'old_historical_cap');live=load(D/'recursive-current62/observe_current62_bfd_postjoin.py','new_weekly_cap')
tree=lambda path:ast.parse(Path(path).read_bytes())
fn=lambda t,n:next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==n)
assert ast.dump(fn(tree(old.__file__),'validate_fresh_physical'),include_attributes=False)==ast.dump(fn(tree(live.__file__),'validate_fresh_physical'),include_attributes=False)
assert old.PINS['prior_ledger']==live.PINS['prior_ledger'] and live.PINS['limits']==P['limits']
core=tree(P['frontier_core']['path']);newcore=tree(D/'live_frontier_core.py');assert ast.dump(fn(core,'validate_fresh_closed_unlaunched'),include_attributes=False)==ast.dump(fn(newcore,'validate_fresh_closed_unlaunched'),include_attributes=False)
def drop_limits(t):return [ast.dump(x,include_attributes=False)for x in t.body if not (isinstance(x,ast.Assign)and any(isinstance(z,ast.Name)and z.id=='LIMITS'for z in x.targets))]
assert drop_limits(core)==drop_limits(newcore)
raw=[]
for file in C.glob('command-*/JOIN-WAIT4.json'):
 row=json.loads(file.read_bytes());assert row['returncode']==0 and row['positive_wait4'] is True and row['streams_closed'] is True and row['group_absent'] is True
 raw.append((row['started_epoch'],row,file))
raw.sort();assert len(raw)==5
expected=[live.PREFIX+['ps','-q','--no-trunc'],live.PREFIX+['ps','-aq','--no-trunc','--filter','id='+live.CID],live.PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+live.NAME+'$']]
queries=[]
for argv in expected:
 matches=[row for _,row,_ in raw if row['argv']==argv];assert len(matches)==1;row=matches[0];out=Path(row['raw']['stdout']['path']).read_bytes();err=Path(row['raw']['stderr']['path']).read_bytes();assert out==err==b'';queries.append(dict(argv=argv,returncode=row['returncode'],stdout='',stderr=''))
# Original historical Root60 capture provides real historical structural fields.
root61=tree(S/'recursive-current62/history/observe_bfd_current61.py');pins=ast.literal_eval(next(n.value for n in root61.body if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='PINS' for x in n.targets)))
old_capture=json.loads(Path(pins['capture2']['path']).read_bytes());old_physical=old_capture['historical_Root59_native_and_physical'];history=dict(Root61=live.PINS['prior_ledger'],pids_current=old_capture['pids_current'],no_existing_heavy=old_capture['no_existing_heavy'],active_shared_records_absent=old_capture['active_shared_records_absent'],closed_exclusive_probes=old_capture['closed_exclusive_probes'],capacity=old_physical['capacity'],group_membership_observation=old_capture['group_membership_observation'],boot_id=old_capture['boot_id'],fixed_cutoffs=list(P['limits']))
# Exact captured query UTC and MONOTONIC, with explicitly synthetic positive
# BOOTTIME fixture; real guard first/last were not persisted on this failure.
first=[raw[0][1]['started_epoch'],raw[0][1]['started_monotonic'],P['limits'][2]-1000];last=[raw[-1][1]['started_epoch'],raw[-1][1]['started_monotonic'],P['limits'][2]-999];limits=list(P['limits'])
def rejects(fn,history,first,last,limits,expected=None):
 try:fn(history,[],queries,first,last,limits)
 except ValueError as e:
  if expected is not None:assert str(e)==expected
 else:raise AssertionError('invalid case accepted')
rejects(old.validate_fresh_physical,history,first,last,limits,'fresh observation under actual tighter clamps');assert live.validate_fresh_physical(history,[],queries,first,last,limits) is True
for index in range(3):
 q=list(limits);q[index]=P['limits'][index]+1;rejects(live.validate_fresh_physical,history,first,last,q)
 q=list(last);q[index]=limits[index];rejects(live.validate_fresh_physical,history,first,q,limits)
 q=list(last);q[index]=math.nan;rejects(live.validate_fresh_physical,history,first,q,limits)
q=list(last);q[0]=first[0]-1;rejects(live.validate_fresh_physical,history,first,q,limits)
q=list(last);q[1]=first[1]+121;rejects(live.validate_fresh_physical,history,first,q,limits)
h=copy.deepcopy(history);h['fixed_cutoffs'][0]-=1;rejects(live.validate_fresh_physical,h,first,last,limits)
h=copy.deepcopy(history);h['capacity']['/home/holden/mckernel']=0;rejects(live.validate_fresh_physical,h,first,last,limits)
# Exercise only the exact AST clock predicate from the frontier validator: never
# execute its proc/group/FD reads. Query UTC is actual, other fields are fixtures.
frontier_clock=next(n.value.args[0] for n in fn(core,'validate_fresh_closed_unlaunched').body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and getattr(n.value.func,'id',None)=='need' and 'LIMITS' in ast.unparse(n.value.args[0]))
expr=compile(ast.Expression(body=frontier_clock),'<existing_frontier_clock_predicate>','eval');frontier=json.loads(Path(P['A2frontier']['path']).read_bytes());value={'boot_id':history['boot_id'],'fixed_cutoffs':limits,'observed_clocks':first};env={'value':value,'frontier':frontier,'BOOT':live.BOOT,'LIMITS':old.PINS['limits']};assert not eval(expr,env);env['LIMITS']=limits;assert eval(expr,env);bad=dict(value,boot_id='wrong');assert not eval(expr,dict(env,value=bad));bad=dict(value,fixed_cutoffs=[limits[0]+1]+limits[1:]);assert not eval(expr,dict(env,value=bad))
print(json.dumps(dict(status='PASS_PURE_LIVE_CAP_REVALIDATION_FIXTURE',actual_query_receipts=[ref(p)for _,_,p in raw],old_historical_ceiling_refused=True,weekly_cap_passed=True,physical_negative_cases=13,frontier_negative_cases=2,guard_observe_proc_queries=0,limitations='Recorded query UTC/MONOTONIC; fixture BOOTTIME and historical physical fields; actual in-memory history and guard triplets not persisted; no replay or physical clearance.',runtime_authority=None),indent=2))
