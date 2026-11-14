/* SPDX-License-Identifier: GPL-2.0 */
/* Exact checked and legacy C bodies with explicit kernel-operation adapters. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <unistd.h>
@CALLBACK_TYPES@
struct rb_root { void *head; };
struct fd_node { void *next; int (*close_cb)(void *, void *); };
struct policy_node { struct policy_node *next; };
struct process { void *mckfd; unsigned long lock; int pid; void *vm; };
struct process_vm {
    int refs; void *proc; process_vm_free_cb_fn_t free_cb; void *opt;
    void *address_space; struct rb_root policy;
};
struct thread { int refs; void *vm; void *proc; };
@RUST_BODY_PROTOTYPES@

static char trace[1024], report[128];
static size_t trace_length;
static int rust_selected, dec_calls, thread_dec, vm_dec, checked_vm_override;
static unsigned int vectors;
static void *thread_page, *vm_page, *proc_page;
static struct fd_node fds[2];
static struct policy_node policies[2];
static void event(char value) { assert(trace_length + 1 < sizeof(trace)); trace[trace_length++] = value; trace[trace_length] = 0; }
static void *page(void) {
    void *result = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    assert(result != MAP_FAILED); return result;
}
static void poison(void *object) { assert(mprotect(object, 4096, PROT_NONE) == 0); }
static int injected_dec(void *object, unsigned long offset) {
    int injected = object == thread_page ? thread_dec : vm_dec;
    if (injected != 99) return injected;
    return --*(int *)((char *)object + offset) == 0;
}
int process_ref_dec_and_test_result(void *object, unsigned long offset, process_ref_dec_and_test_fn_t dec) {
    dec_calls++;
    return dec ? dec(object, offset) : --*(int *)((char *)object + offset) == 0;
}
int process_ref_release_should_destroy_result(int result) { return result != 0; }
int process_thread_profile_result(void *thread, void *proc, process_thread_profile_fn_t action) {
    if (action) { action(thread, proc); } return 0;
}
int process_thread_action_result(void *object, process_thread_action_fn_t action) {
    if (!action) { return -EINVAL; } action(object); return 0;
}
int process_vm_action_result(void *object, process_vm_action_fn_t action) {
    if (!action) { return -EINVAL; } action(object); return 0;
}
unsigned long process_spin_lock_result(unsigned long lock, process_spin_lock_fn_t action) { return action ? action(lock) : 0; }
int process_spin_unlock_result(unsigned long lock, unsigned long state, process_spin_unlock_fn_t action) {
    if (!action) { return -EINVAL; } action(lock, state); return 0;
}
int process_mckfd_close_all_result(void *head, unsigned long next, unsigned long close) {
    int count = 0;
    while (head) {
        int (*action)(void *, void *) = *(int (**)(void *, void *))((char *)head + close);
        if (action) { action(head, NULL); count++; }
        head = *(void **)((char *)head + next);
    }
    return count;
}
int process_release_vm_should_run_free_cb_result(unsigned long address) { return address != 0; }
int process_vm_free_cb_result(void *vm, void *opt, process_vm_free_cb_fn_t action) { if (action) action(vm, opt); return 0; }
int process_release_vm_detach_process_result(void *vm, unsigned long as_offset, unsigned long proc_offset,
    unsigned long pid_offset, unsigned long proc_vm_offset, process_detach_address_space_fn_t detach,
    process_release_process_fn_t release) {
    if (!vm || !detach || !release) return 0;
    void *proc = *(void **)((char *)vm + proc_offset);
    if (!proc) return 0;
    detach(*(void **)((char *)vm + as_offset), *(int *)((char *)proc + pid_offset));
    *(void **)((char *)proc + proc_vm_offset) = NULL;
    release(proc); return 1;
}
int process_vm_policy_drain_free_result(struct rb_root *root, unsigned long node_offset, process_policy_free_fn_t action) {
    int count = 0;
    if (!root || !action) return 0;
    while (root->head) {
        struct policy_node *node = root->head;
        root->head = node->next;
        action((char *)node - node_offset); count++;
    }
    return count;
}
int process_free_callback_result(void *object, process_free_fn_t action) { if (!action) { return -EINVAL; } action(object); return 0; }

/* Keep extracted fallback bodies byte-for-byte; rename symbols only through
 * the C preprocessor to link both language implementations in one test. */
