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
        (MEM, '#[no_mangle]\npub unsafe extern "C" fn mem_free_pages_pending_enqueue_result(', '#[no_mangle]\npub unsafe extern "C" fn mem_finish_free_pages_pending_body_result('),
    ]
    for path, begin, end in regions:
        text, binding = extract(path, begin, end)
        parts.append(text)
        bindings.append(binding)
    for prefix in ('const EINVAL:', 'const IHK_MC_PG_USER:', 'const PM_NONE:', 'const PM_PENDING_FREE:',
                   'const LIST_POISON1:', 'const LIST_POISON2:', 'type MemPendingFreeFn =', 'type MemPendingWarnFn ='):
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


EXPECTED = [
    ('empty','detach',0), ('empty','drain',0), ('one','detach',0), ('one','drain',1),
    ('three-order','detach',0), ('three-order','drain',3), ('later-invalid-setup','detach',0),
    ('later-invalid','drain',-22), ('later-invalid-repair','drain',2), ('missing-callback-setup','detach',0),
    ('missing-callback','drain',-22), ('missing-callback-recovery','drain',1), ('wrong-source-setup','detach',0),
    ('wrong-source','drain',-22), ('wrong-source-recovery','drain',1), ('repeated-setup','detach',0),
    ('repeated-detach','detach',-22), ('repeated-recovery','drain',1), ('repeated-drain','drain',-22),
    ('null-source','detach',-22), ('inactive-empty','detach',-22), ('alias-destination','detach',-22),
    ('mixed-destination-links','detach',-22), ('mixed-destination-state','detach',-22),
    ('two-head-isolation','detach',0),
    ('source-reuse','begin',0), ('source-reuse','enqueue',1), ('source-reuse','finish',1),
    ('two-head-isolation','drain',2), ('other-head-finish','finish',1),
]


def check_rows(result):
    assert [(r['case'],r['op'],r['rc']) for r in result] == EXPECTED
    for r in result:
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
    parser.add_argument('--rustc', required=True,
                        help='absolute Rust compiler selected by the build owner')
    parser.add_argument('--cc', required=True,
                        help='absolute C compiler selected by the build owner')
    args = parser.parse_args()
    out = output(args.output_dir)
    ledger = []
    inputs = (ABI, MEM, RUST, C, RUN, Path(__file__).resolve())
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
        for trait in ('Copy','Clone','Unpin','Send','Sync'):
            probe = out/(trait+'.rs')
            probe.write_text(base + '\nfn need<T:'+trait+'>(){} fn main(){need::<PendingFreeBatch>();}\n')
            rc,stdout,stderr = call(compile_rust+['--error-format=json',str(probe),'-o',str(out/trait)],out,'trait-'+trait,ledger)
            assert rc != 0 and not stdout
            diagnostics = [json.loads(line) for line in stderr.splitlines()]
            coded = [d for d in diagnostics if d.get('code')]
            assert coded and all(d['level']=='error' and d['code']['code']=='E0277' for d in coded), trait
            assert not any(d['level']=='warning' for d in diagnostics), trait
            assert all(trait in d.get('rendered','') and 'PendingFreeBatch' in d.get('rendered','') for d in coded), trait
            assert all(d.get('code') or d['message'].startswith(('aborting due to','For more information')) for d in diagnostics), trait
            traits[trait] = {'status':'EXPECTED_E0277_ONLY','diagnostic_count':len(coded)}
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
