"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Literal-only expiry successor assembly."""
import ast,hashlib,json,difflib
from pathlib import Path
P=Path(__file__).resolve().parent;POST=P.parent;B=POST.parents[1];OLD=B/'source';S=P/'source';S.mkdir()
R=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/final-LONG-execution-preparation-1/bounded-correction-1/final-execution-assembly-1/post-M14-fresh-admission-preparation-1/expired-release-successor-1');R.mkdir();(R/'source').mkdir();RP=R.parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def emit(n,x):
 raw=(json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
 for d in (P,R):(d/n).write_bytes(raw)
def literal(s,name):return next(ast.literal_eval(n.value) for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id==name for a in n.targets))
def replace(s,name,value):
 n=next(n for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id==name for a in n.targets));return s.replace(ast.get_source_segment(s,n),name+' = '+repr(value),1)
def funcs(s):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
final=RP/'final-execution-release-1';history=json.loads((final/'ROOT-FINAL-LONG-EXECUTION-RELEASE.json').read_bytes());oldrel=json.loads((final/'LONG-RELEASE.RELEASED.json').read_bytes());oldreq=json.loads((final/'CAPTURE-REQUEST.RELEASED.json').read_bytes());assert oldrel['expires_unix']==1792766399.1448586 and history['actual_execution'] is None
nonce=oldrel['nonce'];assert nonce=='15e709bb3df642d88a345485ce2371f3';newrelease='/home/holden/mckernel-work/scratch/p12s5l1/r-renewal-1.json'
ctlold=(B/'capture_root_LONG.NOT-RELEASED.py').read_text();ctl=replace(ctlold,'OWNER_PATH',str(S/'native_diagnostic_container_owner.py'));ctl=replace(ctl,'RELEASE_PATH',newrelease)
for d in (P,R):(d/'capture_root_LONG.NOT-RELEASED.py').write_text(ctl)
assert funcs(ctlold)==funcs(ctl)
for f in OLD.iterdir():
 if f.is_file() and f.suffix in ('.py','.json'):(S/f.name).write_bytes(f.read_bytes())
told=(S/'long_transport.py').read_text();external=literal(told,'EXTERNAL_CAPTURE_BINDING');external.update(controller_path=str(P/'capture_root_LONG.NOT-RELEASED.py'),controller_sha256=ref(P/'capture_root_LONG.NOT-RELEASED.py')['sha256'],request_path=str(P/'CAPTURE-REQUEST.json'),capture_directory=str(P/'actual-capture-1'),command_source_path=str(S/'native_diagnostic_container_owner.py'))
tnew=replace(told,'EXTERNAL_CAPTURE_BINDING',external);(S/'long_transport.py').write_text(tnew);assert funcs(told)==funcs(tnew)
aold=(S/'native_diagnostic_container_owner.py').read_text();hashes=literal(aold,'SOURCE_HASHES');roots=literal(aold,'EXTRA_READONLY')
for key in list(hashes):
 if key.startswith(str(OLD)+'/'):
  name=Path(key).name;del hashes[key];hashes[str(S/name)]=ref(S/name)['sha256']
