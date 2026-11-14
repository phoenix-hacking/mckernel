"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Immutable literal successor only."""
import ast,hashlib,json,uuid,difflib
from pathlib import Path
D=Path(__file__).resolve().parent;OLD=D.parent;S=D/'source';S.mkdir();R=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/final-LONG-execution-preparation-1/bounded-correction-1/final-execution-assembly-1/post-M14-fresh-admission-preparation-1/expired-release-successor-1/serialized-release-successor-2');R.mkdir();(R/'source').mkdir()
SCOPE=__doc__;nonce=uuid.uuid4().hex;newrelease='/home/holden/mckernel-work/scratch/p12s5l1/r-renewal-2.json'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def emit(n,v):
 raw=(json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
 for p in (D,R):(p/n).write_bytes(raw)
def lit(s,name):return next(ast.literal_eval(n.value) for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
def replace(s,name,value):
 n=next(n for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets));return s.replace(ast.get_source_segment(s,n),name+' = '+repr(value),1)
def funcs(s):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
ctlold=(OLD/'capture_root_LONG.NOT-RELEASED.py').read_text();ctl=replace(replace(replace(ctlold,'OWNER_PATH',str(S/'native_diagnostic_container_owner.py')),'RELEASE_PATH',newrelease),'NONCE',nonce)
for p in (D,R):(p/'capture_root_LONG.NOT-RELEASED.py').write_text(ctl)
assert funcs(ctlold)==funcs(ctl)
for f in (OLD/'source').iterdir():
 if f.is_file() and f.suffix in ('.py','.json'):(S/f.name).write_bytes(f.read_bytes())
told=(S/'long_transport.py').read_text();binding=lit(told,'EXTERNAL_CAPTURE_BINDING');binding.update(controller_path=str(D/'capture_root_LONG.NOT-RELEASED.py'),controller_sha256=ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'],request_path=str(D/'CAPTURE-REQUEST.json'),capture_directory=str(D/'actual-capture-1'),command_source_path=str(S/'native_diagnostic_container_owner.py'));tnew=replace(told,'EXTERNAL_CAPTURE_BINDING',binding);(S/'long_transport.py').write_text(tnew);assert funcs(told)==funcs(tnew)
aold=(S/'native_diagnostic_container_owner.py').read_text();hashes=lit(aold,'SOURCE_HASHES');roots=lit(aold,'EXTRA_READONLY')
for key in list(hashes):
 if key.startswith(str(OLD/'source')+'/'):
  name=Path(key).name;del hashes[key];hashes[str(S/name)]=ref(S/name)['sha256']
anew=replace(replace(replace(replace(aold,'SELF',str(S/'native_diagnostic_container_owner.py')),'RUNNER',str(S/'native_diagnostic_runner.py')),'SOURCE_HASHES',hashes),'EXTRA_READONLY',[str(S) if x==str(OLD/'source') else x for x in roots]);anew=anew.replace('    source = '+repr(str(OLD/'source/native_diagnostic.py')),'    source = '+repr(str(S/'native_diagnostic.py')),1);(S/'native_diagnostic_container_owner.py').write_text(anew)
af,bf=funcs(aold),funcs(anew);assert [k for k in af if af[k]!=bf[k]]==['bound_manifest'];assert af['bound_manifest'].replace(str(OLD/'source/native_diagnostic.py'),'PATH')==bf['bound_manifest'].replace(str(S/'native_diagnostic.py'),'PATH');assert len(hashes)==156 and len(roots)==39
for f in S.iterdir():(R/'source'/f.name).write_bytes(f.read_bytes())
cohort={f.name:ref(f) for f in sorted(S.iterdir()) if f.is_file()};emit('COHORT-BINDINGS.json',cohort)
rel=json.loads((OLD/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());rel['nonce']=nonce;rel['source_sha256']={k:cohort[k]['sha256'] for k in rel['source_sha256']};emit('LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json',rel)
req=json.loads((OLD/'CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());req.update(wrapper_sha256=ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'],command_source=cohort['native_diagnostic_container_owner.py'],capture_directory=str(D/'actual-capture-1'),long_profile_release=dict(path=newrelease,sha256=None));req['argv'][13]=cohort['native_diagnostic_container_owner.py']['path']
for flag,val in [('--owner-sha256',cohort['native_diagnostic_container_owner.py']['sha256']),('--nonce',nonce),('--long-profile-release',newrelease)]:req['argv'][req['argv'].index(flag)+1]=val
req['argv'][-1]=None;emit('CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json',req)
argv=json.loads((OLD/'ROOT-ARGV.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());argv[-3]=str(D/'capture_root_LONG.NOT-RELEASED.py');argv[-2]=str(D/'CAPTURE-REQUEST.json');emit('ROOT-ARGV.PROTOTYPE.NOT-EXECUTABLE.json',argv)
c=json.loads((OLD/'QUERY-INPUTS.json').read_bytes());c['operation'].update(controller=ref(D/'capture_root_LONG.NOT-RELEASED.py'),runtime_files=cohort,future_request_path=str(D/'CAPTURE-REQUEST.json'),future_release_path=newrelease,capture_directory=str(D/'actual-capture-1'),nonce=nonce);c['controller']=ref(D/'capture_root_LONG.NOT-RELEASED.py');c['growth']=cohort['long_transport.py'];c['owner_constants']['EXTRA_READONLY']=[str(S) if x==str(OLD/'source') else x for x in c['owner_constants']['EXTRA_READONLY']]
pins=[]
for row in c['pins']:
 p=Path(row['path'])
 if p.parent==OLD/'source':pins.append(cohort[p.name])
 elif p==OLD/'capture_root_LONG.NOT-RELEASED.py':pins.append(ref(D/p.name))
 elif p==OLD/'CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json':pins.append(ref(D/p.name))
 elif p==OLD/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json':pins.append(ref(D/p.name))
 else:pins.append(row)
pins.extend([ref(Path('/home/holden/mckernel-work/scratch/p12s5l1/r-renewal-1.json')),ref(OLD/'CAPTURE-REQUEST.json')]);c['pins']=pins;c['prior_failed_nonce']='15e709bb3df642d88a345485ce2371f3';c['prior_failed_owner_paths']=['/home/holden/mckernel-work/native-runs/l12a1/p.owner-15e709bb3df642d88a345485ce2371f3','/home/holden/mckernel-work/native-runs/l12a1/p/attempt-15e709bb3df642d88a345485ce2371f3'];c['status']='SERIALIZED_CANONICAL_RENEWAL2_FRESH_QUERY_NOT_RUN';emit('QUERY-INPUTS.json',c)
qold=(OLD/'read_only_LONG_HOST_admission.py').read_text();q=replace(qold,'CONFIG_SHA',ref(D/'QUERY-INPUTS.json')['sha256'])
q=q.replace(" # Exact lease/exclusion list inherited unchanged from accepted M05 query."," outputs.update({p:os.path.lexists(p) for p in c['prior_failed_owner_paths']})\n # Exact lease/exclusion list inherited unchanged from accepted M05 query.")
q=q.replace("for filt in ['name=^/mckernel-native-diagnostic-'+c['operation']['nonce']+'$','label=mckernel.native-diagnostic.owner='+c['operation']['nonce']]:","for filt in [kind+nonce+suffix for nonce in (c['operation']['nonce'],c['prior_failed_nonce']) for kind,suffix in [('name=^/mckernel-native-diagnostic-','$'),('label=mckernel.native-diagnostic.owner=','')]]:")
for p in (D,R):(p/'read_only_LONG_HOST_admission.py').write_text(q);(p/'run_root_LONG_admission_capture.py').write_bytes((OLD/'run_root_LONG_admission_capture.py').read_bytes())
profile=json.loads((OLD/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json').read_bytes());profile['runner']=ref(D/'run_root_LONG_admission_capture.py');profile['input_sources']=[ref(D/'read_only_LONG_HOST_admission.py'),ref(D/'QUERY-INPUTS.json')];profile['query_argv'][-2]=str(D/'read_only_LONG_HOST_admission.py');profile['query_argv'][-1]=ref(D/'read_only_LONG_HOST_admission.py')['sha256'];profile['capture_directory']=str(D/'actual-fresh-root-admission-1');emit('ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json',profile)
qa=json.loads((OLD/'ROOT-FRESH-OBSERVER-ARGV.NOT-RELEASED.json').read_bytes());qa[-3]=str(D/'run_root_LONG_admission_capture.py');qa[-2]=str(D/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json');qa[-1]=ref(D/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json')['sha256'];emit('ROOT-FRESH-OBSERVER-ARGV.NOT-RELEASED.json',qa)
for name,old,new in [('controller',ctlold,ctl),('transport',told,tnew),('owner',aold,anew),('query',qold,q)]:
 diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='failed-renewal1/'+name,tofile='renewal2/'+name))
 for p in (D,R):(p/(name+'.literal.diff')).write_text(diff)
emit('LITERAL-SUCCESSOR-PROOF.json',dict(scope=SCOPE,controller_functions_AST_identical=True,controller_changed_constants=['OWNER_PATH','RELEASE_PATH','NONCE'],transport_functions_AST_identical=True,transport_changed_constant='EXTERNAL_CAPTURE_BINDING',owner_only_function_AST_delta='bound_manifest sourcepath literal (masked equality asserted)',source_hash_rows=156,readonly_roots=39,query_delta='CONFIG_SHA plus include priorfailed owner/attempt absence and bothnonce Docker identities; existing guards unchanged',nonce=nonce,release_path=newrelease,canonical_function_unchanged=True,validate_release_unchanged=True,expiry_minted=False,actual_query=None,root_release=None,actual_session=None))
print(json.dumps(dict(directory=str(D),nonce=nonce,controller=ref(D/'capture_root_LONG.NOT-RELEASED.py'),owner=cohort['native_diagnostic_container_owner.py'],transport=cohort['long_transport.py'],query=ref(D/'read_only_LONG_HOST_admission.py'),profile=ref(D/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json')),indent=2))
