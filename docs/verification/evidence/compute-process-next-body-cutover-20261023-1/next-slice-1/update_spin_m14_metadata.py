# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Granted metadata files only; no compile/CPU slot/canonical source edits.
from pathlib import Path
import copy,hashlib,json,re,shutil
R=Path('/home/holden/mckernel');P=Path(__file__).resolve().parent;E=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1/next-slice-1';J=R/'docs/verification/os-milestones-20260914/rust-cutover-m14.json';M=J.with_name('RUST-CUTOVER-M14.md')
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
old=J.read_text();oldmd=M.read_text();before=json.loads(old);d=copy.deepcopy(before)
f=next(f for f in d['files'] if f['id']=='M14-F02');s=next(s for s in f['functional_subgoals'] if s['id']=='M14-02-04');baseline=copy.deepcopy(s)
assert s['status']=='partial' and not any(v['id']=='M14-02-04-S03' for v in s['slices'])
base='docs/verification/evidence/compute-process-next-body-cutover-20261023-1/next-slice-1/'
def ev(name,expected,scope):
 path=R/base/name;p=pin(path)
 if expected:assert p['sha256']==expected
 json.loads(path.read_text())
 return dict(path=base+name,sha256=p['sha256'],size=p['bytes'],scope=scope)
canonical=ev('CANONICAL-INTEGRATION.json','e8290a189f27384e3ceed24a2d8f9385df56bc9640813f00d432e57b2f03a7c9','Root exact three-file canonical spin_sleep_or_schedule wrapper integration after156active source-pin exclusion and independent review; no whole C/defaultlink/native or retirement credit.')
leaf=ev('ACTUAL-LEAF-RECEIPT.json','687b629495887d44ebc2496b683bd22d9fa55991d7c49853d3b07eb4776fc3cc','129750 modeled original-selected-C/actual-Rust wrapper/body state and ordered-callback comparisons, including64875 calls through the extracted actual futex direct-schedule callback; current timer/scheduler headerABI compile. Whole production process layout/currentCpuLocal offsets remain OPEN.')
crate=ev('ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json','a19c4303bdbe94285a41fc0822b7528afc3468ff9f83ebccafc7e73c540f28df','Actual78-input same-profile production Rust compile ONCE15.242227s; NM/readelf verify unique GLOBAL FUNC spin_sleep/body/currentCPU, no unresolved spin/descriptor, exact productionU560->559 removingonlyspin, preservedmemory/set_timer exports. Whole C/layout/defaultkernel/native OPEN.')
source_review=ev('INDEPENDENT-PRIVATE-SPIN-SLEEP-SOURCE-LEAF-ACCEPTANCE.ROOT-RECORD.json',None,'Independent private source/ABI and actual modeled leaf acceptance only; no whole layout/defaultlink/native acceptance.')
production_review=ev('INDEPENDENT-PRODUCTION-SPIN-SLEEP-CONSUMER-ACCEPTANCE.ROOT-RECORD.json',None,'Independent actual productionRust object consumer acceptance; compiler diagnostics retained29983B/50warnings with unchanged warning headings, NM/readelf stderr empty; whole C/layout/defaultlink/native OPEN.')
s['proof']['implementation']['evidence'].append(canonical)
s['proof']['focused_checks']['evidence'].extend([leaf,crate,source_review,production_review])
s['slices'].append(dict(id='M14-02-04-S03',title='spin_sleep_or_schedule current-CPU and futex callback orchestration',status='partial',rust_consumer='kernel/rust/sched_helpers.rs::spin_sleep_or_schedule -> sched_spin_sleep_or_schedule_body_result; caller kernel/rust/futex.rs::futex_wait_schedule_direct_bridge',implementation='Canonical selected PUBLIC C forwarding wrapper replaced by Rust export reusing existing sharedABI offset constructor, lock adapters and body; exact complete C fallback and all other accepted process fixes preserved. No new C provider/data/layout.',focused_checks='129750 modeled C/Rust state/callback-order comparisons incl64875 extracted actual futex callback cases and actual headerABI compile; exact78input productionRust object PASS15.242227s/NM/readelf/productionU560->559; independent acceptance reused.',production_link='OPEN for this slice: actual whole process.c selected TU/currentCpuLocal layout+offset witness and matched default kernel link not executed. Prior idle and set_timer evidence remain separate.',native_validation='OPEN for matching native futex/spin/wakeup/scheduler behavior; functional image unchanged.',remaining_dependencies='Actual whole C/layout/currentCpuLocal offsets, default unique final Rust provider/callback ownership and matching native functional proof; no whole-area/file/native retirement credit.',next_action='Prepare coherent private successor from retained candidate9 with this exact three-file canonical delta and real selected consumer/layout/link guards; no in-place frozen candidate9 edit or runtime claim.',evidence=[canonical,leaf,crate,source_review,production_review]))
# Preserve every existing idle/timer slice, production-link and native field verbatim.
assert s['slices'][:-1]==baseline['slices']
assert s['proof']['production_link']==baseline['proof']['production_link'] and s['proof']['native_validation']==baseline['proof']['native_validation']
for field in ['implementation','focused_checks']:
 assert s['proof'][field]['evidence'][:len(baseline['proof'][field]['evidence'])]==baseline['proof'][field]['evidence']