assert len(hashes)==156 and len(roots)==39
anew=replace(aold,'SELF',str(S/'native_diagnostic_container_owner.py'));anew=replace(anew,'RUNNER',str(S/'native_diagnostic_runner.py'));anew=replace(anew,'SOURCE_HASHES',hashes);anew=replace(anew,'EXTRA_READONLY',[str(S) if x==str(OLD) else x for x in roots]);oldline='    source = '+repr(str(OLD/'native_diagnostic.py'));newline='    source = '+repr(str(S/'native_diagnostic.py'));assert anew.count(oldline)==1;anew=anew.replace(oldline,newline,1);(S/'native_diagnostic_container_owner.py').write_text(anew)
af,bf=funcs(aold),funcs(anew);assert [x for x in af if af[x]!=bf[x]]==['bound_manifest'];assert af['bound_manifest'].replace(str(OLD/'native_diagnostic.py'),'BOUND_PATH')==bf['bound_manifest'].replace(str(S/'native_diagnostic.py'),'BOUND_PATH')
for f in S.iterdir():(R/'source'/f.name).write_bytes(f.read_bytes())
cohort={f.name:ref(f) for f in sorted(S.iterdir()) if f.is_file()};emit('COHORT-BINDINGS.json',cohort)
rel=json.loads(json.dumps(oldrel))
for name in ['status','author','boot_id','expires_unix','independent_review']:rel[name]=None
rel['source_sha256']={name:cohort[name]['sha256'] for name in oldrel['source_sha256']}
req=json.loads(json.dumps(oldreq));req.update(status='RENEWAL_PROTOTYPE_NOT_EXECUTABLE_FRESH_RELEASE_DIGEST_NULL',wrapper_sha256=ref(P/'capture_root_LONG.NOT-RELEASED.py')['sha256'],command_source=cohort['native_diagnostic_container_owner.py'],capture_directory=str(P/'actual-capture-1'),long_profile_release=dict(path=newrelease,sha256=None));req['argv'][13]=cohort['native_diagnostic_container_owner.py']['path'];req['argv'][req['argv'].index('--owner-sha256')+1]=cohort['native_diagnostic_container_owner.py']['sha256'];req['argv'][req['argv'].index('--long-profile-release')+1]=newrelease;req['argv'][-1]=None
assert req['argv'][req['argv'].index('--nonce')+1]==nonce and req['argv'][13]==cohort['native_diagnostic_container_owner.py']['path']
argv=history['root_argv'][:];argv[-3]=str(P/'capture_root_LONG.NOT-RELEASED.py');argv[-2]=str(P/'CAPTURE-REQUEST.json');argv[-1]=None
emit('LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json',rel);emit('CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json',req);emit('ROOT-ARGV.PROTOTYPE.NOT-EXECUTABLE.json',argv)
# Fresh observation: preserve old published immutable artifacts as required present pins, check only new namespaces absent.
c=json.loads((POST/'QUERY-INPUTS.json').read_bytes());oldop=c['operation'];c['operation'].update(controller=ref(P/'capture_root_LONG.NOT-RELEASED.py'),runtime_files=cohort,future_request_path=str(P/'CAPTURE-REQUEST.json'),future_release_path=newrelease,capture_directory=str(P/'actual-capture-1'));c['controller']=ref(P/'capture_root_LONG.NOT-RELEASED.py');c['growth']=cohort['long_transport.py'];c['owner_constants']['EXTRA_READONLY']=[str(S) if x==str(OLD) else x for x in c['owner_constants']['EXTRA_READONLY']]
newpins=[]
for row in c['pins']:
 path=Path(row['path'])
 if path.parent==OLD:newpins.append(cohort[path.name])
 elif path==B/'capture_root_LONG.NOT-RELEASED.py':newpins.append(ref(P/'capture_root_LONG.NOT-RELEASED.py'))
 elif path==B/'CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json':newpins.append(ref(P/'CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json'))
 elif path==B/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json':newpins.append(ref(P/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json'))
 else:newpins.append(row)
for key in ['release','request']:
 row=history[key];newpins.append(dict(path=row['path'],sha256=row['sha256'],bytes=row['bytes']))
c['pins']=newpins;c['preserved_expired_release']=history['release'];c['preserved_expired_request']=history['request'];c['status']='EXPIRY_LITERAL_SUCCESSOR_FRESH_QUERY_NOT_RUN';c['expiry_history']=dict(prior_root_release=ref(final/'ROOT-FINAL-LONG-EXECUTION-RELEASE.json'),old_expiry=oldrel['expires_unix'],root_failure_timecheck=1792766425.822,old_execution_count=0,qualification='Roottimecheckrefusedexpiredrelease before anyexecution; immutablepublished inputs remain requiredpresentpins, not absence targets.')
emit('QUERY-INPUTS.json',c)
qold=(POST/'read_only_LONG_HOST_admission.py').read_text();node=next(n for n in ast.parse(qold).body if isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id=='CONFIG_SHA' for a in n.targets));qnew=qold.replace(ast.get_source_segment(qold,node),'CONFIG_SHA='+repr(ref(P/'QUERY-INPUTS.json')['sha256']),1);assert funcs(qold)==funcs(qnew)
for d in (P,R):
 (d/'read_only_LONG_HOST_admission.py').write_text(qnew);(d/'run_root_LONG_admission_capture.py').write_bytes((POST/'run_root_LONG_admission_capture.py').read_bytes())
