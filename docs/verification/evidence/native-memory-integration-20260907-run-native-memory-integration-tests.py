import hashlib,json,os,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
repo=Path('/workspace')
private=Path('/work/native-memory-integration-20260907')
head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
if not private.exists():
 subprocess.run(['git','clone','--shared','--no-hardlinks','--no-checkout',str(repo),str(private)],check=True)
 subprocess.run(['git','-C',str(private),'checkout','--detach',head],check=True)
 subprocess.run(['git','clone','--shared','--no-hardlinks','--no-checkout',str(repo/'ihk'),str(private/'ihk')],check=True)
 ihk_head=subprocess.check_output(['git','-C',str(repo/'ihk'),'rev-parse','HEAD'],text=True).strip()
 subprocess.run(['git','-C',str(private/'ihk'),'checkout','--detach',ihk_head],check=True)
if subprocess.check_output(['git','-C',str(private),'rev-parse','HEAD'],text=True).strip()!=head:
 raise SystemExit('Private base is not the current repository HEAD')
changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only','HEAD','-z']).split(b'\0')
changed+=subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard','-z']).split(b'\0')
inputs=[]
for raw in sorted(set(changed)):
 if not raw: continue
 relative=os.fsdecode(raw); source=repo/relative
 if not source.is_file() or source.is_symlink(): raise SystemExit('Unexpected changed input: '+relative)
 target=private/relative; target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(source,target); target.chmod(source.stat().st_mode&0o755)
 data=source.read_bytes(); inputs.append(dict(path=relative,sha256=hashlib.sha256(data).hexdigest(),size=len(data)))
env=dict(os.environ,MCKERNEL_RUSTC_1_92='/usr/bin/rustc',RUSTC='/usr/bin/rustc',PYTHONPATH=str(private/'scripts'),PYTHONDONTWRITEBYTECODE='1')
commands=[['git','diff','--check'], ['rustfmt','--check','--edition','2021','--config','skip_children=true','host-kernel/native-rust/smp_memory.rs'],
 ['python3','-m','unittest','-f','scripts.tests.test_ihk_smp_resource','scripts.tests.test_ihk_smp_buildid','scripts.tests.test_ihk_smp_native_lifecycle_check','scripts.tests.test_rocky_rust_staging','scripts.tests.test_native_rust_host_audit','scripts.tests.test_native_rust_build_surface_audit','scripts.tests.test_native_rust_kbuild_link_closure','scripts.tests.test_native_rust_unsafe_ffi_ledger']]
if len(sys.argv)>2:
 commands[-1]=["python3","-m","unittest","-f"]+sys.argv[2:]
run_id=sys.argv[1]
recipe_data=Path(__file__).read_bytes()
record=dict(recipe=dict(path=__file__,sha256=hashlib.sha256(recipe_data).hexdigest(),size=len(recipe_data)),source_parent=head,changed_inputs=inputs,commands=commands,started_utc=datetime.now(timezone.utc).isoformat(),results=[])
out=Path('/work/native-memory-integration-tests-20260907-'+run_id+'.json')
logpath=out.with_suffix('.log')
with logpath.open('wb') as log:
 for command in commands:
  log.write(('COMMAND '+repr(command)+'\n').encode()); log.flush()
  result=subprocess.run(command,cwd=private,env=env,stdout=log,stderr=subprocess.STDOUT)
  record['results'].append(dict(command=command,exit_code=result.returncode))
  if result.returncode: break
record.update(exit_code=result.returncode,finished_utc=datetime.now(timezone.utc).isoformat())
out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print('Memory integration tests:',result.returncode,logpath,flush=True)
raise SystemExit(result.returncode)
