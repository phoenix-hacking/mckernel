"""Real staged inputs, imported owner/runner, effect-stubbed consumer and fresh parent."""
import argparse,contextlib,hashlib,importlib.util,io,json,os,socket,stat,subprocess,sys,types
from pathlib import Path
D=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,label):
 if not ok:raise ValueError(label)
def ref(p):
 p=Path(p);s=p.stat();return dict(path=str(p),sha256=sha(p.read_bytes()),size=s.st_size,mode=s.st_mode)
def ref3(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=sha(b),bytes=len(b))
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def write(p,b):
 with Path(p).open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def js(p,d):write(p,(json.dumps(d,indent=2)+'\n').encode())
def main(path,digest):
 need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={7},'UID1000/CPU7')
 raw=Path(path).read_bytes();need(sha(raw)==digest,'whole preparation binding');b=json.loads(raw)
 for r in b['inputs'].values():need(ref3(r['path'])==r,'frozen preparation input '+r['path'])
 stage=Path(b['stage']);stage_manifest=stage/'manifest.json';m=json.loads(stage_manifest.read_bytes());old_manifest=json.loads(Path(b['inputs']['parent']['path']).read_bytes())
 for key in ('modules','profile','payload','pair'):need(m[key]==old_manifest[key],'unchanged selected tuple/contract '+key)
 result=json.loads((stage/'stage-result.json').read_bytes());need(result['status']=='PASS_SOURCE_BOUND_TWO_COMPLETE_CYCLE_STAGE_ONLY' and result['changed_existing_members']==['bin/native-boot','init'] and result['added_members']==['bin/native-resource-release-probe'],'genuine producer result shape')
 runtime=Path(b['runtime']);normalized=Path(b['normalized']);parent=Path(b['parent']);nonce=b['nonce']
 for p in (runtime,normalized,parent.parent):need(not os.path.lexists(p),'fresh complete preparation output '+str(p))
 runtime.mkdir(mode=0o700);normalized.mkdir(mode=0o700);write(normalized/'manifest.json',stage_manifest.read_bytes())
 case=dict(oracle_sha256=ref3(stage/'cycle_oracle.py')['sha256'],boot_sha256=ref3(stage/'native-boot')['sha256'],collector_sha256=ref3(stage/'init')['sha256'],release_path=str(stage/'native-resource-release-probe'),release_sha256=ref3(stage/'native-resource-release-probe')['sha256'],release_bytes=(stage/'native-resource-release-probe').stat().st_size,stager_sha256=ref3(stage/'stage_cycles.py')['sha256'],fixed_cycles=2,logger_seconds=120,full_restoration_verified=False)
 js(runtime/'runtime-case.json',case);write(runtime/'cycle_oracle.py',(stage/'cycle_oracle.py').read_bytes())
 write(runtime/'native_diagnostic.py',(D/'native_diagnostic.py.in').read_bytes())
 def replace(template,values):
  text=template
  for key,value in values.items():need(text.count('@'+key+'@')==1,'single rendered source slot '+key);text=text.replace('@'+key+'@',repr(value))
  need('@' not in text,'no unresolved source slot');return text.encode()
 runner_ref=b['inputs']['runner'];owner_ref=b['inputs']['owner']
 write(runtime/'native_diagnostic_runner.py',replace((D/'native_diagnostic_runner.py.in').read_text(),dict(RUNNER_PATH=runner_ref['path'],RUNNER_SHA=runner_ref['sha256'])))
 for name,key in [('native_diagnostic_backend.py','backend'),('qmp_capture.py','qmp')]:
  r=b['inputs'][key];text='import hashlib,importlib.util\nfrom pathlib import Path\np=Path('+repr(r['path'])+')\nif hashlib.sha256(p.read_bytes()).hexdigest()!='+repr(r['sha256'])+':raise ValueError("pinned imported engine")\ns=importlib.util.spec_from_file_location('+repr('original_cycle_'+key)+',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nglobals().update({k:v for k,v in vars(m).items() if not k.startswith("__")})\n';write(runtime/name,text.encode())
 owner_basis=load('exact_original_cycle_owner_basis',owner_ref['path']);sources=dict(owner_basis.SOURCE_HASHES)
 for r in b['runtime_source_inputs'].values():sources[r['path']]=r['sha256']
 for p in runtime.iterdir():sources[str(p)]=sha(p.read_bytes())
 extra=list(owner_basis.EXTRA_READONLY)
 for p in b['additional_readonly']:
  if p not in extra:extra.append(p)
 write(runtime/'native_diagnostic_container_owner.py',replace((D/'native_diagnostic_container_owner.py.in').read_text(),dict(OWNER_PATH=owner_ref['path'],OWNER_SHA=owner_ref['sha256'],SOURCE_HASHES=sources,EXTRA_READONLY=extra)))
 calls=[]
 def forbidden(*a,**k):calls.append('forbidden');raise AssertionError('real process/socket/root factory forbidden')
 subprocess.Popen=forbidden;socket.socket=forbidden;os.execve=forbidden
 owner=load('actual_complete_cycle_owner',runtime/'native_diagnostic_container_owner.py');runner=load('actual_complete_cycle_runner',runtime/'native_diagnostic_runner.py')
 nd,manifest=owner.bound_manifest(str(normalized/'manifest.json'),ref3(normalized/'manifest.json')['sha256'])
 loaded_nd,loaded_backend=runner._runtime();need(loaded_nd._case==case and callable(loaded_backend.process_factory),'actual runner imports current mandatory case/backend')
 need(nd._case==case and nd._oracle is not None,'mandatory whole cycle consumer actually bound')
 parent.parent.mkdir(mode=0o700);parent.mkdir(mode=0o700);st=parent.lstat();identity=dict(path=str(parent),device=st.st_dev,inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=oct(stat.S_IMODE(st.st_mode)),size=st.st_size,nlink=st.st_nlink,mtime_ns=st.st_mtime_ns,ctime_ns=st.st_ctime_ns)
 actual=owner.DiagnosticOwner(str(parent),manifest=str(normalized/'manifest.json'),manifest_sha256=ref3(normalized/'manifest.json')['sha256'],nonce=nonce)
 inside=actual._inside_args();create=actual._create_argv();qemu=nd.expected_qemu_argv(manifest,actual.attempt)
 need(qemu==json.loads(Path(b['inputs']['prospective_argv']['path']).read_bytes())['qemu_argv'],'whole actual argv equals preconstructed complete geometry')
 need(inside[inside.index('--attempt-parent')+1]==str(parent) and inside[inside.index('--nonce')+1]==nonce,'whole inside invocation')
 unix=[]
 for i,arg in enumerate(qemu):
  if arg.startswith('unix:'):
   p=arg[5:].split(',',1)[0];need(len(os.fsencode(p))<=107,'AF_UNIX107');unix.append(dict(option=qemu[i-1],path=p,encoded_bytes=len(os.fsencode(p))))
 need(unix==[dict(option='-qmp',path=str(actual.attempt/'qmp.sock'),encoded_bytes=len(os.fsencode(actual.attempt/'qmp.sock')))] and qemu[qemu.index('-monitor')+1]=='none','sole complete QMP/no hidden monitor')
 roots=[Path(owner.REPO),Path(owner.SCRATCH),*[Path(x) for x in owner.EXTRA_READONLY]]
 def visible(p):return any(Path(p)==r or (r.is_dir() and Path(p).is_relative_to(r)) for r in roots)
 consumed=[str(normalized/'manifest.json'),*owner.SOURCE_HASHES,*[r['path'] for r in manifest['artifacts'].values()],*[r['path'] for r in manifest['modules']],*[r['path'] for r in manifest['staging'].values()],*[r['payload']['path'] for r in manifest['pair']['apps']],manifest['pair']['source_authority']['path'],manifest['pair']['inherited_overlay_manifest']['path']]
 authority=json.loads(Path(manifest['pair']['source_authority']['path']).read_bytes());gate=load('frozen_cycle_205_authority',b['inputs']['authority_gate']['path']);consumed+=gate.consumed_paths(authority)
 need(all(visible(p) for p in consumed),'entire current consumed source/artifact visibility')
 fake=load('accepted_cycle_fake_transport',b['inputs']['fake']['path']);fake.owner_module=owner
 serial=Path(b['inputs']['modeled_serial']['path']).read_text();fake.serial=lambda nd,bad:serial
 row,image=fake.profile_row(actual);actual._profile(row,image)
 class RootIdentity:
  def getuid(self):return 0
  def geteuid(self):return 0
  def __getattr__(self,n):return getattr(os,n)
 owner.base.os=RootIdentity();owner.base.DockerBackend=lambda:types.SimpleNamespace(call=forbidden)
 def fake_run(obj):
  obj._create_argv();r,im=fake.profile_row(obj);obj._profile(r,im);obj.absent=True
 owner.DiagnosticOwner.run=fake_run
 args=['--attempt-parent',str(parent),'--nonce',nonce,'--owner-sha256',actual.owner_sha,'--manifest',str(normalized/'manifest.json'),'--manifest-sha256',ref3(normalized/'manifest.json')['sha256']]
 out=io.StringIO();err=io.StringIO()
 with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):owner_rc=owner.main(args)
 write(runtime/'owner-fixture.stdout',out.getvalue().encode());write(runtime/'owner-fixture.stderr',err.getvalue().encode());need(owner_rc==0 and not err.getvalue(),'actual owner CLI')
 work=runtime/'fake-attempt-parent';work.mkdir(mode=0o700)
 runner.base._backend_module=lambda:types.SimpleNamespace(process_factory=lambda argv,attempt:lambda timeout:fake.FakeProcess(argv,attempt,'good',nd),qmp_factory=lambda p:lambda timeout:fake.FakeQMP())
 out=io.StringIO();err=io.StringIO()
 with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):runner_rc=runner.main(['--manifest',str(normalized/'manifest.json'),'--attempt-parent',str(work),'--attempt-name','a','--timeout','10'])
 write(runtime/'runner-fixture.stdout',out.getvalue().encode());write(runtime/'runner-fixture.stderr',err.getvalue().encode());report=json.loads((work/'a/result.json').read_bytes())
 need(runner_rc==0 and not err.getvalue() and report['status']=='PROTOCOL_PASS','actual runner CLI')
 need(report['guest_report']==nd._oracle.evaluate_protocol(serial),'mandatory complete-cycle report not one-pair proxy')
 need(report['cleanup']=={'reaped':True,'errors':[]} and not report['capture_errors'],'unchanged host reaping/capture predicates')
 need(not calls and not list(parent.iterdir()) and not os.path.lexists(actual.evidence),'zero forbidden factories/real parent untouched')
 owner_argv=['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3','-B',str(runtime/'native_diagnostic_container_owner.py'),*args]
 result=dict(status='PASS_ACTUAL_IMPORTED_CYCLE_OWNER_RUNNER_AND_FULL_PARENT_FIXTURE_ONLY',stage_manifest=ref3(stage_manifest),normalized_manifest=ref3(normalized/'manifest.json'),parent_identity=identity,parent=str(parent),nonce=nonce,owner_argv=owner_argv,inside_argv=inside,create_argv=create,qemu_argv=qemu,AF_UNIX_endpoints=unix,runtime_source_hashes=sources,mandatory_cycle_oracle=ref3(runtime/'cycle_oracle.py'),case_binding=ref3(runtime/'runtime-case.json'),actual_owner_cli_rc=owner_rc,actual_runner_cli_rc=runner_rc,modeled_serial_input=b['inputs']['modeled_serial'],expected_model_report=report['guest_report'],entire_consumed_paths=sorted(set(consumed)),readonly_roots=[str(r) for r in roots],forbidden_factory_calls=calls,native_cycles=0,real_payload_launches=0,full_restoration_verified=False,repeat_quota_credit=False,root_operations=0)
 js(runtime/'preparation-result.json',result)
 for r in b['inputs'].values():need(ref3(r['path'])==r,'unchanged preparation input')
 print(json.dumps({k:result[k] for k in ('status','actual_owner_cli_rc','actual_runner_cli_rc','native_cycles')}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--binding',required=True);p.add_argument('--binding-sha256',required=True);a=p.parse_args();main(a.binding,a.binding_sha256)
