#!/usr/bin/env python3
"""Extract both production C drains; execution needs a separate build release.

--source-only never invokes a compiler or fixture. Runtime checks concern a
stable, exclusively owned ring, not VM/token/extent authority or M03 acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
MEM = ROOT / 'kernel/mem.c'
PAGE = ROOT / 'kernel/include/page.h'
LIST = ROOT / 'lib/list.c'
LIST_H = ROOT / 'lib/include/list.h'
CC_SHA = '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2'
GUARD_RESULT = '\tif (mem_validate_pending_free_ring(pendings) < 0)\n\t\treturn -EINVAL;\n'
GUARD_PUBLIC = ('\tif (mem_validate_pending_free_ring(pendings) < 0) {\n'
                '\t\tpanic("free_pending_pages:invalid ring");\n\t\treturn;\n\t}\n')
CASES = ('inactive', 'empty', 'one', 'two', 'invalid-second', 'invalid-last',
         'zero-count', 'negative-count', 'wide-count', 'end-overflow',
         'null-next', 'bad-prev', 'mixed-head', 'foreign-cycle')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(path, begin, end):
    source = path.read_text()
    if source.count(begin) != 1:
        raise ValueError('ambiguous extraction start: ' + begin)
    start = source.index(begin)
    stop = source.index(end, start)
    body = source[start:stop]
    return body, dict(path=str(path.relative_to(ROOT)), start=start, end=stop,
                      sha256=hashlib.sha256(body.encode()).hexdigest())


def inputs():
    paths = (MEM, PAGE, LIST, LIST_H, Path(__file__),
             ROOT / 'scripts/tests/test_pending_free_c_actual_harness.py')
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def production():
    parts, bindings = [], []
    for path, begin, end in (
        (LIST_H, 'struct list_head {', '/* Static ABI initialization'),
        (PAGE, 'struct page {', 'struct page *phys_to_page('),
        (LIST, 'void __list_del(', 'void list_replace('),
        (MEM, 'static int mem_validate_pending_free_ring(',
         'int mem_finish_free_pages_pending_body_result('),
        (MEM, 'void finish_free_pages_pending(void)\n{',
         '#endif\n\nstatic struct ihk_mc_pa_ops allocator'),
    ):
        body, binding = extract(path, begin, end)
        parts.append(body)
        bindings.append(binding)
    for guard in (GUARD_RESULT, GUARD_PUBLIC):
        if '\n'.join(parts).count(guard) != 1:
            raise ValueError('missing or duplicated preflight call')
    return parts, bindings


SUPPORT = r'''
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <setjmp.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#define PAGE_SIZE 4096UL
#define IHK_MC_PG_USER 1
#define LIST_POISON1 ((void *)0x00100129)
#define LIST_POISON2 ((void *)0x00200229)
/* Layout shims for unused atomic fields; no kernel ABI qualification claimed. */
typedef struct { int counter; } ihk_atomic_t;
typedef struct { long counter; } ihk_atomic64_t;
typedef void (*mem_pending_free_fn_t)(unsigned long, int, int);
'''

BRIDGES = r'''
static struct cpu_local { struct list_head pending_free_pages; } cpu;
static struct page pages[3];
static struct { unsigned long phys; int npages, user; } calls[3];
static int ncalls, panics;
static jmp_buf panic_return;
static struct cpu_local *get_this_cpu_local_var(void) { return &cpu; }
static void panic(const char *s) { (void)s; panics++; longjmp(panic_return, 1); }
static void record_free(unsigned long phys, int npages, int user) {
    assert(ncalls < 3); calls[ncalls].phys=phys; calls[ncalls].npages=npages;
    calls[ncalls++].user=user;
}
static void *phys_to_virt(unsigned long phys) { return (void *)(uintptr_t)phys; }
static uintptr_t page_to_phys(struct page *p) { return p->phys; }
static void __mckernel_free_pages_in_allocator(void *v, int n, int u) {
    record_free((uintptr_t)v,n,u);
}
static int id(const struct list_head *p) {
    if (!p) return 0;
    if (p==&cpu.pending_free_pages) return 1;
    if (p==LIST_POISON1) return 90;
    if (p==LIST_POISON2) return 91;
    for (int i=0;i<3;i++) {
        if (p==&pages[i].list) return 10+i;
        if (p==&pages[i].hash) return 20+i;
    }
    return 99;
}
static void init(int n) {
    memset(&cpu,0,sizeof(cpu)); memset(pages,0,sizeof(pages));
    ncalls=panics=0;
    struct list_head *h=&cpu.pending_free_pages;
    h->next=n ? &pages[0].list : h; h->prev=n ? &pages[n-1].list : h;
    for (int i=0;i<3;i++) {
        pages[i].mode=PM_PENDING_FREE; pages[i].phys=0x1000UL*(i+1);
        pages[i].offset=i+1; pages[i].pgshift=12+i;
        pages[i].count.counter=30+i; pages[i].mapped.counter=40+i;
        pages[i].hash.next=pages[i].hash.prev=&pages[i].hash;
        if (i<n) {
            pages[i].list.prev=i ? &pages[i-1].list : h;
            pages[i].list.next=i+1<n ? &pages[i+1].list : h;
        }
    }
}
static void snapshot(const struct list_head *h, const struct page *p) {
    printf("{\"head\":[%d,%d],\"pages\":[",id(h->next),id(h->prev));
    for (int i=0;i<3;i++) {
        if(i) putchar(',');
        printf("{\"list\":[%d,%d],\"hash\":[%d,%d],\"mode\":%u,"
               "\"phys\":%llu,\"offset\":%lld,\"count\":%d,\"mapped\":%ld,\"pgshift\":%d}",
               id(p[i].list.next),id(p[i].list.prev),id(p[i].hash.next),id(p[i].hash.prev),
               (unsigned)p[i].mode,(unsigned long long)p[i].phys,(long long)p[i].offset,
               p[i].count.counter,p[i].mapped.counter,p[i].pgshift);
    }
    printf("]}");
}
'''

VECTORS = r'''
static void row(const char *name, int fallback) {
    struct list_head before_head=cpu.pending_free_pages;
    struct page before[3]; memcpy(before,pages,sizeof(pages));
    int rc;
    ncalls=panics=0;
    if (fallback) {
        if (!setjmp(panic_return)) finish_free_pages_pending();
        rc=panics ? -EINVAL : ncalls;
    } else rc=mem_finish_free_pages_pending_result(&cpu.pending_free_pages,record_free);
    printf("JSON|{\"case\":\"%s\",\"route\":\"%s\",\"rc\":%d,\"panic\":%d,\"before\":",
           name,fallback?"fallback":"result",rc,panics);
    snapshot(&before_head,before); printf(",\"after\":"); snapshot(&cpu.pending_free_pages,pages);
    printf(",\"callbacks\":[");
    for (int i=0;i<ncalls;i++) {
        if(i) putchar(',');
        printf("[%lu,%d,%d]",calls[i].phys,calls[i].npages,calls[i].user);
    }
    puts("]}");
}
static void invalid(const char *name, int fallback, int kind) {
    int n=kind==1 ? 3 : 2;
    init(n);
    struct list_head original_head=cpu.pending_free_pages;
    struct page original[3]; memcpy(original,pages,sizeof(pages));
    switch(kind) {
    case 0: pages[1].mode=PM_NONE; break;
    case 1: pages[2].mode=PM_NONE; break;
    case 2: pages[1].offset=0; break;
    case 3: pages[1].offset=-1; break;
    case 4: pages[1].offset=(off_t)INT_MAX+1; break;
    case 5: pages[1].phys=ULONG_MAX-4095; break;
    case 6: pages[1].list.next=NULL; break;
    case 7: pages[1].list.prev=&cpu.pending_free_pages; break;
    case 8: cpu.pending_free_pages.prev=&cpu.pending_free_pages; break;
    case 9: pages[1].list.next=&pages[0].list; pages[0].list.prev=&pages[1].list; break;
    }
    row(name,fallback);
    /* Restore only defect-bearing fields, never the released first node or
     * head.next. Thus the recovery cannot hide a prior valid-prefix mutation. */
    pages[1].mode=original[1].mode; pages[2].mode=original[2].mode;
    pages[1].offset=original[1].offset; pages[1].phys=original[1].phys;
    pages[1].list=original[1].list; pages[0].list.prev=original[0].list.prev;
    cpu.pending_free_pages.prev=original_head.prev;
    char recovery[80]; snprintf(recovery,sizeof(recovery),"%s-recovery",name);
    row(recovery,fallback);
}
int main(int argc, char **argv) {
    (void)mem_validate_pending_free_ring;
    const char *names[]={"invalid-second","invalid-last","zero-count","negative-count",
                        "wide-count","end-overflow","null-next","bad-prev","mixed-head","foreign-cycle"};
    if (argc==2 && !strcmp(argv[1],"mutant")) {
        for (int route=0;route<2;route++) {
            init(2); pages[1].mode=PM_NONE; row("invalid-second",route);
        }
        return 0;
    }
    assert(argc==1);
    for (int route=0;route<2;route++) {
        init(0); cpu.pending_free_pages.next=cpu.pending_free_pages.prev=NULL; row("inactive",route);
        init(0); row("empty",route);
        init(1); row("one",route);
        init(2); row("two",route);
        for (int k=0;k<10;k++) invalid(names[k],route,k);
    }
    return 0;
}
'''


def generate(mutant=False):
    parts, bindings = production()
    body = parts[3] + '\n' + parts[4]
    if mutant:
        body = body.replace(GUARD_RESULT, '').replace(GUARD_PUBLIC, '')
    return SUPPORT + parts[0] + parts[1] + parts[2] + BRIDGES + body + VECTORS, bindings


def check_rows(rows):
    expected = []
    for route in ('result', 'fallback'):
        for name, count in (('inactive', 0), ('empty', 0), ('one', 1), ('two', 2)):
            expected.append((route, name, count))
        for name in CASES[4:]:
            expected.extend(((route, name, -22), (route, name+'-recovery', 3 if name=='invalid-last' else 2)))
    assert [(r['route'], r['case'], r['rc']) for r in rows] == expected
    for row in rows:
        before, after, rc = row['before'], row['after'], row['rc']
        assert row['panic'] == int(rc < 0 and row['route'] == 'fallback')
        if rc < 0:
            assert before == after and row['callbacks'] == [], row['case']
            continue
        assert row['callbacks'] == [[4096*(i+1), i+1, 1] for i in range(rc)], row['case']
        assert after['head'] == [0, 0]
        for i, (old, new) in enumerate(zip(before['pages'], after['pages'])):
            wanted = dict(old)
            if i < rc:
                wanted.update(mode=0, list=[90, 91])
            assert new == wanted, (row['case'], i)


def check_mutant(rows):
    assert len(rows) == 2
    for row, route in zip(rows, ('result', 'fallback')):
        assert (row['case'], row['route'], row['rc']) == ('invalid-second', route, -22)
        assert row['panic'] == int(route == 'fallback')
        assert row['callbacks'] == [[4096, 1, 1]]
        assert row['before'] != row['after']
        assert row['after']['pages'][0]['mode'] == 0
        assert row['after']['pages'][0]['list'] == [90, 91]
        assert row['after']['head'] == [11, 11]
        assert row['after']['pages'][1]['list'] == [1, 1]


def source_only():
    candidate, bindings = generate()
    mutant, _ = generate(True)
    return dict(status='PASS_SOURCE_ONLY_C_PENDING_PREFLIGHT', inputs=inputs(),
                extracts=bindings, candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest(),
                mutant_sha256=hashlib.sha256(mutant.encode()).hexdigest(),
                planned_rows=48, planned_mutant_rows=2, executed_c_rows=0,
                scope='Extraction only; no VM/token/extent authority or full M03 acceptance')


def execute(out, cc, expected_inputs):
    if inputs() != expected_inputs:
        raise ValueError('source binding changed')
    if not Path(cc).is_absolute() or sha(Path(cc)) != CC_SHA:
        raise ValueError('compiler is not the reviewed pinned-image GCC')
    out.mkdir(parents=False, exist_ok=False)
    ledger = []
    def save(name, data):
        (out/name).write_text(json.dumps(data, sort_keys=True, indent=2)+'\n')
    save('source-only.json', source_only())
    def run(argv, label, seconds):
        record = dict(argv=argv, label=label, timeout=seconds,
                      environment={'PATH':'/usr/bin:/bin','HOME':'/tmp','LC_ALL':'C','LANG':'C'},
                      cwd=str(out), started_ns=time.time_ns())
        ledger.append(record); save('commands.json', ledger)
        try:
            with (out/(label+'.stdout')).open('wb') as stdout, (out/(label+'.stderr')).open('wb') as stderr:
                result = subprocess.run(argv, stdout=stdout, stderr=stderr, cwd=out,
                                        env=record['environment'], timeout=seconds)
            record['returncode'] = result.returncode
            if result.returncode:
                raise RuntimeError(label+' failed')
        except Exception as error:
            record['error'] = repr(error)
            raise
        finally:
            record['finished_ns'] = time.time_ns(); save('commands.json', ledger)
    for label, mutated in (('candidate', False), ('mutant', True)):
        source, _ = generate(mutated)
        path = out/(label+'.c'); path.write_text(source)
        run([cc, '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', str(path), '-o', str(out/label)], label+'-build', 60)
        run([str(out/label)]+(['mutant'] if mutated else []), label+'-run', 10)
    def rows(label):
        return [json.loads(line[5:]) for line in (out/(label+'-run.stdout')).read_text().splitlines() if line.startswith('JSON|')]
    candidate_rows, mutant_rows = rows('candidate'), rows('mutant')
    check_rows(candidate_rows); check_mutant(mutant_rows)
    if inputs() != expected_inputs:
        raise ValueError('source binding changed during execution')
    save('result.json', dict(status='PASS_SCOPED_C_PENDING_PREFLIGHT', inputs=inputs(),
         rows=candidate_rows, mutant_rows=mutant_rows,
         scope='Stable live exclusive ring only; no VM/token/extent authority or full M03 acceptance',
         artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-only', action='store_true')
    parser.add_argument('--cc')
    parser.add_argument('--pinned-hashes')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    if args.source_only:
        print(json.dumps(source_only(), sort_keys=True))
    else:
        if not all((args.cc, args.pinned_hashes, args.output_dir)):
            parser.error('execution requires --cc, --pinned-hashes and fresh --output-dir')
        execute(Path(args.output_dir).resolve(), args.cc, json.loads(Path(args.pinned_hashes).read_text()))
        print('PASS_SCOPED_C_PENDING_PREFLIGHT')


if __name__ == '__main__':
    main()
