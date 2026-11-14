/* SPDX-License-Identifier: GPL-2.0 */
/* Test-only actual original-C versus actual candidate-Rust consumer. */
#include "generated/include/linux/mm.h"
#include "generated/original/mcctrl_vm_write_compat.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void m15_rust_assert_mmap_write_locked(struct mm_struct *);
void m15_rust_mmap_write_lock(struct mm_struct *);
void m15_rust_mmap_write_unlock(struct mm_struct *);
void m15_rust_vma_start_write(struct vm_area_struct *);

struct event { uint32_t tag, target, value; };
struct result {
    uint32_t sequence, vma[2], held_mmap, held_vma[2], count;
    struct event events[256];
};
struct world {
    struct mm_struct mm;
    struct vma_lock locks[2];
    struct vm_area_struct vmas[2];
    uint32_t outer_mask, inner_mask;
    struct result result;
};
static struct world world;
static void record(uint32_t tag, uint32_t target, uint32_t value)
{
    assert(world.result.count < 256);
    world.result.events[world.result.count++] = (struct event){tag,target,value};
}
void m15_fixture_note_assert_read(uint64_t count)
{
    record(9,0,(uint32_t)count);
    record(11,0,(uint32_t)(count >> 32));
}
long m15_fixture_atomic_long_read(const atomic_long_t *value)
{
    assert(value == &world.mm.mmap_lock.count);
    uint64_t count=(uint64_t)value->counter;
    m15_fixture_note_assert_read(count);
    return (long)count;
}
void m15_fixture_write_lock_warning(void)
{ record(10,0,0); }
bool m15_fixture_outer_gate(unsigned event)
{
    assert(event < 3);
    uint32_t enabled = (world.outer_mask >> event) & 1;
    record(1,event,enabled);
    return enabled != 0;
}
static void trace(unsigned event, struct mm_struct *mm, bool write, bool success)
{
    assert(mm == &world.mm && write);
    uint32_t argument = 1u | ((event == 1 && success) ? 2u : 0u);
    record(2,event,argument);
    uint32_t enabled = (world.inner_mask >> event) & 1;
    record(3,event,enabled);
    if (enabled) record(4,event,argument);
}
void __mmap_lock_do_trace_start_locking(struct mm_struct *mm, bool write)
{ trace(0,mm,write,false); }
void __mmap_lock_do_trace_acquire_returned(struct mm_struct *mm, bool write, bool success)
{ assert(success); trace(1,mm,write,success); }
void __mmap_lock_do_trace_released(struct mm_struct *mm, bool write)
{ trace(2,mm,write,false); }
void down_write(struct rw_semaphore *sem)
{
    assert(sem->fixture_id < 3 && !sem->held);
    sem->held=1;
    sem->count.counter=1;
    record(5,sem->fixture_id,0);
}
void up_write(struct rw_semaphore *sem)
{
    assert(sem->fixture_id < 3 && sem->held);
    record(6,sem->fixture_id,0);
    sem->held=0;
    sem->count.counter=0;
}
void m15_fixture_smp_wmb(void)
{ record(7,0,world.mm.mm_lock_seq.sequence); }
void m15_fixture_note_write_once_u32(uint32_t *address, uint32_t value)
{
    unsigned index = address == &world.vmas[0].vm_lock_seq ? 0 : 1;
    assert(address == &world.vmas[index].vm_lock_seq);
    assert(world.mm.mmap_lock.held && world.locks[index].lock.held);
    assert(*address == value);
    record(8,index+1,value);
}
void m15_fixture_write_once_u32(volatile uint32_t *address, uint32_t value)
{
    *address=value;
    m15_fixture_note_write_once_u32((uint32_t *)address,value);
}
static struct result run(bool rust, uint32_t sequence, uint32_t first, uint32_t second,
                         uint32_t outer, uint32_t inner, const char *ops)
{
    memset(&world,0,sizeof(world));
    world.mm.mmap_lock.fixture_id=0;
    world.mm.mm_lock_seq.sequence=sequence;
    world.outer_mask=outer;
    world.inner_mask=inner;
    for (unsigned i=0;i<2;i++) {
        world.locks[i].lock.fixture_id=i+1;
        world.vmas[i].vm_mm=&world.mm;
        world.vmas[i].vm_lock=&world.locks[i];
        world.vmas[i].vm_lock_seq=i ? second : first;
    }
    for (const char *op=ops; *op; op++) {
        if (*op=='L') {
            if (rust) m15_rust_mmap_write_lock(&world.mm);
            else mckernel_inherited_mmap_write_lock(&world.mm);
        } else if (*op=='U') {
            if (rust) m15_rust_mmap_write_unlock(&world.mm);
            else mckernel_inherited_mmap_write_unlock(&world.mm);
        } else {
            unsigned i=(unsigned)(*op-'0');
            assert(i<2 && world.mm.mmap_lock.held);
            if (rust) m15_rust_vma_start_write(&world.vmas[i]);
            else mckernel_inherited_vma_start_write(&world.vmas[i]);
        }
    }
    world.result.sequence=world.mm.mm_lock_seq.sequence;
    world.result.held_mmap=world.mm.mmap_lock.held;
    for (unsigned i=0;i<2;i++) {
        world.result.vma[i]=world.vmas[i].vm_lock_seq;
        world.result.held_vma[i]=world.locks[i].lock.held;
    }
    return world.result;
}
static uint32_t number(const char *arg)
{
    char *end;
    errno=0;
    unsigned long value=strtoul(arg,&end,10);
    if (errno || !*arg || *end || value>UINT32_MAX) exit(2);
    return (uint32_t)value;
}
/* Exercise only the assertion on synthetic no-writer counts; never perform
 * an invalid Linux unlock/VMA operation and never execute the kernel UD2 here. */
