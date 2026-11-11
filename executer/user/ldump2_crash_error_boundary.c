/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Narrow remaining C ABI debt: setjmp's returns-twice semantics stay in C.
 * All conversion, allocation ownership and BFD work remain in the Rust body.
 * Includes the exact selected crash header; no pc/jmp_buf layout is guessed.
 */
#ifndef MCKERNEL_CRASH_DEFS_HEADER
#error The nonlocal boundary requires the selected actual crash provider header
#endif
#include MCKERNEL_CRASH_DEFS_HEADER
#include <setjmp.h>
#include <string.h>

#define INTERNAL __attribute__((visibility("hidden")))

_Static_assert(_Generic(&pc, struct program_context **: 1, default: 0),
               "actual crash context pointer ABI");
_Static_assert(sizeof(pc->main_loop_env) == sizeof(jmp_buf) &&
               sizeof(pc->foreach_loop_env) == sizeof(jmp_buf),
               "use actual header-declared opaque jump environments");
_Static_assert(_Generic(&readmem,
    int (*)(ulonglong, int, void *, long, char *, ulong): 1, default: 0),
    "actual readmem ABI");
_Static_assert(_Generic(&symbol_value, ulong (*)(char *): 1, default: 0),
               "actual symbol_value ABI");

struct mck_crash_restart {
    struct program_context *host;
    jmp_buf saved_main;
    jmp_buf saved_foreach;
    int pending; /* 0: ordinary return, 1: original main, 2: original foreach */
};

extern void mck_ldump2mcdump_rust_body(void *) INTERNAL;

static void restore_targets(struct mck_crash_restart *scope)
{
    memcpy(scope->host->main_loop_env, scope->saved_main, sizeof(jmp_buf));
    memcpy(scope->host->foreach_loop_env, scope->saved_foreach, sizeof(jmp_buf));
}

/* These setjmp frames are BELOW the calling Rust frame. The provider's real
 * longjmp therefore crosses only C frames, then becomes an ordinary Rust
 * return. The original opaque environments remain live in the command caller.
 * Crash's normal synchronous command context keeps pc stable through calls.
 */
int INTERNAL
mck_crash_guarded_readmem(void *opaque, ulonglong addr, int type, void *buf,
                          long size, char *msg, ulong flags, int *result)
{
    struct mck_crash_restart *scope = opaque;
    if (setjmp(scope->host->main_loop_env) != 0) {
        scope->pending = 1;
        restore_targets(scope);
        return 0;
    }
    if (setjmp(scope->host->foreach_loop_env) != 0) {
        scope->pending = 2;
        restore_targets(scope);
        return 0;
    }
    *result = readmem(addr, type, buf, size, msg, flags);
    restore_targets(scope);
    return 1;
}

int INTERNAL
mck_crash_guarded_symbol_value(void *opaque, char *name, ulong *value)
{
    struct mck_crash_restart *scope = opaque;
    if (setjmp(scope->host->main_loop_env) != 0) {
        scope->pending = 1;
        restore_targets(scope);
        return 0;
    }
    if (setjmp(scope->host->foreach_loop_env) != 0) {
        scope->pending = 2;
        restore_targets(scope);
        return 0;
    }
    *value = symbol_value(name);
    restore_targets(scope);
    return 1;
}

/* This is the sole public command entry, still void(void). All Rust owners
 * have returned and dropped before the original destination is resumed. Real
 * readmem flags and __error diagnostics/foreach selection are never replaced
 * or replayed. Ordinary returned provider values, including false/zero, remain
 * distinct from an intercepted nonlocal transfer.
 */
void cmd_ldump2mcdump(void)
{
    struct mck_crash_restart scope;
    scope.host = pc;
    scope.pending = 0;
    memcpy(scope.saved_main, pc->main_loop_env, sizeof(jmp_buf));
    memcpy(scope.saved_foreach, pc->foreach_loop_env, sizeof(jmp_buf));
    mck_ldump2mcdump_rust_body(&scope);
    restore_targets(&scope);
    if (scope.pending == 2)
        RESUME_FOREACH();
    if (scope.pending == 1)
        RESTART();
}
