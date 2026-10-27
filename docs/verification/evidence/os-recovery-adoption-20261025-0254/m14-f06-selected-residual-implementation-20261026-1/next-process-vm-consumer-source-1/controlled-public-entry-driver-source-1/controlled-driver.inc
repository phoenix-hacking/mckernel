/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Controlled HOST providers, not production lock/MM/user-copy implementations.
 * They assert the real typed pointers, stack node boundaries and effect order.
 */
extern void abort(void);
extern int puts(const char *);
#define CHECK(x) do { if (!(x)) abort(); } while (0)

static struct cpu_local_var cpu;
static struct thread local_thread;
static struct process local_process, remote_process;
static struct process_vm local_vm, remote_vm;
static struct address_space remote_space;
static struct vm_range local_range, remote_range;
static unsigned char local_bytes[8192] __attribute__((aligned(4096)));
static unsigned char remote_bytes[8192] __attribute__((aligned(4096)));
static struct iovec liov, riov;
static int mode, range_locks[2], update_held, hash_held, vm_holds;
static int cpu_reads, vtop_calls, faults, copies, copied_bytes, found_calls;
static void *find_node, *update_node;
struct effect { int kind, owner; unsigned long a, b; };
static struct effect effects[256], saved_effects[256];
static unsigned long effect_count;

enum { NORMAL, BAD_FLAGS, BAD_LOCAL_COUNT, LOCAL_DESCRIPTOR, REMOTE_DESCRIPTOR,
       UNEQUAL_LENGTH, MISSING_PROCESS, EXITED_PROCESS, MISSING_VM, CREDENTIALS,
       LOCAL_PERMISSION, REMOTE_PERMISSION, FAULT_RETRY, FAULT_FAIL, PARTIAL_FAIL,
       VTOP_RETRY_FAIL, LOCAL_FULL_RANGE, REMOTE_FULL_RANGE, ZERO_LENGTH,
       BAD_REMOTE_COUNT, CASE_COUNT };

static void event(int k, int owner, unsigned long a, unsigned long b)
{
    CHECK(effect_count < 256);
    effects[effect_count++] = (struct effect){k, owner, a, b};
}

static int vm_id(struct process_vm *vm)
{
    CHECK(vm == &local_vm || vm == &remote_vm);
    return vm == &remote_vm;
}

struct cpu_local_var *fixture_cpu(void)
{
    CHECK(cpu.current == &local_thread);
    cpu_reads++;
    event(1, 0, 0, 0);
    return &cpu;
}

void fixture_range_lock(ihk_rwspinlock_t *lock)
{
    int id = lock == &remote_vm.memory_range_lock;
    CHECK(lock == &local_vm.memory_range_lock || id);
    CHECK(range_locks[id]++ == 0);
    event(2, id, 0, 0);
}

void fixture_range_unlock(ihk_rwspinlock_t *lock)
{
    int id = lock == &remote_vm.memory_range_lock;
    CHECK(lock == &local_vm.memory_range_lock || id);
    CHECK(range_locks[id]-- == 1);
    event(3, id, 0, 0);
}

struct vm_range *fixture_lookup(struct process_vm *vm, unsigned long start,
                               unsigned long end)
{
    int id = vm_id(vm);
    CHECK(range_locks[id] == 1 && end >= start);
    event(4, id, start, end);
    if (start == (unsigned long)&liov && mode == LOCAL_DESCRIPTOR) return NULL;
    if (start == (unsigned long)&riov && mode == REMOTE_DESCRIPTOR) return NULL;
    if (start == (unsigned long)local_bytes && end - start == 32 &&
        mode == LOCAL_FULL_RANGE) return NULL;
    if (start == (unsigned long)remote_bytes && end - start == 32 &&
        mode == REMOTE_FULL_RANGE) return NULL;
    return id ? &remote_range : &local_range;
}

struct process *fixture_find(int pid, struct mcs_rwlock_node_irqsave *node)
{
    CHECK(pid == 31 && node && ((unsigned long)node & 63) == 0);
    CHECK(!hash_held && !update_held && !range_locks[0] && !range_locks[1]);
    found_calls++;
    event(5, 1, 0, 0);
    if (mode == MISSING_PROCESS) return NULL;
    hash_held = 1;
    find_node = node;
    return &remote_process;
}

