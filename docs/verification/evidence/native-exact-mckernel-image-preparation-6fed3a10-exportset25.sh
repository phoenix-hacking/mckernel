#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
exec /usr/bin/python3 -I -B - "$@" <<'PY'
import hashlib, json, os, stat, sys
from pathlib import Path

C='6fed3a1022db0b4f9828dd42a8bd8f88fc052053'; I='3114d9e7101ad52030eb3effa849a5c108972a1f'
S=Path('/home/holden/mckernel-work/scratch')
BASE=S/'native-exact-inputs-6fed3a10-scratch-13.json'
SRC=S/'mckernel-exact-candidate-6fed3a10-scratch-13'; BACK=S/'native-exact-metadata-backup-6fed3a10-scratch-13'
OUT=S/'native-exact-build-output-4e99a82c-scratch-12'; NIGHT=S/'native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu'
RECEIPT=Path('/home/holden/mckernel-exact-image-evidence-6fed3a10-6/image-receipt.json')
ROOT=S/'native-exact-mckernel-image-work-6fed3a10-exportset-25'; EVID=S/'native-exact-mckernel-image-owner-evidence-6fed3a10-exportset-25'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inv(p):
    import runpy
    m=runpy.run_path('/home/holden/mckernel/scripts/native_rust_exact_mckernel_image_container_owner.py')
    return m['_tree_inventory'](Path(p))
if os.geteuid()==0: raise SystemExit('root-launch-prohibited')
if sys.argv[1:]: raise SystemExit('no arguments permitted')
if os.stat('/home/holden').st_dev != 66306 or os.stat(S).st_dev != 1831: raise SystemExit('device-admission')
if os.statvfs('/home/holden').f_bavail*os.statvfs('/home/holden').f_frsize < 16*2**30 or os.statvfs(S).f_bavail*os.statvfs(S).f_frsize < 12*2**30: raise SystemExit('capacity-admission')
for p in (BASE,SRC,BACK,OUT,NIGHT,RECEIPT):
    if not p.exists(): raise SystemExit('missing '+str(p))
for p in (ROOT,EVID, S/'native-exact-mckernel-image-request-6fed3a10-exportset-25.json', S/'native-exact-mckernel-image-toolchain-6fed3a10-exportset-25.json', S/'native-exact-mckernel-image-prepare-inputs-6fed3a10-exportset-25.json'):
    if p.exists() or p.is_symlink(): raise SystemExit('target-not-fresh '+str(p))
for p in (ROOT,EVID):
    if p.exists() or p.is_symlink(): raise SystemExit('target-not-fresh '+str(p))
    p.mkdir(mode=0o700); os.chmod(p,0o700)
for path, digest in {
 '/home/holden/mckernel/scripts/native_rust_exact_mckernel_image_request_prepare.py':'ec3f70b',
 '/home/holden/mckernel/scripts/native_rust_exact_mckernel_image_container_owner.py':'a6d6ffa',
 '/home/holden/mckernel/scripts/native_rust_exact_mckernel_image_offline.py':'91aa047',
 '/home/holden/mckernel/scripts/native_rust_exact_build_offline.py':'cc24312',
 '/home/holden/mckernel/scripts/native_rust_exact_build_container_owner.py':'a8c4c9f',
 '/usr/bin/git':'c3edb15'}.items():
 if not sha(path).startswith(digest): raise SystemExit('tool-hash '+path)
base=json.loads(BASE.read_text());
if base.get('candidate_sha')!=C or base.get('ihk_sha')!=I: raise SystemExit('candidate-identity')
values=dict(candidate_manifest=str(BASE), backup_root=str(BACK), backup_inventory=inv(BACK), build_output=str(OUT),
 image_receipt=str(RECEIPT), image_id='sha256:5688f9c8cb83e2aafb43c6aba8e8ff85fe17ddbc83a5935b6b804c1478bdcb98',
 nightly_root=str(NIGHT), host_git={'path':'/usr/bin/git','sha256':'c3edb15c9715b79fcfb1fa978256cdfc14a9ad72a4a8d5680a9fc5ebc6a57e0e'},
 driver_path='/home/holden/mckernel/scripts/native_rust_exact_mckernel_image_offline.py', provenance_path='/home/holden/mckernel/scripts/native_rust_exact_build_offline.py',
 host_owner_path='/home/holden/mckernel/scripts/native_rust_exact_build_container_owner.py', source_root=str(SRC), owner_work_root=str(ROOT), owner_evidence_root=str(EVID),
 output_root=str(ROOT/'output'), evidence_root=str(ROOT/'evidence'), attempt_root=str(EVID/'attempt'), lease_path=str(S/'native-exact-mckernel-image-lease-6fed3a10-exportset-25.json'),
 common_exclusion_path=str(S/'native-exact-candidate-operational-exclusion-exportset-25.json'), toolchain_manifest=str(S/'native-exact-mckernel-image-toolchain-6fed3a10-exportset-25.json'), jobs=4, timeout=19800,
 disk_admission={'host_device':os.stat('/home/holden').st_dev,'host_free_floor':16*2**30,'host_root':'/home/holden','scratch_device':os.stat(S).st_dev,'scratch_free_floor':12*2**30,'scratch_root':str(S)},
 expected_toolchain_lock_sha256='fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802',
 gitlink_manifest=str(S/'native-exact-mckernel-gitlink-inputs-6fed3a10-exportset-25.json'), gitlink_root=str(S/'native-exact-mckernel-gitlink-libdwarf-6fed3a10-exportset-25'))
inputs=S/'native-exact-mckernel-image-prepare-inputs-6fed3a10-exportset-25.json'
fd=os.open(inputs,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
try:
 os.write(fd,json.dumps(values,sort_keys=True).encode()+b'\n'); os.fsync(fd.fileno())
finally: os.close(fd)
fd=os.open(str(S),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); os.fsync(fd); os.close(fd)
os.execv('/usr/bin/python3',['/usr/bin/python3','-I','-B','/home/holden/mckernel/scripts/native_rust_exact_mckernel_image_request_prepare.py',str(inputs),'--request',str(S/'native-exact-mckernel-image-request-6fed3a10-exportset-25.json')])
PY
