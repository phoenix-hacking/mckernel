"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root ordinary one-manifest stage from actual bound bytes; same successful235 typed/API procedure.
No compose, compiler, guard, observation, native call, grant or cleanup; execute only as Root-owned stage.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,stat
D=Path(__file__).resolve().parent
PINS={'manifest': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1/original227-contract-case-correction-source-1/process227.RETAINED-COMPOSE.CONTRACT-BOUND.json', 'bytes': 9066, 'sha256': '5ad7d1619e3fa612453f7a9f70877798b6e47d98753d1df4622fa5427130e7f1'}, 'binding': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1/original227-contract-case-correction-source-1/COLLECTOR-AND-STAGE-BINDING.json', 'bytes': 4168, 'sha256': 'f6e085b05ed381010b1c347ff6cead6ff997ea0c8e9030a5b57e11823c6596b6'}, 'binder': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1/original227-contract-case-correction-source-1/bind_process227_collector.py', 'bytes': 10892, 'sha256': '4c8f08723bf86d627dc3cd0e39c8ba16d4328e28d101607c4f8b924ec6d7b2eb'}, 'planned_parent': '/home/holden/mckernel-work/scratch/m15p227n1', 'scratch_parent': '/home/holden/mckernel-work/scratch/m15p227n1-inputs', 'scratch_manifest': '/home/holden/mckernel-work/scratch/m15p227n1-inputs/manifest.json'}
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 assert os.getuid()==os.geteuid()==1000
 for key in ('manifest','binding','binder'):assert ref(PINS[key]['path'])==PINS[key]
 source=Path(PINS['manifest']['path']);raw=source.read_bytes();assert len(raw)<1<<20 and not source.is_symlink()
 parent=Path(PINS['planned_parent']);inputs=Path(PINS['scratch_parent']);target=Path(PINS['scratch_manifest'])
 receipt=D/'ROOT-ACTUAL-SCRATCH-STAGE.json'
 for p in (parent,inputs,receipt):assert not os.path.lexists(p),str(p)
 assert parent.parent==inputs.parent==Path('/home/holden/mckernel-work/scratch') and parent.name=='m15p227n1' and inputs.name=='m15p227n1-inputs'
 parent.mkdir(mode=0o700);inputs.mkdir(mode=0o700)
 with target.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 fd=os.open(inputs,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
 assert target.read_bytes()==raw and not list(parent.iterdir())
 spec=importlib.util.spec_from_file_location('literal_qualified227_data_binder',PINS['binder']['path']);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
 plan,facts,profile,diagnostic,owner=b.source_check()
 owner._manifest_identity(str(target),ref(target)['sha256']);owner._manifest_outside_writable_parent(str(target),str(parent));m=diagnostic.load_manifest(str(target))
 assert m['case_id']=='P-M01-02-child-SIGTERM-and-exec-recovery-227B' and m['staging']['collector']['sha256']=='ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c'
 value=dict(scope=__doc__.splitlines()[0],status='ACTUAL_ROOT_ORDINARY_227_MANIFEST_SCRATCH_STAGE_OWNER_API_PASS',source_manifest=PINS['manifest'],scratch_manifest=ref(target),planned_attempt_parent=str(parent),nonce=None,runtime_authority=None)
 with receipt.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
 print(json.dumps(dict(status=value['status'],stage=ref(receipt),manifest=ref(target),actual_owner_API_only=True,native_acceptance=False)))
if __name__=='__main__':main()