void fixture_process_unlock(struct process *proc, struct mcs_rwlock_node_irqsave *node)
{
    CHECK(proc == &remote_process && node == find_node && hash_held && !update_held);
    hash_held = 0;
    event(6, 1, 0, 0);
}

void fixture_update_lock(struct mcs_rwlock_lock *lock, struct mcs_rwlock_node *node)
{
    CHECK(lock == &remote_process.update_lock && node && ((unsigned long)node & 63) == 0);
    CHECK((void *)node != find_node && hash_held && !update_held);
    update_node = node;
    update_held = 1;
    event(7, 1, 0, 0);
}

void fixture_update_unlock(struct mcs_rwlock_lock *lock, struct mcs_rwlock_node *node)
{
    CHECK(lock == &remote_process.update_lock && node == update_node && update_held);
    update_held = 0;
    event(8, 1, 0, 0);
}

void fixture_hold(struct process_vm *vm)
{
    CHECK(vm == &remote_vm && hash_held && update_held && vm_holds == 0);
    vm_holds++;
    event(9, 1, 0, 0);
}

void fixture_release(struct process_vm *vm)
{
    CHECK(vm == &remote_vm && vm_holds == 1 && !hash_held && !update_held);
    CHECK(!range_locks[0] && !range_locks[1]);
    vm_holds--;
    event(10, 1, 0, 0);
}

int fixture_vtop(struct page_table *pt, const void *virt, unsigned long *phys,
                 unsigned long *psize)
{
    CHECK(pt == remote_space.page_table && vm_holds == 1);
    CHECK(!range_locks[0] && !range_locks[1] && !hash_held && !update_held);
    CHECK((unsigned long)virt >= (unsigned long)remote_bytes &&
          (unsigned long)virt < (unsigned long)remote_bytes + 32);
    event(11, 1, (unsigned long)virt, 0);
    vtop_calls++;
    if ((mode == FAULT_RETRY || mode == FAULT_FAIL) && vtop_calls == 1) return -EFAULT;
    if (mode == VTOP_RETRY_FAIL || (mode == PARTIAL_FAIL && vtop_calls > 1)) return -EFAULT;
    *phys = (unsigned long)virt;
    *psize = 16; /* controlled power-of-two boundary; not a real page mapping */
    return 0;
}

int fixture_fault(struct process_vm *vm, void *addr, unsigned long reason)
{
    CHECK(vm == &remote_vm && vm_holds == 1);
    CHECK(addr == (void *)remote_bytes);
    CHECK(reason == (PF_POPULATE | PF_WRITE | PF_USER));
    faults++;
    event(12, 1, (unsigned long)addr, reason);
    return mode == FAULT_FAIL || mode == PARTIAL_FAIL ? -EFAULT : 0;
}

void *fixture_phys(unsigned long phys)
{
    CHECK(vm_holds == 1);
    event(13, 1, phys, 0);
    return (void *)phys;
}

void *fixture_copy(void *dst, const void *src, size_t bytes)
{
    CHECK(vm_holds == 1 && !hash_held && !update_held);
    CHECK(!range_locks[0] && !range_locks[1]);
    CHECK(bytes == 16 && copies < 2);
    CHECK((dst == local_bytes + copied_bytes && src == remote_bytes + copied_bytes) ||
          (dst == remote_bytes + copied_bytes && src == local_bytes + copied_bytes));
    event(14, dst == remote_bytes + copied_bytes, bytes, copied_bytes);
    for (size_t i = 0; i < bytes; i++) ((unsigned char *)dst)[i] = ((const unsigned char *)src)[i];
    copies++;
    copied_bytes += bytes;
    return dst;
}

void arch_process_vm_rw_log_bridge(const struct arch_process_vm_rw_log_record *record)
{
    CHECK(record && record->event >= 1 && record->event <= 4);
    /* Records deliberately initialize only event-specific fields. Never read padding. */
    event(15, record->event, 0, 0);
}