#define process_release_thread_body_result c_process_release_thread_body_result
#define process_release_vm_body_result c_process_release_vm_body_result
#define process_release_thread_checked_body_result c_process_release_thread_checked_body_result
#define process_release_vm_checked_body_result c_process_release_vm_checked_body_result
@ACTUAL_C_BODIES@
#undef process_release_thread_body_result
#undef process_release_vm_body_result
#undef process_release_thread_checked_body_result
#undef process_release_vm_checked_body_result

static void profile(void *thread, void *proc) { assert(thread == thread_page && proc == proc_page); event('P'); }
static void procfs_delete(void *thread) { assert(thread == thread_page); event('X'); }
static void destroy_thread(void *thread) { assert(thread == thread_page); event('D'); poison(thread); }
static unsigned long lock_vm(unsigned long lock) { assert(lock == (unsigned long)proc_page + offsetof(struct process, lock)); event('L'); return 77; }
static void unlock_vm(unsigned long lock, unsigned long state) { assert(lock == (unsigned long)proc_page + offsetof(struct process, lock) && state == 77); event('U'); }
static int close_fd(void *fd, void *unused) { assert(fd && !unused); event('C'); return 0; }
static void pre_free(void *vm, void *opt) { assert(vm == vm_page && opt == (void *)55); event('B'); }
static void flush_vm(void *vm) { assert(vm == vm_page); event('F'); }
static void free_ranges(void *vm) { assert(vm == vm_page); event('R'); }
static void detach_vm(void *address_space, int pid) { assert(address_space == (void *)66 && pid == 123); event('A'); }
static void release_proc(void *proc) { assert(proc == proc_page); event('Q'); poison(proc); }
static void free_policy(void *policy) { assert(policy == &policies[0] || policy == &policies[1]); event('N'); }
static void free_vm(void *vm) { assert(vm == vm_page); event('Z'); poison(vm); }

#define VM_ARGS(vm, mask) (vm), offsetof(struct process_vm, refs), offsetof(struct process_vm, proc), \
    offsetof(struct process, mckfd), offsetof(struct process, lock), offsetof(struct fd_node, next), \
    offsetof(struct fd_node, close_cb), offsetof(struct process_vm, free_cb), offsetof(struct process_vm, opt), \
    offsetof(struct process_vm, address_space), offsetof(struct process, pid), offsetof(struct process, vm), \
    offsetof(struct process_vm, policy), 0, injected_dec, \
    ((mask)&1 ? NULL : lock_vm), ((mask)&2 ? NULL : unlock_vm), ((mask)&4 ? NULL : flush_vm), \
    ((mask)&8 ? NULL : free_ranges), ((mask)&16 ? NULL : detach_vm), ((mask)&32 ? NULL : release_proc), \
    ((mask)&64 ? NULL : free_policy), ((mask)&128 ? NULL : free_vm)
