/* SPDX-License-Identifier: GPL-2.0 */
/* Actual guest preparation and Linux mirror ownership. No task is scheduled. */
#define NATIVE_MCCTRL_PROCESS_MAIN native_process_reference_main
#include "native-mcctrl-process.c"
#undef NATIVE_MCCTRL_PROCESS_MAIN
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>
#include <sys/resource.h>
#include "native-image-c-abi.h"

#if !defined(__x86_64__)
#error The image consumer under test is the existing x86_64 launcher ABI.
#endif
_Static_assert(sizeof(struct program_load_desc) == 776, "launcher descriptor");
_Static_assert(sizeof(struct program_image_section) == 56, "launcher section");
static struct {
    struct program_load_desc desc;
    struct program_image_section sections[2];
} image_request;
static struct { unsigned long count, offset, null; char text[16]; } image_args = {1, 24, 0, "/image-probe"};
static unsigned long image_envs[2];
static unsigned char payload[8192], readback[8192];
static unsigned image_checks;
static volatile unsigned image_child_progress;

static void image_require(int condition, int line)
{
    image_checks++;
    if (!condition) { message("NATIVE_MCCTRL_IMAGE FAIL line="); print_number(line); message("\n"); fail(line); }
}
#undef require
#define require(value) image_require(!!(value), __LINE__)

static long map_low(unsigned long address)
{
    long result;
    register long fourth __asm__("r10") = 0x100022; /* NOREPLACE|PRIVATE|ANON */
    register long fifth __asm__("r8") = -1;
    register long sixth __asm__("r9") = 0;
    __asm__ volatile("syscall" : "=a"(result) : "0"(9L), "D"(address), "S"(4096L), "d"(3L),
                     "r"(fourth), "r"(fifth), "r"(sixth) : "rcx", "r11", "memory");
    return result;
}

static void compare(const unsigned char *expected, const volatile unsigned char *actual, unsigned length)
{
    unsigned i;
    for (i = 0; i < length; i++) if (expected[i] != actual[i]) break;
    require(i == length);
}

static void transfer(int fd, unsigned long physical, void *user, unsigned long length, unsigned char direction, long expected)
{
    struct remote_transfer request = {physical, user, length, direction};
    long result = call(SYS_IOCTL, fd, MCEXEC_UP_TRANSFER, (long)&request);
    if (result != expected) {
        message("NATIVE_IMAGE_TRANSFER error_negative="); print_number(result < 0);
        message(" magnitude="); print_number(result < 0 ? -result : result); message("\n");
    }
    require(result == expected);
}

static void capability_snapshot(unsigned data[6])
{
    unsigned header[2] = {0x20080522, 0};
    require(call(125, (long)header, (long)data, 0) == 0);
}

static void reject_text_write(void)
{
    const struct rlimit no_core = {0, 0};
    require(call(160, RLIMIT_CORE, (long)&no_core, 0) == 0);
    long child;
    /* Raw vfork shares this exact MM. The child first proves writable access
     * to data, preserving the original byte, then attempts a text write.
     * Keep all child work in assembly so the parent's stack is untouched. */
    __asm__ volatile("mov $58, %%eax\n\tsyscall\n\t"
                     "test %%rax, %%rax\n\tjnz 1f\n\t"
                     "movb $0x83, 0x601080\n\t"
                     "movl $1, (%1)\n\t"
                     "movb $0x5a, 0x400080\n\t"
                     "mov $60, %%eax\n\tmov $99, %%edi\n\tsyscall\n\tud2\n"
                     "1:"
                     : "=&a"(child) : "r"(&image_child_progress)
                     : "rcx", "r11", "rdi", "cc", "memory");
    require(child > 0);
    int status = -1;
    require(call(SYS_WAIT, child, (long)&status, 0) == child);
    require(image_child_progress == 1);
    require((status & 0x7f) == 7); /* SIGBUS from rejected guest write permission. */
}

