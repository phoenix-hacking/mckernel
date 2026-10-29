"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow created-only successor to the reviewed ordinary41778 image owner.
No CLI/release/lease framework. Root supplies existing reviewed owner/admission bridge.
"""
from pathlib import Path
import ast,hashlib,json,os,re,stat,struct
D=Path(__file__).resolve().parent
IMAGE='sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'
PREFIX=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock']
FORBIDDEN_CID='2460c49fbbbf8be6ee5ae931e7e769eec2f26e352937e7f4a4dcf5d2ebec8008'
BINDINGS_SHA='f6670b8f41e08b20a4a9161b5ed6d780df6f8fc498285d5f057e5859437a2975'

class Refusal(RuntimeError):pass

def need(ok,why):
 if not ok:raise Refusal(why)
def reference(p):
 p=Path(p);need(p.is_absolute() and not p.is_symlink() and p.is_file(),'ordinary absolute input')
 a=p.stat();raw=p.read_bytes();z=p.stat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns,z.st_ctime_ns),'stable input bytes')
 return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def checked(r):
 need(type(r)is dict and set(r)=={'path','bytes','sha256'} and reference(r['path'])==r,'exact source/data reference');return Path(r['path']).read_bytes()
def bindings():
 need(reference(D/'BINDINGS.json')['sha256']==BINDINGS_SHA,'sealed extraction source binding');return json.loads((D/'BINDINGS.json').read_bytes())
def interfaces(b):
 """Import only exact reviewed AST units; never import/execute the full owner."""
 old=checked(b['reviewed_owner_snapshot']);backend=checked(b['ordinary_backend']);review=json.loads(checked(b['reviewed_source_record']))
 need(review['status']=='PASS_SOURCE_ONLY' and review['source']['sha256']==hashlib.sha256(old).hexdigest() and IMAGE in review['actual_read_only_checks']['image_identity'],'exact reviewed41778 lineage')
 ns=dict(os=os,RebindProbeError=Refusal)
 tree=ast.parse(backend)
 for node in tree.body:
  if isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id in ('LIMITS','RESOURCE_ARGS') for n in node.targets):exec(compile(ast.Module(body=[node],type_ignores=[]),b['ordinary_backend']['path'],'exec'),ns)
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='check_profile');exec(compile(ast.Module(body=[node],type_ignores=[]),b['ordinary_backend']['path'],'exec'),ns)
 names={'create_args','validate_image_inspect','validate_container'};nodes=[n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name in names];need(len(nodes)==3,'three unchanged reviewed profile units')
 exec(compile(ast.Module(body=nodes,type_ignores=[]),b['reviewed_owner_snapshot']['path'],'exec'),ns)
 return ns

def validate_request(q):
 need(q['author']=='/root' and q['operation']=='CREATED_ONLY_41778_LIBELF_EXPORT' and type(q['maximum_invocations'])is int and q['maximum_invocations']==1,'exact new Root extraction request')
 need(q['image']==IMAGE and q['source']=='/usr/lib64/libelf.so.1','one fixed immutable image/source')
 need(type(q['nonce'])is str and re.fullmatch('[0-9a-f]{32}',q['nonce']),'Root fresh32hex owner nonce')
 need(q['name']=='m15-libelf-extract-'+q['nonce'],'exact fresh extraction name')
 out=Path(q['output_root']);need(out.is_absolute() and out.parent==D and re.fullmatch('actual-libelf-export-[A-Za-z0-9_-]+',out.name),'fresh confined Root-owned output namespace')
 need(q['target']==str(out/'libelf.so.1') and q['native_or_build_authority'] is False,'one new ordinary library output; no runtime authority')
 return out

def inspect_library(path):
 """Byte-only initial exported-object check; SONAME/version closure remains OPEN."""
 r=reference(path);p=Path(path);st=p.stat();need(st.st_nlink==1 and st.st_uid in (0,1000) and st.st_size<=32<<20 and os.access(p,os.R_OK),'bounded readable single-link Root-mediated or ordinary export')
 raw=p.read_bytes();need(len(raw)>=64 and raw[:6]==b'\x7fELF\x02\x01','genuine ELF64 little-endian bytes')
 h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw,0);need(h[1]==3 and h[2]==62,'x86_64 shared-library ELF ABI')
 return dict(file=r,owner=dict(uid=st.st_uid,gid=st.st_gid,mode=oct(stat.S_IMODE(st.st_mode)),provenance='exact sudo Docker cp may produce Root-owned output; no chown/metadata rewrite'),e_type=3,e_machine=62,SONAME_and_GNU_versions_accepted=False,recursive_NEEDED_closure_accepted=False)

def execute_created_only(q,*,commands,admit,publish,retain_uncertainty,library_inspector=inspect_library):
 """Root's existing ordinary owner must hold custody and install before_popen.
 admit authenticates new Root grant/reviews/current controls/currentfree/resources/
 exclusive27:4 + lease and output ownership. No historical rebind release is used.
 Commands is the existing no-signal wait4 transport; no arbitrary argv is exposed.
 """
 out=validate_request(q);b=bindings();api=interfaces(b);need(callable(getattr(commands,'before_popen',None)),'actual final pre-Popen control/clock hook required')
 need(not os.path.lexists(q['target']),'fresh library destination absent')
 cid=None;create_attempted=False;created=False;removed=False;count=0
 def call(args,check=True):
  nonlocal count
  admit(q);result=commands.exact(PREFIX+args,timeout=30,check=check);count+=1
  need(not commands.client_retirement_unproven,'every actual export client positively joined')
  return result
 def container():
  rows=json.loads(call(['inspect','--type','container',cid]).stdout);need(type(rows)is list and len(rows)==1,'one exact fresh container inspect');info=rows[0]
  need(info['Id']==cid and info['Name']=='/'+q['name'],'exact newly created CID/name')
  api['validate_container'](info,IMAGE,q['nonce'])
  state=info['State'];need(state['Status']=='created' and state['Running'] is False and state['Pid']==0 and not any(state.get(k,False) for k in ('Paused','Restarting','Dead','OOMKilled')),'created-only; no running PID/state')
  labels=dict(b['pinned_image_labels']);labels['mckernel.owner']=q['nonce']
  need(info['Config']['Labels']==labels and info['Config']['Env']==b['pinned_image_env'],'exact inherited metadata plus only explicit fresh owner label')
  return info
 try:
  image_rows=json.loads(call(['image','inspect',IMAGE]).stdout);image=api['validate_image_inspect'](image_rows,IMAGE)
  need(image['Config']['Labels']==b['pinned_image_labels'] and image['Config']['Env']==b['pinned_image_env'],'exact pinned image environment/labels')
  publish('PREPARED.json',dict(operation=q['operation'],nonce=q['nonce'],image=IMAGE,source=q['source'],target=q['target'],no_start=True))
  # Same reviewed create args/resource profile; sleep is configured but NEVER started.
  create_attempted=True;result=call(api['create_args'](q['name'],IMAGE,q['nonce']));cid=result.stdout.strip()
  need(re.fullmatch('[0-9a-f]{64}',cid) and cid!=FORBIDDEN_CID,'actual fresh created CID; retired2460 forbidden');created=True
  before=container();publish('CREATED.json',before)
  call(['cp','-L',cid+':/usr/lib64/libelf.so.1',q['target']])
  library=library_inspector(Path(q['target']));publish('EXPORTED-ELF.json',library)
  after=container();need(after['State']==before['State'],'container was never started during export')
  publish('PRE-REMOVE.json',dict(cid=cid,created_only=True,exported=library))
  result=call(['rm','--',cid]);need(result.returncode==0 and result.stdout.strip()==cid and result.stderr=='','exact owned created-container removal');removed=True
  for query in ('id='+cid,'name=^/'+q['name']+'$'):
   result=call(['ps','--all','--quiet','--no-trunc','--filter',query]);need(result.stdout==result.stderr=='','exact created-container ID/name absence')
  result=dict(status='PASS_CREATED_ONLY_LIBELF_EXPORT_PENDING_ELF_VERSION_CLOSURE_AND_POSTJOIN',nonce=q['nonce'],cid=cid,image=IMAGE,library=library,created_only=True,container_absent=True,command_count=count,signals_sent=0,container_starts=0,builds=0,native_cases=0,owner_parentjoin_and_fresh_current_required=True,SONAME_version_dependency_acceptance=False,file_closure=False)
  publish('RESULT.json',result);return result
 except BaseException as exc:
  # No failure cleanup, signals or retry. Root retains its lease/global custody.
  retain_uncertainty(dict(error=repr(exc),cid=cid,create_attempt_may_have_occurred=create_attempted,created_confirmed=created,removed_confirmed=removed,commands_completed=count,signals_sent=0,no_automatic_cleanup_or_retry=True))
  raise
