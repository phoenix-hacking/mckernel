/* SPDX-License-Identifier: GPL-2.0 */
/* Exact original C bodies are extracted into the two generated includes. */
#include <errno.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/resource.h>
#include "../../../executer/include/uprotocol.h"
#include "native-application-syscall-c-layout.h"

#define SYSCALL_POLICY_HELPER_SCOPE
#define smp_store_release(p, value) __atomic_store_n((p), (value), __ATOMIC_RELEASE)
#define smp_load_acquire(p) __atomic_load_n((p), __ATOMIC_ACQUIRE)
#define cmpxchg(p, old, value) __sync_val_compare_and_swap((p), (old), (value))
#define syscall_response guest_syscall_response
#include "native-application-syscall-c-producer.h"
#undef syscall_response

typedef void *ihk_os_t;
struct ihk_ikc_channel_desc { int unused; };
struct channel_entry { struct ihk_ikc_channel_desc *c; };
struct mcctrl_usrdata { struct channel_entry *channels; };
struct mcctrl_per_proc_data { int unused; };
static struct ihk_ikc_channel_desc channel;
static struct channel_entry channels[4] = {{&channel}, {&channel}, {&channel}, {&channel}};
static struct mcctrl_usrdata userdata = {channels};
static int sends, wake_message, wake_tid;
static unsigned long send_status;
static struct syscall_response *current_response;
static struct mcctrl_usrdata *ihk_host_os_get_usrdata(ihk_os_t os) { (void)os; return &userdata; }
static int ihk_host_validate_os(ihk_os_t os) { (void)os; return 0; }
static void *ihk_os_to_dev(ihk_os_t os) { return os; }
static unsigned long ihk_device_map_memory(void *dev, unsigned long pa, size_t size)
{ (void)dev; (void)size; return pa; }
static void *ihk_device_map_virtual(void *dev, unsigned long pa, size_t size, void *unused, int flags)
{ (void)dev; (void)size; (void)unused; (void)flags; return (void *)pa; }
static void ihk_device_unmap_memory(void *dev, unsigned long pa, size_t size)
{ (void)dev; (void)pa; (void)size; }
static void ihk_device_unmap_virtual(void *dev, void *va, size_t size)
{ (void)dev; (void)va; (void)size; }
static int ihk_ikc_send(struct ihk_ikc_channel_desc *c, struct ikc_scd_packet *packet, int flags)
{
    (void)c; (void)flags;
    ++sends; wake_message = packet->msg; wake_tid = packet->ttid;
    send_status = current_response->status;
    return 0;
}
#define pr_err(...) ((void)0)
#define printk(...) ((void)0)
#define dprintk(...) ((void)0)
#define dump_stack() ((void)0)
#define mb() __atomic_thread_fence(__ATOMIC_SEQ_CST)
#include "native-application-syscall-c-completion.h"

static void hex(const void *pointer, size_t size)
{
    const unsigned char *bytes = pointer;
    for (size_t i = 0; i < size; ++i) printf("%02x", bytes[i]);
    putchar('\n');
}

int main(void)
{
#define R(name) offsetof(struct syscall_request, name)
#define S(name) offsetof(struct syscall_response, name)
#define W(name) offsetof(struct syscall_wait_desc, name)
#define T(name) offsetof(struct syscall_ret_desc, name)
    const size_t layout[] = {
        sizeof(struct syscall_request), _Alignof(struct syscall_request),
        R(rtid), R(ttid), R(valid), R(number), R(args),
        sizeof(struct syscall_response), _Alignof(struct syscall_response),
        S(ttid), S(stid), S(status), S(req_thread_status), S(ret), S(fault_address),
        sizeof(struct guest_syscall_response),
        sizeof(struct syscall_wait_desc), _Alignof(struct syscall_wait_desc), W(cpu), W(sr), W(pid),
        sizeof(struct syscall_ret_desc), _Alignof(struct syscall_ret_desc),
        T(cpu), T(ret), T(src), T(dest), T(size),
        sizeof(struct ikc_scd_packet), offsetof(struct ikc_scd_packet, req), offsetof(struct ikc_scd_packet, resp_pa),
    };
    fputs("layout", stdout);
    for (size_t i = 0; i < sizeof(layout) / sizeof(layout[0]); ++i) printf(" %zu", layout[i]);
    putchar('\n');
    const unsigned long numbers[] = {1, 39, 231, 203, 0, 0xffffffffUL};
    for (size_t n = 0; n < sizeof(numbers) / sizeof(numbers[0]); ++n) {
        struct syscall_request req = {.valid = 0xa5, .number = numbers[n],
            .args = {0, 1, 0x400123, ULONG_MAX, 0x8000000000000000UL, 17}};
        struct guest_syscall_response response;
        struct ikc_scd_packet packet = {0};
        memset(&response, 0xa5, sizeof(response));
        (void)syscall_offload_prepare_result(&req, &response, 700 + n, numbers[n], req.args[0], 203, 0);
        if (syscall_send_prepare_result(&req, &response) ||
            syscall_request_copy_result(&packet.req, &req) ||
            syscall_request_publish_result(&packet.req) ||
            syscall_packet_traditional_prepare_result(&packet, 4, n % 4, 600 + n, 0x180000 + 128*n))
            return 1;
        printf("request %zu ", n); hex(&packet, sizeof(packet));
    }
    const long values[] = {0, -1, -4095, LONG_MAX, LONG_MIN, 23};
    for (int state = 0; state <= 2; state += 2) {
        for (size_t n = 0; n < sizeof(values) / sizeof(values[0]); ++n) {
            union { uint64_t alignment[8]; unsigned char bytes[64]; } response;
            struct ikc_scd_packet packet = {0};
            memset(&response, 0xa5, sizeof(response));
            current_response = (struct syscall_response *)&response;
            current_response->status = 0;
            current_response->req_thread_status = state;
            packet.req.rtid = 700; packet.ref = 2; packet.pid = 600;
            packet.resp_pa = (unsigned long)&response;
            sends = wake_message = wake_tid = 0; send_status = ULONG_MAX;
            __return_syscall(&userdata, NULL, &packet, values[n], 900);
            printf("response %d %zu %d %d %d %lu ", state, n, sends, wake_message, wake_tid, send_status);
            hex(&response, sizeof(response));
        }
    }
    for (int state = 0; state <= 2; state += 2) {
        union { uint64_t alignment[8]; unsigned char bytes[64]; } response;
        struct ikc_scd_packet packet = {0};
        memset(&response, 0xa5, sizeof(response));
        current_response = (struct syscall_response *)&response;
        current_response->status = 0;
        current_response->req_thread_status = state;
        packet.req.rtid = 700; packet.ref = 2; packet.pid = 600;
        packet.resp_pa = (unsigned long)&response;
        sends = wake_message = wake_tid = 0; send_status = ULONG_MAX;
        /* Original worker/process cleanup uses stid zero and -ERESTARTSYS. */
        __return_syscall(&userdata, NULL, &packet, -512, 0);
        printf("cancellation %d %d %d %d %lu ", state, sends, wake_message, wake_tid, send_status);
        hex(&response, sizeof(response));
    }
    return 0;
}
