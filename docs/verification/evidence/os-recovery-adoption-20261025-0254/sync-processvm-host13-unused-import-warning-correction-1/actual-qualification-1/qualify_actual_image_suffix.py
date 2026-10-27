"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Execute unchanged 9d2d image/link/probe guards through explicit RO mount resolution.
"""
import ast,hashlib,json,os,re,shlex,stat,struct,subprocess,traceback
from pathlib import Path as HP,PurePosixPath as PP
D=HP(__file__).resolve().parent;E=HP('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
ROOT=E/'ROOT-SYNC-PROCESSVM-HOST13-FIVE-BUILD-ADMISSION-1/OUTPUT';B=ROOT/'work/output/build';A=ROOT/'work/evidence'
DRIVER=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py'
profile=json.loads((E/'ROOT-SYNC-PROCESSVM-HOST13-FIVE-BUILD-ADMISSION-1/PROFILE.SOURCE-ONLY.json').read_text());I=profile['inputs'];seed=HP(I['retained_seed'])
# This map is the actual immutable Docker RO binding, not the zero host placeholders.
exact={'/work/output/build/'+r['build_relative']:HP(r['source']['path']) for r in I['configuration']+[r for r in I['objects'] if not r['replace']]}
def actual(value):
 s=str(value)
 if s in exact:return exact[s]
 if s.startswith('/work/output/build/'):return B/s.removeprefix('/work/output/build/')
 if s=='/work/output/build':return B
 return HP(s)
class Bound:
 def __init__(self,value):self.value=PP(str(value))
 def __str__(self):return str(self.value)
 def __fspath__(self):return str(actual(str(self)))
 def __truediv__(self,other):return Bound(self.value/str(other))
 def __eq__(self,other):return str(self)==str(other)
 def __hash__(self):return hash(str(self))
 @property
 def parent(self):return Bound(self.value.parent)
 @property
 def name(self):return self.value.name
 def is_absolute(self):return self.value.is_absolute()
 def exists(self):return actual(self).exists()
 def is_file(self):return actual(self).is_file()
 def is_symlink(self):return actual(self).is_symlink()
 def stat(self):return actual(self).stat()
 def lstat(self):return actual(self).lstat()
 def resolve(self,strict=True):
  p=actual(self);assert p.resolve(strict=strict)==p;return self
 def open(self,*a,**kw):return actual(self).open(*a,**kw)
 def read_bytes(self):return actual(self).read_bytes()
 def read_text(self,*a,**kw):return actual(self).read_text(*a,**kw)
 def relative_to(self,other):return self.value.relative_to(str(other))
def Path(value):return value if isinstance(value,Bound) else Bound(value) if str(value).startswith('/work/output/build') else HP(value)
commands=[]
def bounded(argv,label,timeout=30,raw_bytes=False,reject_stderr=False,**kw):
 assert argv[0] in ['/usr/bin/readelf','/usr/bin/nm','/usr/bin/dd']
 mapped=[]
 for x in argv:
  if x.startswith('if=/work/output/build/'):x='if='+str(actual(x[3:]))
  elif x.startswith('/work/output/build/'):x=str(actual(x))
  mapped.append(x)
 p=subprocess.run(mapped,capture_output=True,timeout=timeout,check=False)
 commands.append(dict(label=label,container_argv=argv,actual_host_argv=mapped,returncode=p.returncode))
 assert p.returncode==0 and (not reject_stderr or not p.stderr),(label,p.stderr)
 return p.stdout if raw_bytes else p.stdout.decode()
source=DRIVER.read_bytes();assert hashlib.sha256(source).hexdigest()=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd'
tree=ast.parse(source)
names={'_fail','_canonical','_regular','_json','_artifact','_stable_bytes','_stable_snapshot','_validate_image','_validate_link_contract','_revalidate_link_contract_snapshots','_validate_modules_end_probe','_fsync_file','_fsync_dir','_write_fsync'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['EXPECTED_SYMBOLS','FORBIDDEN_C_SOURCES','MAX_JSON'] for t in n.targets)]
ns=dict(Path=Path,hashlib=hashlib,json=json,os=os,re=re,shlex=shlex,stat=stat,ImageBuildError=RuntimeError,_check_signal=lambda:None,_bounded_output=bounded)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(DRIVER)+':UNCHANGED_IMAGE_LINK_PROBE_GUARDS','exec'),ns)
tools=dict(tools={x:dict(path='/usr/bin/'+x) for x in ['readelf','nm','ld','dd']})
result=dict(scope=__doc__.splitlines()[0],status='IN_PROGRESS',phases={},seven_RO_input_resolution=[dict(container='/work/output/build/'+r['build_relative'],actual_original=r['source']) for r in I['objects'] if not r['replace']],new_host_placeholders_not_treated_as_objects=True)
try:
 # Check mounted originals against all retained exact bytes without reading placeholder bytes.
 for row in I['configuration']+[r for r in I['objects'] if not r['replace']]:
  p=actual('/work/output/build/'+row['build_relative']);raw=p.read_bytes();assert len(raw)==row['source']['bytes'] and hashlib.sha256(raw).hexdigest()==row['source']['sha256']
 result['phases']['RO_binding_identity']='PASS_ALL_RETAINED_CONFIGURATION_AND_SEVEN_EXACT_ORIGINAL_OBJECT_REFS'
 artifacts,snapshot=ns['_validate_image'](Bound('/work/output/build'),tools,D)
 result['phases']['image_and_rawld_link_contract']=dict(status='PASS_UNCHANGED_9D2D_IMAGE_AND_LINK_GUARDS',artifacts=artifacts,required_native_symbols=ns['EXPECTED_SYMBOLS'])
 probe=ns['_validate_modules_end_probe'](Bound('/work/output/build'),tools,D)
 result['phases']['retained_MODULES_END_probe']=dict(status='PASS_UNCHANGED_CONFIGURE_PROBE_AND_ALL_CONSUMERS',map_kernel_start_hex=probe['map_kernel_start_hex'])
 ns['_revalidate_link_contract_snapshots'](Bound('/work/output/build'),D,snapshot)
 # Match actual linker dependency input set to the accepted exact 11 producer inputs.
 dep=(B/'kernel/CMakeFiles/mckernel.img.dir/link.d').read_text()
 tokens=shlex.split(dep.replace('\\\n',' '));wanted={r['link_token'] for r in I['objects']}
 assert all(x in tokens or (x+':') in tokens for x in wanted)
 result['phases']['actual_link_d_inputs']=dict(status='PASS_ACTUAL_DEPFILE_CONTAINS_ALL_ELEVEN_INPUTS',exact_inputs=sorted(wanted))
 result['status']='PASS_ACTUAL_IMAGE_RAW_LINK_DEPFILE_RETAINED_PROBE_AND_NATIVE_SYMBOL_GUARDS'
except BaseException as error:
 result['status']='FAIL_FIRST_IMAGE_SUFFIX_VALIDATOR_PRESERVED';result['first_failure']=repr(error);result['traceback']=traceback.format_exc()
result['host_observer_commands']=commands
(D/'IMAGE-LINK-RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],first_failure=result.get('first_failure'),phases=list(result['phases']))))
if result['status'].startswith('FAIL'):raise SystemExit(1)