profile=json.loads((POST/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json').read_bytes());profile['runner']=ref(P/'run_root_LONG_admission_capture.py');profile['query_argv'][-2]=str(P/'read_only_LONG_HOST_admission.py');profile['query_argv'][-1]=ref(P/'read_only_LONG_HOST_admission.py')['sha256'];profile['input_sources']=[ref(P/'read_only_LONG_HOST_admission.py'),ref(P/'QUERY-INPUTS.json')];profile['capture_directory']=str(P/'actual-fresh-root-admission-1');emit('ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json',profile)
qargv=json.loads((POST/'ROOT-FRESH-OBSERVER-ARGV.NOT-RELEASED.json').read_bytes());qargv[-3]=str(P/'run_root_LONG_admission_capture.py');qargv[-2]=str(P/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json');qargv[-1]=ref(P/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json')['sha256'];emit('ROOT-FRESH-OBSERVER-ARGV.NOT-RELEASED.json',qargv)
proof=dict(scope=SCOPE,status='PASS_LITERAL_ONLY_PRIVATE_RENEWAL_SOURCE_SCOPE_NOT_RUNTIME',previous_controller=ref(B/'capture_root_LONG.NOT-RELEASED.py'),controller=ref(P/'capture_root_LONG.NOT-RELEASED.py'),controller_functions_AST_identical=True,controller_changed_literals=['OWNER_PATH','RELEASE_PATH'],previous_owner=ref(OLD/'native_diagnostic_container_owner.py'),owner=cohort['native_diagnostic_container_owner.py'],owner_only_functionAST_difference='bound_manifest local diagnostic sourcepath literal; identical when only thatliteralmasked',owner_changed_module_literals=['SELF','RUNNER','SOURCE_HASHES','EXTRA_READONLY'],source_rows=156,readonly_roots=39,transport_functions_AST_identical=True,transport_only_changed_constant='EXTERNAL_CAPTURE_BINDING',query_functions_AST_identical=True,query_only_changed_literal='CONFIG_SHA',observer_byte_identical_SHA256=ref(P/'run_root_LONG_admission_capture.py')['sha256'],manifest_SDK_image_launcher_apps_quotas_deadlines_unchanged=True,original600second_expiry_guard_unchanged=True,expiry_minted=False,expired_artifacts_preserved=True,original_unusednonce=nonce)
emit('LITERAL-RENEWAL-SOURCE-PROOF.json',proof)
for name,old,new in [('controller',ctlold,ctl),('owner',aold,anew),('transport',told,tnew)]:
 diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='accepted/'+name,tofile='renewal/'+name))
 for d in (P,R):(d/(name+'.literal.diff')).write_text(diff)
operation=dict(scope=SCOPE,status='LITERAL_RENEWAL_READY_FOR_CONSUMER_AND_FOCUSED_REVIEW_NOT_RELEASED',history=ref(final/'ROOT-FINAL-LONG-EXECUTION-RELEASE.json'),newrelease_path=newrelease,newrequest_path=str(P/'CAPTURE-REQUEST.json'),newcapture_path=str(P/'actual-capture-1'),nonce=nonce,nonce_reuse_qualification='Previously neverexecuted; onlyfuturefreshqueryunusedidentity/namespace confirmation allows singlefirstworkload; oldexpiredinputsneverreplayed',sourceproof=ref(R/'LITERAL-RENEWAL-SOURCE-PROOF.json'),controller=ref(P/'capture_root_LONG.NOT-RELEASED.py'),cohort=ref(R/'COHORT-BINDINGS.json'),release_draft=ref(R/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json'),request_draft=ref(R/'CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json'),rootargv_draft=ref(R/'ROOT-ARGV.PROTOTYPE.NOT-EXECUTABLE.json'),freshquery=dict(source=ref(P/'read_only_LONG_HOST_admission.py'),inputs=ref(P/'QUERY-INPUTS.json'),observer=ref(P/'run_root_LONG_admission_capture.py'),profile=ref(P/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json'),argv=ref(P/'ROOT-FRESH-OBSERVER-ARGV.NOT-RELEASED.json'),old_inputs='PRESENT exact pinnedsha/bytes; preserved immutable',new_inputs='ABSENT newrelease/newrequest/newcapture/unusedHOSTattempt+owner',actual=None,independent_release=None),expiry_order='Staticpublication+actualconsumer/focusedreview+freshadmission first; onlythen rootauthors exactcurrentboot/now+<=600expiry, independentcanonicalpayloadreview, publishesfreshreleaseSHA→freshrequestSHA→finalrootargv and executes immediately withoutcompaction/checkpoint consuming600swindow.',actual_consumer=None,independent_source_review=None,source_publication=None,root_final_release=None,actual_LONG=None)
emit('EXACT-IMMUTABLE-EXPIRY-RENEWAL.NOT-RELEASED.json',operation)
print(json.dumps({'operation':ref(R/'EXACT-IMMUTABLE-EXPIRY-RENEWAL.NOT-RELEASED.json'),'proof':ref(R/'LITERAL-RENEWAL-SOURCE-PROOF.json'),'controller':operation['controller'],'owner':cohort['native_diagnostic_container_owner.py'],'transport':cohort['long_transport.py'],'query':operation['freshquery']['source'],'profile':operation['freshquery']['profile'],'argv':operation['freshquery']['argv']},indent=2))
