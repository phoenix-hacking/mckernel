/* Functional McKernel OS/apps + Rust/assembly only; no security testing.
 * One IPC_PRIVATE segment, only two own-process attachments, normal RMID/detach.
 * Raw x86_64 syscalls exercise key int32 narrowing and the real user SHM ABI.
 * No global key lookup, IPC inventory, other-process memory or permission change.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>
#if !defined(__x86_64__) || __SIZEOF_POINTER__ != 8
#error selected Linux x86_64 LP64 ABI required
#endif
_Static_assert(sizeof(long) == 8 && sizeof(size_t) == 8 && sizeof(key_t) == 4 && sizeof(int) == 4 && sizeof(pid_t) == 4,
               "selected shmget key/size ABI");
_Static_assert(sizeof(struct shmid_ds) == 112 && offsetof(struct shmid_ds, shm_segsz) == 48 &&
               offsetof(struct shmid_ds, shm_nattch) == 88, "selected public shmid_ds ABI");
_Static_assert(SYS_shmget == 29 && SYS_shmat == 30 && SYS_shmctl == 31 && SYS_shmdt == 67,
               "selected x86_64 SHM syscall numbers");
static long control(int id, int command, struct shmid_ds *ds) {
    return syscall(SYS_shmctl, (long)id, (long)command, ds);
}
int main(void) {
    const size_t bytes = 4096;
    const unsigned int bad_huge = (unsigned int)SHM_HUGETLB | (20u << 26);
    errno = 0;
    long rejected = syscall(SYS_shmget, 0UL, (unsigned long)bytes,
                            (unsigned long)(IPC_CREAT | 0600u | bad_huge));
    int huge_errno = errno;
    if (rejected != -1 || huge_errno != EINVAL) {
        int cleanup = 0;
        if (rejected >= 0 && rejected <= INT_MAX) cleanup = (int)control((int)rejected, IPC_RMID, NULL);
        fprintf(stderr, "shm invalid huge shift result=%ld errno=%d cleanup=%d\n", rejected, huge_errno, cleanup);
        return 1;
    }
    /* Genuine key_t narrows this register word to IPC_PRIVATE==0. */
    long raw_id = syscall(SYS_shmget, 0x100000000UL, (unsigned long)bytes,
                          (unsigned long)(IPC_CREAT | 0600));
    if (raw_id < 0) { perror("private shmget"); return 1; }
    if (raw_id > INT_MAX) {
        fputs("SHM ID outside selected int32 ABI; ownership cleanup unproved\n", stderr);
        return 1;
    }
    int id = (int)raw_id, removed_attempted = 0, rc = 1, cleanup_failed = 0;
    void *a = (void *)-1, *b = (void *)-1;
    struct shmid_ds ds = {0};
    a = (void *)syscall(SYS_shmat, (long)id, 0UL, 0UL);
    if (a == (void *)-1) { perror("private shmat first"); goto cleanup; }
    b = (void *)syscall(SYS_shmat, (long)id, 0UL, 0UL);
    if (b == (void *)-1) { perror("private shmat second"); goto cleanup; }
    if (a == b) { fputs("SHM attachments did not have distinct owned addresses\n", stderr); goto cleanup; }
    volatile unsigned char *x = a, *y = b;
    for (size_t i = 0; i < bytes; ++i) {
        if (x[i] != 0 || y[i] != 0) { fputs("new private SHM was not zeroed\n", stderr); goto cleanup; }
        x[i] = (unsigned char)((i * 11u + 3u) & 255u);
    }
    for (size_t i = 0; i < bytes; ++i)
        if (y[i] != (unsigned char)((i * 11u + 3u) & 255u)) { fputs("private SHM aliases disagree\n", stderr); goto cleanup; }
    y[bytes - 1] = 0xa7;
    if (x[bytes - 1] != 0xa7 || control(id, IPC_STAT, &ds) != 0 ||
        ds.shm_segsz != bytes || (ds.shm_perm.mode & 0777) != 0600 ||
        ds.shm_cpid != getpid() || ds.shm_nattch != 2) {
        fputs("private SHM initial metadata/alias contract failed\n", stderr); goto cleanup;
    }
    removed_attempted = 1; /* Never repeat an uncertain/remove-failed action. */
    if (control(id, IPC_RMID, NULL) != 0) { perror("private SHM mark remove"); goto cleanup; }
    if (control(id, IPC_STAT, &ds) != 0 || !(ds.shm_perm.mode & SHM_DEST) ||
        ds.shm_nattch != 2 || x[bytes - 1] != 0xa7 || y[bytes - 1] != 0xa7) {
        fputs("marked SHM lifetime did not preserve own attachments\n", stderr); goto cleanup;
    }
    if (syscall(SYS_shmdt, b) != 0) { perror("private shmdt second"); b = (void *)-1; cleanup_failed = 1; goto cleanup; }
    b = (void *)-1;
    if (control(id, IPC_STAT, &ds) != 0 || ds.shm_nattch != 1) {
        fputs("private SHM first detach refcount contract failed\n", stderr); goto cleanup;
    }
    if (syscall(SYS_shmdt, a) != 0) { perror("private shmdt first"); a = (void *)-1; cleanup_failed = 1; goto cleanup; }
    a = (void *)-1;
    errno = 0;
    long gone = control(id, IPC_STAT, &ds);
    int removed_errno = errno;
    if (gone != -1 || (removed_errno != EINVAL && removed_errno != EIDRM)) {
        fputs("destroyed own SHM ID still accepted or wrong source-defined lookup error\n", stderr); goto cleanup;
    }
    rc = 0;
cleanup:
    if (!removed_attempted) {
        removed_attempted = 1;
        if (control(id, IPC_RMID, NULL) != 0) { perror("private cleanup RMID"); cleanup_failed = 1; }
    }
    if (b != (void *)-1 && syscall(SYS_shmdt, b) != 0) { perror("private cleanup second detach"); cleanup_failed = 1; }
    if (a != (void *)-1 && syscall(SYS_shmdt, a) != 0) { perror("private cleanup first detach"); cleanup_failed = 1; }
    if (rc || cleanup_failed) return 1;
    puts("shm_private huge_invalid=1 key_narrowed_private=1 alias_shared=1 size=4096 nattch_initial=2 marked_live=1 nattch_after_detach=1 removed_lookup_rejected=1 cleanup=1");
    return 0;
}
