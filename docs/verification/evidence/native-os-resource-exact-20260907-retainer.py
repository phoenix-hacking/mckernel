"""Retain completed local exact-stage evidence without changing gate scores."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,io,json,tarfile
repo=Path('/home/holden/mckernel'); scratch=Path('/home/holden/mckernel-work/scratch')
build=scratch/'native-os-resource-exact-stage-20260907'; runtime=scratch/'native-runtime-os-resource-exact-20260907'
b=json.loads((build/'build-record.json').read_text()); r=json.loads((runtime/'local-run.json').read_text())
if b['status']!='PASS' or r['status']!='technical-capture-passed':raise SystemExit('Both build and guest must have passed')
if not r['staging_lock_refreshed'] or r['mckernel_boot_proven'] or r['production_gate_credit']:raise SystemExit('Unexpected runtime scope')
out=repo/'docs/verification/evidence'; artifacts=[]
def put(label,data,compressed=False):
 target=out/('native-os-resource-exact-20260907-'+label)
 if target.exists():raise SystemExit('Refusing to replace retained evidence '+str(target))
 original=data
 if compressed:data=gzip.compress(data,mtime=0)
 target.write_bytes(data);value=dict(path=str(target.relative_to(repo)),size=len(data),sha256=hashlib.sha256(data).hexdigest())
 if compressed:value.update(uncompressed_size=len(original),uncompressed_sha256=hashlib.sha256(original).hexdigest())
 artifacts.append(value)
def archive(label,paths):
 buffer=io.BytesIO()
 with tarfile.open(fileobj=buffer,mode='w',format=tarfile.USTAR_FORMAT) as tar:
  for source,name in sorted(paths,key=lambda p:p[1]):
   data=source.read_bytes(); info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(data))
 put(label,buffer.getvalue(),True)
for directory,names in [(build,['build-record.json','stage-lock.json','kbuild-link-closure.json','kernel-build.log','module-build.log','build-helper.py','kernel-build.command','module-build.command']), (runtime,['local-run.json','serial.log','qemu.log','run-helper.py'])]:
 for name in names:put(('build-' if directory==build else 'guest-')+name+'.gz',(directory/name).read_bytes(),True)
paths=[]
for subdir in ('staged-source','repository-inputs'):
 paths += [(p,str(p.relative_to(build))) for p in (build/subdir).rglob('*') if p.is_file()]
paths += [(p,p.name) for p in build.iterdir() if p.is_file() and (p.suffix in ('.cmd','.mod','.patch') or p.name in ('resolved.config','kernel.release','Module.symvers','bindings_generated.rs','objtool-check.c','memory_hotplug.c','show_mem.c'))]
archive('source-and-compiler-records.tar.gz',paths)
archive('guest-probes.tar.gz',[(p,'probe-source/'+str(p.relative_to(runtime/'probe-source'))) for p in (runtime/'probe-source').rglob('*') if p.is_file()]+[(runtime/'root/init','init')]+[(p,'bin/'+p.name) for p in (runtime/'root/bin').iterdir() if p.is_file() and (p.name.startswith('native-memory-') or p.name.startswith('mcd0-ioctl-'))])
for name in ('ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko'):
 put('build-'+name+'.gz',(build/name).read_bytes(),True)
for name in ('native-os-resource-exact-module-checks-20260907.json','check-native-os-resource-exact-modules.py'):
 put(name+'.gz',(scratch/name).read_bytes(),True)
put('retainer.py',Path(__file__).read_bytes())
value=dict(schema_version=1,kind='native-os-resource-exact-stage-debug-checkpoint',recorded_utc=datetime.now(timezone.utc).isoformat(),source_parent=b['source_parent'],build=b,runtime_result={k:r[k] for k in ['status','qemu_exit_code','started_utc','finished_utc','cpus','memory_mib','numa_nodes','staging_lock_refreshed','memory_reservation_proven','memory_assignment_proven','cpu_assignment_proven','mckernel_boot_proven','production_gate_credit']},scope='declared stage with isolated fault-injection debug configuration; both ABIs across two module cycles',full_repository_suite_passed=False,remaining=['historical witness fixture integration and fresh full repository suite','McKernel image loading and AP startup','IKC and applications','McKernel Rust/assembly-only completion and production acceptance'],artifacts=artifacts)
p=repo/'docs/verification/native-os-resource-exact-stage-checkpoint-20260907.json'
if p.exists():raise SystemExit('Checkpoint already exists')
p.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print('Retained exact-stage build and guest:',len(artifacts),'artifacts')
