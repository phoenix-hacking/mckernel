# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Root data filling only, prepared before resource capture; no spawn/query/guard.
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent
S=D.parent/'next114-debug32-perf3-coherent-source-1/root41-admission-source-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
b=json.loads((S/'ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json').read_text())
r=json.loads((D/'ROOT-REQUEST-ADOPTION.json').read_text())
b.update(author='/root',decision='BIND_CURRENT110_ACTUAL_HELD_BUILD_RESOURCES',root_attests_only_intervening_holder_preparation=True,nonce=r['nonce'],request_sha256=r['request_sha256'],profile=ref(D/'PROFILE.SOURCE-ONLY.json'),request=ref(D/'ROOT-REQUEST-ADOPTION.json'),source_publication=ref(D/'ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json'),physical_observation=ref(D/'ROOT-PREHOLDER-PHYSICAL-1.json'),runner=ref(D/'run_build_only.py'),worker=ref(D/'build_only_worker.py'),input_export_authority=ref(D/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json'),other_reserved_memory_bytes=2<<30,other_reserved_pids=64,aggregate_pid_budget=576,status='ACTUAL_ROOT41_HELD_RESOURCE_INPUT_NOT_COMPILER_RELEASE')
f=D/'ROOT-ACTUAL-RESOURCE-INPUT-1.json'
with f.open('x') as o:json.dump(b,o,indent=2);o.write('\n')
print(json.dumps(dict(status='ROOT_ACTUAL_RESOURCE_DATA_FILLED',reference=ref(f))))
