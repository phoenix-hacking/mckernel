import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone
repo=Path('/workspace')
private=Path('/work/native-cpu-validation-20260907')
changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only','HEAD','-z']).split(b'\0')
changed+=subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard','-z']).split(b'\0')
inputs=[]
for raw in sorted(set(changed)):
    if not raw: continue
    relative=os.fsdecode(raw)
    source=repo/relative
    if not source.is_file() or source.is_symlink():
        raise SystemExit('Unexpected changed input: '+relative)
    target=private/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)
    target.chmod(source.stat().st_mode & 0o755)
    data=source.read_bytes()
    inputs.append(dict(path=relative,sha256=hashlib.sha256(data).hexdigest(),size=len(data)))
subprocess.run(['git','-C',str(private),'diff','--check'],check=True)
subprocess.run(['rustfmt','--check','--edition','2021','--config','skip_children=true',str(private/'host-kernel/native-rust/smp_cpu.rs')],check=True)
environment=dict(os.environ, MCKERNEL_RUSTC_1_92='/usr/bin/rustc',
                 MCKERNEL_ROCKY_SOURCE_6_12='/work/native-pristine-api-source',
                 MCKERNEL_RK007_BUILD_ARTIFACT='/work/artifacts/rk007-bc60-original.zip',
                 MCKERNEL_RK007_V2_ARTIFACT='/work/artifacts/rk007-ef58-original.zip',
                 PYTHONPATH=str(private/'scripts'),PYTHONDONTWRITEBYTECODE='1')
command=['python3','-m','unittest','discover','-s','scripts/tests','-p','test_*.py','-f']
record=dict(source_parent=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),
            changed_inputs=inputs,command=command,started_utc=datetime.now(timezone.utc).isoformat(),
            environment={k:v for k,v in environment.items() if k.startswith('MCKERNEL_') or k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE')})
out=Path('/work/native-cpu-full-suite-20260907-11.json')
out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
with Path('/work/native-cpu-full-suite-20260907-11.log').open('wb') as log:
    result=subprocess.run(command,cwd=private,env=environment,stdout=log,stderr=subprocess.STDOUT)
record.update(exit_code=result.returncode,finished_utc=datetime.now(timezone.utc).isoformat())
out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print('Full suite exit:',result.returncode)
raise SystemExit(result.returncode)