static int call_vm(void *vm, unsigned int mask, int checked) {
    if (checked) {
        if (rust_selected) return process_release_vm_checked_body_result(VM_ARGS(vm, mask));
        return c_process_release_vm_checked_body_result(VM_ARGS(vm, mask));
    }
    if (rust_selected) return process_release_vm_body_result(VM_ARGS(vm, mask));
    return c_process_release_vm_body_result(VM_ARGS(vm, mask));
}
static int checked_vm_bridge(void *vm) {
    event('V');
    if (checked_vm_override != 99) return checked_vm_override;
    return call_vm(vm, 0, 1);
}
static void legacy_vm_bridge(void *vm) { event('V'); (void)call_vm(vm, 0, 0); }
static int call_thread(void *thread, unsigned int mask, int checked, int optional_profile) {
    process_thread_profile_fn_t p = optional_profile ? NULL : profile;
    process_thread_action_fn_t x = mask&1 ? NULL : procfs_delete;
    process_thread_action_fn_t d = mask&2 ? NULL : destroy_thread;
    if (checked) {
        process_vm_release_checked_fn_t v = mask&4 ? NULL : checked_vm_bridge;
        if (rust_selected) return process_release_thread_checked_body_result(thread,
            offsetof(struct thread, refs), offsetof(struct thread, vm), offsetof(struct thread, proc), injected_dec, p, x, d, v);
        return c_process_release_thread_checked_body_result(thread,
            offsetof(struct thread, refs), offsetof(struct thread, vm), offsetof(struct thread, proc), injected_dec, p, x, d, v);
    }
    if (rust_selected) return process_release_thread_body_result(thread,
        offsetof(struct thread, refs), offsetof(struct thread, vm), offsetof(struct thread, proc), injected_dec, p, x, d, legacy_vm_bridge);
    return c_process_release_thread_body_result(thread,
        offsetof(struct thread, refs), offsetof(struct thread, vm), offsetof(struct thread, proc), injected_dec, p, x, d, legacy_vm_bridge);
}
static void setup(int thread_refs, int vm_refs, int optional_free, int lists) {
    thread_page = page(); vm_page = page(); proc_page = page();
    struct thread *thread = thread_page;
    struct process_vm *vm = vm_page;
    struct process *proc = proc_page;
    *thread = (struct thread){thread_refs, vm, proc};
    *vm = (struct process_vm){vm_refs, proc, optional_free ? pre_free : NULL, (void *)55, (void *)66, {NULL}};
    *proc = (struct process){NULL, 0, 123, vm};
    fds[0] = (struct fd_node){&fds[1], close_fd}; fds[1] = (struct fd_node){NULL, close_fd};
    policies[0].next = &policies[1]; policies[1].next = NULL;
    if (lists) { proc->mckfd = &fds[0]; vm->policy.head = &policies[0]; }
    trace_length = 0; trace[0] = 0; dec_calls = 0;
    thread_dec = vm_dec = checked_vm_override = 99;
}
static void done(int result, int expected, const char *expected_trace) {
    assert(result == expected); assert(strcmp(trace, expected_trace) == 0);
    assert(munmap(thread_page, 4096) == 0); assert(munmap(vm_page, 4096) == 0); assert(munmap(proc_page, 4096) == 0);
    vectors++;
}
static int ack_adapter(int host_revoked, unsigned long expected, unsigned long identity, int *acks, int *calls) {
    /* Cache scalar identity before the consuming release; no object read or
     * retry follows it. This adapter is not production fork integration. */
    unsigned long cached = identity;
    if (!host_revoked || cached != expected) return -EPERM;
    (*calls)++;
    int result = call_thread(thread_page, 0, 1, 0);
    if (result == 2 && cached == expected) (*acks)++;
    return result;
}
const char *fork_final_destructor_suite(int use_rust) {
    if (prctl(PR_SET_DUMPABLE, 0) != 0) _exit(86);
    rust_selected = use_rust; vectors = 0;
    setup(2, 1, 1, 1); int r = call_thread(thread_page, 0, 1, 0); assert(dec_calls == 1); done(r, 0, "");
    setup(1, 2, 1, 1); r = call_thread(thread_page, 0, 1, 0); assert(dec_calls == 2); done(r, 1, "PXDV");
    setup(1, 1, 1, 1); r = call_thread(thread_page, 0, 1, 0); assert(dec_calls == 2); done(r, 2, "PXDVLCCUBFRAQNNZ");
    setup(1, 1, 0, 0); done(call_thread(thread_page, 0, 1, 1), 2, "XDVLUFRAQZ");
    setup(1, 2, 1, 1); done(call_vm(vm_page, 0, 1), 0, "");
    const char *vm_traces[2][2] = {{"LUFRAQZ", "LCCUFRAQNNZ"}, {"LUBFRAQZ", "LCCUBFRAQNNZ"}};
    for (int optional = 0; optional < 2; optional++) {
        for (int lists = 0; lists < 2; lists++) {
            setup(1, 1, optional, lists); done(call_vm(vm_page, 0, 1), 1, vm_traces[optional][lists]);
        }
    }
    for (unsigned int mask = 1; mask <= 4; mask <<= 1) {
        setup(1, 1, 1, 1); r = call_thread(thread_page, mask, 1, 0); assert(dec_calls == 0); done(r, -EINVAL, "");
    }
    for (unsigned int mask = 1; mask <= 128; mask <<= 1) {
        setup(1, 1, 1, 1); r = call_vm(vm_page, mask, 1); assert(dec_calls == 0); done(r, -EINVAL, "");
    }
    setup(1, 1, 1, 1); r = call_thread(NULL, 0, 1, 0); assert(dec_calls == 0); done(r, -EINVAL, "");
    setup(1, 1, 1, 1); r = call_vm(NULL, 0, 1); assert(dec_calls == 0); done(r, -EINVAL, "");
    setup(1, 1, 1, 1); ((struct thread *)thread_page)->vm = NULL;
    r = call_thread(thread_page, 0, 1, 0); assert(dec_calls == 0); done(r, -EINVAL, "");
    setup(1, 1, 1, 1); ((struct thread *)thread_page)->proc = NULL;
    r = call_thread(thread_page, 0, 1, 0); assert(dec_calls == 0); done(r, -EINVAL, "");
    setup(1, 1, 1, 1); ((struct process_vm *)vm_page)->proc = NULL;
    r = call_vm(vm_page, 0, 1); assert(dec_calls == 0); done(r, -EINVAL, "");
    const int decrements[] = {0, 1, -5, 2};
    for (size_t index = 0; index < sizeof(decrements)/sizeof(decrements[0]); index++) {
        int dec = decrements[index];
        setup(1, 1, 1, 1); thread_dec = dec;
        r = call_thread(thread_page, 0, 1, 0);
        done(r, dec == 1 ? 2 : dec == 2 ? -EINVAL : dec, dec == 1 ? "PXDVLCCUBFRAQNNZ" : "");
        setup(1, 1, 1, 1); vm_dec = dec;
        r = call_vm(vm_page, 0, 1);
        done(r, dec == 2 ? -EINVAL : dec, dec == 1 ? "LCCUBFRAQNNZ" : "");
    }
    for (int index = 0; index < 2; index++) {
        setup(1, 1, 1, 1); checked_vm_override = index == 0 ? -5 : 2;
        done(call_thread(thread_page, 0, 1, 0), index == 0 ? -5 : -EINVAL, "PXDV");
    }
    /* Legacy result 1 still proves only thread destruction. Its original body
     * and public wrappers are separately byte/hash-frozen by Python checks. */
    setup(1, 2, 1, 1); done(call_thread(thread_page, 0, 0, 0), 1, "PXDV");
    setup(1, 1, 1, 1); done(call_thread(thread_page, 0, 0, 0), 1, "PXDVLCCUBFRAQNNZ");
    setup(1, 2, 1, 1); done(call_vm(vm_page, 0, 0), 0, "");
    setup(1, 1, 1, 1); done(call_vm(vm_page, 0, 0), 1, "LCCUBFRAQNNZ");
    for (int invalid = 0; invalid < 2; invalid++) {
        int acks = 0, calls = 0;
        setup(1, 1, 1, 1);
        r = ack_adapter(invalid, 55, invalid ? 56 : 55, &acks, &calls);
        assert(acks == 0 && calls == 0 && dec_calls == 0); done(r, -EPERM, "");
    }
    for (int outcome = 0; outcome < 5; outcome++) {
        int acks = 0, calls = 0;
        setup(outcome == 0 ? 2 : 1, outcome == 1 ? 2 : 1, 1, 1);
        if (outcome >= 3) checked_vm_override = outcome == 3 ? -5 : 2;
        r = ack_adapter(1, 55, 55, &acks, &calls);
        assert(calls == 1 && acks == (outcome == 2));
        const int expected[] = {0, 1, 2, -5, -EINVAL};
        done(r, expected[outcome], outcome == 0 ? "" : outcome == 2 ? "PXDVLCCUBFRAQNNZ" : "PXDV");
    }
    assert(vectors == 46);
    snprintf(report, sizeof(report), "checked-release-vectors=%u;poisoned-thread-vm-proc=1;ack-only-result2=1", vectors);
    return report;
}

int fork_final_destructor_poison_controls(void) {
    if (prctl(PR_SET_DUMPABLE, 0) != 0) _exit(86);
    for (int index = 0; index < 2; index++) {
        void *object = page(); poison(object);
        pid_t child = fork(); assert(child >= 0);
        if (child == 0) {
            if (prctl(PR_SET_DUMPABLE, 0) != 0) _exit(86);
            volatile int value = *(volatile int *)object; (void)value; _exit(99);
        }
        int status; assert(waitpid(child, &status, 0) == child);
        assert(WIFSIGNALED(status) && WTERMSIG(status) == SIGSEGV);
        assert(munmap(object, 4096) == 0);
    }
    return 2;
}
