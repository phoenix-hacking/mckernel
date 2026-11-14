/* Functional McKernel OS/apps/Rust only; NO SECURITY TESTING.
 * One real PT_INTERP-on-interpreter rejection, not the four shebang cases.
 * Whole production object, real CRT --wrap=main and transparent libc calls.
 */
#define _GNU_SOURCE
#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <uprotocol.h>

extern struct program_load_desc *mcexec_load_alloc_desc_bridge(int);
extern struct program_load_desc *load_interp(struct program_load_desc *, FILE *);
extern void *__real_malloc(size_t);
extern void *__real_calloc(size_t, size_t);
extern void *__real_realloc(void *, size_t);
extern void __real_free(void *);
extern FILE *__real_fopen(const char *, const char *);
extern int __real_fclose(FILE *);
extern int __real_fflush(FILE *);

static const char input_path[] = "/retained/interp-bearing-input.elf";
enum phase { IDLE, ALLOCATE, OPEN_INPUT, VALIDATE_INPUT, LOAD_INTERP, CLOSE_INPUT };
static enum phase phase;
static uintptr_t original_base, current_base, file_address;
static size_t current_size;
static unsigned generation, live, failed, sequence;
static unsigned mallocs, callocs, reallocs, realloc_successes, production_frees;
static unsigned opens, callee_closes, caller_closes, diagnostic_flushes;
static unsigned allocation_order, open_order, realloc_order, flush_order;
static unsigned free_order, return_order, close_order, realloc_moved;
static int input_fd = -1;
static struct stat input_identity;

static _Noreturn void refuse(const char *message)
{
    (void)write(STDERR_FILENO, message, strlen(message));
    _Exit(96);
}

static void remember_initial(void *result, size_t bytes)
{
    if (phase != ALLOCATE || mallocs + callocs != 1 || !result ||
        bytes != sizeof(struct program_load_desc)) failed = 1;
    if (phase == ALLOCATE && result) {
        original_base = current_base = (uintptr_t)result;
        current_size = bytes;
        generation = live = 1;
        allocation_order = ++sequence;
    }
}

void *__wrap_malloc(size_t bytes)
{
    void *result = __real_malloc(bytes);
    int saved = errno;
    if (phase != IDLE) {
        ++mallocs;
        remember_initial(result,bytes);
    }
    errno = saved;
    return result;
}

void *__wrap_calloc(size_t count, size_t bytes)
{
    void *result = __real_calloc(count, bytes);
    int saved = errno;
    if (phase != IDLE) {
        ++callocs;
        /* Observe the actual libc allocation if the genuine malloc+zero body
         * was lowered to calloc. No wrapper chooses or substitutes a provider.
         */
        if (count && bytes > SIZE_MAX/count) failed = 1;
        else remember_initial(result,count*bytes);
    }
    errno = saved;
    return result;
}

void *__wrap_realloc(void *pointer, size_t bytes)
{
    /* Integer identities are captured while the original pointer is live.
     * Successful realloc consumes generation1 even when its address is reused.
     */
    uintptr_t incoming = (uintptr_t)pointer;
    unsigned tracked = phase == LOAD_INTERP && live && incoming == current_base;
    void *result = __real_realloc(pointer, bytes);
    int saved = errno;
    if (phase != IDLE) {
        ++reallocs;
        if (!tracked || incoming != original_base || reallocs != 1 || bytes != 1000 ||
            !result || generation != 1)
            failed = 1;
        if (tracked && result) {
            ++realloc_successes;
            realloc_moved = (uintptr_t)result != incoming;
            current_base = (uintptr_t)result;
            current_size = bytes;
            ++generation;
            realloc_order = ++sequence;
        }
    }
    errno = saved;
    return result;
}