int main(void)
{
    require((unsigned long)&image_request > 0x008000000000UL);
    int fd = open_os(0);
    ppd(fd, 0, 0);
    struct program_load_desc *desc = &image_request.desc;
    desc->magic = PLD_MAGIC; desc->num_sections = 2; desc->cpu = 0;
    desc->pid = -999; /* The kernel must use the referenced current TGID. */
    desc->stack_prot = 3; desc->entry = 0x400000; desc->at_entry = desc->entry;
    desc->args = (char *)&image_args; desc->args_len = sizeof(image_args);
    desc->envs = (char *)image_envs; desc->envs_len = sizeof(image_envs);
    desc->enable_vdso = 1; desc->stack_premap = 65536;
    desc->mpol_mode = PLD_MPOL_MAX; desc->nr_processes = 1; desc->cpu_set[0] = 1;
    for (int i = 0; i < 20; i++) desc->rlimit[i].rlim_cur = desc->rlimit[i].rlim_max = RLIM_INFINITY;
    desc->rlimit[3].rlim_cur = desc->rlimit[3].rlim_max = 8 * 1024 * 1024;
    desc->sections[0] = (struct program_image_section){.vaddr=0x400000, .len=4096, .filesz=4096, .prot=5};
    desc->sections[1] = (struct program_image_section){.vaddr=0x600000, .len=8192, .filesz=8192, .prot=3};

    require(call(SYS_IOCTL, fd, MCEXEC_UP_PREPARE_IMAGE, 1) == -14);
    desc->num_sections = 17;
    require(call(SYS_IOCTL, fd, MCEXEC_UP_PREPARE_IMAGE, (long)desc) == -22);
    desc->num_sections = 2;
    image_args.offset = 8;
    require(call(SYS_IOCTL, fd, MCEXEC_UP_PREPARE_IMAGE, (long)desc) == -22);
    image_args.offset = 24;
    require(map_low(0x100000) == 0x100000);
    *(volatile unsigned long *)0x100000 = 0x13579bdfUL;
    require(call(SYS_IOCTL, fd, MCEXEC_UP_PREPARE_IMAGE, (long)desc) == -12);
    require(*(volatile unsigned long *)0x100000 == 0x13579bdfUL);
    require(call(SYS_MUNMAP, 0x100000, 4096, 0) == 0);

    unsigned before[6], after[6], cap_header[2] = {0x20080522, 0};
    capability_snapshot(before);
    before[0] &= ~(1U << 17); /* Exercise promotion rather than starting privileged. */
    require(call(126, (long)cap_header, (long)before, 0) == 0);
    capability_snapshot(before);
    require((before[0] & (1U << 17)) == 0);
    long prepared = call(SYS_IOCTL, fd, MCEXEC_UP_PREPARE_IMAGE, (long)desc);
    message("NATIVE_IMAGE_PREPARE error_negative="); print_number(prepared < 0);
    message(" magnitude="); print_number(prepared < 0 ? -prepared : prepared); message("\n");
    require(prepared == 0);
    capability_snapshot(after); compare((unsigned char *)before, (unsigned char *)after, sizeof(before));
    require(desc->pid == call(39, 0, 0, 0));
    require(desc->args == (char *)&image_args && desc->envs == (char *)image_envs);
    require(desc->user_start == 0 && desc->user_end > 0x100000000000UL && desc->user_end < (unsigned long)&image_request);
    require(desc->rprocess >= 0xffff800000000000UL && desc->rpgtable != 0 && desc->rpgtable % 4096 == 0);
    require(desc->sections[0].remote_pa && desc->sections[1].remote_pa);
    require(call(SYS_IOCTL, fd, MCEXEC_UP_PREPARE_IMAGE, (long)desc) == -16);
    references(2); /* One mcos file and one anonymous mirror file. */

    for (unsigned i = 0; i < sizeof(payload); i++) payload[i] = (i * 17 + 3) & 255;
    transfer(fd, desc->sections[0].remote_pa, payload, 4096, 0, 0);
    transfer(fd, desc->sections[1].remote_pa, payload, 8192, 0, 0);
    transfer(fd, desc->sections[1].remote_pa, readback, 8192, 1, 0);
    compare(payload, readback, 8192);
    compare(payload, (volatile unsigned char *)0x400000, 4096);
    compare(payload, (volatile unsigned char *)0x600000, 8192);
    message("NATIVE_IMAGE_MIRROR reads-complete\n");
    reject_text_write();
    compare(payload, (volatile unsigned char *)0x400000, 4096);
    message("NATIVE_IMAGE_MIRROR readonly-write-rejected\n");
    ((volatile unsigned char *)0x600000)[128] = 0x5a;
    message("NATIVE_IMAGE_MIRROR data-write-complete\n");
    transfer(fd, desc->sections[1].remote_pa, readback, 8192, 1, 0);
    payload[128] = 0x5a; compare(payload, readback, 8192);
    transfer(fd, desc->rpgtable, payload, 4096, 0, -13);
    transfer(fd, 0, readback, 4096, 1, -13);
    transfer(fd, desc->sections[0].remote_pa, (void *)1, 4096, 0, -14);
    transfer(fd, desc->sections[0].remote_pa, payload, 8192, 0, -13);
    unsigned long clear[2] = {0x600000, 0x602000};
    require(call(SYS_IOCTL, fd, MCEXEC_UP_RELEASE_USER_SPACE, (long)clear) == 0);
    compare(payload, (volatile unsigned char *)0x600000, 8192);
    require(call(SYS_MPROTECT, 0x400000, 4096, 3) == -95);
    int child = call(SYS_FORK, 0, 0, 0);
    require(child >= 0);
    if (child == 0) {
        /* An inherited MM needs the pending non-null PPD adapter before faults. */
        require(call(SYS_IOCTL, fd, MCEXEC_UP_RELEASE_USER_SPACE, (long)clear) == -22);
        call(SYS_EXIT, 0, 0, 0); __builtin_unreachable();
    }
    join(child);

    message("NATIVE_IMAGE_CAPTURE x86_64 prepared pid="); print_number(desc->pid);
    message(" user_end="); print_number(desc->user_end);
    message(" thread="); print_number(desc->rprocess);
    message(" pgtable="); print_number(desc->rpgtable);
    message(" text_pa="); print_number(desc->sections[0].remote_pa);
    message(" data_pa="); print_number(desc->sections[1].remote_pa); message("\n");
    const long pause[2] = {2, 0}; require(call(35, (long)pause, 0, 0) == 0);
    close_fd(fd); references(1);
    require(call(SYS_DELETE_MODULE, (long)"mcctrl", 2048, 0) == -EAGAIN);
    require(call(SYS_MUNMAP, 0x200000, 4096, 0) == 0);
    references(1);
    require(call(SYS_MUNMAP, desc->user_start, desc->user_end - desc->user_start, 0) == 0);
    references(0);
    /* A subsequent acknowledged request on the same CPU queue proves that
     * the earlier prepared cleanup handler returned past terminate_host. */
    fd = open_os(0); ppd(fd, 0, 0); close_fd(fd); references(0);
    message("NATIVE_MCCTRL_IMAGE x86_64 PASS checks="); print_number(image_checks);
    message(" prepared=1 transfer_bytes=12288 readback_bytes=16384 mirror_bytes=24576 readonly_write_sigbus=1 shared_mm_write=1 pte_clear=1 capability_restored=1 foreign_process_rejected=1 mapping_unload_veto=1 cleanup_barrier=1 final_release=1 applications=0\n");
    return 0;
}
