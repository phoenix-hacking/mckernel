# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Dispatcher-granted writes: these two M14 files and this evidence packet only.
from pathlib import Path
import copy,hashlib,json,shutil
R=Path('/home/holden/mckernel');P=Path(__file__).resolve().parent;E=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1';J=R/'docs/verification/os-milestones-20260914/rust-cutover-m14.json';M=J.with_name('RUST-CUTOVER-M14.md')
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
old=J.read_text(); oldmd=M.read_text(); before=json.loads(old);d=copy.deepcopy(before)
file=next(f for f in d['files'] if f['id']=='M14-F02');sub=next(s for s in file['functional_subgoals'] if s['id']=='M14-02-04');baseline=copy.deepcopy(sub);assert sub['status']=='partial'
base='docs/verification/evidence/compute-process-next-body-cutover-20261023-1/'
def evidence(name,sha,scope):
 p=R/base/name;assert pin(p)['sha256']==sha;return dict(path=base+name,sha256=sha,size=p.stat().st_size,scope=scope)
integ=evidence('CANONICAL-INTEGRATION.json','fc641655391f9ee414ecb79fd8b6f3a31cd9c086a665d38131146a26f342317e','Exact three-file canonical set_timer wrapper source integration after independent ABI review; unchanged functional image; no retirement credit.')
leaf=evidence('ACTUAL-LEAF-RECEIPT.json','1b1d55a3bc57d3122607dc026b29c446a244977130597c5480f2541ab93241d7','25750 original-C/actual-Rust wrapper and existing timer-body comparisons: state, callback identity/order, lock ownership, mutable-global read order, ignored signed returns; actual timer header ABI compile. Host model only.')
crate=evidence('ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json','7f2e8d83fe83067e64cdd6628cfb6dcc704d3ff99ef2c5d763faef9afe5969d3','Actual78-input pinned nightly production Rust object compiled once17.651s: unique Tset_timer/noUset_timer, currentCPU/timer providers and descriptor/four callback imports; prior memory exports preserved. One observer-only U-count correction preserved; production U556->560 distinct from broad harness593->597. No whole C TU/default link/native.')
review=evidence('INDEPENDENT-SOURCE-ABI-ACCEPTANCE.ROOT-RECORD.json','7b4382c28686032125b466595e73a2ed38643f8c2532488ede7c1790510c722f','Independent source/ABI and actual Rust object consumer acceptance only; whole C TU/default image/native/retirement OPEN.')
assert not any(s['id']=='M14-02-04-S02' for s in sub.get('slices',[]))
sub['proof']['implementation']['evidence'].append(integ)
sub['proof']['focused_checks']['evidence'].extend([leaf,crate,review])
sub['slices'].append(dict(id='M14-02-04-S02',title='set_timer current-CPU and timer callback orchestration',status='partial',rust_consumer='kernel/rust/sched_helpers.rs::set_timer -> timer_set_timer_body_result',implementation='Canonical Rust export replaces only PUBLIC set_timer C wrapper; exact C fallback remains. Immutable C offset producer and four unchanged C primitive callbacks remain explicit dependencies.',focused_checks='25750 originalC/Rust comparisons, current-headerABI compile and exact78-input productionRust object passed; independent source/ABI acceptance reused.',production_link='OPEN for this slice: actual whole process.c selected TU and matched final default kernel set_timer/provider link have not run. Existing idle slice production-link evidence is separate and preserved.',native_validation='OPEN for matching native timer/scheduler call path; current functional image unchanged.',remaining_dependencies='Whole C TU selection/ABI/relocations, unique final Rust set_timer and matching callback/data providers, then applicable native proof; no whole-area/file retirement credit.',evidence=[integ,leaf,crate,review]))
sub['next_action']+=' For set_timer S02, prepare a separate coherent successor of frozen candidate8 with exact three canonical overlays and selected process.c ABI/symbol/relocation guards; no in-place candidate8 edit or new defaultlink/native credit.'
file['known_partial_cutovers'].append('Canonical set_timer wrapper now exports from existing Rust scheduler/timer body after independent review:25750 originalC/Rust comparisons and78-input productionRust object passed; exact C fallback and immutable offset/four primitive C callback providers remain. Slice M14-02-04-S02 whole C/defaultlink/native OPEN; no whole-file credit.')
assert sub['proof']['production_link']==baseline['proof']['production_link'] and sub['proof']['native_validation']==baseline['proof']['native_validation']
for f0,f1 in zip(before['files'],d['files']):
 if f0['id']!='M14-F02':assert f0==f1
