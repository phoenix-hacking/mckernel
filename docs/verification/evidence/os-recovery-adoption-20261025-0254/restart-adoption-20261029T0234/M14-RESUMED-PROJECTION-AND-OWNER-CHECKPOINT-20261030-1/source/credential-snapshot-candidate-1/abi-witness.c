/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Compile-only witness source; not run or compiled by this assignment. */
#include "credential-owner-abi.h"
#include <process.h>
const size_t f03_cred_c_process_offsets_v1[] = {
    offsetof(struct process, update_lock),
    offsetof(struct process, ruid), offsetof(struct process, euid),
    offsetof(struct process, suid), offsetof(struct process, fsuid),
    offsetof(struct process, rgid), offsetof(struct process, egid),
    offsetof(struct process, sgid), offsetof(struct process, fsgid),
};
_Static_assert(sizeof(((struct process *)0)->ruid) == sizeof(int), "uid field width");
_Static_assert(sizeof(((struct process *)0)->rgid) == sizeof(int), "gid field width");
static struct f03_cred_begin_v1 (*const begin_type)(struct process *, int) = f03_cred_owner_begin_v1;
static struct f03_cred_reply_v1 (*const snapshot_type)(void *) = f03_cred_owner_snapshot_v1;
static int (*const finish_type)(void *, int, int) = f03_cred_owner_finish_v1;
static void (*const uid_type)(void) = do_setresuid;
static void (*const gid_type)(void) = do_setresgid;
/* By-value ABI needs an emitted C/Rust cross-language witness on the selected
 * architecture/compiler pair. Matching static layout assertions alone do not
 * qualify register/hidden-result calling convention or runtime transport. */
