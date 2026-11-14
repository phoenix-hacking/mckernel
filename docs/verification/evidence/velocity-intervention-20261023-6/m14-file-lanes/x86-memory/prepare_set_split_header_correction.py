"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Sole bounded fixture header-transport correction; source preparation, no execution.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json,re,stat
B=Path(__file__).resolve().parent;ROOT=Path('/home/holden/mckernel');P=B/'set-page-split-provider-fixture-preparation-1';D=P/'observer-header-inclusion-correction-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as o:o.write(s)
def rec(p,d):put(p,json.dumps(d,indent=2,sort_keys=True)+'\n')
assert not D.exists()
R0=P/'SET-SPLIT-FIXTURE-RECIPE.NOT-EXECUTED.json';old=json.loads(R0.read_bytes())
assert ref(R0)['sha256']=='c70d9b9f05bc587262cf3b91764c25c59d46e73f824353de22fd44e817abce7f'
A=P/'actual-set-split-attempt-1';objrec=A/'01-Rust-set-split/DURABLE-OBJECT.json';joinrec=A/'01-Rust-set-split/whole-join.json';obj=json.loads(objrec.read_bytes());joined=json.loads(joinrec.read_bytes())
assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and joined['error'] is None
st=Path(obj['path']).lstat()
for k,v in [('device',st.st_dev),('inode',st.st_ino),('size',st.st_size),('mtime_ns',st.st_mtime_ns),('ctime_ns',st.st_ctime_ns),('uid',st.st_uid),('gid',st.st_gid),('nlink',st.st_nlink)]:assert obj[k]==v,k
assert stat.S_ISREG(st.st_mode) and oct(stat.S_IMODE(st.st_mode))==obj['mode']
# Literal definitions from exactly the two real headers, also identical to the
# already-used accepted allocator type closure. No numeric substitute guesses.
headers=[(ROOT/'arch/x86_64/kernel/include/arch-memory.h','PAGE_P2ALIGN'),(ROOT/'lib/include/ihk/mm.h','IHK_MC_PG_KERNEL')]
closure='/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n * Literal finite real-header macro closure; source header bindings in recipe. */\n'
for h,n in headers:
 lines=[s for s in h.read_text().splitlines(True) if re.match(r'#define '+n+r'\s',s)]
 assert len(lines)==1;closure+=lines[0]
