from pathlib import Path
import ast,copy,hashlib,importlib.util,json
P=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel')
B=P.parent/'rust-scheduler-debug-materialization-final-20261018-1'
OLD=P.parent/'rust-fp-reset-image-terminal-preparation-20261018-1'
T=Path('/home/holden/mckernel-work/scratch/rust-three-port-terminal-preparation-20261018-1')
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(p,n):
 sp=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
checks=[]
m=module(P/'cleanup.py','cleanup');o=module(P/'observe_reset_image_retirement.py','observer');c=module(P/'consume_raw_five.py','raw');e=module(P/'export_raw_five.py','export');s=module(P/'readback_observer.py','summary');post=module(P/'postjoin_readback.py','post');ret=module(P/'retention_observer.py','retention')
import contextlib,io
with contextlib.redirect_stdout(io.StringIO()):
 assert m.main([])==1
checks.append('cleanup CLI refuses without exact independent release')
with contextlib.redirect_stderr(io.StringIO()):
 try:o.main([])
 except SystemExit as ex:assert ex.code==2;checks.append('observer CLI requires exact independently released arguments')
 else:raise AssertionError('observer without release executed')
static=load(P/'selected-static-map.json');q=load(B/'image-request.json')
assert len(static['full_source_sha256'])==11 and q['host_owner_path'] in static['full_source_sha256']
for p,h in static['paths'].items():assert sha(Path(p))==h
checks.append('all actual eleven source and request/compiler-input bytes match')
ns=dict(m.__dict__);ns.update(target={'exit_code':0},client_rows=[{'status_path':'/fixture/client-status'}],ROOT_TERMINAL=Path('/fixture/guard'))
exec(compile((P/'actual-required-body.py').read_text(),'actual configure required body','exec'),ns)
rows=[dict(path=k,sha256=h) for k,h in static['paths'].items()]
rows += [dict(path=str(x),sha256='f'*64) for x in (m.TERMINAL,ns['ROOT_TERMINAL'],m.EVIDENCE/'attempt/container.log',m.OUTPUT/'evidence/receipt.json',m.OUTPUT/'output/build/kernel/mckernel.img',m.OUTPUT/'evidence/artifacts/mckernel.img',Path('/fixture/client-status'))]
assert ns['actual_required_joins'](q,rows);checks.append('actual configure consumer accepts all current source joins')
for name in ('missing-host-owner','wrong-host-owner','wrong-toolchain'):
 bad=copy.deepcopy(rows);key=q['host_owner_path'] if name!='wrong-toolchain' else q['toolchain_manifest']
 if name=='missing-host-owner':bad=[r for r in bad if r['path']!=key]
 else:next(r for r in bad if r['path']==key)['sha256']='0'*64
 try:ns['actual_required_joins'](q,bad)
 except (m.Refusal,KeyError,TypeError):checks.append('reject '+name)
 else:raise AssertionError('bad current source accepted')
selected=set()
for n in ast.walk(ast.parse((P/'observe_reset_image_retirement.py').read_text())):
 if isinstance(n,ast.List) and all(isinstance(x,ast.Constant) and isinstance(x.value,str) for x in n.elts):selected.update(ast.literal_eval(n))
assert set(static['paths'])<=selected;checks.append('actual observer executable selection includes real host owner and full11')
archive=T/'cleanup-proposal-1/dispatcher-raw-five.stdout';summary=load(T/'observer-actual-join-1/dispatcher-readback.stdout')
data,values=c.validate(archive.read_bytes(),summary);assert len(data)==5 and values['cleanup-release-draft.json']['observation']==values['observation.json'];checks.append('accepted actual raw-five original bytes consumed')
bad=copy.deepcopy(summary);bad['file_sha256'][c.NAMES[0]]='0'*64
try:c.validate(archive.read_bytes(),bad)
except AssertionError:checks.append('reject wrong raw original hash')
else:raise AssertionError('bad raw hash accepted')
pairs=load(Path(load(T/'actual-retained-join.json')['authority']['path']));image=next(p for p in pairs if p['original']['path'].endswith('mckernel.img'))
meta=o.new_object_binding(m,image['retained']);assert meta['sha256']==image['retained']['sha256'] and all(k in meta for k in ('mtime_ns','ctime_ns','size','device','inode'));checks.append('actual accepted retained image fd stable bytes size metadata')
assert e.COMMAND[-5:]==list(c.NAMES)==list(s.NAMES) and post.OBSERVER_SHA==sha(P/'observe_reset_image_retirement.py')
assert 'len(actual)==30' in (P/'postjoin_readback.py').read_text();checks.append('finite raw5 and30row postjoin consumer bindings')
try:ret.validate({'status':'PENDING'})
except RuntimeError:checks.append('unreleased retention refuses')
else:raise AssertionError('unreleased retention accepted')
old=module(OLD/'downstream-2/observe_reset_image_retirement.py','oldobserver')
functions=lambda p:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
before=functions(OLD/'downstream-2/observe_reset_image_retirement.py');after=functions(P/'observe_reset_image_retirement.py')
for name in ('stable_bytes','store','docker_child_profile','observed_command','new_object_binding','validate_observation_release'):assert before[name]==after[name]
checks.append('six accepted safety and actual-consumer bodies unchanged')
report=dict(status='PASS_AFFECTED_ACTUAL_CONSUMERS_ONLY',checks=checks,source_rows=11,raw_files=5,new_builds=0,new_guest_behavior=0,pending=list(o.PENDING_BINDINGS),root=False,docker=False,cleanup=False)
(P/'actual-consumer-checks.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(status=report['status'],checks=len(checks))))
