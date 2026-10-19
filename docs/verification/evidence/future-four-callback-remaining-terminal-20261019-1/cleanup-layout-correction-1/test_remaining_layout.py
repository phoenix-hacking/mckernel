from pathlib import Path
import ast,copy,hashlib,importlib.util,json,tarfile
D=Path(__file__).resolve().parent;L=D.parent;B=L/'terminal-handoff-preparation-1'
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
spec=importlib.util.spec_from_file_location('affected_remaining_cleanup',D/'cleanup_fourleaf_remaining_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tarfile.open(B/'actual-root-readonly-1/raw-five-export.tar') as f:obs=json.loads(f.extractfile('observation.json').read())
request=json.loads(m.REQUEST.read_bytes());item=obs['container_inspect'];target=obs['target'];checks=[]
# Extract the EXACT consumed configure profile+mount statements. Earlier git,
# namespace and root effects are intentionally outside this no-effect fixture.
source=(D/'cleanup_fourleaf_remaining_layout.py').read_text();tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='configure');start=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and ast.get_source_segment(source,n).startswith('config, host ='));stop=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and ast.get_source_segment(source,n).startswith("records = obs['retained_exclusions']"));body=copy.deepcopy(fn.body[start:stop]);assert len(body)==7
f=ast.FunctionDef(name='saved_profile_block',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=n) for n in ('request','item','target')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=body+[ast.Return(value=ast.Constant(value=True))],decorator_list=[]);mod=ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[]));exec(compile(mod,'<actual configure profile and mounts>','exec'),m.__dict__)
args,mounts=m.image_layout(request);assert args==item['Args']==item['Config']['Cmd'];assert m.saved_profile_block(request,item,target);checks.append('actual_saved_remaining_args_full_prefix_suffix_caps_mounts')
baseargs,_=m.image_layout_base(request);assert args==baseargs+['--retained-phase-proof','/work/remaining-phase-proof.json','--retained-phase-sha256','672aa7078db36e418637bf53685928f0a01a3a89f23ce6c66cdc37a1a107a46a'];checks.append('exact_reviewed_producer_suffix')
def refusal(name,call,wanted):
 try:call()
 except m.Refusal as e:assert str(e)==wanted,(name,str(e),wanted);checks.append(name);return
 raise AssertionError('accepted:'+name)
def badargs(name,new):
 v=copy.deepcopy(item);v['Args']=new;v['Config']['Cmd']=new;refusal(name,lambda:m.saved_profile_block(request,v,target),'reviewed-container-profile')
badargs('missing_suffix',args[:-4]);badargs('reordered_suffix',args[:-4]+[args[-2],args[-1],args[-4],args[-3]]);badargs('duplicate_suffix',args+args[-4:]);badargs('changed_proof_path',args[:-3]+['/work/other-proof.json']+args[-2:]);badargs('changed_proof_hash',args[:-1]+['0'*64]);badargs('unbounded_suffix',args+['--other']);badargs('changed_prefix',args[:2]+['/other-source']+args[3:])
v=copy.deepcopy(item);v['Config']['Cmd']=args[:-4];refusal('args_cmd_disagreement',lambda:m.saved_profile_block(request,v,target),'reviewed-container-profile')
v=copy.deepcopy(item);v['HostConfig']['Memory']=1;refusal('original_host_cap_preserved',lambda:m.saved_profile_block(request,v,target),'reviewed-container-profile')
v=copy.deepcopy(item);v['Mounts'][0]['RW']=not v['Mounts'][0]['RW'];refusal('original_mount_constraint_preserved',lambda:m.saved_profile_block(request,v,target),'exact-image-mounts')
original=m.REMAINING_LAYOUT_BINDINGS
for label,field,value,wanted in [('unauthenticated_proof_path','path','/work/unreviewed-proof.json','remaining-layout-review-lineage'),('unauthenticated_proof_hash','sha256','0'*64,'remaining-layout-review-lineage')]:
 m.REMAINING_LAYOUT_BINDINGS=copy.deepcopy(original);m.REMAINING_LAYOUT_BINDINGS['proof'][field]=value;refusal(label,lambda:m.image_layout(request),wanted)
m.REMAINING_LAYOUT_BINDINGS=copy.deepcopy(original);m.REMAINING_LAYOUT_BINDINGS['canonical_review']['sha256']='0'*64;refusal('unauthenticated_authority',lambda:m.image_layout(request),'remaining-layout-authenticated-input');m.REMAINING_LAYOUT_BINDINGS=original
# Freeze exact function equivalence: all preexisting gates, including configure,
# remain identical. Only image_layout is expanded; its old body is exact base.
a=ast.parse((L/'cleanup_fourleaf.py').read_bytes());oldf={n.name:n for n in a.body if isinstance(n,ast.FunctionDef)};newf={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
for n in oldf:
 if n!='image_layout':assert ast.dump(oldf[n],include_attributes=False)==ast.dump(newf[n],include_attributes=False),n
base=copy.deepcopy(newf['image_layout_base']);base.name='image_layout';assert ast.dump(base,include_attributes=False)==ast.dump(oldf['image_layout'],include_attributes=False)
p0=ast.parse((L/'postjoin_readback.py').read_bytes());p1=ast.parse((D/'postjoin_readback_remaining_layout.py').read_bytes());functions=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef)};assert functions(p0)==functions(p1)
for t in (p0,p1):
 for n in t.body:
  if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('ENGINE','ENGINE_SHA'):n.value=ast.Constant(value=n.targets[0].id)
assert ast.dump(p0,include_attributes=False)==ast.dump(p1,include_attributes=False);checks.append('all_old_gates_and_postjoin_functions_unchanged')
x=dict(status='PASS_ACTUAL_SAVED_LAYOUT_AND_EXTRACTED_CONFIGURE_PROFILE_BLOCK_ONLY',checks=checks,count=len(checks),cleanup=ref(D/'cleanup_fourleaf_remaining_layout.py'),postjoin=ref(D/'postjoin_readback_remaining_layout.py'),saved_archive=ref(B/'actual-root-readonly-1/raw-five-export.tar'),actual_configure_block_ast_sha256=hashlib.sha256(ast.dump(ast.Module(body=body,type_ignores=[]),include_attributes=False).encode()).hexdigest(),unchanged_original_functions=len(oldf)-1,original_configure_function_ast_unchanged=True,postjoin_only_engine_literal_changes=True,root_executed=False,full_configure_acceptance_claimed=False)
p=D/'fixture-result.json'
with p.open('x') as f:json.dump(x,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(dict(status=x['status'],count=len(checks),result=ref(p))))