assert all(x in (B/'next-pt-alloc-source-only-1/EXACT-REAL-HEADER-TYPE-CLOSURE.inc').read_text() for x in closure.splitlines(True) if x.startswith('#define'))
H=D/'EXACT-REAL-HEADER-MACROS.inc';put(H,closure)
oldc=P/'fixture.c';newc=P/'fixture.header-inclusion-correction-1.c';s=oldc.read_text();anchor='#include <sys/types.h>\n';assert s.count(anchor)==1
corrected=s.replace(anchor,anchor+'#include "'+str(H)+'"\n',1);put(newc,corrected)
patch=''.join(difflib.unified_diff(s.splitlines(True),corrected.splitlines(True),fromfile=str(oldc),tofile=str(newc)));put(D/'EXACT-FIXTURE-HEADER-INCLUSION.patch',patch)
commands=copy.deepcopy(old['commands'][1:]);assert len(commands)==5
assert commands[0]['argv'].count('fixture.c')==1
commands[0]['argv']=[newc.name if x=='fixture.c' else x for x in commands[0]['argv']]
assert commands[1:]==old['commands'][2:]
recipe=copy.deepcopy(old);recipe.update(commands=commands,sources=old['sources']+[ref(x) for x in [newc,H,D/'EXACT-FIXTURE-HEADER-INCLUSION.patch',objrec,joinrec,A/'01-Rust-set-split/command.json',A/'FAILURE.STOP.json',A/'02-GCC-link-set-split/stderr']]+[ref(h) for h,n in headers],retained_Rust_object=dict(object=obj,producer_command=ref(A/'01-Rust-set-split/command.json'),producer_join=ref(joinrec),durable_object_authority=ref(objrec),source_inputs=old['sources'],stat_only_revalidated=True,no_Rust_recompile=True,no_Rust_object_rehash=True),correction_scope='One genuine real-header macro-closure include inserted in fixture only. Product bytes, Rust object/input bytes, assertions, oracle and pending four command objects unchanged. Resume failed original02 plus pending03..06 (five commands total); old grant shorthand remaining4 means pending four, not Rust replay.',failure_history=dict(original_capture=str(A),failure=ref(A/'FAILURE.STOP.json'),stderr=ref(A/'02-GCC-link-set-split/stderr'),failed_PID=4117134,failed_start=61523051,one_bounded_correction=True,further_unexpected='STOP/expert; no automatic author retry'),actual_outputs=None,execution_grant=None)
R=D/'EXACT-FAILED02-PLUS-PENDING4.NOT-RELEASED.json';rec(R,recipe)
d=(P/'run_actual_once.NOT-RELEASED.py').read_text()
d=d.replace('One bounded four-provider set/split original-C/Rust reference cohort','Sole bounded fixture-header correction, retained Rust object, failed02 plus pending four commands')
d=d.replace('P = Path(__file__).resolve().parent','P = Path('+repr(str(P))+')')
d=d.replace("RECIPE = P / 'SET-SPLIT-FIXTURE-RECIPE.NOT-EXECUTED.json'",'RECIPE = Path('+repr(str(R))+')').replace(ref(R0)['sha256'],ref(R)['sha256'])
d=d.replace("for name in ('fixture-set-split.o', 'fixture-set-split'):","for name in ('fixture-set-split',):")
d=d.replace("A = P / 'actual-set-split-attempt-1'","A = P / 'actual-set-split-attempt-2-header-inclusion-correction-1'")
needle='sources()\n# h990'
reuse='''sources()
# Reuse the original durable producer authority and stat identity, no object read.
retained = r['retained_Rust_object']['object']
retained_stat = Path(retained['path']).lstat()
for key, value in [('device',retained_stat.st_dev),('inode',retained_stat.st_ino),('size',retained_stat.st_size),('mtime_ns',retained_stat.st_mtime_ns),('ctime_ns',retained_stat.st_ctime_ns),('uid',retained_stat.st_uid),('gid',retained_stat.st_gid),('nlink',retained_stat.st_nlink)]:
    assert retained[key] == value, (key, retained['path'])
assert not Path(retained['path']).is_symlink()
prior_join = json.loads(Path(r['retained_Rust_object']['producer_join']['path']).read_bytes())
assert prior_join['returncode'] == 0 and prior_join['direct_child_joined'] and prior_join['group_absent'] and prior_join['closed_streams']
# h990'''
assert d.count(needle)==1;d=d.replace(needle,reuse)
d=d.replace("results, artifacts = [], {}","results, artifacts = [], {'Rust-set-split': retained}")
d=d.replace("cap.write(A/'HEADROOM.json', facts)","cap.write(A/'HEADROOM.json', facts)\ncap.write(A/'REUSED-RUST-STAT-AND-PRODUCER.json',dict(retained=retained,producer=r['retained_Rust_object'],original_digest_authority_only=True,object_rehashed=False,Rust_recompiled=False))")
d=d.replace("for i, item in enumerate(r['commands'],1):","for i, item in enumerate(r['commands'],2):")
d=d.replace("cap.write(P/'ACTUAL-SET-SPLIT-RECEIPT.json',receipt)",'cap.write(Path('+repr(str(D/'ACTUAL-SET-SPLIT-BOUNDED-HEADER-CORRECTION-RECEIPT.json'))+'),receipt)')
d=d.replace("CPU6_released=True)\n    cap.write", "CPU6_released=True,reused_Rust_stat_and_producer=r['retained_Rust_object'],Rust_recompile=False,Rust_object_rehash=False,sole_bounded_header_correction=True)\n    cap.write")
ast.parse(d);driver=D/'run_remaining_once.NOT-RELEASED.py';put(driver,d)
rec(D/'EXECUTABLE-READY.NOT-RELEASED.json',dict(scope=__doc__,status='SOLE_HEADER_TRANSPORT_CORRECTION_SOURCE_READY_NO_EXECUTION',argv=['/usr/bin/taskset','-c','6','/home/holden/anaconda3/bin/python3','-I','-B',str(driver)],driver=ref(driver),recipe=ref(R),minimal_diff=ref(D/'EXACT-FIXTURE-HEADER-INCLUSION.patch'),new_macro_header=ref(H),source_headers=[ref(h) for h,n in headers],successful_Rust_retained=recipe['retained_Rust_object'],commands='Original failed02 GCC link with sole corrected fixture input filename, then exact original03/04/05/06 command objects; NO Rust compile. Five actual commands, four formerly pending.',product_sources_unchanged=[x for x in old['sources'] if '/candidate/' in x['path']],profile=old['profile'],expected_actual_pairs=498,first_failure=recipe['failure_history'],actual_outputs=None,execution_grant=None,CPU_reservation=None,qualification=old['qualification'],default_partial_native=None))
print(json.dumps(dict(handoff=ref(D/'EXECUTABLE-READY.NOT-RELEASED.json'),driver=ref(driver),recipe=ref(R),diff=ref(D/'EXACT-FIXTURE-HEADER-INCLUSION.patch'),commands=5,successful_Rust_digest_from_original_authority=obj['sha256'])))
