/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Private ABI contract only: declares no runtime implementation or admission. */
#ifndef F03_CREDENTIAL_OWNER_ABI_V1
#define F03_CREDENTIAL_OWNER_ABI_V1
#include <stddef.h>
struct process;
struct f03_cred_begin_v1 { void *token; int status; int reserved; };
struct f03_cred_reply_v1 { int outcome; int status; int ids[8]; };
struct f03_cred_begin_v1 f03_cred_owner_begin_v1(struct process *, int);
struct f03_cred_reply_v1 f03_cred_owner_snapshot_v1(void *);
int f03_cred_owner_finish_v1(void *, int, int);
void f03_cred_refresh_failure_v1(struct process *, int, int);
void do_setresuid(void);
void do_setresgid(void);
_Static_assert(sizeof(int) == 4, "CInt width");
_Static_assert(sizeof(void *) == 8, "supported pointer width");
_Static_assert(sizeof(struct f03_cred_begin_v1) == 16, "begin size");
_Static_assert(_Alignof(struct f03_cred_begin_v1) == 8, "begin alignment");
_Static_assert(offsetof(struct f03_cred_begin_v1, status) == 8, "begin status");
_Static_assert(sizeof(struct f03_cred_reply_v1) == 40, "reply size");
_Static_assert(_Alignof(struct f03_cred_reply_v1) == 4, "reply alignment");
_Static_assert(offsetof(struct f03_cred_reply_v1, ids) == 8, "reply ids");
#endif
