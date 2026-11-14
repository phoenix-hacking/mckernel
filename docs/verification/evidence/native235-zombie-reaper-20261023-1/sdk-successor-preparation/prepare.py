"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Host-only source preparation; no compiler, container, root, scratch mutation or release.
"""
from pathlib import Path
import json,hashlib,uuid,copy,ast,difflib
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-sdk-successor-20261023-1')
H.mkdir(exist_ok=False);(H/'source-modules').mkdir();(H/'prepared-inputs').mkdir();(H/'derived-runtime').mkdir()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def ref(p):p=Path(p);return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
P=R/'docs/verification/evidence/current68-native235-v3-host-control-sdk-preparation-20261022-1.json'
old=json.loads(P.read_text());assert sha(P)=='c10aa8e755d4900cc607b77951ac2ff2657224a6ee7a183c86bf099716097a44'
p=copy.deepcopy(old);frozen=R/'docs/verification/evidence/native235-zombie-reaper-20261023-1/candidate-mcctrl_process.rs';assert sha(frozen)=='fcddb2679847c70e8d663cdf990f54be3a7645560c0dac2910018cda82ae5d2f'
rows=[];deltas=[]
for row in p['closure']:
 original=Path(row['origin']);assert sha(original)==row['sha256']
 selected=frozen if row['path']=='mcctrl_process.rs' else original
 target=H/'source-modules'/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(selected.read_bytes());target.chmod(0o600)
 previous=row['sha256'];row['origin']=str(target);row['sha256']=sha(target);row['bytes']=target.stat().st_size
 assert target.stat().st_nlink==1
 if previous!=row['sha256']:deltas.append({'relative':row['path'],'old':previous,'new':row['sha256'],'bytes':row['bytes']})
 rows.append({'relative':row['path'],'source':ref(target)})
assert [d['relative'] for d in deltas]==['mcctrl_process.rs']
identity_rows=sorted([[r['path'],r['sha256'],r['bytes']] for r in p['closure']]);identity=hashlib.sha256(json.dumps(identity_rows,separators=(',',':')).encode()).hexdigest()
assert hashlib.sha256(json.dumps(json.loads(Path(old['current_closure_ref']['path']).read_text())['source_identity_rows'],separators=(',',':')).encode()).hexdigest()==old['source_identity']
mp={'status':'PREPARED_EXACT68_ZOMBIE_REAPER_SUCCESSOR_NOT_RELEASED','source_identity':identity,'source_identity_encoding':'SHA256 compact JSON sorted [relative,sha256,bytes] triples; retained accepted encoding','source_identity_rows':identity_rows,'rows':rows,'source_files':68,'source_bytes':sum(r['bytes'] for r in p['closure']),'logical_changed_sources':['mcctrl_process.rs'],'changed_relative_rows':['mcctrl_process.rs'],'predecessor_preparation':ref(P),'predecessor_recorded_identity':old['source_identity'],'source_acceptance':None,'execution_release':None}
mapfile=H/'CURRENT68-ZOMBIE-INPUT-MAP.json';dump(mapfile,mp)
p['source_identity']=identity;p['source_candidate_sha']=identity;p['current_closure_ref']=ref(mapfile);p['closure_bytes']=mp['source_bytes']
for row in p['references'].values():
 prior=Path(row['retained_copy']);source=Path('/home/holden/mckernel-work/scratch/native-running-modules-inputs-bc3cf0ecfe164d6bbcad77dd3bae8e16')/prior.name
 assert sha(source)==row['sha256']
 target=H/'prepared-inputs'/prior.name;target.write_bytes(source.read_bytes());target.chmod(0o600);row['retained_copy']=str(target)
preparation=H/'preparation.json';dump(preparation,p);(H/'prepared-inputs'/'preparation.json').write_bytes(preparation.read_bytes())
oldid=old['source_identity'];oldsha=sha(P);newsha=sha(preparation);newmap={r['path']:[r['sha256'],r['bytes']] for r in p['closure']};newrepl={r['path']:r['sha256'] for r in p['closure'] if r['reviewed_replacement']}
patches=[]
for name in ['native_running_external_modules_offline.py','native_running_external_modules_owner.py']:
 source=R/'scripts'/name;s=source.read_text();assert (name!='native_running_external_modules_offline.py' or sha(source)=='2f34764cc2740eb950013654e0eb5ae27978631a3038e9dccdce0a942979b76c')
 t=s.replace(oldid,identity).replace(oldsha,newsha).replace(str(old['closure_bytes']),str(p['closure_bytes']))
 lines=t.splitlines()
 for i,line in enumerate(lines):
  if line.startswith('EXACT_SOURCE_MAP = '):lines[i]='EXACT_SOURCE_MAP = '+repr(newmap)
  if line.startswith('REPLACEMENTS = '):lines[i]='REPLACEMENTS = '+repr(newrepl)
 t='\n'.join(lines)+'\n'
 if name.endswith('_owner.py'):
  t=t.replace("REPO = Path(__file__).resolve().parents[1]", "REPO = Path('/home/holden/mckernel')")
  t=t.replace("PREPARATION = REPO / 'docs/verification/evidence/current68-native235-v3-host-control-sdk-preparation-20261022-1.json'",'PREPARATION = Path('+repr(str(preparation))+')')
  t=t.replace("DRIVER = REPO / 'scripts/native_running_external_modules_offline.py'",'DRIVER = Path('+repr(str(H/'derived-runtime/native_running_external_modules_offline.py'))+')')
  marker="\n\nclass Refusal(RuntimeError):"
  overrides={ 'scripts/native_running_external_modules_owner.py':str(H/'derived-runtime/native_running_external_modules_owner.py'),'scripts/native_running_external_modules_offline.py':str(H/'derived-runtime/native_running_external_modules_offline.py') }
  t=t.replace(marker,'\n\n# Exact successor paths; canonical support source keys and all digest checks remain.\nRUNTIME_SOURCE_PATHS = '+repr(overrides)+marker)
  t=t.replace("installed_owner = safe_path(str(REPO / 'scripts/native_running_external_modules_owner.py'), False)","installed_owner = safe_path(RUNTIME_SOURCE_PATHS['scripts/native_running_external_modules_owner.py'], False)")
  t=t.replace("path = safe_path(str(REPO / name), False)\n        observed[name]", "path = safe_path(RUNTIME_SOURCE_PATHS.get(name, str(REPO / name)), False)\n        observed[name]")
 ast.parse(t);target=H/'derived-runtime'/name;target.write_text(t);target.chmod(0o600)
 patches.append(''.join(difflib.unified_diff(s.splitlines(True),t.splitlines(True),fromfile=str(source),tofile=str(target))))
(E/'DERIVED-RUNTIME.patch').write_text('\n'.join(patches))
# Request is a fresh unexecuted template. Root alone materializes execution roots,
# gathers fresh identities/capacity/lease data, reviews and creates the actual release.
request=json.loads((R/'docs/verification/evidence/current68-native235-sdk-v3-actual-build-20261023-1/retained/actual-materialization/request.json').read_text());nonce=uuid.uuid4().hex
request.update(nonce=nonce,request_path=str(H/'request.json'),preparation={'path':str(preparation),'sha256':newsha},driver={'path':str(H/'derived-runtime/native_running_external_modules_offline.py'),'sha256':sha(H/'derived-runtime/native_running_external_modules_offline.py')},candidate_root='/home/holden/mckernel-work/host-preparation/native-running-modules-host-output/native-running-modules-candidate-'+nonce,input_root='/home/holden/mckernel-work/scratch/native-running-modules-inputs-'+nonce,owner_evidence_root='/home/holden/mckernel-work/host-preparation/native-running-modules-host-output/native-running-modules-owner-'+nonce)
for k in ['candidate_identity','input_identity','backing_identity','basis_identity','output_parent_identity']:request[k]=None
dump(H/'REQUEST.TEMPLATE.PENDING-LIVE-IDENTITIES.json',request)
cohort={name:sha(H/'derived-runtime'/Path(name).name if name in ['scripts/native_running_external_modules_owner.py','scripts/native_running_external_modules_offline.py'] else R/name) for name in ast.literal_eval(next(line.split(' = ',1)[1] for line in (R/'scripts/native_running_external_modules_owner.py').read_text().splitlines() if line.startswith('SOURCES = '))+'\n') } if False else {}
# Extract tuple through AST without importing an execution-capable owner.
tree=ast.parse((R/'scripts/native_running_external_modules_owner.py').read_text());names=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='SOURCES'for x in n.targets))
for name in names:
 selected=H/'derived-runtime'/Path(name).name if name in ['scripts/native_running_external_modules_owner.py','scripts/native_running_external_modules_offline.py'] else R/name
 cohort[name]=ref(selected)
dump(H/'RUNTIME-COHORT.json',cohort)
summary={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'HOST_SOURCE_AND_DERIVED_RUNTIME_PREPARED_NO_BUILD_NO_RELEASE','host_root':str(H),'source_identity':identity,'predecessor_identity':oldid,'source_files':68,'source_bytes':p['closure_bytes'],'deltas':deltas,'nonce_reserved_not_executed':nonce,'preparation':ref(preparation),'derived_driver':ref(H/'derived-runtime/native_running_external_modules_offline.py'),'derived_owner':ref(H/'derived-runtime/native_running_external_modules_owner.py'),'runtime_cohort':ref(H/'RUNTIME-COHORT.json'),'request_template':ref(H/'REQUEST.TEMPLATE.PENDING-LIVE-IDENTITIES.json'),'external_command':p['proposed_external_command'],'compiler_runs':0,'root_operations':0,'Docker_operations':0,'scratch_writes':0,'required_next':['source acceptance and exact derived runtime review','root materializes tiny prepared input set at fresh accepted scratch input namespace and candidate source set at fresh accepted HOST output namespace','fresh live identities/headroom/leases/historical observer and positive physical clearance','independent exact one-shot execution release for matching cohort/request','actual full module build/link/provider artifact checks/physical retirement'],'profile_unchanged':{'container_CPUs':'2-5','container_memory_bytes':12*1024**3,'container_swap':0,'container_tasks':512,'network':'none','make_jobs':2,'read_only':['/out','/inputs','/driver.py'],'writable':['/candidate']},'reused_read_only_basis':old['baseline_candidate'],'reused_tool_image':old['tool_image'],'unchanged_MM_C_providers':[r for r in p['closure'] if r['path'].startswith('mcctrl_vm_write_compat.')], 'source_acceptance':None,'execution_release':None}
dump(H/'PREPARATION-RESULT.json',summary);dump(E/'PREPARATION-RESULT.json',summary)
print(json.dumps({k:summary[k]for k in ['status','source_identity','source_files','source_bytes','nonce_reserved_not_executed','preparation','derived_driver','derived_owner']},indent=2))
