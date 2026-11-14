"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
TEST_ONLY: retained expired A2 metadata, simulated clocks/Proc snapshots, NO_APPROVAL.
Never runs utility main, real account guard/current query, publisher or grant writer.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,sys,types
Q=Path(__file__).resolve().parent;C=Q.parent;D=C.parent;E=D.parent
A=E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-2';H=A/'FINITE-REVIEW-HANDOFF';R=C/'attempt2-root49-metadata-rebase-source-1'
TEST_ONLY=True

def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
u=module(Q/'finite_review.py','TEST_ONLY_hot_utility_no_main')
pred=module(Q/'hot_predicates.py','TEST_ONLY_exact_pure_predicates')
real_read=u.read_json_ref;real_reference=u.reference

def read(p):return json.loads(Path(p).read_bytes())
b=read(R/'REVIEWER-ACTUAL-BINDINGS.json');b['_bindings']=str(R/'REVIEWER-ACTUAL-BINDINGS.json')
refs=b['static_refs'];p=real_read(refs['profile']);x=real_read(refs['input_export']);request=real_read(refs['request_payload']);adoption=real_read(refs['request_adoption']);ledger=real_read(refs['nonce_ledger']);publication=real_read(refs['source_publication']);marker=read(H/'ROOT-HELD-CAPTURE.COMPLETE.json');resource=real_read(marker['resource']);physical=real_read(marker['physical']);root_input=real_read(marker['root_resource_input']);holder=real_read(marker['holder_ready'])['holder'];policy=read(C/'ROOT-AGGREGATE-JOB-POLICY-AND-RESERVATION.json');schema=read(Q/'TEST_ONLY-A2-OBSERVER-SCHEMA.json')
# All real payloads remain immutable and hash-authenticated. Simulation changes
# only clock/Proc sources, never observed timestamps, JSON refs or actual policy.
allrefs=list(refs.values())+[marker[k] for k in ['pending_input','resource','physical','root_resource_input','holder_ready','holder_bootstrap']]
original_bytes={r['path']:Path(r['path']).read_bytes() for r in allrefs}
now=[v+1 for v in resource['observed_clocks']]
limits=[min(v) for v in zip(u.CUTOFFS,p['fixed_three_clock_cutoffs'],physical['physical']['fixed_cutoffs'])]
# Reuse exact original resource_guards PURE body. It has no IO, subprocesses or
# service calls; simulated physical values are its explicit function arguments.
runner_tree=ast.parse(Path(refs['runner']['path']).read_text());nodes=[]
for z in runner_tree.body:
 if isinstance(z,ast.FunctionDef) and z.name in ['require','resource_guards']:nodes.append(z)
 if isinstance(z,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['DEADLINE','MEMORY','BUDGET'] for t in z.targets):nodes.append(z)
ns={'os':os};exec(compile(ast.Module(body=nodes,type_ignores=[]),'TEST_ONLY exact original pure resource_guards','exec'),ns)
trace=[]
class Runner:
 def current_operation_guard(self):trace.append('TEST_ONLY_GUARD_STUB_NO_IO');return list(now)
 def resource_guards(self,*args):trace.append('ORIGINAL_RESOURCE_GUARDS_PURE');return ns['resource_guards'](*args)
