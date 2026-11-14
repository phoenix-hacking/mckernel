#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

One bounded ordinary production-header ABI/consumer link check and exact staging.
No canonical/image/root/Docker/container/full-TU/full-image modification or build.
"""
from pathlib import Path
import hashlib
import json
import os
import shlex
import subprocess
import sys

REPO = Path('/home/holden/mckernel')
OUT = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1')
BASE = Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')
SOURCE = BASE / 'source-materialization-1/materialized-source'
BUILD = BASE / 'full-image-attempt-1/owner-work/output/build'
EV = BASE / 'full-image-attempt-1/owner-work/evidence'
PRIOR = REPO / 'docs/verification/evidence/rust-idle-runqueue-scan-20261022-1'
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
SYMBOL = 'sched_idle_runqueue_has_running_result'
IMAGE_SHA = '10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2'


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def item(text, marker):
    begin = text.index(marker)
    opening = text.index('{', begin)
    depth = 0
    for end in range(opening, len(text)):
        if text[end] == '{':
            depth += 1
        elif text[end] == '}':
            depth -= 1
            if depth == 0:
                return text[begin:end + 1]
    raise RuntimeError('unbalanced selected source item')


def main():
    need(os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {6}, 'ordinary CPU6 grant required')
    runroot = OUT / 'actual-check-1'
    runroot.mkdir()
    commands = []
    def run(label, argv):
        commands.append(dict(scope=SCOPE, label=label, argv=argv))
        (runroot / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                timeout=35, env=dict(os.environ, RUST_MIN_STACK='2097152'))
        for stream in ('stdout', 'stderr'):
            (runroot / (label + '.' + stream)).write_text(getattr(result, stream))
        (runroot / (label + '.status')).write_text(str(result.returncode) + '\n')
        need(result.returncode == 0, 'first failed ordinary command: ' + label)
        return result.stdout

    result = dict(scope=SCOPE, status='FAIL_PRESERVE_ALL', current_image_sha256=IMAGE_SHA,
                  current_image_modified=False, canonical_source_modified=False,
                  production_default_link_proven=False, native_idle_port_proven=False)
    try:
        mapping = json.loads((PRIOR / 'source-map.json').read_text())['sources']
        provenance = json.loads((EV / 'provenance.json').read_text())['source']
        rows = []
        for row in mapping:
            rel = row['path']
            old = (SOURCE / rel).read_bytes()
            new = Path(row['postimage']).read_bytes()
            need(sha(old) == row['preimage_sha256'] == provenance['repository_files'][rel]
                 == provenance['materialized_repository_files'][rel], 'exact selected source preimage mismatch: ' + rel)
            need(sha(new) == row['postimage_sha256'], 'exact independently reviewed postimage mismatch: ' + rel)
            for folder, raw in [('preimage', old), ('postimage', new)]:
                path = OUT / folder / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as stream:
                    stream.write(raw)
            rows.append(dict(path=rel, preimage_sha256=sha(old), postimage_sha256=sha(new)))
        result['staged_exact_three_source_delta'] = rows
        result['current_image_source_has_idle_port'] = False
        for inventory in ('symbols.txt', 'rust-object-symbols.txt'):
            text = (EV / inventory).read_text()
            need(not any(line.split()[-1:] == [SYMBOL] for line in text.splitlines()), 'port already linked unexpectedly')
        actual_process = BUILD / 'kernel/CMakeFiles/mckernel.img.dir/process.c.o'
        caller_symbols = run('current-process-symbols', ['/usr/bin/nm', '-u', str(actual_process)])
        need(SYMBOL not in caller_symbols, 'current C object unexpectedly imports new port')
        compile_commands = json.loads((EV / 'artifacts/compile_commands.json').read_text())
        production = next(row for row in compile_commands if row['file'] == '/src/kernel/process.c')
        original = shlex.split(production['command'])
        need('-DMCKERNEL_RUST_PROCESS_HELPERS' in original, 'default process Rust selection missing')
        cmake = (SOURCE / 'kernel/CMakeLists.txt').read_text()
        need('option(ENABLE_RUST_KERNEL "Enable Rust code in the McKernel image" ON)' in cmake,
             'production default Rust image option is not ON')
        post = OUT / 'postimage'
        process = (post / 'kernel/process.c').read_text()
        rust = (post / 'kernel/rust/sched_helpers.rs').read_text()
        start = process.index('#ifdef MCKERNEL_RUST_PROCESS_HELPERS', process.index(
            's = ihk_mc_spinlock_lock(&v->runq_lock);', process.index('void idle(')))
        end = process.index('\n#endif', start) + len('\n#endif')
        selection = process[start:end]
        selected = selection.split('#else\n', 1)[0].split('\n', 1)[1]
        include = run('host-gcc-include', ['/usr/bin/gcc', '-print-file-name=include']).strip()
        run('host-gcc-version', ['/usr/bin/gcc', '--version'])
        version = run('rust-version', [RUSTC, '--version'])
        need(version.startswith('rustc 1.92.0 '), 'pinned Rust1.92 required')
        # Reuse exact selected macro set and production-generated include roots,
        # with ONLY a small new probe TU and host compiler builtin include path.
        # This intentionally is NOT the pinned container process.c compilation.
        flags = original[1:original.index('-o')]
        rebased = []
        for token in flags:
            token = token.replace('/work/output/build', str(BUILD)).replace('/src', str(SOURCE))
            if token == '/usr/lib/gcc/x86_64-redhat-linux/14/include':
                token = include
            rebased.append(token)
        rebased.insert(0, '-I' + str(post / 'kernel/include'))
        # Actual production definitions, not fixture structs or copied offsets.
        probe = '''#include <process.h>
#include <sched_helpers.h>
#include <cpulocal.h>
const unsigned long idle_production_abi[] = {
 sizeof(struct thread), offsetof(struct thread, status), offsetof(struct thread, sched_list),
 sizeof(((struct thread *)0)->status), offsetof(struct cpu_local_var, runq),
 offsetof(struct cpu_local_var, status), sizeof(unsigned long), sizeof(void *),
 PS_RUNNING, CPU_STATUS_IDLE, CPU_STATUS_RESERVED, CPU_STATUS_RUNNING
};
int idle_actual_header_consumer(struct cpu_local_var *v) {
''' + selected + '''
 return v->status;
}
static struct cpu_local_var cpu;
static struct thread thread;
int main(void) {
 cpu.runq.next=&cpu.runq; cpu.runq.prev=&cpu.runq;
 cpu.status=CPU_STATUS_IDLE;
 if(idle_actual_header_consumer(&cpu)!=CPU_STATUS_IDLE) return 21;
 cpu.runq.next=&thread.sched_list; cpu.runq.prev=&thread.sched_list;
 thread.sched_list.next=&cpu.runq; thread.sched_list.prev=&cpu.runq;
 thread.status=PS_STOPPED; thread.spin_sleep=1; cpu.status=CPU_STATUS_RESERVED;
 if(idle_actual_header_consumer(&cpu)!=CPU_STATUS_RESERVED) return 22;
 thread.status=PS_RUNNING;
 if(idle_actual_header_consumer(&cpu)!=CPU_STATUS_RUNNING) return 23;
 return 0;
}
'''
        cpath = runroot / 'actual_production_headers_probe.c'
        cpath.write_text(probe)
        cobject = runroot / 'actual_production_headers_probe.o'
        run('actual-header-consumer-object', ['/usr/bin/gcc', *rebased, '-fno-pie', '-c', str(cpath), '-o', str(cobject)])
        run('actual-header-dependencies', ['/usr/bin/gcc', *rebased, '-MM', str(cpath)])
        run('actual-header-abi-data', ['/usr/bin/objdump', '-s', '-j', '.rodata', str(cobject)])
        imports = run('actual-header-consumer-imports', ['/usr/bin/nm', '-u', str(cobject)])
        need(imports.split()[-1:] == [SYMBOL] and len(imports.splitlines()) == 1, 'exact new Rust-only consumer dependency required')
        helper = item(rust, 'unsafe fn list_next(')
        body = item(rust, 'pub unsafe extern "C" fn ' + SYMBOL + '(')
        rpath = runroot / 'actual_existing_rust_provider.rs'
        rpath.write_text('#![no_std]\nuse core::ptr::read_volatile;\ntype CInt=i32;\n' + helper + '\n#[no_mangle]\n' + body + '\n')
        robject = runroot / 'actual_existing_rust_provider.o'
        rustflags = ['panic=abort', 'opt-level=2', 'codegen-units=1', 'code-model=large', 'relocation-model=static',
                     'no-redzone=yes', 'force-frame-pointers=yes', 'overflow-checks=off', 'force-unwind-tables=no',
                     'no-vectorize-loops', 'no-vectorize-slp',
                     'target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
        run('actual-rust-provider-object', [RUSTC, '--edition=2021', '--crate-type=lib', '--emit=obj',
            *[part for flag in rustflags for part in ('-C', flag)], str(rpath), '-o', str(robject)])
        need(not run('actual-rust-provider-undefined', ['/usr/bin/nm', '-u', str(robject)]).strip(), 'Rust helper has undefined references')
        binary = runroot / 'actual_header_consumer_link'
        run('actual-header-consumer-link', ['/usr/bin/gcc', '-no-pie', '-Wl,--no-undefined', str(cobject), str(robject), '-o', str(binary)])
        defined = run('actual-linked-provider-symbol', ['/usr/bin/nm', '-g', '--defined-only', str(binary)])
        need(sum(line.split()[-1:] == [SYMBOL] for line in defined.splitlines()) == 1, 'unique linked Rust definition required')
        run('actual-header-consumer-execute', [str(binary)])
        result.update(status='PASS_EXACT_STAGING_AND_ACTUAL_PRODUCTION_HEADER_HOST_CONSUMER_LINK',
                      production_compile_row=production,
                      actual_header_consumer_link=True, actual_header_cases=3,
                      host_compiler_scope='GCC9 production-header diagnostic; not pinned GCC14 production TU acceptance',
                      native_idle_port_proven=False)
        # The future PINNED container must mount the coherent successor source
        # as /src and reuse this generated build only under its reviewed lease.
        pinned_tu = original.copy()
        pinned_tu[pinned_tu.index('-o') + 1] = '/work/idle-cutover-production/process.c.o'
        write(OUT / 'NEXT-PINNED-PRODUCTION-COMMAND.json', dict(scope=SCOPE, preparation_only=True,
              execution_released=False, exact_selected_process_compile_row=production,
              proposed_production_tu_argv=pinned_tu,
              required_source_overlay=rows,
              prerequisite='New coherent successor /src plus existing reviewed pinned container profile and one heavy lease; never alter10972/source in place',
              followup='Use selected production Rust build recipe then existing default image target in a fresh coherent successor; verify process.o import, unique Rust/final definition, no final undefineds and native idle behavior'))
    except BaseException as error:
        result['error'] = repr(error)
    write(OUT / 'RESULT.json', result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
