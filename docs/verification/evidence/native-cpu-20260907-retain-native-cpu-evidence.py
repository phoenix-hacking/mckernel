"""Retain source-bound local CPU evidence without awarding production credit."""
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile

scratch=Path('/work')
repo=Path('/workspace')
out=scratch/'native-cpu-retained-evidence-20260907'
out.mkdir()
rows=[]
def retain(source,name,compress=False):
    data=source.read_bytes()
    blob=gzip.compress(data,mtime=0) if compress else data
    (out/name).write_bytes(blob)
    rows.append(dict(source_path=str(source),path='evidence/'+name,
                     sha256=hashlib.sha256(blob).hexdigest(),size=len(blob),
                     uncompressed_sha256=hashlib.sha256(data).hexdigest(),uncompressed_size=len(data)))

def archive(root,names,name):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        for relative in sorted(names):
            source=root/relative
            if not source.is_file() or source.is_symlink():raise SystemExit('Unexpected archive input: '+str(source))
            data=source.read_bytes()
            info=tarfile.TarInfo(relative);info.size=len(data);info.mode=0o644;info.mtime=0
            tar.addfile(info,io.BytesIO(data))
    data=stream.getvalue();blob=gzip.compress(data,mtime=0)
    (out/name).write_bytes(blob)
    rows.append(dict(source_path=str(root),path='evidence/'+name,
                     sha256=hashlib.sha256(blob).hexdigest(),size=len(blob),
                     uncompressed_sha256=hashlib.sha256(data).hexdigest(),uncompressed_size=len(data)))

runs=[]
for label,directory in (('prototype','native-runtime-cpu-adapter-20260907'),
                         ('exact-numa','native-runtime-cpu-exact-numa-20260907')):
    base=scratch/directory
    record=json.loads((base/'local-run.json').read_text())
    if record['status']!='technical-capture-passed' or record['qemu_exit_code']!=0:
        raise SystemExit('Guest did not pass: '+directory)
    runs.append(dict(label=label,status=record['status'],cpus=record['cpus'],
                     numa_nodes=record.get('numa_nodes',1),staging_lock_refreshed=record['staging_lock_refreshed'],
                     runtime_record='evidence/native-cpu-20260907-'+label+'-runtime.json'))
    retain(base/'local-run.json','native-cpu-20260907-'+label+'-runtime.json')
    retain(base/'serial.log','native-cpu-20260907-'+label+'-serial.log.gz',True)
    retain(base/'qemu.log','native-cpu-20260907-'+label+'-qemu.log.gz',True)

exact=scratch/'native-cpu-exact-stage-20260907'
if (exact/'build.phase').read_text().strip()!='complete':raise SystemExit('Exact rebuild incomplete')
retain(exact/'kbuild-link-closure.json','native-cpu-20260907-link-closure.json')
retain(exact/'stage-lock.json','native-cpu-20260907-stage-lock.json')
retain(exact/'module-build.command','native-cpu-20260907-module-build.command')
retain(scratch/'native-cpu-exact-stage-build.log','native-cpu-20260907-exact-build.log.gz',True)
for label in ('native-cpu-adapter-prototype.log','native-cpu-adapter-prototype-2.log',
              'native-cpu-adapter-prototype-3.log','native-cpu-adapter-prototype-4.log',
              'native-cpu-integration-tests-10.log','native-cpu-ffi-lexer-tests.log'):
    retain(scratch/label,'native-cpu-20260907-'+label+'.gz',True)
for path in ('run-native-cpu-guest.py','run-native-cpu-exact-numa-guest.py',
             'build-native-cpu-exact-stage.py','write-native-cpio-spec.py',
             'run-native-cpu-full-tests.py','retain-native-cpu-evidence.py'):
    retain(scratch/path,'native-cpu-20260907-'+path)
for label,root in (('prototype-source',exact/'prototype-stage'),('staged-source',exact/'staged-source')):
    names=[str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()]
    archive(root,names,'native-cpu-20260907-'+label+'.tar.gz')
records=[p.name for p in exact.iterdir() if p.name.endswith(('.cmd','.mod'))]
records+=['resolved.config','Module.symvers','kernel.release','stage-lock.json','module-build.command','build.phase']
archive(exact,records,'native-cpu-20260907-compiler-records.tar.gz')
suite=scratch/'native-cpu-full-suite-20260907-11.json'
if json.loads(suite.read_text())['exit_code'] != 0:
    raise SystemExit('Full suite did not pass')
retain(suite,'native-cpu-20260907-full-suite.json')
retain(scratch/'native-cpu-full-suite-20260907-11.log','native-cpu-20260907-full-suite.log.gz',True)
for filename in ('native-cpu-full-suite-20260907-9.log',
                 'native-cpu-full-suite-20260907-10.log',
                 'native-cpu-license-chain-tests.log',
                 'native-cpu-license-chain-tests-2.log'):
    retain(scratch/filename,'native-cpu-20260907-'+filename+'.gz',True)
record=dict(schema='mckernel-local-native-cpu-checkpoint-v1',
            source_parent='b8d5170d00c30075ea726a17ea819aae80a4fe18',created_utc=datetime.now(timezone.utc).isoformat(),
            scope='native CPU reservation on fixed present topology; production acceptance remains open',
            isolation=dict(image='sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94',
                           cpus=4,cpuset='2-5',container_memory_bytes=12884901888,guest_memory_mib=8192,
                           uid=1000,network='none',acceleration='TCG',privileged=False),
            runs=runs,artifacts=rows,
            source_reuse=dict(smp_resource_sha256='879317596a89f065e9c61755b7663f9915aaa4cc8cca99ce2b57ba6b6a2be098',
                              shared_abi_sha256='89e0f72e821cbef91ad4771f4b4b24515d89035d357dc9c23c935a313b7d12c3',
                              status='unchanged existing policy and ABI; new Linux adapter'),
            claims=dict(native_cpu_reservation_proven=True,native_compat_cpu_ioctls_proven=True,
                        rollback_and_resource_module_pin_proven=True,two_node_cpu_hotplug_proven=True,
                        memory_assignment_proven=False,native_mckernel_boot_proven=False,
                        hpc_workloads_proven=False,production_gate_credit=False,full_external_source_closure_proven=False))
(out/'native-cpu-checkpoint-20260907.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print('Retained',len(rows),'artifacts in',out)
