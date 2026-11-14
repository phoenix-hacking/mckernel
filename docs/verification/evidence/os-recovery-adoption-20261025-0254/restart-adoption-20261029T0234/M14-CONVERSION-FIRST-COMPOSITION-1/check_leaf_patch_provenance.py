"""Functional OS fixed-input byte provenance only; no security testing/runtime."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;A=D.parent
items=[('ten',A/'M14-PRIVATE-TEN-LEAF-BATCH-1/TEN-LEAF-BATCH.PRIVATE-NOT-APPLIED.patch','a36e5af75024ae2fa610004a488230c8e6146f247440b00e441a4743da753948'),('context',A/'M14-UPGRADED-F03-CONTEXT-FORWARD-PAIR-1/CONTEXT-PAIR-ON-TEN.PRIVATE-NOT-APPLIED.patch','2f4a986ce57a5ee1e4d2769ec59ab51b8f9f1384a57329e3555f618e0b35f2a8'),('kfree_Rust_owned',A/'M14-UPGRADED-F03-PTRACE-KFREE-1/Rust-owned-metadata-correction-1/RUST-METADATA.PRIVATE-NOT-APPLIED.patch','7777f386ad0a80b6dbb98ccb6b693ebf2422d8b33302743f181af459c7096982'),('exitgroup',A/'M14-UPGRADED-F03-EXIT-GROUP-TERMINATE-1/EXIT-GROUP-TERMINATE.PRIVATE-NOT-APPLIED.patch','3d5f4dbf86497d84b02a328404c3266d4cf2ebe83fd33611f56dc88fffdcdab1'),('wakeup_IRQ_pair',A/'M14-UPGRADED-F03-WAKEUP-WRITER-PAIR-1/WAKEUP-WRITER-PAIR.PRIVATE-NOT-APPLIED.patch','21d42afec1870491af6b49f8f726269389bf34fbd11125be2e6d91b24f2250a2'),('raw_wakeup',A/'M14-UPGRADED-F03-RAW-CALLBACK-QUEUE-1/wakeup/PRIVATE-NOT-APPLIED.patch','75a77afc899abb70191b62b495764556be9961d74f3153e1f031f038c9464b45'),('raw_terminate_mcexec',A/'M14-UPGRADED-F03-RAW-CALLBACK-QUEUE-1/terminate_mcexec/PRIVATE-NOT-APPLIED.patch','04ede8182c5b7f0ceb86292df614eeb7f9f96e5e7395ee116551042f751c7817'),('raw_perf_open',A/'M14-UPGRADED-F03-RAW-CALLBACK-QUEUE-1/perf_open/PRIVATE-NOT-APPLIED.patch','1b737bdcf1bf9e643dc161e707550607679c0c16cf40e92750bd84f2161373aa')]
leaves={};patchrefs={}
for label,p,expected in items:
 data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==expected,label;patchrefs[label]=dict(path=str(p),bytes=len(data),sha256=expected);old_is_null=False;target=None;added=[]
 def flush():
  if old_is_null and target and target.endswith('.rs'):
   assert target not in leaves,target;leaves[target]=''.join(added).encode()
 for line in data.decode().splitlines(True):
  if line.startswith('--- '):flush();old_is_null=line.strip()=='--- /dev/null';target=None;added=[]
  elif line.startswith('+++ b/'):target=line[len('+++ b/'):].strip()
  elif old_is_null and target and line.startswith('+'):added.append(line[1:])
 flush()
rows=json.loads((D/'FILEMAP.SOURCE-ONLY.json').read_text())['files'];used=[r for r in rows if r['reused_leaf']];assert len(used)==len(leaves)==16
for r in used:assert leaves[r['target']]==Path(r['source']['path']).read_bytes(),r['target']
(D/'PATCH-INPUT-PROVENANCE.json').write_text(json.dumps(dict(status='PASS_EXACT16_LEAVES_FROM8_HASHED_ORIGINAL_PATCHES',input_patches=patchrefs,leaf_body_count=16,new_body_review_state='PENDING_OR_REUSED_AT_EXACT_SOURCE_SCOPE_NOT_ACCEPTANCE',no_effects=True),indent=2)+'\n');print('PASS16leaf bodies exact from8original hashed patches')
