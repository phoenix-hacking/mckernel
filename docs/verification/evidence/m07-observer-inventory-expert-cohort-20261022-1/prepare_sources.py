"""Expert-directed source generation only. No helper/test execution or release.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import ast,difflib,hashlib,json
D=Path(__file__).parent
H=D.parent
PREVIOUS=H/'m07-observer-full-inventory-schema-correction-20261022-1'
ORIGINAL=H/'m07-sigill-successor-native-data-preparation-20261022-1/actual-terminal-preparation-1'
GEN=ORIGINAL/'prepare_existing_current_terminal_sources.FRESH-CORRECTION-1.py'
def sha(b):return hashlib.sha256(b).hexdigest()
def create(p,raw):
 if isinstance(raw,str):raw=raw.encode()
 with p.open('xb') as stream:stream.write(raw)
 p.chmod(0o600)
def js(p,value):create(p,json.dumps(value,indent=2,sort_keys=True)+'\n')
def ref(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
def once(text,old,new):
 assert text.count(old)==1,old[:120]
 return text.replace(old,new)
def function(text,name):
 node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name)
 return ''.join(text.splitlines(True)[node.lineno-1:node.end_lineno])+'\n'
case=json.loads((PREVIOUS/'PASS-CASE-STATIC.json').read_bytes())
assert case['finite_unique_path_count']==len(case['finite_unique_paths'])==88 and case['finite_role_count']==len(case['finite_roles'])==97
assert case['current_live_postjoin']==case['finite_roles']['guard_postjoin'] and case['current_live_postjoin']['sha256']=='2f092dd706e7b1f6bb740164eda938a66ed7dcc7a92cee38a304bf878ccff357'
assert all(case[k] is None for k in ('postjoin_result','cleanup_release','cleanup_result','observation','observation_release'))
js(D/'PASS-CASE-STATIC.json',case)
b=json.loads((ORIGINAL/'TERMINAL-GENERATOR.CONTAINER-LOG-LOCATOR-CORRECTION-1.json').read_bytes());b['terminal']['case']=ref(D/'PASS-CASE-STATIC.json');b['terminal']['observation_nonce']='m07-sigill-pass-image-observation-expert-inventory-cohort-1';js(D/'TERMINAL-GENERATOR.EXPERT-BOUND.json',b)
schema=(PREVIOUS/'finite_case_decoder.SOURCE.py').read_text()
observer=(PREVIOUS/'observe_current_pass_image_retirement.py').read_text()
post=(PREVIOUS/'postjoin_readback.py').read_text()
consumer=function(post,'finite_metadata_consumer')
text=GEN.read_text()
text=once(text,"outdir('bound-terminal-source-correction-1')","outdir('bound-terminal-expert-source-1')")
text=once(text,'def terminal(b):',schema+'def terminal(b):')
text=once(text,"    need(case['artifact_acceptance']==t['artifact_acceptance']", "    decode_finite_case(case)\n    need(type(case.get('current_live_postjoin')) is dict and case['current_live_postjoin']==case['finite_roles']['guard_postjoin'], 'exact genuine predecessor guard postjoin reference required; future cleanup is separate')\n    need(case['artifact_acceptance']==t['artifact_acceptance']")
old="    observer=texts.pop('observe_current_pass_image_retirement.py').replace(str(C),str(p))"
new=old+"\n    observer=once(observer,'def main(argv=None):',"+repr(schema)+"+'def main(argv=None):')\n    observer=once(observer,'case=m.parse(stable_bytes(FAILURE_CASE,FAILURE_CASE_SHA,4<<20))','case=m.parse(stable_bytes(FAILURE_CASE,FAILURE_CASE_SHA,4<<20))\\n    finite_paths=decode_finite_case(case)')\n    observer=observer.replace(\"case['finite_unique_paths']\",'finite_paths')\n    observer=once(observer,\"    root_join=json.loads(stable_bytes(Path(case['current_live_postjoin']['path']),case['current_live_postjoin']['sha256']))\",\"    postjoin_ref=case.get('current_live_postjoin')\\n    need(isinstance(postjoin_ref,dict) and postjoin_ref==case['finite_roles']['guard_postjoin'],\\n         'exact genuine predecessor guard postjoin reference required; future cleanup is separate')\\n    root_join=json.loads(stable_bytes(Path(postjoin_ref['path']),postjoin_ref['sha256']))\")"
text=once(text,old,new)
old="        if name=='postjoin_readback.py': text=global_value(global_value(text,'OBSERVER_SHA',repr(observer_ref['sha256'])),'ENGINE_SHA',repr(engine_ref['sha256']))"
new="""        if name=='postjoin_readback.py':
            text=global_value(global_value(text,'OBSERVER_SHA',repr(observer_ref['sha256'])),'ENGINE_SHA',repr(engine_ref['sha256']))
            start=text.index("        selected={x['path']:x for x in obs['selected_files']};side=")
            end=text.index('        request=m.parse',start)
            text=text[:start]+'        actual,objects=finite_metadata_consumer(m,o,obs)\\n'+text[end:]
            text=once(text,'def main():',"""+repr(consumer)+"+'\\ndef main():')"
text=once(text,old,new)
compile(text,str(D/GEN.name),'exec');create(D/GEN.name,text)
create(D/(GEN.name+'.diff'),''.join(difflib.unified_diff(GEN.read_text().splitlines(True),text.splitlines(True),fromfile=str(GEN),tofile=str(D/GEN.name))))
# Test starts from the previous exact candidate. Only the four approved repairs.
t=(PREVIOUS/'test_full_main.py').read_text()
t=t.replace('import ast,contextlib,copy,fcntl,hashlib,importlib.util,io,json,os,stat,subprocess,tempfile,types','import ast,contextlib,copy,fcntl,hashlib,importlib.util,io,json,os,stat,subprocess,types')
t=t.replace('ENGINE=Path('+repr(str(ORIGINAL/'bound-terminal-source-correction-1/cleanup_pass_image.py'))+')',"G=D/'bound-terminal-expert-source-1'\nENGINE=G/'cleanup_pass_image.py'\nPRODUCTION_CASE_SHA=__CASE_SHA__\nEXPECTED_PATH_COUNT=__PATH_COUNT__\nEXPECTED_ROLE_COUNT=__ROLE_COUNT__")
# Retention context records every stage even when an unexpected exception aborts.
t=t.replace('def test(label,negative=None):\n with tempfile.TemporaryDirectory(dir=D,prefix=\'fixture-\'+label+\'-\') as tmp:', '''class RetainedAttempt:
 def __init__(self,label):self.label=label;self.path=D/('retained-fixture-'+label+'-1');self.stage='new'
 def record(self,stage,**values):
  self.stage=stage;path=self.path/('stage-%02d.json'%len(list(self.path.glob('stage-*.json'))))
  with path.open('x') as out:json.dump(dict(label=self.label,stage=stage,location=str(self.path),**values),out,sort_keys=True);out.write('\\n');out.flush();os.fsync(out.fileno())
 def __enter__(self):self.path.mkdir(mode=0o700);self.record('attempt-created');return self
 def __exit__(self,kind,error,tb):
  if error is not None:self.record('UNEXPECTED_FAILURE',previous_stage=self.stage,error_type=kind.__name__,error=str(error))
  return False

def test(label,negative=None):
 with RetainedAttempt(label) as attempt:
  tmp=str(attempt.path)''')
t=t.replace("original=json.loads((D/'PASS-CASE-STATIC.json').read_bytes());case=copy.deepcopy(original)","raw=(G/'PASS-CASE-STATIC.json').read_bytes();assert sha(raw)==PRODUCTION_CASE_SHA;original=json.loads(raw);assert original['finite_unique_path_count']==EXPECTED_PATH_COUNT and original['finite_role_count']==EXPECTED_ROLE_COUNT;case=copy.deepcopy(original)")
t=t.replace("case['finite_unique_path_count']=88", "case['finite_unique_path_count']=EXPECTED_PATH_COUNT")
t=t.replace("o=load(D/'observe_current_pass_image_retirement.py'", "o=load(G/'observe_current_pass_image_retirement.py'")
t=t.replace("summary=load(D/'readback_observer.py'", "summary=load(G/'readback_observer.py'")
t=t.replace("post=load(D/'postjoin_readback.py'", "post=load(G/'postjoin_readback.py'")
t=t.replace('real_stat=os.stat;real_fstat=os.fstat;real_read=Path.read_text','real_stat=os.stat;real_fstat=os.fstat;real_lstat=os.lstat;real_read=Path.read_text')
# SAME lexical model, mutex uid/gid untouched: only device/inode synthetic there.
t=once(t,"   if p==lock or p==observer_output or observer_output in p.parents:\n    fields={k:getattr(meta,k) for k in dir(meta) if k.startswith('st_')};fields.update(st_uid=0,st_gid=0)\n    if p==lock:fields.update(st_dev=27,st_ino=4)\n    return types.SimpleNamespace(**fields)","   if p==lock or p==observer_output or observer_output in p.parents:\n    fields={k:getattr(meta,k) for k in dir(meta) if k.startswith('st_')}\n    if p==lock:fields.update(st_dev=27,st_ino=4)\n    else:fields.update(st_uid=0,st_gid=0)\n    return types.SimpleNamespace(**fields)")
# Production observer requires root-owned mutex. Its fixture is an ordinary user file:
# expert requires only device/inode synthetic mutex, so exact mutex uid boundary must
# be represented without weakening observer: use the existing root-owned harmless
# regular fixture? No root read; derive metadata requirement explicitly below.
# This comment in preparation flags that conflict for independent review.
t=once(t,"  def read_text(p,*a,**kw):", "  def lstat_call(p,*a,dir_fd=None,**kw):\n   path=Path(p)\n   if not path.is_absolute():path=(Path(os.readlink('/proc/self/fd/'+str(dir_fd))) if dir_fd is not None else Path.cwd())/path\n   return model(real_lstat(p,*a,dir_fd=dir_fd,**kw),path)\n  def read_text(p,*a,**kw):")
t=t.replace("patch.object(os,'stat',stat_call),", "patch.object(os,'stat',stat_call),patch.object(os,'lstat',lstat_call),")
t=t.replace('   try:\n    with contextlib.redirect_stdout(io.StringIO()):o.main', "   attempt.record('before-generated-observer-main',generated_observer=str(G/'observe_current_pass_image_retirement.py'))\n   try:\n    with contextlib.redirect_stdout(io.StringIO()):o.main")
t=t.replace("    expected=('finite-case:' if label not in ('descriptor-drift','incomplete-client-ledger','final-inventory-drift') else {'descriptor-drift':'closed PASS role bytes differ','incomplete-client-ledger':'all exact current original clients required','final-inventory-drift':'preserved output metadata changed'}[label])", "    expected=(('exact sorted distinct role path union required' if label in ('missing-path','extra-path','duplicate-path') else 'finite-case:') if label not in ('descriptor-drift','incomplete-client-ledger','final-inventory-drift') else {'descriptor-drift':'closed PASS role bytes differ','incomplete-client-ledger':'all exact current original clients required','final-inventory-drift':'preserved output metadata changed'}[label])")
t=t.replace("    return dict(label=label,status='REFUSED'", "    attempt.record('EXPECTED_REFUSAL',reason=str(exc),output_directory_created=observer_output.exists(),success_outputs_absent=True,lock_reacquired=True)\n    return dict(location=str(attempt.path),label=label,status='REFUSED'")
t=t.replace("   assert negative is None,('negative accepted',label)", "   attempt.record('generated-observer-main-returned',output=str(observer_output))\n   assert negative is None,('negative accepted',label)")
t=t.replace("assert len(actual)==88 and objects()==actual", "assert len(actual)==EXPECTED_PATH_COUNT and objects()==actual\n   attempt.record('generated-postjoin-consumer-returned',generated_postjoin=str(G/'postjoin_readback.py'),finite_objects=len(actual),summary_validated=True)")
t=t.replace("scalar['finite_unique_paths']=88", "scalar['finite_unique_paths']=EXPECTED_PATH_COUNT")
t=t.replace("   return dict(label=label,status='PASS_FULL_ACTUAL_MAIN_RETURN_AND_POSTJOIN_FINITE_CONSUMER',finite_objects=len(actual),finite_roles=97", "   attempt.record('PASS_COMPLETE_FIXTURE',finite_objects=len(actual),finite_roles=EXPECTED_ROLE_COUNT,lock_reacquired=True)\n   return dict(location=str(attempt.path),label=label,status='PASS_FULL_ACTUAL_MAIN_RETURN_AND_POSTJOIN_FINITE_CONSUMER',finite_objects=len(actual),finite_roles=EXPECTED_ROLE_COUNT")
t=t.replace('def main():\n results=', "def mutate_path_union(case,kind):\n if kind=='missing':case['finite_unique_paths'].pop()\n elif kind=='extra':case['finite_unique_paths'].append('/extra')\n else:case['finite_unique_paths'].append(case['finite_unique_paths'][0])\n case['finite_unique_path_count']=len(case['finite_unique_paths'])\n\ndef main():\n results=")
t=t.replace("c.update(finite_unique_paths=88)","c.update(finite_unique_paths=EXPECTED_PATH_COUNT)")
t=t.replace("lambda c,p,m:c['finite_unique_paths'].pop()", "lambda c,p,m:mutate_path_union(c,'missing')").replace("lambda c,p,m:c['finite_unique_paths'].append('/extra')", "lambda c,p,m:mutate_path_union(c,'extra')").replace("lambda c,p,m:c['finite_unique_paths'].append(c['finite_unique_paths'][0])", "lambda c,p,m:mutate_path_union(c,'duplicate')")
t=t.replace('c.update(finite_unique_path_count=87)','c.update(finite_unique_path_count=EXPECTED_PATH_COUNT-1)')
create(D/'test_generated_full_main.TEMPLATE.py',t)
js(D/'PREPARATION-INPUT-REFS.json',dict(status='SOURCE_ONLY_NO_TEST',previous_refs={name:ref(PREVIOUS/name) for name in ('PASS-CASE-STATIC.json','finite_case_decoder.SOURCE.py','observe_current_pass_image_retirement.py','postjoin_readback.py','test_full_main.py')},original_generator=ref(GEN),bindings=ref(D/'TERMINAL-GENERATOR.EXPERT-BOUND.json')))