void __wrap_free(void *pointer)
{
    int entering_errno = errno;
    uintptr_t address = (uintptr_t)pointer;
    unsigned tracked = pointer && live && address == current_base;
    if (phase != IDLE && pointer) {
        if (!tracked || phase != LOAD_INTERP || generation != 2 ||
            production_frees || diagnostic_flushes != 1)
            refuse("REFUSED: unexpected allocation ownership/free boundary\n");
        /* Mark the real current generation consumed; never inspect it again. */
        live = 0;
    }
    errno = entering_errno;
    __real_free(pointer);
    if (tracked && phase == LOAD_INTERP) {
        ++production_frees;
        free_order = ++sequence;
    }
}

FILE *__wrap_fopen(const char *path, const char *mode)
{
    FILE *result = __real_fopen(path, mode);
    int saved = errno;
    if (phase != IDLE) {
        ++opens;
        if (phase != OPEN_INPUT || opens != 1 || strcmp(path,input_path) ||
            strcmp(mode,"rb") || !result) failed = 1;
        if (result) {
            file_address = (uintptr_t)result;
            input_fd = fileno(result);
            if (input_fd < 0 || fstat(input_fd,&input_identity) ||
                !S_ISREG(input_identity.st_mode) || input_identity.st_size != 427048)
                failed = 1;
            open_order = ++sequence;
        }
    }
    errno = saved;
    return result;
}

int __wrap_fclose(FILE *stream)
{
    unsigned tracked = file_address && (uintptr_t)stream == file_address;
    int fd = input_fd;
    if (tracked && phase != CLOSE_INPUT) ++callee_closes;
    int result = __real_fclose(stream);
    int saved = errno;
    if (tracked) {
        int fd_result, fd_error;
        if (phase == CLOSE_INPUT) ++caller_closes;
        errno = 0;
        fd_result = fcntl(fd,F_GETFD);
        fd_error = errno;
        if (result || fd_result != -1 || fd_error != EBADF) failed = 1;
        file_address = 0; /* Released FILE is never dereferenced again. */
        close_order = ++sequence;
    }
    errno = saved;
    return result;
}

int __wrap_fflush(FILE *stream)
{
    int result = __real_fflush(stream);
    int saved = errno;
    if (phase == LOAD_INTERP) {
        if (stream != stderr || result) failed = 1;
        ++diagnostic_flushes;
        flush_order = ++sequence;
    }
    errno = saved;
    return result;
}

int __wrap_ioctl(int fd, unsigned long operation, ...)
{
    (void)fd; (void)operation;
    refuse("REFUSED: unexpected ioctl/device boundary\n");
}

static int same_input(const struct stat *now)
{
    return now->st_dev == input_identity.st_dev && now->st_ino == input_identity.st_ino &&
        now->st_mode == input_identity.st_mode && now->st_size == input_identity.st_size &&
        now->st_mtim.tv_sec == input_identity.st_mtim.tv_sec &&
        now->st_mtim.tv_nsec == input_identity.st_mtim.tv_nsec &&
        now->st_ctim.tv_sec == input_identity.st_ctim.tv_sec &&
        now->st_ctim.tv_nsec == input_identity.st_ctim.tv_nsec;
}

static int check_real_headers(FILE *fp, long *rejection_position)
{
    Elf64_Ehdr header;
    Elf64_Phdr phdr;
    unsigned loads = 0, interps = 0, first_interp = 0;
    if (fread(&header,sizeof(header),1,fp) != 1 ||
        memcmp(header.e_ident,ELFMAG,SELFMAG) ||
        header.e_ident[EI_CLASS] != ELFCLASS64 || header.e_ident[EI_DATA] != ELFDATA2LSB ||
        header.e_type != ET_DYN || header.e_machine != EM_X86_64 ||
        header.e_ehsize != sizeof(header) || header.e_phoff != 64 ||
        header.e_phentsize != sizeof(phdr) || header.e_phnum != 13 ||
        fseek(fp,(long)header.e_phoff,SEEK_SET)) return -1;
    for (unsigned i = 0; i < header.e_phnum; ++i) {
        if (fread(&phdr,sizeof(phdr),1,fp) != 1) return -1;
        if (phdr.p_type == PT_LOAD) ++loads;
        if (phdr.p_type == PT_INTERP) { first_interp = i; ++interps; }
    }
    if (loads != 4 || interps != 1) return -1;
    *rejection_position = (long)header.e_phoff + (long)(first_interp+1)*sizeof(phdr);
    return fseek(fp,0,SEEK_SET);
}

