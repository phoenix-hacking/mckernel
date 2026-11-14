/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
/* Test-only inclusion after the selected actual x86 syscall.h and IKC headers.
 * No runtime object, implementation, or executable authority is supplied. */
_Static_assert(sizeof(struct syscall_request) == 72, "request wire size");
_Static_assert(__alignof__(struct syscall_request) == 8, "request natural alignment");
_Static_assert(__builtin_offsetof(struct syscall_request, rtid) == 0, "request rtid");
_Static_assert(__builtin_offsetof(struct syscall_request, ttid) == 4, "request ttid");
_Static_assert(__builtin_offsetof(struct syscall_request, valid) == 8, "request valid");
_Static_assert(__builtin_offsetof(struct syscall_request, number) == 16, "request number");
_Static_assert(__builtin_offsetof(struct syscall_request, args) == 24, "six request args");
_Static_assert(sizeof(((struct syscall_request *)0)->args) == 48, "six wire words");
_Static_assert(sizeof(struct ikc_scd_packet) == 128, "full IKC packet");
_Static_assert(__alignof__(struct ikc_scd_packet) == 8, "packet alignment");
_Static_assert(__builtin_offsetof(struct ikc_scd_packet, header) == 0, "packet header");
_Static_assert(__builtin_offsetof(struct ikc_scd_packet, msg) == 8, "packet message");
_Static_assert(__builtin_offsetof(struct ikc_scd_packet, err) == 12, "packet error");
_Static_assert(__builtin_offsetof(struct ikc_scd_packet, reply) == 16, "packet reply");
_Static_assert(__builtin_offsetof(struct ikc_scd_packet, req) == 48, "packet request");
_Static_assert(__builtin_offsetof(struct ikc_scd_packet, resp_pa) == 120, "packet response");