for key in s:
 if key not in ['proof','slices']:assert s[key]==baseline[key]
for f0,f1 in zip(before['files'],d['files']):
 if f0['id']!='M14-F02':assert f0==f1
 else:
  for key in f0:
   if key!='functional_subgoals':assert f0[key]==f1[key]
  for s0,s1 in zip(f0['functional_subgoals'],f1['functional_subgoals']):
   if s0['id']!='M14-02-04':assert s0==s1
for key in before:
 if key!='files':assert before[key]==d[key]
paragraph='''Bounded M14-02-04-S03 progress: [`spin_sleep_or_schedule` canonical integration](../evidence/compute-process-next-body-cutover-20261023-1/next-slice-1/CANONICAL-INTEGRATION.json) moves the selected wrapper into the existing Rust scheduler body, reusing its shared-ABI offset constructor and lock adapters while preserving the exact C fallback. [129,750 modeled original-C/Rust comparisons](../evidence/compute-process-next-body-cutover-20261023-1/next-slice-1/ACTUAL-LEAF-RECEIPT.json) include 64,875 calls through the extracted actual futex callback. The [78-input production Rust compile](../evidence/compute-process-next-body-cutover-20261023-1/next-slice-1/ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json) passed once in 15.242227s; NM/readelf prove the export and exact unresolved-symbol change560→559, removing only `spin_sleep_or_schedule` and preserving memory/`set_timer` exports. [Source/leaf review](../evidence/compute-process-next-body-cutover-20261023-1/next-slice-1/INDEPENDENT-PRIVATE-SPIN-SLEEP-SOURCE-LEAF-ACCEPTANCE.ROOT-RECORD.json) and [production-consumer review](../evidence/compute-process-next-body-cutover-20261023-1/next-slice-1/INDEPENDENT-PRODUCTION-SPIN-SLEEP-CONSUMER-ACCEPTANCE.ROOT-RECORD.json) accepted this bounded scope. Whole C/layout/current `CpuLocalVar` offsets, default kernel link and native behavior remain **OPEN**. Prior idle/timer proofs are unchanged; no area/file/native retirement or practical check closure.\n\n'''
anchor='Verification focus: Idle lost-wakeup window,';assert oldmd.count(anchor)==1 and 'Bounded M14-02-04-S03 progress:' not in oldmd
newmd=oldmd.replace(anchor,paragraph+anchor,1)
(P/'M14-METADATA.before-spin.json').write_text(old);(P/'M14-METADATA.before-spin.md').write_text(oldmd)
J.write_text(json.dumps(d,indent=2)+'\n');M.write_text(newmd)
assert json.loads(J.read_text())==d
links=re.findall(r'\]\(([^)]+)\)',paragraph);assert len(links)==5 and all((M.parent/l).resolve().is_file() for l in links)
assert M.read_text().replace(paragraph,'')==oldmd
report=dict(scope=d['assignment_scope'],status='PASS_FOCUSED_SPIN_M14_METADATA_UPDATE',subgoal='M14-02-04',slice='M14-02-04-S03',files={str(p.relative_to(R)):pin(p) for p in [J,M]},prior_idle_timer_slices_exactly_preserved=True,prior_production_link_and_native_fields_exactly_preserved=True,prior_evidence_prefixes_preserved=True,all_other_fields_files_subgoals_preserved=True,JSON_and_five_new_links_valid=True,new_slice_whole_C_layout_currentCpuLocal_offsets_defaultlink_native='OPEN',practical_change=False,retirement_credit=False,compiler_executed=False,CPU6_held=False)
(P/'M14-SPIN-METADATA-UPDATE-RECEIPT.json').write_text(json.dumps(report,indent=2)+'\n')
for name in ['update_spin_m14_metadata.py','M14-METADATA.before-spin.json','M14-METADATA.before-spin.md','M14-SPIN-METADATA-UPDATE-RECEIPT.json']:shutil.copyfile(P/name,E/name)
print(json.dumps(dict(receipt=pin(P/'M14-SPIN-METADATA-UPDATE-RECEIPT.json'),files=report['files'],CPU6_held=False)))
