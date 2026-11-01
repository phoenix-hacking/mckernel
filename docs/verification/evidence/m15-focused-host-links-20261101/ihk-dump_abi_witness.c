/* NONSHIPPED build/test orchestration. Functional OS work only; no security testing.
 * Extend the existing m15-bfd real-header witness contract with dump-only fields.
 * Never link this witness into libihk or a delivered tool. */
#include <bfd.h>
#include <errno.h>
#include <limits.h>
#include <pwd.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <ihk/ihk_host_user.h>
#include <ihk/ihklib.h>
#if !defined(__x86_64__) || !defined(__linux__)
#error Dump witness currently qualifies Linux x86_64 LP64 only
#endif
#ifndef PAGE_SIZE
#error Pass the actual selected libihk PAGE_SIZE definition
#endif
_Static_assert(sizeof(long) == 8 && sizeof(void *) == 8 && CHAR_BIT == 8, "LP64");
_Static_assert(sizeof(int) == 4 && CHAR_MIN == -128, "int and char ABI");
_Static_assert(sizeof(bfd_format) == sizeof(int), "BFD format enum ABI");
#define SAME(type, expression) _Static_assert( \
    __builtin_types_compatible_p(type, __typeof__(expression)), #expression " ABI")
typedef __typeof__(bfd_close((bfd *)0)) dump_bfd_bool;
SAME(time_t, (long)0);
SAME(uid_t, (unsigned int)0);
SAME(bfd_size_type, (unsigned long)0);
SAME(bfd_vma, (unsigned long)0);
SAME(file_ptr, (long)0);
SAME(flagword, (unsigned int)0);
SAME(unsigned int (*)(void), &bfd_init);
SAME(bfd *(*)(const char *, const char *, const char *, int), &bfd_fopen);
SAME(dump_bfd_bool (*)(bfd *, bfd_format), &bfd_set_format);
SAME(asection *(*)(bfd *, const char *), &bfd_make_section_anyway);
SAME(dump_bfd_bool (*)(asection *, bfd_size_type), &bfd_set_section_size);
SAME(dump_bfd_bool (*)(asection *, flagword), &bfd_set_section_flags);
SAME(asection *(*)(bfd *, const char *), &bfd_get_section_by_name);
SAME(dump_bfd_bool (*)(bfd *, asection *, const void *, file_ptr, bfd_size_type),
     &bfd_set_section_contents);
SAME(bfd_size_type, ((asection *)0)->size);
SAME(bfd_vma, ((asection *)0)->vma);
SAME(char *, ((struct passwd *)0)->pw_name);
SAME(int, ((dumpargs_t *)0)->cmd);
SAME(unsigned int, ((dumpargs_t *)0)->level);
SAME(long, ((dumpargs_t *)0)->start);
SAME(long, ((dumpargs_t *)0)->size);
SAME(void *, ((dumpargs_t *)0)->buf);
SAME(void *[4], ((dumpargs_t *)0)->spare);
SAME(int, ((dump_mem_chunks_t *)0)->nr_chunks);
SAME(unsigned long, ((dump_mem_chunks_t *)0)->kernel_base);
SAME(unsigned long, ((dump_mem_chunks_t *)0)->phys_start);
SAME(unsigned long, ((struct dump_mem_chunk *)0)->addr);
SAME(unsigned long, ((struct dump_mem_chunk *)0)->size);
_Static_assert(__builtin_types_compatible_p(dump_bfd_bool, int) ||
               __builtin_types_compatible_p(dump_bfd_bool, bool), "BFD boolean ABI");
_Static_assert(offsetof(asection, size) % _Alignof(unsigned long) == 0, "section size aligned");
_Static_assert(offsetof(asection, vma) % _Alignof(unsigned long) == 0, "section vma aligned");
_Static_assert(offsetof(struct passwd, pw_name) % _Alignof(char *) == 0, "passwd name aligned");
_Static_assert(offsetof(dump_mem_chunks_t, chunks) == sizeof(dump_mem_chunks_t),
               "flexible chunk array follows header");
#define SIZE(name, value) printf("pub const " #name ": usize = %zu;\n", (size_t)(value))
#define INT(name, value) printf("pub const " #name ": core::ffi::c_int = %d;\n", (int)(value))
#define UINT(name, value) printf("pub const " #name ": core::ffi::c_uint = %u;\n", (unsigned)(value))
#define ULONG(name, value) printf("pub const " #name ": core::ffi::c_ulong = %lu;\n", (unsigned long)(value))
int main(void)
{
    puts("// Generated from selected real BFD/libc/IHK headers; never supply guessed offsets.");
    if (__builtin_types_compatible_p(dump_bfd_bool, bool)) {
        puts("pub type BfdBool = bool;\npub const BFD_FALSE: BfdBool = false;");
    } else {
        puts("pub type BfdBool = core::ffi::c_int;\npub const BFD_FALSE: BfdBool = 0;");
    }
    SIZE(DUMP_ARGS_SIZE, sizeof(dumpargs_t));
    SIZE(DUMP_ARGS_LEVEL, offsetof(dumpargs_t, level));
    SIZE(DUMP_ARGS_START, offsetof(dumpargs_t, start));
    SIZE(DUMP_ARGS_SIZE_FIELD, offsetof(dumpargs_t, size));
    SIZE(DUMP_ARGS_BUF, offsetof(dumpargs_t, buf));
    SIZE(DUMP_ARGS_SPARE, offsetof(dumpargs_t, spare));
    SIZE(MEMORY_CHUNK_SIZE, sizeof(struct dump_mem_chunk));
    SIZE(MEMORY_CHUNK_SIZE_FIELD, offsetof(struct dump_mem_chunk, size));
    SIZE(MEMORY_CHUNKS_SIZE, sizeof(dump_mem_chunks_t));
    SIZE(MEMORY_CHUNKS_DATA, offsetof(dump_mem_chunks_t, chunks));
    SIZE(MEMORY_CHUNKS_KERNEL_BASE, offsetof(dump_mem_chunks_t, kernel_base));
    SIZE(MEMORY_CHUNKS_PHYS_START, offsetof(dump_mem_chunks_t, phys_start));
    SIZE(PASSWD_NAME, offsetof(struct passwd, pw_name));
    SIZE(SECTION_SIZE, offsetof(asection, size));
    SIZE(SECTION_VMA, offsetof(asection, vma));
    SIZE(HOSTNAME_CAPACITY, HOST_NAME_MAX + 1);
    ULONG(PAGE_SIZE, PAGE_SIZE);
    ULONG(IHK_OS_DUMP, IHK_OS_DUMP);
    INT(DUMP_NMI, DUMP_NMI);
    INT(DUMP_READ, DUMP_READ);
    INT(DUMP_SET_LEVEL, DUMP_SET_LEVEL);
    INT(DUMP_QUERY_NUM_MEM_AREAS, DUMP_QUERY_NUM_MEM_AREAS);
    INT(DUMP_QUERY_MEM_AREAS, DUMP_QUERY_MEM_AREAS);
    INT(DUMP_NMI_CONT, DUMP_NMI_CONT);
    INT(IHK_STATUS_INACTIVE, IHK_STATUS_INACTIVE);
    INT(EINVAL, EINVAL);
    INT(ENOMEM, ENOMEM);
    INT(EFAULT, EFAULT);
    INT(W_OK, W_OK);
    INT(BFD_OBJECT, bfd_object);
    UINT(SEC_ALLOC, SEC_ALLOC);
    UINT(SEC_HAS_CONTENTS, SEC_HAS_CONTENTS);
    return 0;
}
