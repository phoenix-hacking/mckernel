"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root preclock publication data assembly; cached145 predecessor rows, no120rehash.
"""
from pathlib import Path
import json,hashlib
S=Path(__file__).resolve().parent
root=Path('/home/holden/mckernel')
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
p=json.loads((S/'PUBLICATION-ROWS.SOURCE-PLAN.NOT-AUTHORITY.json').read_text());A=Path(p['actual_admission']);D=S.parents[2]
profile=json.loads((A/'PROFILE.SOURCE-ONLY.json').read_text());template=json.loads((D/'PROFILE.TEMPLATE.SOURCE-ONLY.json').read_text())
assert profile['actual_nonce']==p['nonce'] and profile['exact_commands']==template['exact_commands']
assert profile['inputs']['objects']==template['inputs']['objects']
rows=list(p['cached_rows']);seen={r['actual']['path'] for r in rows}
for name in p['new_staged_paths']:
 q=Path(name);assert q.is_file() and not q.is_symlink()
 if name not in seen:rows.append(dict(actual=ref(q),fetched_equivalent_path=str(q.relative_to(root))));seen.add(name)
# Do not read/hash cached120 snapshots or retainedobjects again.
value=dict(scope=p['scope'],runtime_authority=None,status='ROOT_PRECLOCK_SOURCE_PUBLICATION_ROWS_PREPARED_NOT_FETCH_PROOF',rows=rows,cached_rows_reused=len(p['cached_rows']),new_small_staged_paths_hashed=len(p['new_staged_paths']),compiler_or_configure_operations=0,actual_fetched_commit=None)
f=A/'PUBLICATION-ROWS.PREPARED.json'
with f.open('x') as o:json.dump(value,o,indent=2);o.write('\n')
print(json.dumps(dict(status=value['status'],prepared_rows=ref(f),count=len(rows),new_hashes=len(p['new_staged_paths']))))
