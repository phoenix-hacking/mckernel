"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic Q/physical/observer data checks. No guard, capture or runtime authority.
"""
import ast,copy,hashlib,importlib.util,json,pathlib,tempfile,types,unittest
D=pathlib.Path(__file__).resolve().parent
O=D.parent/'CONVERSION-FIRST-POSTJOIN-CURRENTFREE-PREPARATION-1'
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
q=load(D/'readonly_operation_guard.py','q_pure');obs=load(D/'observe_conversion_postjoin.py','obs_pure');phys=load(pathlib.Path(obs.PHYSICAL['path']),'physical_pure')
def ref(p):
 p=pathlib.Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
class Closure(unittest.TestCase):
 def setUp(self):
  self.ctx=json.loads((D/'ROOT-OPERATION-INTENT.TEMPLATE.NOT-AUTHORITY.json').read_text())['context'];self.ctx['bootstrap_caps']=ref(pathlib.Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1/EARLIEST-CONTROL-CAPS.json'));self.ctx['nonce']='ab'*16
  self.cust=json.loads((D/'ROOT-CUSTODY.TEMPLATE.NOT-AUTHORITY.json').read_text());self.cust.update(author='/root',decision='BIND_EXACT_CONVERSION_POSTRETIREMENT_READONLY_CUSTODY',no_unlisted_physical_or_custody_operations_since_retirement=True)
  self.fake={'path':'/SYNTHETIC_CUSTODY_NOT_AUTHORITY','bytes':1,'sha256':'a'*64};self.ctx['source_authority']=self.fake
  self.oldread,self.oldauth=q.read,q.auth
  q.read=lambda r:self.cust if r==self.fake else self.oldread(r);q.auth=lambda r:pathlib.Path(r['path']) if r==self.fake else self.oldauth(r)
 def tearDown(self):q.read,q.auth=self.oldread,self.oldauth;phys._BINDING=None
 def test_q_context_and_nonce(self):
  subjects=q.context_subjects(self.ctx);self.assertEqual(subjects['readonly:observer'],ref(D/'observe_conversion_postjoin.py'))
  old=self.ctx['nonce'];self.ctx['nonce']=q.read(self.ctx['current_ledger'])['consumed_nonces'][-1]
  with self.assertRaises(ValueError):q.context_subjects(self.ctx)
  self.ctx['nonce']=old;self.ctx['armed_controls']=ref(O.parent/'M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/recovery-quota-confirmation-binding-1/actual-control-binding-2/guardian_guard.py')
  with self.assertRaises(ValueError):q.context_subjects(self.ctx)
 def test_q_operation_exact_review_and_caps(self):
  subjects=q.context_subjects(self.ctx);limits=q.MAXIMUM
  op=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',operation=q.OPERATION,window_sha256=q.WINDOW_SHA,first_prepared_window_sha256=q.WINDOW_SHA,weekly_limit_identity=q.WEEKLY,billing_mode='included_only',allow_prepaid_fallback=False,predecessor_cutoffs=None,operation_cutoffs=list(limits),subjects=subjects,context=self.ctx,guardian=dict(source=subjects['guardian'],entrypoint='guard'),source_owners=['/root','/root/frontier_successor'])
  review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,implementation_ownership=False,reviewer='/root/synthetic_reviewer',operation=q.OPERATION,successor=op)
  self.assertEqual(q.validate_operation(op,review,subjects,self.ctx,(1,1,1),limits),limits)
  for key,val in [('allow_prepaid_fallback',True),('operation','wrong'),('predecessor_cutoffs',[1,1,1])]:
   changed=copy.deepcopy(op);changed[key]=val
   with self.assertRaises(ValueError):q.validate_operation(changed,review,subjects,self.ctx,(1,1,1),limits)
  with self.assertRaises(ValueError):q.validate_operation(op,review,subjects,self.ctx,limits,limits)
 def test_physical_binding_observer_route(self):
  q.context_subjects(self.ctx)
  with tempfile.TemporaryDirectory() as t:
   t=pathlib.Path(t);cfg=t/'synthetic-q-binding.json';cfg.write_text('{}');adapter=ref(D/'readonly_history_guard.py');source=ref(pathlib.Path(obs.PHYSICAL['path']));chain=phys.source_chain()
   review=dict(independent=True,implementation_ownership=False,decision='PASS_EXACT_NEW_WINDOW_PHYSICAL_HISTORY_SUCCESSOR',successor_source=source,historical_sources=chain,guard_adapter=adapter,guard_config=ref(cfg))
   rp=t/'review.json';rp.write_text(json.dumps(review));binding=dict(author='/root',successor_source=source,historical_sources=chain,guard_adapter=adapter,guard_config=ref(cfg),independent_review=ref(rp))
   bp=t/'binding.json';bp.write_text(json.dumps(binding));phys.configure(ref(bp));self.assertEqual(phys.binding(),binding)
   # Observer requires exactly this successor adapter and Q binding; no observe call.
   self.assertEqual(binding['guard_adapter'],obs.ref(D/'readonly_history_guard.py'));self.assertEqual(binding['guard_config'],ref(cfg))
   tree=ast.parse((D/'observe_conversion_postjoin.py').read_text());f=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='observe')
   candidates=[x.value for x in f.body if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and len(x.value.args)>1 and isinstance(x.value.args[1],ast.Constant) and x.value.args[1].value=='exact retained physical history with native Q adapter']
   pred=compile(ast.Expression(candidates[0].args[0]),'<physical-fixture>','eval');guard=types.SimpleNamespace(ref=lambda _:ref(cfg),BINDING=cfg)
   env=dict(history_binding=binding,ref=obs.ref,HERE=D,guard=guard)
   self.assertTrue(eval(pred,env))
   for key,wrong in [('guard_adapter',ref(O/'readonly_history_guard.py')),('guard_config',{'path':'wrong'})]:
    copy_binding=copy.deepcopy(binding);copy_binding[key]=wrong;env['history_binding']=copy_binding;self.assertFalse(eval(pred,env))
   wrong=copy.deepcopy(review);wrong['guard_adapter']=ref(O/'readonly_history_guard.py');rp.write_text(json.dumps(wrong));binding['independent_review']=ref(rp);bp.write_text(json.dumps(binding));phys._BINDING=None
   with self.assertRaises(AssertionError):phys.configure(ref(bp))
  b=dict(author='/root',decision='BIND_CONVERSION_FRONTIER_READONLY_OBSERVER',runtime_authority=None,source=obs.ref(D/'observe_conversion_postjoin.py'),current_ledger=self.ctx['current_ledger'],current_free=self.ctx['post119_current_free'],current_boundary=self.ctx['current_boundary'],independent_review={'path':'synthetic'})
  review=dict(decision='PASS_EXACT_CONVERSION_FRONTIER_READONLY_OBSERVER',independent=True,implementation_ownership=False,observer=b['source'],current_ledger=b['current_ledger'],current_free=b['current_free'],current_boundary=b['current_boundary'],complete_actual_actor_frontier=True,original_resource_lock_holder_cgroup_checks_preserved=True,runtime_authority=None,binding_payload={k:v for k,v in b.items() if k!='independent_review'})
  obs.validate_route(b,self.ctx,review)
  for key in ('source','current_ledger','current_free','current_boundary'):
   wrong=copy.deepcopy(b);wrong[key]={'path':'wrong'}
   with self.subTest(key=key):
    with self.assertRaises(ValueError):obs.validate_route(wrong,self.ctx,review)
 def test_q_propagates_tighter_dynamic_caps(self):
  # Replace every live dependency with inert synthetic inputs; no real guard is called.
  names=('read','ref','decode','binding_metadata','confirmed_weekly_ceiling','validate_operation','auth','load','triplet','STATE')
  old={name:getattr(q,name) for name in names};oldtime=q.time
  limit=(1000,1000,1000);dynamic=(900,800,700)
  guardian=types.SimpleNamespace(guard=lambda:[100,100,100],current_caps=lambda:dynamic)
  binder=types.SimpleNamespace(weekly_limits=lambda a,b:limit)
  q.read=lambda x: {'accepted_helper':'fake'} if x==q.FIXED else {};q.ref=lambda x:'fake';q.decode=lambda x:{}
  q.binding_metadata=lambda x: ({},{},{'armed_controls':'a','bootstrap_caps':'b'},{'guardian':'g'})
  q.confirmed_weekly_ceiling=lambda a,b:limit;q.validate_operation=lambda *a:limit;q.auth=lambda x:None
  q.load=lambda ref,name: guardian if name=='exact_readonly_weekly_guardian' else binder
  q.triplet=lambda x:tuple(x);q.STATE=types.SimpleNamespace(read_bytes=lambda:b'{}')
  q.time=types.SimpleNamespace(time=lambda:100,monotonic=lambda:100,CLOCK_BOOTTIME=1,clock_gettime=lambda _:100)
  try:self.assertEqual(q._evaluate()[1],dynamic)
  finally:
   for name,value in old.items():setattr(q,name,value)
   q.time=oldtime
 def test_release_output_exact_predicates_without_main(self):
  tree=ast.parse((D/'observe_conversion_postjoin.py').read_text());main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main')
  calls=[x.value for x in main.body if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='need']
  # Evaluate the actual unchanged release and output AST against synthetic arguments.
  release_pred=compile(ast.Expression(calls[1].args[0]),'<release-fixture>','eval')
  binding=obs.BINDING;out=D/'actual-frontier-1/OBSERVATION.json';bref={'path':'synthetic-binding'}
  release=dict(author='/root',decision='AUTHORIZE_ONE_CONVERSION_POSTJOIN_READONLY_CAPTURE',maximum_invocations=1,source=obs.ref(D/'observe_conversion_postjoin.py'),bindings=bref,output=str(out),native_authority=None,runtime_authority=None)
  env={'args':types.SimpleNamespace(bindings=binding,output=out),'BINDING':binding,'release':release,'ref':obs.ref,'__file__':str(D/'observe_conversion_postjoin.py'),'binding_ref':bref,'str':str}
  self.assertTrue(eval(release_pred,env))
  for key,val in [('source',ref(O/'observe_conversion_postjoin.py')),('bindings',{'path':'wrong'}),('output','/wrong'),('maximum_invocations',2),('decision','wrong')]:
   old=release[key];release[key]=val
   with self.subTest(key=key):self.assertFalse(eval(release_pred,env))
   release[key]=old
  env['args']=types.SimpleNamespace(bindings=O/'ROOT-ACTUAL-FRONTIER-OBSERVER-BINDING.json',output=out);self.assertFalse(eval(release_pred,env))
  output_pred=compile(ast.Expression(calls[4].args[0].values[0]),'<output-path-fixture>','eval')
  env.update(args=types.SimpleNamespace(output=out),HERE=D);self.assertTrue(eval(output_pred,env))
  env['args']=types.SimpleNamespace(output=O/'actual-frontier-1/OBSERVATION.json');self.assertFalse(eval(output_pred,env))
if __name__=='__main__':unittest.main()