for a,b in zip(next(f for f in before['files'] if f['id']=='M14-F02')['functional_subgoals'],file['functional_subgoals']):
 if a['id']!='M14-02-04':assert a==b
for key in before:
 if key!='files':assert before[key]==d[key]
paragraph='''Bounded M14-02-04-S02 progress: [`set_timer(int)` canonical source integration](../evidence/compute-process-next-body-cutover-20261023-1/CANONICAL-INTEGRATION.json) moves the selected public wrapper into `sched_helpers.rs`, reusing the existing Rust timer body. [25,750 original-C/Rust comparisons and real-header ABI checks](../evidence/compute-process-next-body-cutover-20261023-1/ACTUAL-LEAF-RECEIPT.json) and the [actual 78-input production Rust object](../evidence/compute-process-next-body-cutover-20261023-1/ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json) passed, with [independent source/ABI acceptance](../evidence/compute-process-next-body-cutover-20261023-1/INDEPENDENT-SOURCE-ABI-ACCEPTANCE.ROOT-RECORD.json). The exact C fallback, immutable C offset descriptor and four primitive C callbacks remain. Whole `process.c` TU, this slice's default kernel link and native timer/scheduler proof remain **OPEN**. Prior idle production-link evidence is preserved separately; no whole-area/file retirement or practical check closure.\n\n'''
anchor='Verification focus: Idle lost-wakeup window,';assert oldmd.count(anchor)==1 and 'M14-02-04-S02 progress:' not in oldmd
newmd=oldmd.replace(anchor,paragraph+anchor,1)
(P/'M14-METADATA.before.json').write_text(old);(P/'M14-METADATA.before.md').write_text(oldmd)
J.write_text(json.dumps(d,indent=2)+'\n');M.write_text(newmd)
# Focused JSON/evidence/link checks only. No compiler, build, root or guest.
assert json.loads(J.read_text())==d
for ev in [integ,leaf,crate,review]:assert pin(R/ev['path'])['sha256']==ev['sha256']
import re
links=re.findall(r'\]\(([^)]+)\)',paragraph)
assert len(links)==4 and all((M.parent/link).resolve().is_file() for link in links)
assert M.read_text().replace(paragraph,'')==oldmd
report=dict(scope=d['assignment_scope'],status='PASS_FOCUSED_M14_METADATA_UPDATE',files={str(p.relative_to(R)):pin(p) for p in [J,M]},subgoal='M14-02-04',slice='M14-02-04-S02',old_idle_production_link_exactly_preserved=True,native_validation_exactly_preserved=True,other_subgoals_and_files_and_top_level_exactly_preserved=True,JSON_and_four_new_links_valid=True,new_slice_whole_C_default_link_native='OPEN',practical_check_change=False,wholefile_retirement_credit=False,CPU6_held=False)
(P/'M14-METADATA-UPDATE-RECEIPT.json').write_text(json.dumps(report,indent=2)+'\n')
for n in ['update_focused_m14_metadata.py','M14-METADATA.before.json','M14-METADATA.before.md','M14-METADATA-UPDATE-RECEIPT.json']:shutil.copyfile(P/n,E/n)
print(json.dumps(dict(receipt=pin(P/'M14-METADATA-UPDATE-RECEIPT.json'),files=report['files'])))
