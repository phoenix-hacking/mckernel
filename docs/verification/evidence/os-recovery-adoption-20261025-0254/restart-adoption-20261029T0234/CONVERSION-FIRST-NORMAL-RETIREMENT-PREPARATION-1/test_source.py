"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source/retained-DATA and explicitly synthetic negative metadata fixtures only.
"""
from pathlib import Path
import ast,copy,json,hashlib,importlib.util
D=Path(__file__).resolve().parent;OLD=D.parent/'CURRENT119-NORMAL-RETIREMENT-PREPARATION-1/parent-custody-data-correction-1'
def ref(p):
 b=Path(p).read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
spec=importlib.util.spec_from_file_location('source_only_conversion_retirement',D/'retire_exact_conversion_stopped_container.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
b=m.bindings();packet,protected,profile,claim,plan,terminal=m.validate_retained(b)
assert b['cid']=='a7fe0b67d129afc3868d329d65f68317b6aadee6bedd7bc76330a52cdd0ae7ef' and b['nonce']=='4709c9fae2c743a7acd662e93a663358'
assert len(b['prior_actors'])==212 and len({(a['pid'],a['start'])for a in b['prior_actors']})==207 and len(b['new_known_actors'])==2
assert profile['inputs']['retained_count']==9 and b['command_count']==len(plan['commands'])==3
for r in packet['retained_actual_outputs']:m.authenticated(r)
for r in protected['records']:
 if r['kind']=='file':m.authenticated({k:r[k]for k in ('path','bytes','sha256')})
 else:assert Path(r['path']).is_symlink() and str(Path(r['path']).readlink())==r['target']
oldtree=ast.parse((OLD/'retire_exact_current119_stopped_container.py').read_bytes());newtree=ast.parse((D/'retire_exact_conversion_stopped_container.py').read_bytes())
nodes=lambda t:{n.name:n for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};a,c=nodes(oldtree),nodes(newtree)
class Text(ast.NodeTransformer):
 def visit_Constant(self,n):return ast.copy_location(ast.Constant(value='TEXT'),n)if isinstance(n.value,str)else n
unchanged=[]
for name in a:
 if name not in ['validate_retained','validate_release']:
  assert ast.dump(Text().visit(copy.deepcopy(a[name])),include_attributes=False)==ast.dump(Text().visit(copy.deepcopy(c[name])),include_attributes=False),name
  unchanged.append(name)
# Execute only the release's actual typed-ledger block, excluding publication,
# independent-review and runtime output paths. Pure fixture auth substitutes only
# the ledger or acceptance document for each deliberate negative case.
f=c['validate_release'];start=next(i for i,n in enumerate(f.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='ledger'for t in n.targets));end=next(i for i,n in enumerate(f.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='source'for t in n.targets));block=ast.Module(body=f.body[start:end],type_ignores=[]);code=compile(block,'<pure_consumed74_entry>','exec');release=json.loads((D/'RELEASE.TEMPLATE.NOT-AUTHORITY.json').read_bytes());ledger=m.authenticated(b['current_ledger'],True)
def exercise(query,ledger_override=None,accept_override=None):
 def authenticated(r,declared_json=False):
  if r==b['current_ledger']and ledger_override is not None:return ledger_override
  if r==b['current_build_ledger_entry']['independent_artifact_acceptance']and accept_override is not None:return accept_override
  return m.authenticated(r,declared_json)
 env=dict(authenticated=authenticated,r=query,b=b,need=m.need);exec(code,env)
exercise(release);negative=[]
def reject(name,mutate):
 l=copy.deepcopy(ledger);mutate(l)
 try:exercise(release,l)
 except (m.Refusal,KeyError,AssertionError):negative.append(name)
 else:raise AssertionError('accepted '+name)
reject('missing consumed nonce',lambda l:l['consumed_nonces'].pop())
reject('wrong container',lambda l:l['conversion_first_build'].__setitem__('container','0'*64))
reject('wrong command count',lambda l:l['conversion_first_build'].__setitem__('command_returncodes',[0]*4))
reject('native acceptance invented',lambda l:l['conversion_first_build'].__setitem__('native_acceptance',True))
reject('UNKNOWN client births rewritten',lambda l:l['conversion_first_build'].__setitem__('unmeasured_docker_client_births','KNOWN'))
reject('pending clearance cleared',lambda l:l.__setitem__('current_physical_clearance_pending',False))
reject('changed heavy native history',lambda l:l.__setitem__('current_native_operation',{}))
assert len(negative)==7
out=dict(status='PASS_SOURCE_AND_ACTUAL_RETAINED_DATA_ONLY',actual_packet_ref=ref(D/'NORMAL-RETIREMENT-PACKET.json'),actual_bindings_ref=ref(D/'BINDINGS.json'),protected_records=len(protected['records']),retained212_prior_rows=True,new_known_actors=2,commands=3,retained_objects=9,unchanged_AST_except_schema_strings=unchanged,negative_metadata_cases=negative,explicitly_synthetic_negative_documents=True,guard=0,proc=0,Docker=0,compiler=0,native=0)
(D/'PURE-CHECKS.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
