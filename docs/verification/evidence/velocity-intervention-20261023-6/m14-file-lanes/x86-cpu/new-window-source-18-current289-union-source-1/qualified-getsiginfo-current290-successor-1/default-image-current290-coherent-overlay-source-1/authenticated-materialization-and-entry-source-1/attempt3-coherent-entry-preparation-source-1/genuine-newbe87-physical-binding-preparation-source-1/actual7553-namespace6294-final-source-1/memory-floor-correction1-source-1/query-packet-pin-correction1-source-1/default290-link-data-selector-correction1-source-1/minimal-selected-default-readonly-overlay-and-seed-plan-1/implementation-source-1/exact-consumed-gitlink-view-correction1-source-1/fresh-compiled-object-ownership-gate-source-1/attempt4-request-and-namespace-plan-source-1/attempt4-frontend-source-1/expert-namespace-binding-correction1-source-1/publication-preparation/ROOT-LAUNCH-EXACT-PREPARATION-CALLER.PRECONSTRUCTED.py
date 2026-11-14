"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import hashlib,json,os,resource
from pathlib import Path
p=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/expert-namespace-binding-correction1-source-1/publication-preparation')
cmd=json.loads((p/'EXACT-ATTEMPT4-FINAL-CALLER-AND-CLEANUP-COMMANDS.NOT-GRANTED.json').read_bytes())
assert os.getuid()==os.geteuid()==1000
assert resource.getrlimit(resource.RLIMIT_CPU)==(resource.RLIM_INFINITY,resource.RLIM_INFINITY)
argv=cmd['preparation_caller_argv']
assert Path(argv[-3]).exists() and not Path(cmd['caller_exclusive_context_output']).exists()
os.execv(argv[0],argv)