class VPath:
 def __init__(self,p):self.p=str(p)
 def __truediv__(self,p):return VPath(self.p+'/'+str(p))
 def read_text(self):
  trace.append('TEST_ONLY_PROC_FIXTURE:'+self.p)
  values={'/proc/locks':resource['actual_observations']['lock_rows'],'/proc/meminfo':'MemAvailable: '+str(resource['actual_observations']['memory']['MemAvailable']//1024)+' kB\n','/proc/loadavg':'0 0 0 1/'+str(resource['actual_observations']['host_threads'])+' 1\n','/proc/sys/kernel/threads-max':str(resource['actual_observations']['thread_limit'])}
  assert self.p in values,('unexpected TEST_ONLY path',self.p);return values[self.p]
 def stat(self):
  assert self.p=='/proc/'+str(holder['pid'])+'/fd/3';trace.append('TEST_ONLY_FD3_FIXTURE');return types.SimpleNamespace(st_dev=27,st_ino=4)
# Source utility's no_launch function still executes, with an explicit captured
# negative launch-state fixture. No live filesystem occupancy is queried.
no_launch_fn=next(z for z in ast.parse((Q/'handoff_common.py').read_text()).body if isinstance(z,ast.FunctionDef) and z.name=='no_launch')
launch={n:False for n in ['OUTPUT','ACTUAL-INDEPENDENT-BUILD-EXECUTION-REVIEW.json','ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json','HOLDER/ROOT-BUILD-GRANT.READY.json','HOLDER/RUNNER.STARTED.json']}
def fixture_lexists(path):
 name=str(Path(path).relative_to(A));assert name in launch;trace.append('TEST_ONLY_ABSENCE:'+name);return launch[name]
lns={'need':u.need,'os':types.SimpleNamespace(path=types.SimpleNamespace(lexists=fixture_lexists))};exec(compile(ast.Module(body=[no_launch_fn],type_ignores=[]),'TEST_ONLY original no_launch predicate','exec'),lns)
u.Path=VPath;u.birth=lambda pid:(u.need(pid==holder['pid'],'TEST_ONLY exact holderPID'),holder['starttime'])[1];u.no_launch=lns['no_launch'];u.clocks=lambda:list(now)
c=dict(b=b,A=A,H=H,p=p,x=x,q=request,a=adoption,runner=Runner(),predicates=pred,job_policy=policy,observer_schema=schema,ledger=ledger,pub=publication,limits=limits,ready_ref=marker['prewarm_ready'])
def FORBIDDEN_REAL_APPROVAL_WRITER(*args,**kwargs):raise AssertionError('TEST_ONLY real approval writer blocked')
u.atomic_json=FORBIDDEN_REAL_APPROVAL_WRITER
# Exact invocation of the ENTIRE production hot() body, not just pure subsets.
result=u.hot(c,marker)
assert result['implementation_ownership'] is False and result['maximum_invocations']==1 and result['payload_sha256']==marker['pending_input']['sha256']
assert 'ORIGINAL_RESOURCE_GUARDS_PURE' in trace
# Execute the production final-before-publication callback AST with stubs. The
# writer deliberately NEVER publishes any approval path (including under Q).
main=next(z for z in ast.parse((Q/'finite_review.py').read_text()).body if isinstance(z,ast.FunctionDef) and z.name=='main');callback=next(z for z in ast.walk(main) if isinstance(z,ast.FunctionDef) and z.name=='final_before_publish')
cbns=dict(u.__dict__,c=c,result=result);exec(compile(ast.Module(body=[callback],type_ignores=[]),'TEST_ONLY exact postfsync callback','exec'),cbns)
writer_calls=[]
def NO_APPROVAL_WRITER(path,value,before_publish):
 assert TEST_ONLY;writer_calls.append('TEST_ONLY_NO_APPROVAL_WRITER');before_publish();return dict(TEST_ONLY=True,NO_APPROVAL=True)
assert NO_APPROVAL_WRITER('FORBIDDEN_REAL_PASS_PATH',result,cbns['final_before_publish'])==dict(TEST_ONLY=True,NO_APPROVAL=True)
# Entire-hot-path negative controls: concrete mismatches fail closed before any
# no-approval writer call. JSON fixtures remain in memory; expired originals stay.
negatives=[]
def expect_rejected(label,change):
 mutated=copy.deepcopy(resource);mutable_physical=copy.deepcopy(physical);ctx=copy.copy(c);ctx['observer_schema']=copy.deepcopy(schema);ctx['job_policy']=copy.deepcopy(policy)
 ctx['_TEST_ONLY_overrides']={}
 change(ctx,mutated,mutable_physical)
 def fake_read(r):
  if r==marker['resource']:return mutated
  if r==marker['physical']:return mutable_physical
  for key,value in ctx['_TEST_ONLY_overrides'].items():
   if r==marker[key]:return value
  return real_read(r)
 u.read_json_ref=fake_read
 try:u.hot(ctx,marker)
 except (ValueError,RuntimeError,KeyError,AssertionError):negatives.append(label)
 else:raise AssertionError('negative control accepted: '+label)
 finally:u.read_json_ref=real_read
expect_rejected('exact current ledger mismatch',lambda c,r,p:p['physical'].__setitem__('Root49',{'changed':'TEST_ONLY'}))
expect_rejected('source-reviewed observer status mismatch',lambda c,r,p:p['physical'].__setitem__('status','wrong_TEST_ONLY'))
expect_rejected('current-boundary mismatch',lambda c,r,p:p['physical'].__setitem__('current_boundary',{'wrong':'TEST_ONLY'}))
expect_rejected('jobreservation exceeds7',lambda c,r,p:c['job_policy'].__setitem__('other_build_jobs_reserved',3))
expect_rejected('jobpolicy vs current memory reservation',lambda c,r,p:c['job_policy'].__setitem__('ordinary_memory_bytes_reserved',0))
expect_rejected('original CPUcap mismatch',lambda c,r,p:r.__setitem__('cpus',[1,2,3,4]))
expect_rejected('original floor failure',lambda c,r,p:r['actual_observations']['capacity'].__setitem__('scratch',0))
# Additional expert-required bounded negatives across the same complete path.
expect_rejected('missing current ledger key',lambda c,r,p:p['physical'].pop('Root49'))
expect_rejected('historical ledger offered for current',lambda c,r,p:(p['physical'].pop('Root49'),p['physical'].__setitem__('root_ledger35',ledger)))
expect_rejected('historical free offered for current',lambda c,r,p:p['physical'].__setitem__('actual_latest_operation_postjoin_acceptance',{'historical':'TEST_ONLY'}))
expect_rejected('wrong exact envelope observer',lambda c,r,p:p.__setitem__('observer',{'wrong':'TEST_ONLY'}))
expect_rejected('jobpolicy noninteger count',lambda c,r,p:c['job_policy'].__setitem__('ordinary_CPU6_jobs_reserved',1.0))
expect_rejected('jobpolicy declared sum contradiction',lambda c,r,p:c['job_policy'].__setitem__('total_reserved_build_jobs',6))
expect_rejected('jobpolicy wrong Root author',lambda c,r,p:c['job_policy'].__setitem__('author','wrong_TEST_ONLY'))
expect_rejected('policy to current PID mismatch',lambda c,r,p:c['job_policy'].__setitem__('ordinary_pids_reserved',65))
expect_rejected('cgroup occupancy dirty',lambda c,r,p:r['actual_observations']['cgroups'].__setitem__('/sys/fs/cgroup/pids/mckernel-dev/pids.current','1'))
expect_rejected('current noheavy false',lambda c,r,p:p['physical'].__setitem__('no_existing_heavy',False))
expect_rejected('current pids dirty',lambda c,r,p:p['physical'].__setitem__('pids_current',1))
expect_rejected('active records dirty',lambda c,r,p:p['physical'].__setitem__('active_shared_records_absent',False))
expect_rejected('captured sole flock contradiction',lambda c,r,p:r['actual_observations'].__setitem__('lock_rows',''))
expect_rejected('resource holder birth contradiction',lambda c,r,p:r['reservation_holder'].__setitem__('starttime',1))
expect_rejected('resource holder FD contradiction',lambda c,r,p:r['reservation_holder'].__setitem__('fd',4))
def pending_nonce(c,r,p):
 v=real_read(marker['pending_input']);v['nonce']='bad_TEST_ONLY';c['_TEST_ONLY_overrides']['pending_input']=v
expect_rejected('pending nonce mismatch',pending_nonce)
def missing_reservation(c,r,p):
 v=real_read(marker['root_resource_input']);v.pop('other_reserved_pids');c['_TEST_ONLY_overrides']['root_resource_input']=v
expect_rejected('missing Root reservation field',missing_reservation)
# Cold byte authority helper remains bytes-only; corrupted policy hash rejected.
bad=u.reference(C/'ROOT-AGGREGATE-JOB-POLICY-AND-RESERVATION.json');bad['sha256']='0'*64
try:u.verify_ref(bad)
except (ValueError,RuntimeError):negatives.append('altered cold policy authority hash')
else:raise AssertionError('corrupted static authority accepted')
for label,triple in [('before-observed clock',[v-1 for v in resource['observed_clocks']]),('UTC cutoff',[limits[0],resource['observed_clocks'][1]+1,resource['observed_clocks'][2]+1]),('MONO cutoff',[resource['observed_clocks'][0]+1,limits[1],resource['observed_clocks'][2]+1]),('BOOT cutoff',[resource['observed_clocks'][0]+1,resource['observed_clocks'][1]+1,limits[2]])]:
 now[:]=triple
 try:u.hot(c,marker)
 except (ValueError,RuntimeError,KeyError,AssertionError):negatives.append(label)
 else:raise AssertionError('bad simulated clock accepted '+label)
now[:]=[v+1 for v in resource['observed_clocks']]
for key in ['pending_input','resource']:
 bad_marker=copy.deepcopy(marker);bad_marker[key]['sha256']='0'*64
 try:u.hot(c,bad_marker)
 except (ValueError,RuntimeError,KeyError,AssertionError):negatives.append('changed '+key+' byte ref')
 else:raise AssertionError('changed subject byte ref accepted')
try:u.atomic_json(A/'INDEPENDENT-FINITE-REVIEW.PASS.json',result)
except AssertionError:negatives.append('attempted real approval writer blocked')
else:raise AssertionError('real approval writer reachable')
# Finalcallback expiry failure prevents even the NO_APPROVAL writer returning.
now[:]=[v+121 for v in resource['observed_clocks']]
try:NO_APPROVAL_WRITER('FORBIDDEN_REAL_PASS_PATH',result,cbns['final_before_publish'])
except (ValueError,RuntimeError):negatives.append('postfsync original120s expiry')
else:raise AssertionError('expired callback accepted')
assert all(Path(name).read_bytes()==raw for name,raw in original_bytes.items())
proof=dict(scope=__doc__.splitlines()[0],TEST_ONLY=True,decision='TEST_ONLY_HOT_PREDICATES_COMPLETE_NOT_APPROVAL',simulated_clock=True,actual_resource_reused_only_as_fixture=True,runtime_authority=None,real_PASS_writes=0,real_approval=False,real_account_guards_queries_or_utility_main=0,simulated_clocks='Original retained observed UTC/MONO/BOOT+1 for positive only, +121 negative; originals not rewritten',raw_A2_JSON_or_refs_modified=False,whole_hot_body_exercised=True,exact_original_resource_guards_exercised=True,exact_guardian_pure_predicates_exercised=True,production_postfsync_callback_exercised=True,negative_controls=negatives,NO_APPROVAL_writer_calls=writer_calls,no_real_PASS_written=True,trace=trace,retained_payloads_unchanged=len(original_bytes),all_real_publication_calls_blocked=True)
fixture_rows=[dict(path=name,bytes=len(raw),sha256_before=hashlib.sha256(raw).hexdigest(),sha256_after=hashlib.sha256(Path(name).read_bytes()).hexdigest()) for name,raw in sorted(original_bytes.items())]
with (Q/'RETAINED-A2-FIXTURE-BYTE-HASHES.json').open('x') as f:json.dump(dict(TEST_ONLY=True,runtime_authority=None,raw_payloads=fixture_rows,all29_equal=all(x['sha256_before']==x['sha256_after'] for x in fixture_rows)),f,indent=2);f.write('\n')
output=Q/'TEST_ONLY-ENTIRE-HOT-RESULT-FINAL.json'
with output.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in proof.items() if k!='trace'}))
