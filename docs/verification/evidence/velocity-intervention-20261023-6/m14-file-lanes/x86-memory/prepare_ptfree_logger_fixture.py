"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One source-only original-C/Rust PTfree and range/effect logging fixture queue.
"""
from pathlib import Path
import ast, copy, hashlib, json, re
B=Path(__file__).resolve().parent
FROZEN=B/'next-clear-logging-source-only-1'
ALLOC=B/'next-pt-alloc-source-only-1'
P=B/'ptfree-logger-fixture-preparation-1'
ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as out:out.write(s)
def rec(p,d):put(p,json.dumps(d,indent=2,sort_keys=True)+'\n')
def fn(s,name,rust=False):
 pat=r'(?m)^'+(r'pub unsafe extern "C" fn ' if rust else r'(?:static |X86_MEMORY_PUBLIC_BRIDGE )void ')+r'\*?'+name+r'\([^;]+?\)\s*(?:->[^\n{]+)?\s*\{'
 m=re.search(pat,s);assert m,name
 i=s.index('{',m.start())+1;depth=1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 start=m.start()
 if rust:
  assert s[start-len('#[no_mangle]\n'):start]=='#[no_mangle]\n';start-=len('#[no_mangle]\n')
 return s[start:i]
assert not P.exists()
assert ref(FROZEN/'SOURCE-CLEAR-LOGGING-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json')['sha256']=='b527c00170f59f1f8b6236ef57f40088fcc626bb79c9863a3a4287e591797675'
held=json.loads((ALLOC/'ACTUAL-ALLOCATOR-WRAPPER-RECEIPT.json').read_bytes())
assert held['status']=='PASS_ACTUAL_PT_ALLOCATOR_WRAPPER_468_PAIRS_AND_REAL_ABI' and held['allocator_wrapper_pairs']==468
assert all(x['join']['returncode']==0 and x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in held['results'])
ports=['x86_pt_free_pages_bridge','x86_clear_effect_log_bridge','x86_clear_range_log_bridge']
basec=(FROZEN/'candidate/arch/x86_64/kernel/memory.c').read_text();baser=(FROZEN/'candidate/kernel/rust/x86_memory_helpers.rs').read_text()
cc=(ALLOC/'candidate/arch/x86_64/kernel/memory.c').read_text();rr=(ALLOC/'candidate/kernel/rust/x86_memory_helpers.rs').read_text()
for name in ports:assert fn(basec,name)==fn(cc,name) and fn(baser,name,True)==fn(rr,name,True),name
for rel,s in [('arch/x86_64/kernel/memory.c',cc),('kernel/rust/x86_memory_helpers.rs',rr)]:put(P/'candidate'/rel,s)
abi=B/'passed-six-provider-current-union-production-preparation-1/source/kernel/rust/abi.rs'
dbg=B/'batch-walkers-rss-flush-fixture-preparation-1/rust/actual-debug-type.inc'
constants=['PTL2_SHIFT','PTL3_SHIFT','X86_CLEAR_EFFECT_FREE_ANON','X86_CLEAR_EFFECT_XPMEM_KEEP','X86_CLEAR_EFFECT_FREE_UNMAPPED','X86_CLEAR_EFFECT_CHILD_FREE','X86_CLEAR_RANGE_LOG_SPLIT','X86_CLEAR_RANGE_LOG_LARGE_PHYS']
rust='#![no_std]\n#![allow(dead_code,unused_imports)]\n'+f'#[path="{abi}"] mod abi;\n'+'''use abi::{CInt,CULong,SizeT};
use core::ffi::c_void;
mod debug {
'''+dbg.read_text()+'''}
const _: () = {
 assert!(core::mem::size_of::<debug::Ddebug>()==32);
 assert!(core::mem::align_of::<debug::Ddebug>()==8);
 assert!(core::mem::offset_of!(debug::Ddebug,line_flags)==24);
};
'''
for n in constants:rust+=next(x for x in baser.splitlines(True) if x.startswith('const '+n+':'))
declarations=[next(x for x in baser.splitlines(True) if x.strip().startswith('fn kprintf(')),next(x for x in baser.splitlines(True) if x.strip().startswith('fn _ihk_mc_free_pages('))]
for n in ['x86_pt_free_pages_file','x86_pt_free_pages_line','x86_pt_free_pages_flag']:
 declarations.append(next(x for x in baser.splitlines(True) if x.strip().startswith('static '+n+':')))
sites=json.loads((FROZEN/'SOURCE-CLEAR-LOGGING-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json').read_bytes())['five_original_descriptor_sites']
for n in sites:declarations.append(next(x for x in baser.splitlines(True) if x.strip().startswith('static mut '+n+':')))
rust+='unsafe extern "C" {\n'+''.join(declarations)+'}\n'+'\n'.join(fn(baser,n,True) for n in ports)+'\n'
put(P/'fixture.rs',rust)
debug=(ROOT/'lib/include/ihk/debug.h').read_text();helpers=(ROOT/'arch/x86_64/kernel/include/arch-memory-helpers.h').read_text();arch=(ROOT/'arch/x86_64/kernel/include/arch-memory.h').read_text()
compiler=ROOT/'kernel/include/lwk/compiler-gcc.h'
closure=next(x for x in compiler.read_text().splitlines() if re.match(r'#define __aligned\(',x))+'\n'
closure+=debug[debug.index('struct ddebug {'):debug.index('} __aligned(8);')+len('} __aligned(8);')]+'\n'
for n in ['DDEBUG_NONE','DDEBUG_PRINT','DDEBUG_DEFAULT']:closure+=next(x for x in debug.splitlines(True) if x.startswith('#define '+n+' '))
closure+=debug[debug.index('#define dkprintf('):debug.index('#define BUG_ON(')]
for n in constants:
 source=arch if n.startswith('PTL') else helpers
 closure+=next(x for x in source.splitlines(True) if re.match(r'#define '+n+r'\s',x))
closure+=next(x for x in (ROOT/'lib/include/ihk/mm.h').read_text().splitlines(True) if re.match(r'#define IHK_MC_PG_KERNEL\s',x))
put(P/'EXACT-REAL-C-DEBUG-CLOSURE.inc',closure)
metadata=''
for n in ['x86_pt_free_pages_file','x86_pt_free_pages_line','x86_pt_free_pages_flag']:
 metadata+=next(x for x in cc.splitlines(True) if re.search(r'\b'+n+r'(?:\[\])?\s*=',x))
for n in sites:
 pattern=r'struct ddebug __aligned\(8\) __attribute__\(\(section\("__verbose"\)\)\)\n'+n+r' = \{[^}]+\};\n'
 m=re.search(pattern,cc);assert m,n;metadata+=m.group(0)
put(P/'EXACT-PRODUCT-C-METADATA.inc',metadata)
for n in ports:put(P/(n+'.original.inc'),fn(basec,n)+'\n')
fixture='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Real C debug macro/type; exact original providers and exact extracted Rust bodies.
 * Downstream page free is controlled: no physical allocation/free proof.
 */
#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "EXACT-REAL-C-DEBUG-CLOSURE.inc"
#include "EXACT-PRODUCT-C-METADATA.inc"
#define X86_MEMORY_PUBLIC_BRIDGE static
extern void rust_ptfree(void*,int) __asm__("x86_pt_free_pages_bridge");
extern void rust_effect(int,unsigned long,unsigned long,size_t) __asm__("x86_clear_effect_log_bridge");
extern void rust_range(int,void*,unsigned long*,unsigned long,unsigned long,unsigned long,int,int,unsigned long) __asm__("x86_clear_range_log_bridge");
static void x86_pt_free_pages_bridge(void*,int) __asm__("original_C_ptfree");
static void x86_clear_effect_log_bridge(int,unsigned long,unsigned long,size_t) __asm__("original_C_effect");
static void x86_clear_range_log_bridge(int,void*,unsigned long*,unsigned long,unsigned long,unsigned long,int,int,unsigned long) __asm__("original_C_range");
static struct free_event {void *ptr; int pages,flag; char *file; int line;} seen_free;
static unsigned free_calls,log_calls;
static int logger_return;
static char log_text[1024];
void _ihk_mc_free_pages(void *p,int n,int f,char *file,int line)
{ ++free_calls; seen_free=(struct free_event){p,n,f,file,line}; }
int kprintf(const char *format,...)
{
    va_list ap;va_start(ap,format);++log_calls;
    int n=vsnprintf(log_text,sizeof(log_text),format,ap);va_end(ap);
    assert(n>=0 && (unsigned)n<sizeof(log_text));return logger_return;
}
'''
# Include exact reference bodies, anchored to their original macro/callsite lines.
for n,line in [(ports[0],805),(ports[1],1375),(ports[2],1421)]:
 fixture+='#line '+str(line)+'\n'+fn(basec,n)+'\n'
# Inline the exact declarative bytes so __FILE__ has the same compilation-unit
# identity for original C, displaced selectors, and the static PTfree string.
fixture=fixture.replace('#include "EXACT-PRODUCT-C-METADATA.inc"',metadata.rstrip())
fixture+='''
extern struct ddebug __start___verbose[],__stop___verbose[];
static const char *const selector_func[]={"x86_clear_effect_log_bridge","x86_clear_effect_log_bridge","x86_clear_effect_log_bridge","x86_clear_effect_log_bridge","x86_clear_range_log_bridge"};
static const unsigned selector_line[]={1380,1384,1387,1391,1446};
static void select_flags(const unsigned flags[5])
{
    unsigned hits[5]={0};
    for(struct ddebug *d=__start___verbose;d<__stop___verbose;++d) {
        assert(d->fmt==NULL && strcmp(d->file,x86_pt_free_pages_file)==0);
        unsigned i;
        for(i=0;i<5;++i)if(d->line==selector_line[i] && strcmp(d->func,selector_func[i])==0)break;
        assert(i<5);d->flags=flags[i];assert(d->line==selector_line[i]);++hits[i];
    }
    for(unsigned i=0;i<5;++i)assert(hits[i]==2);
}
static void reset_log(void) { log_calls=0;strcpy(log_text,"<NO OUTPUT>"); }
static unsigned char observer_owned[8192] __attribute__((aligned(4096)));
int main(void)
{
    _Static_assert(sizeof(struct ddebug)==32 && _Alignof(struct ddebug)==8,"actual C descriptor ABI");
    unsigned flagsets[22][5]={{0}},configs=1;
    static const unsigned enabled[]={1,2,128,255};
    for(unsigned d=0;d<5;++d)for(unsigned v=0;v<4;++v)flagsets[configs++][d]=enabled[v];
    for(unsigned d=0;d<5;++d)flagsets[configs][d]=255;
    ++configs;assert(configs==22);
    unsigned zero[5]={0};select_flags(zero);
    static const int pages[]={INT_MIN,-2,-1,0,1,2,8,511,INT_MAX};
    void *pointers[]={NULL,observer_owned,observer_owned+4096,(void*)(uintptr_t)1,(void*)(uintptr_t)UINTPTR_MAX};
    unsigned free_pairs=0,effect_pairs=0,range_pairs=0;
    for(unsigned i=0;i<9;++i)for(unsigned j=0;j<5;++j) {
        unsigned before=free_calls,logs=log_calls;
        x86_pt_free_pages_bridge(pointers[j],pages[i]);struct free_event expected=seen_free;
        assert(free_calls==before+1);rust_ptfree(pointers[j],pages[i]);
        assert(free_calls==before+2 && log_calls==logs);
        assert(seen_free.ptr==expected.ptr && seen_free.pages==expected.pages && seen_free.flag==expected.flag);
        assert(strcmp(seen_free.file,expected.file)==0 && seen_free.line==expected.line);
        assert(seen_free.ptr==pointers[j] && seen_free.pages==pages[i] && seen_free.flag==0 && seen_free.line==807);
        assert(seen_free.file==x86_pt_free_pages_file);++free_pairs;
    }
    static const unsigned long values[]={0,0x123456789abcdef0UL,ULONG_MAX};
    static const int errors[]={0,-7,INT_MIN};
    static const int events[]={2,3,4,5,INT_MIN,INT_MAX};
    static const int range_events[]={8,9,INT_MIN,INT_MAX},levels[]={21,30,12,-1};
    for(unsigned cfg=0;cfg<configs;++cfg) {
        select_flags(flagsets[cfg]);
        for(unsigned event=0;event<6;++event)for(unsigned v=0;v<3;++v) {
            unsigned before=free_calls;logger_return=errors[v];reset_log();
            x86_clear_effect_log_bridge(events[event],values[v],values[2-v],values[v]);
            unsigned calls=log_calls;char expected[1024];strcpy(expected,log_text);
            unsigned should=event<4 && flagsets[cfg][event]!=0;
            assert(calls==should);reset_log();
            rust_effect(events[event],values[v],values[2-v],values[v]);
            assert(log_calls==calls && strcmp(log_text,expected)==0 && free_calls==before);++effect_pairs;
        }
        for(unsigned event=0;event<4;++event)for(unsigned level=0;level<4;++level)for(unsigned v=0;v<3;++v) {
            void *args=pointers[v];unsigned long *pte=(unsigned long*)pointers[4-v];
            unsigned before=free_calls;logger_return=errors[v];reset_log();
            x86_clear_range_log_bridge(range_events[event],args,pte,values[v],values[2-v],values[v],errors[v],levels[level],values[2-v]);
            unsigned calls=log_calls;char expected[1024];strcpy(expected,log_text);
            unsigned should=event==0 || (event==1 && flagsets[cfg][4]!=0);
            assert(calls==should);reset_log();
            rust_range(range_events[event],args,pte,values[v],values[2-v],values[v],errors[v],levels[level],values[2-v]);
            assert(log_calls==calls && strcmp(log_text,expected)==0 && free_calls==before);++range_pairs;
        }
    }
    select_flags(zero);
    assert(free_pairs==45 && effect_pairs==396 && range_pairs==1056);
    puts("PASS PTfree/loggers:1497 actual-original-C/Rust pairs (45 free,396 effect,1056 range);10 real selectors;downstream free controlled");
    return 0;
}
'''
put(P/'fixture.c',fixture)
# Combine the already prepared real-header assertion fragments, one actual C TU
# include. Allocator is held source context, not another468-pair invocation.
realabi='/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n'+f'#include "{P/"candidate/arch/x86_64/kernel/memory.c"}"\n'
for f in [B/'next-pt-free-source-only-1/FUTURE-REAL-ABI-FRAGMENT.NOT-QUEUED.c',FROZEN/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c']:
 text=f.read_text();start=text.index('_Static_assert');realabi+=text[start:]+'\n'
put(P/'real-header-ABI.c',realabi)
oldr=json.loads((ALLOC/'ALLOCATOR-FIXTURE-RECIPE.NOT-EXECUTED.json').read_bytes())
commands=[]
for old in oldr['commands']:
 x=copy.deepcopy(old);x['label']=x['label'].replace('alloc','pending');x['argv']=[a.replace(str(ALLOC),str(P)).replace('m14_pt_alloc_wrapper','m14_ptfree_logger').replace('fixture-alloc','fixture-pending') for a in x['argv']];x['cwd']=str(P);x['purpose']=__doc__+' '+x['label'];commands.append(x)
sourcepaths=[P/n for n in ['fixture.rs','fixture.c','EXACT-REAL-C-DEBUG-CLOSURE.inc','EXACT-PRODUCT-C-METADATA.inc','real-header-ABI.c','candidate/arch/x86_64/kernel/memory.c','candidate/kernel/rust/x86_memory_helpers.rs']]+[abi,dbg,FROZEN/'SOURCE-CLEAR-LOGGING-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json',FROZEN/'RETAINED-FIVE-DDEBUG-CALLSITE-WITNESS.json',ALLOC/'ACTUAL-ALLOCATOR-WRAPPER-RECEIPT.json',ALLOC/'root-actual-allocator-wrapper-1/RESULT.json',ROOT/'lib/include/ihk/debug.h',compiler]
recipe=dict(scope=__doc__,commands=commands,profile=oldr['profile'],sources=[ref(f) for f in sourcepaths],reused67_header_pins=oldr['reused67_header_pins'],expected_stdout={'execute-pending':'PASS PTfree/loggers:1497 actual-original-C/Rust pairs (45 free,396 effect,1056 range);10 real selectors;downstream free controlled\n'},expected_actual_pairs={'PTfree':45,'effect_logger':396,'range_logger':1056},expected_unique_ELF_Rust_T=ports,qualification='Exact three Rust callback bodies from frozenb527 and exact original C references. Real C debug macro/type/selectors and volatile Rust flag semantics. Controlled free endpoint and host vsnprintf: no real page-free/accounting/native formatter claim. Passed allocator held as coherent source/evidence context without repeating468.',held_allocator_receipt=ref(ALLOC/'ACTUAL-ALLOCATOR-WRAPPER-RECEIPT.json'),actual_outputs=None,execution_grant=None)
R=P/'PTFREE-LOGGER-FIXTURE-RECIPE.NOT-EXECUTED.json';rec(R,recipe)
d=(ALLOC/'run_actual_once.NOT-RELEASED.py').read_text()
d=d.replace('One bounded six-provider original-C/Rust reference cohort','One bounded three-callback PTfree/logging original-C/Rust reference cohort')
d=d.replace('ALLOCATOR-FIXTURE-RECIPE.NOT-EXECUTED.json',R.name).replace(ref(ALLOC/'ALLOCATOR-FIXTURE-RECIPE.NOT-EXECUTED.json')['sha256'],ref(R)['sha256']).replace(str(ALLOC),str(P))
d=d.replace("('fixture-alloc.o', 'fixture-alloc')","('fixture-pending.o', 'fixture-pending')").replace('actual-allocator-attempt-1','actual-pending-callback-attempt-1')
d=d.replace('PASS_ACTUAL_PT_ALLOCATOR_WRAPPER_468_PAIRS_AND_REAL_ABI','PASS_ACTUAL_PT_FREE_LOGGERS_1497_PAIRS_AND_REAL_ABI').replace('allocator_wrapper_pairs=468','pending_callback_pairs=1497').replace("actual_tested_ports=['x86_pt_alloc_pages_bridge']","actual_tested_ports=['x86_pt_free_pages_bridge','x86_clear_effect_log_bridge','x86_clear_range_log_bridge']").replace('controlled_downstream_allocator=True','controlled_downstream_free=True').replace('ACTUAL-ALLOCATOR-WRAPPER-RECEIPT.json','ACTUAL-PTFREE-LOGGER-RECEIPT.json').replace('actual_pairs=468','actual_pairs=1497')
ast.parse(d);D=P/'run_actual_once.NOT-RELEASED.py';put(D,d)
rec(P/'EXECUTABLE-READY.NOT-RELEASED.json',dict(scope=__doc__,status='ONE_QUEUE_READY_SOURCE_ONLY_NO_EXECUTION',argv=['/usr/bin/taskset','-c','6','/home/holden/anaconda3/bin/python3','-I','-B',str(D)],driver=ref(D),recipe=ref(R),profile=recipe['profile'],frozen_three_function_source=ref(FROZEN/'SOURCE-CLEAR-LOGGING-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json'),held_allocator_receipt=recipe['held_allocator_receipt'],context='Passed allocator source context; three function bodies byteequal frozenb527. No allocator468 replay or translator inclusion.',total_expected_pairs=1497,actual_outputs=None,execution_grant=None,CPU_reservation=None,coverage='22 independent/nonzero selector configurations; 45 signed-count/raw-pointer free forwarding pairs;396 effect and1056 range string/vararg/error/pointer cases;10 actual C selectors (original+displaced); real PUBLIC/fallback header ABIs.',limitations=recipe['qualification'],failure_history='Original937CWD338e retained, corrected9377b799 and fullproduction36dec passed; first unexpected new result STOP/expert, no author retry.',production_finalimage_native=None))
print(json.dumps(dict(handoff=ref(P/'EXECUTABLE-READY.NOT-RELEASED.json'),driver=ref(D),recipe=ref(R),commands=len(commands),expected_pairs=1497)))