int __wrap_main(int argc, char **argv)
{
    struct program_load_desc *base, *result;
    struct stat after;
    FILE *fp;
    long rejection_position;
    int status = 0;
    if (argc != 1 || !argv) return 80;
    phase = ALLOCATE;
    base = mcexec_load_alloc_desc_bridge(0);
    if (!base || failed || mallocs + callocs != 1 || (uintptr_t)base != current_base ||
        base->magic != PLD_MAGIC || base->num_sections != 0 || base->stack_prot != 7)
        refuse("REFUSED: actual descriptor allocation unavailable/mismatched\n");
    phase = OPEN_INPUT;
    fp = fopen(input_path,"rb");
    if (!fp || failed) refuse("REFUSED: retained real ELF input unavailable/mismatched\n");
    phase = VALIDATE_INPUT;
    if (check_real_headers(fp,&rejection_position))
        refuse("REFUSED: retained input ELF headers differ\n");
    phase = LOAD_INTERP;
    result = load_interp(base,fp);
    return_order = ++sequence;
    /* base is stale after successful real realloc; no dereference/free of it.
     * Descriptor cleanup must already be production-owned; no compensation.
     */
    if (result || live || generation != 2 || current_size != 1000 ||
        mallocs + callocs != 1 || reallocs != 1 || realloc_successes != 1 ||
        production_frees != 1 || diagnostic_flushes != 1 || callee_closes ||
        !file_address || !(allocation_order < open_order && open_order < realloc_order &&
        realloc_order < flush_order && flush_order < free_order && free_order < return_order))
        failed = 1;
    if (!file_address || callee_closes)
        refuse("REFUSED: borrowed FILE was consumed by interpreter loader\n");
    phase = VALIDATE_INPUT;
    if (fcntl(input_fd,F_GETFD) < 0 || fstat(input_fd,&after) || !same_input(&after) ||
        ferror(fp) || ftell(fp) != rejection_position) failed = 1;
    phase = CLOSE_INPUT;
    if (fclose(fp)) failed = 1;
    phase = IDLE;
    if (opens != 1 || caller_closes != 1 || file_address || close_order <= return_order)
        failed = 1;
    if (printf("{\"case\":\"PT_INTERP_on_interpreter\",\"null_result\":%s,"
        "\"mallocs\":%u,\"callocs\":%u,\"reallocs\":%u,\"realloc_bytes\":%zu,"
        "\"generation\":%u,\"realloc_moved\":%s,\"production_frees\":%u,"
        "\"diagnostic_flushed_before_free\":%s,\"callee_FILE_closes\":%u,"
        "\"caller_FILE_closes\":%u,\"caller_descriptor_frees\":0,\"case_pass\":%s}\n",
        result ? "false" : "true",mallocs,callocs,reallocs,current_size,generation,
        realloc_moved ? "true" : "false",production_frees,
        flush_order && flush_order < free_order ? "true" : "false",
        callee_closes,caller_closes,failed ? "false" : "true") < 0) status = 82;
    if (failed) status = 81;
    if (fflush(stdout) || fflush(stderr)) status = 82;
    if (fclose(stdout)) status = 82;
    if (fclose(stderr)) status = 82;
    return status;
}

_Static_assert(sizeof(struct program_load_desc)==776 && _Alignof(struct program_load_desc)==8,"qualified x86_64 non-TOFU descriptor ABI");
_Static_assert(sizeof(struct program_image_section)==56 && _Alignof(struct program_image_section)==8,"qualified image section ABI");