static void setup(int m)
{
    mode = m;
    cpu.current = &local_thread;
    local_thread.proc = &local_process;
    local_thread.vm = &local_vm;
    local_process.euid = 0;
    local_process.ruid = 17;
    local_process.rgid = 18;
    remote_process.ruid = remote_process.euid = remote_process.suid = 17;
    remote_process.rgid = remote_process.egid = remote_process.sgid = 18;
    remote_process.status = m == EXITED_PROCESS ? PS_EXITED : 0;
    remote_process.vm = m == MISSING_VM ? NULL : &remote_vm;
    remote_vm.address_space = &remote_space;
    remote_space.page_table = (struct page_table *)&remote_space;
    local_range.flag = remote_range.flag = VR_PROT_READ | VR_PROT_WRITE;
    if (m == LOCAL_PERMISSION) local_range.flag = 0;
    if (m == REMOTE_PERMISSION) remote_range.flag = 0;
    if (m == CREDENTIALS) { local_process.euid = 17; remote_process.suid = 19; }
    liov = (struct iovec){local_bytes, m == ZERO_LENGTH ? 0 : 32};
    riov = (struct iovec){remote_bytes, m == ZERO_LENGTH ? 0 : m == UNEQUAL_LENGTH ? 16 : 32};
    for (int i = 0; i < 32; i++) { local_bytes[i] = 0x20 + i; remote_bytes[i] = 0x80 + i; }
    range_locks[0] = range_locks[1] = update_held = hash_held = vm_holds = 0;
    cpu_reads = vtop_calls = faults = copies = copied_bytes = found_calls = 0;
    find_node = update_node = NULL;
    effect_count = 0;
}

static int expected_result(int m)
{
    if (m == NORMAL || m == FAULT_RETRY) return 32;
    if (m == ZERO_LENGTH) return 0;
    if (m == BAD_FLAGS || m == BAD_LOCAL_COUNT || m == BAD_REMOTE_COUNT ||
        m == UNEQUAL_LENGTH || m == LOCAL_FULL_RANGE || m == REMOTE_FULL_RANGE) return -EINVAL;
    if (m == MISSING_PROCESS || m == EXITED_PROCESS) return -ESRCH;
    if (m == CREDENTIALS) return -EPERM;
    return -EFAULT;
}

static int invoke(int rust, int op)
{
    unsigned long lc = mode == BAD_LOCAL_COUNT ? 1025 : 1;
    unsigned long rc = mode == BAD_REMOTE_COUNT ? 1025 : 1;
    int result = (rust ? do_process_vm_read_writev : original_selected_process_vm_rw)(
        31, &liov, lc, &riov, rc, mode == BAD_FLAGS ? 1 : 0, op);
    CHECK(result == expected_result(mode));
    CHECK(cpu_reads == 1 && !hash_held && !update_held && vm_holds == 0);
    CHECK(!range_locks[0] && !range_locks[1]);
    int expected_copied = mode == NORMAL || mode == FAULT_RETRY ? 32 : mode == PARTIAL_FAIL ? 16 : 0;
    CHECK(copied_bytes == expected_copied);
    for (int i = 0; i < 32; i++) {
        CHECK(local_bytes[i] == (op == 0 && i < expected_copied ? 0x80 + i : 0x20 + i));
        CHECK(remote_bytes[i] == (op == 1 && i < expected_copied ? 0x20 + i : 0x80 + i));
    }
    CHECK(faults == (mode == FAULT_RETRY || mode == FAULT_FAIL ||
                    mode == PARTIAL_FAIL || mode == VTOP_RETRY_FAIL ? 1 : 0));
    return result;
}

int main(void)
{
    CHECK(f06_process_vm_rw_compare_ABI() == 0);
    setup(NORMAL);
    CHECK(f06_process_vm_rw_validation_entry_comparison() == 0);
    for (int op = 0; op < 2; op++) for (int m = 0; m < CASE_COUNT; m++) {
        setup(m);
        int old = invoke(0, op);
        unsigned long n = effect_count;
        for (unsigned long i = 0; i < n; i++) saved_effects[i] = effects[i];
        setup(m);
        CHECK(invoke(1, op) == old && effect_count == n);
        for (unsigned long i = 0; i < n; i++) {
            CHECK(effects[i].kind == saved_effects[i].kind && effects[i].owner == saved_effects[i].owner);
            CHECK(effects[i].a == saved_effects[i].a && effects[i].b == saved_effects[i].b);
        }
    }
    puts("PASS process_vm public entry ABI22 controlled pairs40 invalidflags4");
    return 0;
}
