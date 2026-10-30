#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import ast,copy,importlib.util,json,pathlib
O=pathlib.Path(__file__).resolve().parent;A=O.parent;sp=importlib.util.spec_from_file_location('validator',O/'validator.py');v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
items=json.loads((A/'m14-configure-input-matrix-1/PROFILE-OUT-ROOT.NOT-RELEASED.json').read_text())['configure_argv_items'];results=[]
def fixture(flags):
 values={'UNAME_R':'synthetic','MCKERNEL_M14_EXPECTED_UNAME_R':'synthetic','MCKERNEL_M14_EXPECTED_MAP_KERNEL_START':'0x1234','MCKERNEL_M14_EXPECTED_MAKE_SHA256':'a'*64,'KBUILD_MAKE_FLAGS':flags,'MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS':flags}
 argv=[i['value'] for i in items if 'flag' not in i]+[i['flag']+'='+values[i['flag'][2:]] for i in items if 'flag' in i]
 pairs={'--make-status':'0','--module':'/work/output/build/tmp.resolve_MODULES_END/driver.ko','--kernel-release':'/out/build/include/config/kernel.release','--uts-release-header':'/out/build/include/generated/utsrelease.h','--uname-r':'synthetic','--expected-map':'0x1234','--cmake-cache':'/work/output/build/CMakeCache.txt','--compile-commands':'/work/output/build/compile_commands.json','--expected-kernel-dir':'/out/build','--expected-build-dir':'/work/output/build'}
 verify=['/usr/bin/python3','-I','-B','/src/scripts/verify_m14_elf.py']
 for k,x in pairs.items():verify.extend([k,x])
 commands=[{'stage':'Configure ON composite','cwd':'/work','argv':argv},{'stage':'Post-generation verification','cwd':'/work','argv':verify}]
 return {'commands':commands,'required_actual_values':values}
for flags in ('','CC=/usr/bin/clang;LD=/usr/bin/ld.lld'):
 x=fixture(flags);v._selectors(x,{'commands':copy.deepcopy(x['commands'])});results.append({'case':'flags_'+('empty' if not flags else 'nonempty'),'outcome':'pass'})
for extra in (['-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL:BOOL=OFF'],['-UKERNEL_DIR'],['-U','KERNEL_DIR'],['-C/tmp/a.cmake'],['-C','/tmp/a.cmake'],['--preset','fake'],['-DUNAME_R:STRING=other'],['-DKERNEL_DIR=/other'],['-G','Ninja']):
 x=fixture('');x['commands'][0]['argv']+=extra
 try:v._selectors(x,{'commands':copy.deepcopy(x['commands'])})
 except ValueError as e:assert 'exact configure argv differs' in str(e),(extra,str(e));results.append({'case':'override_'+repr(extra),'outcome':'rejected','error':str(e)})
 else:raise AssertionError(extra)
for name,value,reason in [('MCKERNEL_M14_EXPECTED_UNAME_R','other','uname mismatch'),('MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS','x','flags mismatch'),('UNAME_R',None,'unbound configure values'),('MCKERNEL_M14_EXPECTED_MAKE_SHA256','x','make hash malformed')]:
 x=fixture('');x['required_actual_values'][name]=value
 try:v._selectors(x,{'commands':copy.deepcopy(x['commands'])})
 except ValueError as e:assert reason in str(e),(name,str(e));results.append({'case':'values_'+name,'outcome':'rejected','error':str(e)})
 else:raise AssertionError(name)
p=A/'m14-root-and-nonheld-composite-1/MOUNT-MANIFEST.json';j=json.loads(p.read_text());mounts=[('/tmp/work','/work',False)]+[(host,target,True) for target,host in j['on_source_mount_proposal'].items()]+[('/tmp/out','/out',True)]
mounts[1:-1]=sorted(mounts[1:-1],key=lambda x:(len(pathlib.PurePosixPath(x[1]).parts),x[1]));ref=v._check_composite_proposal(p,mounts);assert ref['sha256']==v.COMPOSITE_PROPOSAL_SHA;results.append({'case':'composite_binding','outcome':'pass'})
bad=list(mounts);i=next(i for i,x in enumerate(bad) if x[1]=='/src/kernel/process.c');bad[i]=('/tmp/wrong',bad[i][1],True)
try:v._check_composite_proposal(p,bad)
except ValueError as e:assert 'ON source mount proposal mismatch' in str(e);results.append({'case':'composite_mismatch','outcome':'rejected','error':str(e)})
else:raise AssertionError('mismatched composite accepted')
nested=list(mounts);i=next(i for i,x in enumerate(nested) if x[1]=='/src/kernel/rust');nested.insert(i+1,('/tmp/perf',v.PERF_CHILD,True))
try:v._mount_graph(nested)
except ValueError as e:assert 'perf child binding/order' in str(e);results.append({'case':'wrong_child_still_rejected','outcome':'rejected','error':str(e)})
else:raise AssertionError('legacy graph unexpectedly accepts perf child')
driver=ast.parse((A/'m14-configure-quiescence-correction-1/driver.corrected.py').read_text());owner=ast.parse((A/'m14-configure-quiescence-correction-1/owner.corrected.py').read_text())
def function(tree,name):return next(x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name==name)
assert isinstance(function(driver,'require_source_binding').body[0],ast.Raise)
for name in ('main','_sdk13_release_accepted_lease'):assert isinstance(function(owner,name).body[0],ast.Raise)
cls=next(x for x in owner.body if isinstance(x,ast.ClassDef) and x.name=='SDK13ImageOwner');run=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='run');assert isinstance(run.body[0],ast.Raise)
assert any(isinstance(x,ast.Raise) for x in ast.walk(function(owner,'_sdk13_driver_result')))
results.append({'case':'driver_owner_guards_preserved','outcome':'pass'})
(O/'SELECTOR-RESULTS.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS',len(results),'selector/composite checks; overrides rejected even when profile and proposal agree')
