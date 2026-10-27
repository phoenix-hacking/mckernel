# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Root-owned next ordinary preparation command ONLY. Not executed by this worker.
# Run once only after Root reconciles accepted SDK4 postjoin/current ownership.
/home/holden/anaconda3/bin/python3 -I -B - <<'PY_STAGE'
from pathlib import Path
import hashlib,importlib.util,json,os
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
N=E/'current290-core-files-root-preparation-source-1'
source=E/'current290-next-core-cases-source-1/files/manifest.HOST-STATIC.json'
stage=Path('/home/holden/mckernel-work/scratch/n290files1');parent=stage/'p';target=stage/'m.json'
assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest=='f4566bf04455e6d002d104679143abe291bc84a6fedc382d32b15c036647b21e'
assert not os.path.lexists(stage)
owner=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/runtime-provider-rebind-1/native/native_diagnostic_container_owner.py')
assert hashlib.sha256(owner.read_bytes()).hexdigest()=='45010e54e1f78e3efcd6572b71342ee6078abeea98961f2c5d49849575dd5048'
spec=importlib.util.spec_from_file_location('retained_files_pure_owner',owner);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
validator=owner.with_name('native_diagnostic.py');assert hashlib.sha256(validator.read_bytes()).hexdigest()=='f368324242bfdfb0ad1f3f524a906dcf51730ef0beb311315e6b66f5d585748c'
spec=importlib.util.spec_from_file_location('retained_files_manifest_validator',validator);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
# Validate source before the exclusive ordinary staging mutation.
v.load_manifest(source)
stage.mkdir(mode=0o700);parent.mkdir(mode=0o700)
with target.open('xb') as out:out.write(raw)
assert target.read_bytes()==raw and not list(parent.iterdir())
m._manifest_identity(str(target),digest);m._manifest_outside_writable_parent(str(target),str(parent));v.load_manifest(target)
receipt=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_EXCLUSIVE_ORDINARY_SCRATCH_STAGE_AND_TWO_OWNER_PURE_PATH_GUARDS',source_manifest=dict(path=str(source),bytes=len(raw),sha256=digest),scratch_manifest=dict(path=str(target),bytes=len(raw),sha256=digest),planned_attempt_parent=str(parent),parent_uid=parent.stat().st_uid,parent_gid=parent.stat().st_gid,parent_mode=oct(parent.stat().st_mode),parent_empty=True,checks=['_manifest_identity','_manifest_outside_writable_parent','existing_native_load_manifest'],kernel_image_unchanged=True,overlay_unchanged=True,runtime_authority=None,nonce=None,resources=None,review=None)
with (N/'ACTUAL-SCRATCH-MANIFEST-STAGE.json').open('x') as out:json.dump(receipt,out,indent=2);out.write('\n')
print(json.dumps(receipt))
PY_STAGE
