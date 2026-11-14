"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Expert-approved additive receipt only: never import/rerun original executing driver.
"""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;B=D.parent;P=B.parent;A=B/'actual-fixture-cohort-1'
def pin(f):
 b=f.read_bytes();return dict(path=str(f),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
expert=P/'observer-metadata-review/RETAINED-ONLY-RECEIPT-DISPOSITION.json';assert pin(expert)['sha256']=='469ada2383c92318a57d0ff67e4152a6902b56a4316ba1aaad20156d97da662d'
ready=B/'sourcehandoff/EXECUTABLE-READY.GRANTED.json';assert pin(ready)['sha256']=='1f6d517008214dde8bbf8cf446a3afdb16fbfb7b24785198e6dbe2e1c8aced95';plan=json.loads(ready.read_bytes())
assert pin(B/'sourcehandoff/run_actual_once.py')['sha256']=='fd7c44cafaad69672e7c10d5594c6693ca49696f7ead2e59c49baeda6a459b0c'
assert pin(B/'sourcehandoff/ACTUAL-CORRECTION-WRITER-STOP-RECEIPT.json')['sha256']=='abfa3193b91d1d7f98ffa674032151cbef11feb961e6e293eef6cd0a77f079a5'
joins=[json.loads((A/str(i)/'whole-join.json').read_bytes()) for i in range(1,6)]
for j in joins:
 assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None
 for cap in j['captures'].values():assert pin(Path(cap['path']))['sha256']==cap['sha256']
text=(A/'3/stdout').read_text();assert text=='PASS direct=4608 PUBLIC-walker=576 original-C/Rust L3 pairs; actual level/effects/oldaction/phys/walk bodies; retained lower-provider traces\n'
for row in plan['sources']:assert pin(Path(row['path']))['sha256']==row['sha256']
obj=json.loads((A/'DURABLE-RUST-OBJECT.json').read_bytes())['object'];elf=json.loads((A/'DURABLE-FIXTURE-ELF.json').read_bytes())['ELF']
for row in (obj,elf):
 st=Path(row['path']).stat()
 for k,v in [('device',st.st_dev),('inode',st.st_ino),('size',st.st_size),('mtime_ns',st.st_mtime_ns),('ctime_ns',st.st_ctime_ns),('uid',st.st_uid),('gid',st.st_gid),('nlink',st.st_nlink)]:assert row[k]==v
qualification='Controlled lowerproviders; actual level/effects/oldaction/phys/walk/pageunmap; no lowerCchain/native acceptance'
receipt=dict(scope=__doc__,status='PASS_RETAINED_ACTUAL_COMPLETE_L3_5184_PAIRS_PUBLIC_FALLBACK_ABI_WITH_ADDITIVE_RECEIPT_DISPOSITION',actual_pairs=5184,actual_direct_pairs=4608,actual_PUBLIC_walker_pairs=576,all14_provider_categories_required_and_passed=True,captures=joins,ready=pin(ready),expert_disposition=pin(expert),executing_writer_preserved=pin(B/'sourcehandoff/run_actual_once.py'),first_E0425_stop=pin(P/'sourcehandoff/FIRST-FAILURE-PRESERVED.json'),original_writer_stop=pin(B/'sourcehandoff/ACTUAL-CORRECTION-WRITER-STOP-RECEIPT.json'),original_writer_failure=pin(A/'FAILURE.json'),Rust_object=obj,fixture_ELF=elf,object_hashes_reused_not_recomputed=True,source_bindings_unchanged=True,CPU_seconds=None,CPU_seconds_unavailable_reason='Original writer failed before saving total CPU use. Child whole-join records do not retain CPU usage; current process CPU cannot reconstruct historical total.',sum_actual_child_wall_seconds=sum(j['seconds'] for j in joins),qualifications=plan['limits']+[qualification],callback_chain_C_debt=plan['remaining_C_debt'],controlled_callback_qualification=plan['fixture_scope'],new_compiler_link_test_children=0,failed_product_candidates=1,sole_product_corrections=1,writer_keyerror_preserved=True,metadata_only_field_mapping="qualifications=plan['limits']+[existingcontrolled-providerqualification]",production_fullcrate_default_C_TU_link_native='OPEN',canonical_frozen15_currentimage_changes=0,CPU6_released=True,generator_source=pin(Path(__file__)))
out=D/'FINAL-RETAINED-ACTUAL-FIXTURE-HANDOFF.json';out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(pin(out)))
