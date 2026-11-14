"""Actual idle Rust scan versus retained C scan; compile/behavior only.

Use MCKERNEL_IDLE_SCAN_SOURCE for the private postimage and
MCKERNEL_IDLE_SCAN_PREIMAGE for the preserved production preimage. Every command,
stream and generated source is retained under MCKERNEL_IDLE_SCAN_OUTPUT.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import unittest

from scripts.tests.test_shutdown_cpu_reclaim import balanced_item

ROOT = Path(__file__).resolve().parents[2]
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'


class RustIdleRunqueueScanTests(unittest.TestCase):
    def test_actual_scan_and_selected_consumer(self):
        source = Path(os.environ.get('MCKERNEL_IDLE_SCAN_SOURCE', ROOT))
        before = Path(os.environ['MCKERNEL_IDLE_SCAN_PREIMAGE'])
        out = Path(os.environ['MCKERNEL_IDLE_SCAN_OUTPUT'])
        out.mkdir(exist_ok=False)
        commands = []

        def run(label, argv):
            commands.append({'label': label, 'argv': argv})
            (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
            result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            for stream in ('stdout', 'stderr'):
                (out / (label + '.' + stream)).write_text(getattr(result, stream))
            (out / (label + '.status')).write_text(str(result.returncode) + '\n')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

        process = (source / 'kernel/process.c').read_text()
        old_process = (before / 'kernel/process.c').read_text()
        rust = (source / 'kernel/rust/sched_helpers.rs').read_text()
        header = (source / 'kernel/include/sched_helpers.h').read_text()
        old_start = old_process.index('\t\t\tfor (t =', old_process.index('void idle('))
        original = balanced_item(old_process[old_start:], '\t\t\tfor (t =')
        selected_start = process.index('#ifdef MCKERNEL_RUST_PROCESS_HELPERS', process.index('s = ihk_mc_spinlock_lock(&v->runq_lock);', process.index('void idle(')))
        selected_end = process.index('\n#endif', selected_start) + len('\n#endif')
        selection = process[selected_start:selected_end]
        fallback = selection.split('#else\n', 1)[1].removesuffix('\n#endif')
        self.assertEqual(fallback, original)
        self.assertIn('offsetof(struct thread, sched_list)', selection)
        self.assertIn('offsetof(struct thread, status), PS_RUNNING', selection)
        self.assertIn('__typeof__(((struct thread *)0)->status), int)', selection)
        self.assertIn('sizeof(((struct thread *)0)->status) == 4', selection)
        self.assertIn('offsetof(struct list_head, next) == 0', selection)
        self.assertEqual(process.count('sched_idle_runqueue_has_running_result('), 1)
        # Remove just the candidate bridge and declaration guards: all other
        # production process bytes, including FP/post-switch fixes, must match.
        restored = process[:selected_start] + original + process[selected_end:]
        restored = restored.replace('#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n\t\t\tstruct thread *t;\n#endif', '\t\t\tstruct thread *t;', 1)
        self.assertEqual(restored, old_process)
        definition = balanced_item(rust, 'pub unsafe extern "C" fn sched_idle_runqueue_has_running_result(')
        self.assertNotIn('spin_sleep', definition)
        self.assertNotIn('Thread', definition)
        self.assertNotIn('write_', definition)
        helper = balanced_item(rust, 'unsafe fn list_next(')
        self.assertIn('read_volatile(list_addr as *const usize)', helper)
        thread_decl = balanced_item((before / 'kernel/include/process.h').read_text(), 'struct thread {')
        self.assertRegex(thread_decl, r'\bint status;')
        self.assertRegex((before / 'kernel/include/process.h').read_text(), r'#define\s+PS_RUNNING\s+0x1\b')
        cint_decl = re.search(r'^pub type CInt = i32;', (before / 'kernel/rust/abi.rs').read_text(), re.M)
        self.assertIsNotNone(cint_decl)
        cmake = (before / 'kernel/CMakeLists.txt').read_text()
        self.assertIn('option(ENABLE_RUST_KERNEL "Enable Rust code in the McKernel image" ON)', cmake)
        self.assertIn('set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/process.c"\n\t\tPROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_PROCESS_HELPERS)', cmake)
        prototype = header[header.index('int sched_idle_runqueue_has_running_result('):]
        prototype = prototype[:prototype.index(';') + 1]
        rust_source = '#![no_std]\nuse core::ptr::read_volatile;\n' + cint_decl.group(0) + '\n' + helper + '\n#[no_mangle]\n' + definition + '\n'
        (out / 'actual_scan.rs').write_text(rust_source)
        self.assertTrue(run('rust-version', [RUSTC, '--version']).startswith('rustc 1.92.0 '))
        flags = ['panic=abort', 'opt-level=2', 'code-model=large', 'relocation-model=static',
                 'no-redzone=yes', 'force-frame-pointers=yes', 'overflow-checks=off',
                 'force-unwind-tables=no', 'no-vectorize-loops', 'no-vectorize-slp',
                 'target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
        run('rust-object', [RUSTC, '--edition=2021', '--crate-type=lib', '--emit=obj'] +
            [p for flag in flags for p in ('-C', flag)] + [str(out / 'actual_scan.rs'), '-o', str(out / 'actual_scan.o')])
        disassembly = run('rust-disassembly', ['/usr/bin/objdump', '-dr', str(out / 'actual_scan.o')])
        self.assertNotRegex(disassembly, r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b')
        self.assertNotRegex(run('rust-undefined', ['/usr/bin/nm', '-u', str(out / 'actual_scan.o')]), r'\S')
        # Fixture-only C records: offsets come from C, including a deliberately
        # different second layout. The helper assumes no Rust Thread layout.
        c = '''#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <limits.h>
#include "list.h"
#define PS_RUNNING 1
#define CPU_STATUS_RUNNING 2
struct thread { unsigned char prefix[4184]; int status; unsigned char gap[140]; struct list_head sched_list; unsigned char gap2[12]; int spin_sleep; unsigned char tail[1208]; } __attribute__((aligned(64)));
struct cpu { int status; struct list_head runq; };
_Static_assert(sizeof(int) == 4, "status width");
_Static_assert(sizeof(unsigned long) == sizeof(void *) && sizeof(void *) == 8, "supported LP64 pointer ABI");
_Static_assert(sizeof(struct thread) == 5568, "fixture thread size");
_Static_assert(offsetof(struct thread, status) == 4184, "C status offset");
_Static_assert(offsetof(struct thread, sched_list) == 4328, "C list offset");
_Static_assert(offsetof(struct thread, spin_sleep) == 4356, "fixture spin offset");
'''
        c += prototype + '\nint original_scan(struct cpu *v) { struct thread *t;\n' + original + '\nreturn v->status; }\n'
        c += 'int selected_scan(struct cpu *v) {\n#ifndef MCKERNEL_RUST_PROCESS_HELPERS\nstruct thread *t;\n#endif\n' + selection + '\nreturn v->status; }\n'
        c += '''
struct other_thread { int status; int spin_sleep; unsigned long gap[5]; struct list_head sched_list; };
int main(void) {
  static struct thread threads[3], saved[3];
  int cases[][3] = {{0,0,0},{2,32,16},{1,2,32},{2,1,32},{2,32,1},{3,5,17},{-1,INT_MIN,INT_MAX},{0x10001,0x101,0x201},{2,32,16},{1,1,1}};
  int checked=0;
  for (int n=0;n<=3;n++) for(unsigned c=0;c<sizeof(cases)/sizeof(*cases);c++) for(int initial=1;initial<=3;initial+=2) {
    memset(threads, 0xa5, sizeof(threads));
    struct cpu v={.status=initial};
    struct list_head *tail=&v.runq;
    v.runq.next=&v.runq; v.runq.prev=&v.runq;
    int expected=initial;
    for(int i=0;i<n;i++) {
      threads[i].status=cases[c][i]; threads[i].spin_sleep=c==8 ? 1 : 0;
      struct list_head *node=&threads[i].sched_list;
      node->prev=tail; node->next=&v.runq; tail->next=node; v.runq.prev=node; tail=node;
      if(threads[i].status==PS_RUNNING) expected=CPU_STATUS_RUNNING;
    }
    memcpy(saved,threads,sizeof(threads));
    struct list_head saved_head=v.runq;
    assert(original_scan(&v)==expected);
    assert(memcmp(saved,threads,sizeof(threads))==0);
    assert(memcmp(&saved_head,&v.runq,sizeof(saved_head))==0);
    v.status=initial;
    assert(selected_scan(&v)==expected);
    assert(memcmp(saved,threads,sizeof(threads))==0);
    assert(memcmp(&saved_head,&v.runq,sizeof(saved_head))==0);
    checked++;
  }
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
  struct list_head head; struct other_thread other[2];
  memset(other,0x7b,sizeof(other));
  other[0].status=3; other[1].status=1;
  head.next=&other[0].sched_list; head.prev=&other[1].sched_list;
  other[0].sched_list.prev=&head; other[0].sched_list.next=&other[1].sched_list;
  other[1].sched_list.prev=&other[0].sched_list; other[1].sched_list.next=&head;
  unsigned char snapshot[sizeof(other)]; memcpy(snapshot,other,sizeof(other));
  assert(sched_idle_runqueue_has_running_result((unsigned long)&head,offsetof(struct other_thread,sched_list),offsetof(struct other_thread,status),1)==1);
  assert(memcmp(snapshot,other,sizeof(other))==0);
  other[1].status=3;
  memcpy(snapshot,other,sizeof(other));
  assert(sched_idle_runqueue_has_running_result((unsigned long)&head,offsetof(struct other_thread,sched_list),offsetof(struct other_thread,status),1)==0);
  assert(memcmp(snapshot,other,sizeof(other))==0);
#endif
  printf("PASS %d exact C/Rust idle cases; C offsets, int width, byte preservation\\n",checked);
  return 0;
}
'''
        (out / 'actual_scan.c').write_text(c)
        results = []
        for name, defines in [('selected', ['-DMCKERNEL_RUST_PROCESS_HELPERS']), ('fallback', [])]:
            run(name + '-object', ['/usr/bin/gcc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-fno-pie', '-I', str(before / 'lib/include'), '-c'] + defines + [str(out / 'actual_scan.c'), '-o', str(out / (name + '.o'))])
            symbols = run(name + '-symbols', ['/usr/bin/nm', str(out / (name + '.o'))])
            if name == 'selected':
                self.assertRegex(symbols, r'\bU sched_idle_runqueue_has_running_result\b')
            else:
                self.assertNotIn('sched_idle_runqueue_has_running_result', symbols)
            run(name + '-link', ['/usr/bin/gcc', '-no-pie', str(out / (name + '.o'))] + ([str(out / 'actual_scan.o')] if name == 'selected' else []) + ['-o', str(out / name)])
            results.append(run(name + '-run', [str(out / name)]))
        self.assertEqual(*results)
        hashes = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
        (out / 'artifact-sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
        print(results[0], end='')


if __name__ == '__main__':
    unittest.main()
