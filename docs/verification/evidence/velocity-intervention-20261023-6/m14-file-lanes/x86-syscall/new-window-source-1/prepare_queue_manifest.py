"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only generation of exact ordinary-queue commands, without executing any.
"""
from pathlib import Path
import hashlib,json,re
D=Path(__file__).resolve().parent
S=D/'fixture-source'; O=D/'output-1'
def pin(path):
 p=Path(path);b=p.read_bytes();return {'path':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
pre=D.parent/'group-pending-actual-consumer-preparation-1/EXACT-GROUP-PENDING-ACTUAL-CONSUMER.NOT-GRANTED.json'
old=json.loads(pre.read_text())
cargv=old['commands'][1]['argv'][:]
cargv[cargv.index('-c')+1]=str(S/'wakeup-compare.c')
cargv[cargv.index('-o')+1]=str(O/'wakeup-C.o')
rust=old['actual_compiler']['path']
commands=[
 {'name':'00-exact-Rust-tail-real-ABI-and-byte-provider-genuine-HOST-runtime','argv':[rust,'--crate-name','f06_wakeup_host_1','--crate-type','staticlib','--edition=2021','-C','panic=abort','-C','opt-level=2','-C','codegen-units=1','-C','no-redzone=yes','--print','native-static-libs',str(S/'wakeup_actual.rs'),'-o',str(O/'libf06_wakeup_host_1.a')]},
 {'name':'01-real-header-original-C-and-public-Rust-consumer','argv':cargv},
 {'name':'02-genuine-HOST-runtime-link','argv':['/usr/bin/gcc-9',str(O/'wakeup-C.o'),str(O/'libf06_wakeup_host_1.a'),'-lgcc_s','-lutil','-lrt','-lpthread','-lm','-ldl','-lc','-o',str(O/'wakeup-compare')]},
 {'name':'03-original-C-Rust10368-parity-comparisons','argv':[str(O/'wakeup-compare')]},
 {'name':'04-unique-public-provider-symbols','argv':['/usr/bin/nm','-g',str(O/'wakeup-compare')]},
 {'name':'05-genuine-HOST-runtime-symbols','argv':['/usr/bin/nm','-C','--defined-only',str(O/'wakeup-compare')]},
]
scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
profile={'jobs':1,'affinity':[6],'AS_bytes':2<<30,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE_bytes':32<<20,'STACK_bytes':2<<20,'NOFILE':256,'CORE':0,'RUST_MIN_STACK':'2097152','root':False,'guest':False,'Docker':False,'network':False}
headers=old['frozen_actual_header_dependencies']
manifest={'scope':scope,'status':'SOURCE_ONLY_NOT_GRANTED_NOT_RUN','physical_clearance':None,'ordinary_slot_grant':None,'compiler':pin(rust),'commands':commands,'profile':profile,'cwd':str(D),'output_root':str(O),'capture_root':str(D/'actual-wakeup-capture-1'),'expected_stdout':'PASS actual_C_Rust_wakeup cases=10368 ABI=30 ordered_callbacks=1 siginfo_bytes=128 release_once=1\n','expected_native_static_libs':['-lgcc_s','-lutil','-lrt','-lpthread','-lm','-ldl','-lc'],'expected_symbol_T':['arch_do_kill_wakeup_result','fixture_wakeup_abi','__inline_memset'],'sources':[pin(p) for p in sorted(S.iterdir()) if p.is_file()],'canonical_bindings':[pin('arch/x86_64/kernel/syscall.c'),pin('kernel/rust/syscall_policy.rs'),pin('kernel/rust/abi.rs'),pin('kernel/rust/string.rs'),pin('kernel/rust/debug.rs')],'frozen_actual_header_dependencies':headers,'tools':[pin('/usr/bin/gcc-9'),pin('/usr/bin/nm')],'predecessor':pin(pre),'capacity':'Root remeasure aggregate <=7 jobs/22.2973GiB and host/scratch floors before admission; one ordinary CPU6 slot requires free CPU6. No source-only statement clears COPY7.','execution_requirements':['Root owned capture/retirement controller; stop first unexpected result with complete stdout/stderr/status and no automatic replay','Pin all inputs; only frozen header table reused; source/header mismatch stops instead of refresh','Reject warnings except unique expected native-static-libs report; require report matches exact seven link flags before link','Require every child joined, streams closed and owned group absent before slot release','Fresh output/capture paths; never overwrite failed attempt','Genuine std HOST/core runtime; no homemade panic provider or raw privileged instruction','Root may bind actual existing helper via separate ordinary queue grant; this manifest does not execute or claim release'],'controls':'Only scheduler, recursive do_kill, vector/IPI and release endpoints controlled; actual private Rust body, actual abi.rs, byte-extracted real Rust __inline_memset and Ddebug. C reference byte-extracted unchanged and real headers. Debug descriptors toggled through actual __verbose section. No live scheduler/IRQ/reference/native proof.','case_dimensions':{'caller_modes':['null','self','other'],'signals':[12,18,9],'ptracecont':[0,1],'doint':[0,1],'blocked':[False,True],'status':[1,32,64,2],'stop_wakeup_result':[0,1,-11],'mutation':['none','successful_stop_wake_switches_process','notify_switches_process_and_CPU_IPI_changes_status'],'enqueue_rc':[0,-12],'debug':[False,True]},'expected_cases':10368,'ABI_values':30,'actual_compile':None,'actual_cases':None,'native':None,'default_link':None}
(D/'EXACT-WAKEUP-QUEUE.NOT-GRANTED.json').write_text(json.dumps(manifest,indent=2)+'\n')
(D/'FIXTURE-READY.json').write_text(json.dumps({'scope':scope,'status':'SOURCE_ONLY_COMPARISON_FIXTURE_READY_NOT_RUN','manifest':pin(D/'EXACT-WAKEUP-QUEUE.NOT-GRANTED.json'),'expected_cases':10368,'expected_ABI_values':30,'actual_cases':None,'holds':['COPY7 physical clearance','ordinary CPU6/job grant','independent callback/lifetime review before canonical integration','default link/native evidence']},indent=2)+'\n')
