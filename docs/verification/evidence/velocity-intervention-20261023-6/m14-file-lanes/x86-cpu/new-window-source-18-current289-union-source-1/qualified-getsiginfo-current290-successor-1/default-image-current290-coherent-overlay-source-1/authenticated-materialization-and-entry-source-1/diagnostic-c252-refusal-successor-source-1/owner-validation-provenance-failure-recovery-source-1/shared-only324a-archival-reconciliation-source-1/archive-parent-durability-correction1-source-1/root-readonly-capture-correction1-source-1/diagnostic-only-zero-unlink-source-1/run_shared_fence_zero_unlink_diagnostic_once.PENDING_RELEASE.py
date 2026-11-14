"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite owned readonly diagnostic capture; never a shared-record mutation release.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,signal
D=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/diagnostic-c252-refusal-successor-source-1/owner-validation-provenance-failure-recovery-source-1/shared-only324a-archival-reconciliation-source-1/archive-parent-durability-correction1-source-1/root-readonly-capture-correction1-source-1/diagnostic-only-zero-unlink-source-1/observe_current290_shared_fence.DIAGNOSTIC_ONLY_ZERO_UNLINK.NOT_RELEASED.py')
SOURCE_SHA='b3aaafa467410b920ed72f08bfe88b2593e5029464b9fe4f71fe52585cdd597f'
PROFILE=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/diagnostic-c252-refusal-successor-source-1/owner-validation-provenance-failure-recovery-source-1/shared-only324a-archival-reconciliation-source-1/archive-parent-durability-correction1-source-1/root-readonly-capture-correction1-source-1/diagnostic-only-zero-unlink-source-1/EXACT-SHARED-FENCE-ZERO-UNLINK-DIAGNOSTIC-PROFILE.json')
PROFILE_SHA='0bde05fdc05787bdd09ef4815c7285fa56e2e33f004b0c8a17e8b099f530c13e'
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA and hashlib.sha256(PROFILE.read_bytes()).hexdigest()==PROFILE_SHA
p=json.loads(PROFILE.read_bytes());H=Path(p['h990']['path']);assert hashlib.sha256(H.read_bytes()).hexdigest()==p['h990']['sha256'];spec=importlib.util.spec_from_file_location('accepted_h990_readonly_capture',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
a=argparse.ArgumentParser(allow_abbrev=False);a.add_argument('--release',type=Path,required=True);a.add_argument('--release-sha256',required=True);args=a.parse_args()
assert hashlib.sha256(args.release.read_bytes()).hexdigest()==args.release_sha256
release=json.loads(args.release.read_bytes());assert release.get('schema')=='mckernel.current290.shared-fence-zero-unlink-diagnostic.release.v1' and release.get('status')=='PASS_READONLY_DIAGNOSTIC_EXECUTION_RELEASE' and release.get('unlink_budget')==0 and release.get('signal_budget')==0
OUT=D/'actual-zero-unlink-diagnostic-owned-capture-1';OUT.mkdir(mode=0o700)
argv=['/usr/bin/taskset','-c','0','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=60:60','--fsize=33554432:33554432','--nofile=256:256','--stack=2097152:2097152','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',str(SOURCE),'--release',str(args.release),'--release-sha256',args.release_sha256,'--execute']
h.write(OUT/'EXACT-DIAGNOSTIC-ARGV.json',{'scope':__doc__,'argv':argv,'source_sha256':SOURCE_SHA,'profile_sha256':PROFILE_SHA,'unlink_budget':0,'signal_budget':0})
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,h.stop)
signal.setitimer(signal.ITIMER_REAL,96)
r=h.owned_capture({'argv':argv,'purpose':__doc__},OUT,90,lambda:None);h.write(OUT/'WHOLE-JOIN.json',r);signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps(r,sort_keys=True));assert r['returncode']==0 and all(r[k] is True for k in ('direct_child_joined','group_absent','closed_streams')) and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None
print((OUT/'stdout').read_text())
