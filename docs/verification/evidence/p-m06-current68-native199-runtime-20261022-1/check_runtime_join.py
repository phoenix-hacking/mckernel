from pathlib import Path
import ast,copy,hashlib,importlib.util,json,types
R=Path(__file__).resolve().parent

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def refuses(action,why):
 try:action()
 except (ValueError,KeyError):print('PASS refusal',why)
 else:raise AssertionError('unexpected acceptance '+why)

b=load('checked_binding',R/'bind_native199.py');manifest=b.build();print('PASS actual closed rawstage -> unchanged overlay transformer -> production manifest consumer')
data=b.checked_json(b.N/'CURRENT68-STAGE-INPUT-DATA.json',b.DATA_SHA);repl=b.checked_json(b.N/'REPLACEMENTS.ACTUAL-CURRENT68-AND-IMAGE.json',b.MAP_SHA);inv=b.checked_json(b.N/'ACTUAL-BASE-INVENTORY-ADMISSION-2.json',b.INVENTORY_SHA);stage=json.loads((b.STAGE/'manifest.json').read_text())
x=copy.deepcopy(stage);x['unknown']=1;refuses(lambda:b.validate_stage(x,data,repl,inv),'unknown raw stage schema')
x=copy.deepcopy(stage);x['replacements']['modules/mcctrl.ko']['sha256']='0'*64;refuses(lambda:b.validate_stage(x,data,repl,inv),'wrong current68 module tuple')
x=copy.deepcopy(stage);x['payload']['sha256']='0'*64;refuses(lambda:b.validate_stage(x,data,repl,inv),'wrong selected199 payload')
d=load('production_diagnostic',R/'native_diagnostic.py')
receipt=R/'actual-native199-overlay-1.manifest.json';x=json.loads(receipt.read_text());x['final_map']['modules/mcctrl.ko']['sha256']='0'*64;bad=R/'wrong-final-map.fixture.json';bad.write_text(json.dumps(x));s=copy.deepcopy(manifest['staging']);s['overlay_manifest']=b.ref(bad)
refuses(lambda:d._staging(s,manifest['artifacts'],manifest['modules']),'wrong actual overlay module member join')
x=json.loads(receipt.read_text());x['unknown']=0;bad=R/'wrong-overlay-schema.fixture.json';bad.write_text(json.dumps(x));s=copy.deepcopy(manifest['staging']);s['overlay_manifest']=b.ref(bad)
refuses(lambda:d._staging(s,manifest['artifacts'],manifest['modules']),'unknown actual overlay schema')
o=load('production_owner',R/'native_diagnostic_container_owner.py');instance=object.__new__(o.DiagnosticOwner);instance.parent=Path('/home/holden/mckernel-work/scratch/p-m06-native199-261022-1/owner-parent');instance.name='fixture';instance.label='fixture';instance.owner_sha='f'*64;instance.manifest_path='/home/holden/mckernel-work/scratch/p-m06-native199-261022-1/manifest.json';instance.manifest_sha256='e'*64;instance.nonce='a'*32
argv=instance._create_argv();mounts=[argv[i+1]for i,x in enumerate(argv)if x=='--mount'];expected_roots=[o.REPO,o.SCRATCH]+o.EXTRA_READONLY
assert all('type=bind,src='+x+',dst='+x+',readonly' in mounts for x in expected_roots)
assert len(mounts)==len(expected_roots)+1 and '--pids-limit=512' in argv and '--memory-swap=12g' in argv and '--network=none' in argv
# Execute the unchanged actual production mount-oracle AST, not a mirror.
t=ast.parse((R/'native_diagnostic_container_owner.py').read_text());cls=next(n for n in t.body if isinstance(n,ast.ClassDef)and n.name=='DiagnosticOwner');method=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='_profile');start=next(i for i,n in enumerate(method.body)if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Tuple));end=next(i for i,n in enumerate(method.body)if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Name)and n.targets[0].id=='networks');code=compile(ast.fix_missing_locations(ast.Module(body=method.body[start:end],type_ignores=[])),'actual production mount oracle','exec')
pairs=[(x,x,True)for x in expected_roots]+[(str(instance.parent),str(instance.parent),False)]
h={'Mounts':[dict(Type='bind',Source=x,Target=y,ReadOnly=ro)for x,y,ro in pairs]};row={'Mounts':[dict(Type='bind',Source=x,Destination=y,RW=not ro,Propagation='rprivate')for x,y,ro in pairs]}
def check(h,row):exec(code,dict(self=instance,h=h,row=row,need=o.need,REPO=o.REPO,SCRATCH=o.SCRATCH,EXTRA_READONLY=o.EXTRA_READONLY))
check(h,row);print('PASS actual owner create argv and requested/actual readonly mount oracle')
x=copy.deepcopy(h);x['Mounts'][-2]['ReadOnly']=False;refuses(lambda:check(x,row),'writable current input requested mount')
x=copy.deepcopy(row);x['Mounts'][-2]['RW']=True;refuses(lambda:check(h,x),'writable current input actual mount')
x=copy.deepcopy(row);x['Mounts'].pop();refuses(lambda:check(h,x),'missing actual mount')
x=copy.deepcopy(h);x['Mounts'].append(dict(Type='bind',Source='/unknown',Target='/unknown',ReadOnly=True));refuses(lambda:check(x,row),'unknown extra mount')
# Exact owner semantic delta remains constants and source-local diagnostic path.
original=ast.parse(Path('/home/holden/mckernel-work/host-preparation/current-v6-composite-native-probe-20261020-1/consumer-readonly-correction-1/native_diagnostic_container_owner.py').read_text())
old={n.name:ast.dump(n,include_attributes=False)for n in ast.walk(original)if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};new={n.name:ast.dump(n,include_attributes=False)for n in ast.walk(t)if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};assert [name for name in old if old[name]!=new[name]]==['bound_manifest']
assert (R/'native_diagnostic.py').read_bytes()==Path('/home/holden/mckernel-work/host-preparation/current-v6-composite-native-probe-20261020-1/consumer-readonly-correction-1/native_diagnostic.py').read_bytes()
print('PASS unchanged runner/evaluator/oracles/owner lifecycle and mount-control functions; only bound diagnostic path changed')
print('PASS 12 focused production join and refusal checks; no native execution')
