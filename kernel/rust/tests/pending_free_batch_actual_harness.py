#!/usr/bin/env python3
"""Candidate10: source-bound focused oracle with retained first-failure evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
ABI = ROOT / 'kernel/rust/abi.rs'
MEM = ROOT / 'kernel/rust/mem_helpers.rs'
RUST = ROOT / 'kernel/rust/tests/pending_free_batch_vectors.rs'
C = ROOT / 'kernel/rust/tests/pending_free_batch_vectors.c'
CMEM = ROOT / 'kernel/mem.c'
RUN = ROOT / 'kernel/rust/tests/run_equivalence.sh'
# The isolated build owner supplies absolute, immutable compiler paths.  Do not
# inherit rustup/cargo selection state: it would make the source fixture's
# compiler lane depend on the invoking developer account.
ENV = {k: os.environ[k] for k in ('PATH', 'HOME', 'USER') if k in os.environ}
ENV.update({'LANG': 'C', 'LC_ALL': 'C'})


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def js(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def extract(path, begin, end):
    source = path.read_text()
    assert source.count(begin) == 1 and source.count(end) == 1, (path, begin, end)
    start = source.index(begin)
    stop = source.index(end, start)
    text = source[start:stop]
    return text, {'path': str(path.relative_to(ROOT)), 'begin': begin, 'end': end,
                  'start': start, 'end_offset': stop, 'sha256': hashlib.sha256(text.encode()).hexdigest()}


def prelude():
    parts = ['#![allow(dead_code, unsafe_op_in_unsafe_fn)]\n'
             'use core::marker::{PhantomData,PhantomPinned};\nuse core::pin::Pin;\n'
             'use core::ptr::{null_mut,write_volatile};\n'
             'use core::ffi::c_void;\n'
             'use core::mem::{size_of,align_of,offset_of};\n']
    bindings = []
    regions = [
        (ABI, 'pub type CInt = i32;', 'pub const MCK_RLIM_MAX'),
        (ABI, '#[repr(C)]\n#[derive(Clone, Copy)]\npub struct AbiListHead', '#[repr(C)]\n#[derive(Clone, Copy)]\npub struct AbiRbNode'),
        (ABI, '#[repr(C)]\n#[derive(Clone, Copy)]\npub struct IhkAtomic {', '#[repr(C)]\n#[derive(Clone, Copy)]\npub struct IhkSpinlock'),
        (MEM, '#[repr(C)]\npub struct MemPage', '#[repr(C)]\npub struct KmallocTrackAddrEntry'),
        (MEM, '#[inline(always)]\nunsafe fn list_add(', '#[inline(always)]\nunsafe fn kmalloc_track_hash('),
        (MEM, '#[derive(Clone, Copy, PartialEq, Eq)]\nenum PendingFreeBatchState', '#[no_mangle]\npub extern "C" fn round_up'),
        (MEM, '#[no_mangle]\npub unsafe extern "C" fn mem_begin_free_pages_pending_result(', '#[no_mangle]\npub unsafe extern "C" fn mem_begin_free_pages_pending_body_result('),
        (MEM, '#[no_mangle]\npub unsafe extern "C" fn mem_begin_free_pages_pending_body_result(', '#[no_mangle]\npub unsafe extern "C" fn mem_begin_free_pages_pending_public_body_result('),
        (MEM, '#[no_mangle]\npub unsafe extern "C" fn mem_free_pages_pending_enqueue_result(', '#[no_mangle]\npub unsafe extern "C" fn mem_finish_free_pages_pending_body_result('),
        (MEM, '#[no_mangle]\npub unsafe extern "C" fn mem_mckernel_free_pages_body_result(', '#[no_mangle]\npub unsafe extern "C" fn mem_mckernel_free_pages_public_body_result('),
    ]
    for path, begin, end in regions:
        text, binding = extract(path, begin, end)
        parts.append(text)
        bindings.append(binding)
    for prefix in ('const EINVAL:', 'const PAGE_SHIFT:', 'const PAGE_SIZE:', 'const IHK_MC_PG_USER:', 'const PM_NONE:', 'const PM_PENDING_FREE:',
                   'const LIST_POISON1:', 'const LIST_POISON2:', 'type MemPendingFreeFn =', 'type MemPendingWarnFn =',
                   'type MemBeginFreePagesPendingFn =', 'type MemVirtToPhysFn =', 'type MemPhysToPageFn =',
                   'type MemFreeInAllocatorFn =', 'type MemVoidFn ='):
        lines = [line for line in MEM.read_text().splitlines(True) if line.startswith(prefix)]
        assert len(lines) == 1, (prefix, len(lines))
        parts.append(lines[0])
        bindings.append({'path': str(MEM.relative_to(ROOT)), 'line_prefix': prefix,
                         'sha256': hashlib.sha256(lines[0].encode()).hexdigest()})
    text, binding = extract(MEM, '    assert!(size_of::<MemPage>()', '    assert!(size_of::<KmallocTrackAddrEntry>()')
    parts.append('const _: () = {\n' + text + '};\n')
    bindings.append(binding)
    return ''.join(parts), bindings


def output(arg):
    if arg is None:
        return Path(tempfile.mkdtemp(prefix='mckernel-pending-candidate10-'))
    path = Path(arg).resolve()
    if path.exists() and any(path.iterdir()):
        raise RuntimeError('refusing nonempty output ' + str(path))
    path.mkdir(parents=True, exist_ok=True)
    return path


def call(argv, out, label, ledger, timeout=120):
    entry = {'label': label, 'argv': [str(x) for x in argv], 'cwd': str(ROOT), 'environment': ENV,
             'timeout_seconds': timeout, 'started_ns': time.time_ns()}
    ledger.append(entry)
    js(out / 'commands.json', ledger)
    with (out / (label + '.stdout')).open('w') as stdout, (out / (label + '.stderr')).open('w') as stderr:
        try:
            result = subprocess.run(entry['argv'], cwd=ROOT, env=ENV, stdout=stdout, stderr=stderr, timeout=timeout)
            entry['returncode'] = result.returncode
        except subprocess.TimeoutExpired:
            entry['timeout'] = True
            raise
        finally:
            stdout.flush()
            stderr.flush()
            entry['finished_ns'] = time.time_ns()
            entry['stdout_sha256'] = digest(out / (label + '.stdout'))
            entry['stderr_sha256'] = digest(out / (label + '.stderr'))
            js(out / 'commands.json', ledger)
    return result.returncode, (out / (label + '.stdout')).read_text(), (out / (label + '.stderr')).read_text()


def success(argv, out, label, ledger):
    rc, stdout, stderr = call(argv, out, label, ledger)
    assert rc == 0, '{} failed with {}'.format(label, rc)
    return stdout


def rows(text):
    return [json.loads(line[5:]) for line in text.splitlines() if line.startswith('JSON|')]


def extract_after(path, begin, end):
    source = path.read_text()
    assert source.count(begin) == 1, (path, begin)
    start = source.index(begin)
    stop = source.index(end, start)
    text = source[start:stop]
    return text, {'path': str(path.relative_to(ROOT)), 'begin': begin, 'end': end,
                  'start': start, 'end_offset': stop, 'sha256': hashlib.sha256(text.encode()).hexdigest()}


def exact_c_partial_release_control():
    result, result_binding = extract_after(
        CMEM,
        'int mem_finish_free_pages_pending_result(struct list_head *pendings,\n\t\tmem_pending_free_fn_t free_fn)\n{',
        'int mem_finish_free_pages_pending_body_result(struct list_head *pendings,')
    fallback, fallback_binding = extract_after(
        CMEM, 'void finish_free_pages_pending(void)\n{', '#endif\n\nstatic struct ihk_mc_pa_ops allocator')
    support = r'''
#include <assert.h>
#include <setjmp.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#define EINVAL 22
#define PM_NONE 0
#define PM_PENDING_FREE 1
#define IHK_MC_PG_USER 1
struct list_head { struct list_head *next, *prev; };
struct page { struct list_head list; int mode; unsigned long phys; int offset; };
typedef void (*mem_pending_free_fn_t)(unsigned long, int, int);
struct cpu_local { struct list_head pending_free_pages; };
static struct cpu_local current_cpu;
static int callbacks, panics;
static jmp_buf panic_return;
static void list_del(struct list_head *entry) { entry->prev->next=entry->next; entry->next->prev=entry->prev; }
static void *phys_to_virt(unsigned long phys) { return (void *)(uintptr_t)phys; }
#define page_to_phys(page) ((page)->phys)
static void __mckernel_free_pages_in_allocator(void *ignored, int npages, int user) { (void)ignored; assert(npages==1 && user==1); callbacks++; }
static struct cpu_local *get_this_cpu_local_var(void) { return &current_cpu; }
static void panic(const char *ignored) { (void)ignored; panics++; longjmp(panic_return, 1); }
static void result_callback(unsigned long phys, int npages, int user) { assert(phys==0x1000 && npages==1 && user==1); callbacks++; }
static void init_two(void) { static struct page pages[2]; struct list_head *h=&current_cpu.pending_free_pages; pages[0].list.next=&pages[1].list; pages[0].list.prev=h; pages[1].list.next=h; pages[1].list.prev=&pages[0].list; pages[0].mode=PM_PENDING_FREE; pages[1].mode=PM_NONE; pages[0].phys=0x1000; pages[1].phys=0x3000; pages[0].offset=1; pages[1].offset=2; h->next=&pages[0].list; h->prev=&pages[1].list; callbacks=0; panics=0; }
'''
    controls = r'''
int main(void) {
    init_two();
    assert(mem_finish_free_pages_pending_result(&current_cpu.pending_free_pages, result_callback) == -EINVAL);
    assert(callbacks == 1);
    init_two();
    if (!setjmp(panic_return)) { finish_free_pages_pending(); assert(!"fallback must panic after first callback"); }
    assert(callbacks == 1 && panics == 1);
    puts("PASS_EXACT_C_PARTIAL_RELEASE_CONTROLS");
    return 0;
}
'''
    return support + '\n' + result + '\n' + fallback + '\n' + controls, [result_binding, fallback_binding]


def source_only_admission():
    """Layer-A parser/source gate.  It deliberately performs no build or run."""
    import ast
    ast.parse(Path(__file__).read_text(), filename=str(Path(__file__)))
    mem = MEM.read_text()
    c_mem = CMEM.read_text()
    required = (
        'struct PendingInventoryLease', 'struct ValidatedPendingInventory',
        'validate_pending_inventory_metadata', 'validate_pending_inventory_ring',
        'try_reanchor_into', 'reanchor_into', 'drain_validated_pending_inventory',
        'callback_args.add(index)', 'lease.descriptor_index(node)',
    )
    assert all(item in mem for item in required), required
    cases = ('missing','extra','duplicate','foreign','link','mode','negative-count','count',
             'alignment','range','end-overflow','overlap','destination')
    assert all(('"' + case + '"') in RUST.read_text() for case in cases), cases
    generated_c, c_bindings = exact_c_partial_release_control()
    assert 'mem_finish_free_pages_pending_result' in generated_c
    assert 'finish_free_pages_pending' in generated_c
    assert 'callbacks == 1 && panics == 1' in generated_c
    assert 'descriptor_len > CInt::MAX as usize' in mem
    assert 'mem_mckernel_free_pages_body_result' in mem and 'free_in_allocator(va, npages, is_user)' in mem
    assert "'const PAGE_SHIFT:'" in Path(__file__).read_text()
    assert "'const PAGE_SIZE:'" in Path(__file__).read_text()
    vectors = RUST.read_text()
    for evidence in ('DISPATCH_NO_PAGE', 'lease_snapshot', 'token_snapshot',
                     'descriptor_len', 'callback_args_ptr', 'callback_entries',
                     'assert_eq!(callbacks(),"[[65261,2,1]]")',
                     'assert_eq!(w.links(&w.s),"{\\"next\\":10,\\"prev\\":10}")',
                     'assert_eq!(w.links(&w.p[0].list),"{\\"next\\":1,\\"prev\\":1}")',
                     'assert_eq!(w.p[0].mode,PM_PENDING_FREE)',
                     'assert_eq!(w.p[0].offset,2)',
                     'b.lease.is_none()',
                     'DISPATCH_PAGE=null_mut();DISPATCH_NO_PAGE=true'):
        assert evidence in vectors, evidence
    assert '\\\"lease\\\":null' in C.read_text()
    rust_body, rust_binding = extract(
        MEM, '#[no_mangle]\npub unsafe extern "C" fn mem_finish_free_pages_pending_result(',
        '#[no_mangle]\npub unsafe extern "C" fn mem_finish_free_pages_pending_body_result(')
    assert 'free_fn' in rust_body
    return {'status': 'PASS_SOURCE_ONLY_M03_ADMISSION', 'hashes': {
        str(MEM.relative_to(ROOT)): digest(MEM), str(CMEM.relative_to(ROOT)): digest(CMEM),
        str(RUST.relative_to(ROOT)): digest(RUST), str(C.relative_to(ROOT)): digest(C),
    }, 'exact_legacy_extracts': [rust_binding] + c_bindings}


EXPECTED = [
    ('empty','detach',0), ('empty','drain',0), ('one','detach',0), ('one','drain',1),
    ('three-order','detach',0), ('three-order','drain',3), ('later-invalid-setup','detach',0),
    ('later-invalid','drain',-22), ('later-invalid-repair','drain',2), ('missing-callback-setup','detach',0),
    ('missing-callback','drain',-22), ('missing-callback-recovery','drain',1), ('wrong-source-setup','detach',0),
    ('wrong-source','drain',-22), ('wrong-source-recovery','drain',1), ('repeated-setup','detach',0),
    ('repeated-detach','detach',-22), ('repeated-recovery','drain',1), ('repeated-drain','drain',-22),
    ('null-source','detach',-22), ('inactive-empty','detach',-22), ('alias-destination','detach',-22),
    ('mixed-destination-links','detach',-22), ('mixed-destination-state','detach',-22),
    ('conflicting-begin','begin',-22), ('nested-begin-first','begin',0),
    ('nested-begin-second','begin',-22), ('begin-panic-bridge','begin-body',-22),
    ('malformed-active-empty','detach',-22), ('malformed-boundary-prev','detach',-22),
    ('malformed-boundary-next','detach',-22),
    ('two-head-isolation','detach',0),
    ('source-reuse','begin',0), ('source-reuse','enqueue',1), ('source-reuse','finish',1),
    ('two-head-isolation','drain',2), ('other-head-finish','finish',1),
]


def check_rows(result):
    assert [(r['case'],r['op'],r['rc']) for r in result] == EXPECTED
    for r in result:
        assert r.get('panic', 0) == (1 if r['case'] == 'begin-panic-bridge' else 0), r['case']
        if r['rc'] < 0:
            assert r['before'] == r['after'] and r['callbacks'] == [], r['case']
        if r['case'] == 'two-head-isolation':
            assert r['before']['other'] == r['after']['other']
            assert r['before']['pages'][3] == r['after']['pages'][3]
        if r['case'] == 'source-reuse':
            assert r['before']['batch']['state'] == 1
            assert r['before']['batch'] == r['after']['batch']
            assert r['before']['pages'][:2] == r['after']['pages'][:2]
            assert r['before']['other'] == r['after']['other']
            assert r['before']['pages'][3] == r['after']['pages'][3]
        for old, new in zip(r['before']['pages'], r['after']['pages']):
            for field in ('hash','phys','count','mapped','pgshift'):
                assert old[field] == new[field], (r['case'], field)
        wanted = []
        if r['op'] in ('drain','finish') and r['rc'] > 0:
            wanted = [[100+i,i+1,1] for i in range(r['rc'])]
            if r['case'] == 'other-head-finish':
                wanted = [[103,4,1]]
            if r['case'] == 'source-reuse':
                wanted = [[102,7,1]]
        assert r['callbacks'] == wanted, r['case']
    failed = next(r for r in result if r['case']=='later-invalid')
    recovered = next(r for r in result if r['case']=='later-invalid-repair')
    repaired = json.loads(json.dumps(failed['after']))
    repaired['pages'][1]['mode'] = 1
    assert recovered['before'] == repaired
    for first,second in [('wrong-source','wrong-source-recovery'),('missing-callback','missing-callback-recovery')]:
        assert next(r for r in result if r['case']==first)['after'] == next(r for r in result if r['case']==second)['before']
    retained = next(i for i,r in enumerate(result) if r['case']=='two-head-isolation')
    for previous, current in zip(result[retained:retained+4], result[retained+1:retained+5]):
        assert previous['after'] == current['before']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir')
    parser.add_argument('--static-admission', action='store_true',
                        help='parse/source inspection only; no compiler or fixture execution')
    parser.add_argument('--rustc',
                        help='absolute Rust compiler selected by the build owner')
    parser.add_argument('--cc',
                        help='absolute C compiler selected by the build owner')
    args = parser.parse_args()
    if args.static_admission:
        print(json.dumps(source_only_admission(), sort_keys=True))
        return
    if not args.rustc or not args.cc:
        parser.error('--rustc and --cc are required unless --static-admission is selected')
    out = output(args.output_dir)
    ledger = []
    inputs = (ABI, MEM, CMEM, RUST, C, RUN, Path(__file__).resolve())
    try:
        # Freeze all sources before the first syntax, compiler, or fixture execution.
        frozen = out / 'inputs'
        frozen.mkdir()
        for path in inputs:
            shutil.copyfile(path, frozen / path.name)
        identities = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
        js(out/'input-manifest.json', {'inputs': identities, 'environment': ENV, 'platform': platform.platform(),
                                     'harness_argv': __import__('sys').argv, 'cwd': str(Path.cwd())})
        success(['bash','-n',str(RUN)],out,'bash-syntax',ledger)
        # Exercise both destination modes without executing the focused suite twice.
        default = output(None)
        assert default.is_dir() and not any(default.iterdir())
        explicit = output(str(out/'explicit-output-control'))
        assert explicit.is_dir() and not any(explicit.iterdir())
        js(out/'output-modes.json',{'default':str(default),'explicit':str(explicit),'status':'PASS'})
        base, bindings = prelude()
        fixture = RUST.read_text()
        actual = out / 'actual_extracted_and_vectors.rs'
        actual.write_text(base + '\n// fixture appended verbatim\n' + fixture)
        js(out/'source-extraction.json',{'items':bindings,'inputs':identities})
        rustc_arg, cc_arg = Path(args.rustc), Path(args.cc)
        assert rustc_arg.is_absolute() and cc_arg.is_absolute(), 'compiler argv must be absolute'
        # Keep the owner-reviewed logical argv; the immutable-image owner binds
        # the compiler bytes before starting this harness.
        rustc = rustc_arg
        cc = cc_arg
        assert rustc.is_file() and cc.is_file()
        success([str(rustc),'--version','--verbose'],out,'rustc-identity',ledger)
        success([str(cc),'--version'],out,'cc-identity',ledger)
        rb = out/'actual'
        compile_rust = [str(rustc),'--edition=2021','-D','warnings']
        success(compile_rust+[str(actual),'-o',str(rb)],out,'rust-compile',ledger)
        rsout = success([str(rb)],out,'rust-run',ledger)
        assert 'CONTROL|callback-borrow-and-capacity-observed' in rsout
        rs = rows(rsout)
        cb = out/'reference-c'
        success([str(cc),'-std=c11','-Wall','-Wextra','-Werror',str(C),'-o',str(cb)],out,'c-compile',ledger)
        cs = rows(success([str(cb)],out,'c-run',ledger))
        exact_c, exact_c_bindings = exact_c_partial_release_control()
        exact_c_path = out/'exact-c-partial-release-controls.c'
        exact_c_path.write_text(exact_c)
        exact_c_bin = out/'exact-c-partial-release-controls'
        success([str(cc),'-std=gnu11','-Wall','-Wextra','-Werror',str(exact_c_path),'-o',str(exact_c_bin)],out,'exact-c-partial-compile',ledger)
        assert success([str(exact_c_bin)],out,'exact-c-partial-run',ledger).strip() == 'PASS_EXACT_C_PARTIAL_RELEASE_CONTROLS'
        check_rows(rs)
        check_rows(cs)
        assert rs == cs, 'Rust and C complete computed snapshots differ'
        # This mutation invokes the extracted production legacy finish loop, which
        # releases page 100 before discovering invalid page 101 on the retained ring.
        needle = 'let rc=drain_pending_free_batch(s,self.b.as_mut(),if callback{Some(free_page)}else{None});'
        replacement = 'let rc=if name=="later-invalid" {mem_finish_free_pages_pending_result(&raw mut self.b.as_mut().get_unchecked_mut().head,Some(free_page))}else{drain_pending_free_batch(s,self.b.as_mut(),if callback{Some(free_page)}else{None})};'
        assert fixture.count(needle) == 1
        mutant = out/'partial-release-mutant.rs'
        mutant.write_text(base + '\n' + fixture.replace(needle,replacement))
        mb = out/'partial-release-mutant'
        success(compile_rust+[str(mutant),'-o',str(mb)],out,'mutant-compile',ledger)
        rc,stdout,stderr = call([str(mb)],out,'mutant-run',ledger)
        mr = rows(stdout)
        assert rc != 0 and 'PARTIAL_RELEASE_DETECTED case=later-invalid' in stderr
        bad = mr[-1]
        assert bad['case']=='later-invalid' and bad['rc']==-22 and bad['callbacks']==[[100,1,1]]
        assert bad['before']['pages'][0]['mode']==1 and bad['after']['pages'][0]['mode']==0
        assert bad['after']['pages'][0]['list']=={'next':90,'prev':91}
        assert bad['before']['pages'][1]['mode']==bad['after']['pages'][1]['mode']==0
        assert mr[:-1] == rs[:len(mr)-1], 'mutant failed before target case'
        traits = {}
        for target in ('PendingFreeBatch','PendingInventoryLease','ValidatedPendingInventory'):
            for trait in ('Copy','Clone','Unpin','Send','Sync'):
                probe = out/(target+'-'+trait+'.rs')
                probe.write_text(base + '\nfn need<T:'+trait+'>(){} fn main(){need::<'+target+'>();}\n')
                rc,stdout,stderr = call(compile_rust+['--error-format=json',str(probe),'-o',str(out/(target+'-'+trait))],out,'trait-'+target+'-'+trait,ledger)
                assert rc != 0 and not stdout
                diagnostics = [json.loads(line) for line in stderr.splitlines()]
                coded = [d for d in diagnostics if d.get('code')]
                assert coded and all(d['level']=='error' and d['code']['code']=='E0277' for d in coded), trait
                assert not any(d['level']=='warning' for d in diagnostics), trait
                assert all(trait in d.get('rendered','') and target in d.get('rendered','') for d in coded), trait
                assert all(d.get('code') or d['message'].startswith(('aborting due to','For more information')) for d in diagnostics), trait
                traits[target+'-'+trait] = {'status':'EXPECTED_E0277_ONLY','diagnostic_count':len(coded)}
        assert identities == {str(p.relative_to(ROOT)):digest(p) for p in inputs}, 'input changed during execution'
        success(['git','diff','--check'],out,'diff-check',ledger)
        js(out/'manifest.json',{'status':'PASS_PENDING_FREE_BATCH_FOCUSED_EQUIVALENCE_ONLY',
                              'scope':'source fixture only; no runtime or production credit',
                              'inputs':identities,'commands':ledger,'expected':EXPECTED,
                              'rust_rows':rs,'c_rows':cs,'mutant_detected':bad,'trait_negatives':traits})
        print('PASS_PENDING_FREE_BATCH_FOCUSED_EQUIVALENCE_ONLY output='+str(out))
    except Exception as error:
        js(out/'failure.json',{'status':'FAIL','error':repr(error),'commands':ledger})
        raise
    finally:
        js(out/'artifact-manifest.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='artifact-manifest.json'})


if __name__ == '__main__':
    main()