static int assertion_case(uint32_t low, uint32_t high, uint32_t repetitions)
{
    if (!repetitions || repetitions>8) return 2;
    uint64_t count=(uint64_t)low | ((uint64_t)high << 32);
    struct result results[2];
    for (unsigned rust=0;rust<2;rust++) {
        memset(&world,0,sizeof(world));
        world.mm.mmap_lock.count.counter=(int64_t)count;
        for (unsigned i=0;i<repetitions;i++) {
            if (rust) m15_rust_assert_mmap_write_locked(&world.mm);
            else mmap_assert_write_locked(&world.mm);
        }
        results[rust]=world.result;
    }
    if (memcmp(&results[0],&results[1],sizeof(results[0]))) return 1;
    unsigned warnings=0;
    for (unsigned i=0;i<results[0].count;i++)
        warnings += results[0].events[i].tag==10;
    unsigned expected=(low & 1) ? 0 : repetitions;
    if (warnings!=expected || results[0].count!=2*repetitions+expected) return 1;
    printf("{\"equal\":true,\"warnings\":%u,\"assertion_reads\":%u,"
           "\"low\":%u,\"high\":%u}\n",warnings,repetitions,low,high);
    return 0;
}
int main(int argc,char **argv)
{
    if (argc==5 && !strcmp(argv[1],"--assert-warning"))
        return assertion_case(number(argv[2]),number(argv[3]),number(argv[4]));
    if (argc!=7) return 2;
    uint32_t seq=number(argv[1]), first=number(argv[2]), second=number(argv[3]);
    uint32_t outer=number(argv[4]), inner=number(argv[5]);
    if (outer>7 || inner>7 || strlen(argv[6])>16) return 2;
    bool held=false;
    for (const char *op=argv[6];*op;op++) {
        if (*op=='L') {if (held) return 2; held=true;}
        else if (*op=='U') {if (!held) return 2; held=false;}
        else if ((*op!='0' && *op!='1') || !held) return 2;
    }
    if (held) return 2; /* reject invalid schedules before either FFI call */
    struct result c=run(false,seq,first,second,outer,inner,argv[6]);
    struct result rust=run(true,seq,first,second,outer,inner,argv[6]);
    if (memcmp(&c,&rust,sizeof(c))) {
        fprintf(stderr,"actual C/Rust result or ordered-log mismatch\n");
        return 1;
    }
    printf("{\"equal\":true,\"mm_sequence\":%u,\"vma_sequences\":[%u,%u],"
           "\"held_mmap\":%u,\"held_vma\":[%u,%u],\"events\":[",
           c.sequence,c.vma[0],c.vma[1],c.held_mmap,c.held_vma[0],c.held_vma[1]);
    for (unsigned i=0;i<c.count;i++)
        printf("%s[%u,%u,%u]",i ? "," : "",c.events[i].tag,c.events[i].target,c.events[i].value);
    puts("]}");
    return 0;
}
