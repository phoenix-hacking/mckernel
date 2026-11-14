/* Functional McKernel OS/apps/Rust only; NO SECURITY TESTING.
 * Changed-object adaptation. Genuine libc observations, no provider stand-ins.
 * Standard CRT --wrap=main selects this caller, not production main.
 */
#define _GNU_SOURCE
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

extern int load_elf_desc(char *, struct program_load_desc **, char **);
extern int load_elf_desc_shebang(char *, struct program_load_desc **, char ***, int);
extern int mcexec_load_main_desc_body(char *, struct program_load_desc **, char ***);
extern FILE *__real_fopen(const char *, const char *);
extern ssize_t __real_getline(char **, size_t *, FILE *);
extern int __real_fclose(FILE *);
extern void *__real_malloc(size_t);
extern void __real_free(void *);

static const unsigned char direct_bytes[] = "#! \t/bin/true \t\n";
static const unsigned char outer_bytes[] = "#! \t/output/inner.shebang outerarg \t\n";
static const unsigned char inner_bytes[] = "#! /output/eof.shebang innerarg\n";
static const unsigned char eof_bytes[] = "#!";
static struct input {
    const char *path;
    const unsigned char *bytes;
    size_t length;
    dev_t device;
    ino_t inode;
} inputs[] = {
    {"/output/input.shebang", direct_bytes, sizeof(direct_bytes)-1, 0, 0},
    {"/output/outer.shebang", outer_bytes, sizeof(outer_bytes)-1, 0, 0},
    {"/output/inner.shebang", inner_bytes, sizeof(inner_bytes)-1, 0, 0},
    {"/output/eof.shebang", eof_bytes, sizeof(eof_bytes)-1, 0, 0}
};
enum { GETLINE_OWNER = 1, PACKED_OWNER = 2 };
static struct allocation {
    uintptr_t base;
    size_t bytes;
    unsigned kind, file_sequence, released, production_release;
} allocations[8];
static unsigned allocation_count, line_count, packed_count, production_line_frees;
static unsigned production_packed_frees, caller_transferred_base_frees;
static unsigned opens, lines, closes, line_errors, packed_copy_proved, packed_final_order;
static int observing, failed, current_case, input_fd, active_input;
static uintptr_t file_identity;
static unsigned latest_packed;
static char ***observed_argv_slot;

static _Noreturn void refuse(const char *message)
{
    (void)write(STDERR_FILENO, message, strlen(message));
    _Exit(96);
}

static void remember(void *base, size_t bytes, unsigned kind)
{
    if (!base) return;
    if (allocation_count == 8) { failed = 1; return; }
    allocations[allocation_count] = (struct allocation){
        (uintptr_t)base, bytes, kind, opens, 0, 0};
    if (kind == PACKED_OWNER) {
        latest_packed = allocation_count;
        ++packed_count;
    } else {
        ++line_count;
    }
    ++allocation_count;
}

FILE *__wrap_fopen(const char *path, const char *mode)
{
    FILE *result = __real_fopen(path, mode);
    int saved = errno;
    if (observing) {
        struct stat identity;
        size_t index;
        if (file_identity) failed = 1; /* Original FILE must close before recursion. */
        ++opens;
        for (index = 0; index < 4 && strcmp(path, inputs[index].path); ++index) {}
        if (index == 4 || strcmp(mode, "rb") || !result) {
            failed = 1;
        } else {
            active_input = (int)index;
            file_identity = (uintptr_t)result;
            input_fd = fileno(result);
            if (input_fd < 0 || fstat(input_fd, &identity) ||
                identity.st_dev != inputs[index].device || identity.st_ino != inputs[index].inode)
                failed = 1;
        }
    }
    errno = saved;
    return result;
}

ssize_t __wrap_getline(char **line, size_t *capacity, FILE *stream)
{
    int tracked = observing && (uintptr_t)stream == file_identity;
    int entering_errno = errno;
    ssize_t result = __real_getline(line, capacity, stream);
    int saved = errno;
    if (tracked) {
        ++lines;
        if (entering_errno != 0) failed = 1; /* Repaired producer clears errno. */
        remember(*line, *capacity, GETLINE_OWNER);
        if (active_input == 3) {
            ++line_errors;
            if (result != -1 || saved != 0) failed = 1; /* Genuine regular-file EOF. */
        } else if (result != (ssize_t)(inputs[active_input].length - 2) ||
                   !*line || *capacity < (size_t)result + 1) {
            failed = 1;
        }
    }
    errno = saved;
    return result;
}

int __wrap_fclose(FILE *stream)
{
    int tracked = observing && (uintptr_t)stream == file_identity;
    int fd = input_fd;
    int result = __real_fclose(stream);
    int saved = errno;
    if (tracked) {
        int fd_result, fd_error;
        ++closes;
        errno = 0;
        fd_result = fcntl(fd, F_GETFD);
        fd_error = errno;
        if (result || fd_result != -1 || fd_error != EBADF) failed = 1;
        file_identity = 0; /* Never access the released FILE. */
    }
    errno = saved;
    return result;
}

void *__wrap_malloc(size_t bytes)
{
    void *result = __real_malloc(bytes);
    int saved = errno;
    /* Link-time wrapping observes direct production malloc calls only, not
     * libc's internal getline allocator or an invented allocation provider. */
    if (observing) remember(result, bytes, PACKED_OWNER);
    errno = saved;
    return result;
}

static int verify_current_packed(void)
{
    static const char *const expected[4] = {
        "/output/eof.shebang", "innerarg", "/output/inner.shebang", "outerarg"};
    struct allocation *owner = &allocations[latest_packed];
    char **table;
    if (!observed_argv_slot || owner->released || owner->kind != PACKED_OWNER ||
        owner->bytes < 5 * sizeof(char *) ||
        (uintptr_t)*observed_argv_slot != owner->base)
        return 0;
    table = *observed_argv_slot;
    for (unsigned index = 0; index < 4; ++index) {
        uintptr_t address = (uintptr_t)table[index];
        size_t length = strlen(expected[index]) + 1;
        if (address < owner->base + 5 * sizeof(char *) ||
            address > owner->base + owner->bytes ||
            length > owner->base + owner->bytes - address ||
            memcmp(table[index], expected[index], length))
            return 0;
    }
    return table[4] == NULL;
}

void __wrap_free(void *pointer)
{
    int entering_errno = errno;
    uintptr_t address = (uintptr_t)pointer;
    int match = -1;
    for (unsigned index = 0; pointer && index < allocation_count; ++index) {
        if (!allocations[index].released && allocations[index].base == address) {
            match = (int)index;
            break;
        }
    }
    if (match >= 0) {
        struct allocation *owner = &allocations[match];
        if (observing) {
            owner->production_release = 1;
            if (owner->kind == GETLINE_OWNER) {
                if (closes < owner->file_sequence) failed = 1;
                ++production_line_frees;
            } else {
                ++production_packed_frees;
                /* First old argv is released only after the replacement has
                 * copied/published every string. Final main-error release is
                 * after recursion's last borrow and every getline base free. */
                if (current_case == 3 && packed_count == 2) {
                    if (!verify_current_packed()) failed = 1;
                    if ((unsigned)match != latest_packed) ++packed_copy_proved;
                    else if (production_line_frees == line_count) ++packed_final_order;
                }
            }
        } else {
            if (current_case != 0 || owner->kind != GETLINE_OWNER) failed = 1;
            ++caller_transferred_base_frees;
        }
        owner->released = 1;
    } else if (pointer) {
        for (unsigned index = 0; index < allocation_count; ++index) {
            struct allocation *owner = &allocations[index];
            if ((!owner->released && address > owner->base &&
                 address - owner->base < owner->bytes) || address == owner->base)
                refuse("REFUSED: tracked interior/double free\n");
        }
    }
    errno = entering_errno;
    __real_free(pointer); /* Preserve real allocator result/error behavior. */
}

int __wrap_ioctl(int fd, unsigned long operation, ...)
{
    (void)fd;
    (void)operation;
    refuse("REFUSED: unexpected ioctl/device boundary\n");
}

static int create_inputs(void)
{
    for (unsigned index = 0; index < 4; ++index) {
        struct stat identity;
        size_t offset = 0;
        int fd = open(inputs[index].path, O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC, 0700);
        if (fd < 0) return -1;
        while (offset < inputs[index].length) {
            ssize_t written = write(fd, inputs[index].bytes + offset, inputs[index].length - offset);
            if (written < 0 && errno == EINTR) continue;
            if (written <= 0) { (void)close(fd); return -1; }
            offset += (size_t)written;
        }
        if (fchmod(fd,0700) || fsync(fd) || fstat(fd,&identity) ||
            !S_ISREG(identity.st_mode) || (identity.st_mode & 0777) != 0700 ||
            identity.st_size != (off_t)inputs[index].length) {
            (void)close(fd); return -1;
        }
        inputs[index].device = identity.st_dev;
        inputs[index].inode = identity.st_ino;
        if (close(fd)) return -1;
    }
    return 0;
}

static int run_case(int which)
{
    struct program_load_desc *desc = NULL;
    char *shebang = NULL;
    char **argv = NULL;
    int result, string_exact = 0;
    memset(allocations,0,sizeof(allocations));
    allocation_count=line_count=packed_count=production_line_frees=0;
    production_packed_frees=caller_transferred_base_frees=0;
    opens=lines=closes=line_errors=packed_copy_proved=packed_final_order=0;
    file_identity=0; failed=0; current_case=which; observed_argv_slot=&argv;
    errno=EDOM; /* Genuine EOF must not return this stale caller errno. */
    observing=1;
    if (which == 0 || which == 1)
        result=load_elf_desc((char *)inputs[which ? 3 : 0].path,&desc,&shebang);
    else if (which == 2)
        result=load_elf_desc_shebang((char *)inputs[1].path,&desc,NULL,0);
    else
        result=mcexec_load_main_desc_body((char *)inputs[1].path,&desc,&argv);
    observing=0;

    if (which == 0) {
        if (allocation_count == 1 && !allocations[0].released &&
            allocations[0].bytes >= sizeof("/bin/true") &&
            (uintptr_t)shebang == allocations[0].base)
            string_exact=!memcmp(shebang,"/bin/true",sizeof("/bin/true"));
        if (result || !string_exact || desc || opens!=1 || closes!=1 ||
            production_line_frees || packed_count) failed=1;
        /* Direct public load_elf_desc transferred this genuine base to us.
         * This caller-owned free is NOT recursive/main production cleanup. */
        if (string_exact) { free(shebang); shebang=NULL; }
        if (caller_transferred_base_frees != 1) failed=1;
    } else {
        /* Null-argv recursion preserves the original unsplit optional-argument
         * convention: the real lookup of "inner.shebang outerarg" returns
         * ENOENT, then the original successful getline base is freed. */
        if (result != (which==3 ? 1 : which==2 ? ENOENT : ENOEXEC) ||
            desc || shebang || argv || line_errors!=(which==2 ? 0U : 1U) ||
            opens!=(which==3 ? 3U : 1U) || closes!=opens ||
            production_line_frees!=line_count || caller_transferred_base_frees)
            failed=1;
        if (which==3) {
            if (packed_count!=2 || production_packed_frees!=2 ||
                packed_copy_proved!=1 || packed_final_order!=1) failed=1;
        } else if (packed_count) failed=1;
    }
    for (unsigned index=0;index<allocation_count;++index)
        if (!allocations[index].released) failed=1; /* No test compensation. */
    if (file_identity || lines!=opens) failed=1;
    if (printf("{\"case\":%d,\"result\":%d,\"exact_trim_base_return\":%s,"
               "\"file_opens\":%u,\"file_closes\":%u,\"getline_allocations\":%u,"
               "\"production_getline_frees\":%u,\"production_packed_frees\":%u,"
               "\"caller_transferred_base_frees\":%u,\"copy_before_old_free\":%u,"
               "\"main_error_free_after_recursive_borrows\":%u,\"case_pass\":%s}\n",
               which,result,string_exact?"true":"false",opens,closes,line_count,
               production_line_frees,production_packed_frees,caller_transferred_base_frees,
               packed_copy_proved,packed_final_order,failed?"false":"true")<0) failed=1;
    return failed;
}

int __wrap_main(int argc,char **argv)
{
    int result=0;
    if (argc!=1 || !argv || create_inputs()) return 80;
    /* Four affected, fixed paths; not a generated case matrix or new quota. */
    for (int which=0;which<4;++which) if (run_case(which)) {result=81;break;}
    if (fflush(stdout)||fflush(stderr)) result=82;
    if (fclose(stdout)) result=82;
    if (fclose(stderr)) result=82;
    return result;
}

_Static_assert(sizeof(direct_bytes)-1==16,"unchanged exact direct shebang input");
_Static_assert(sizeof(struct program_load_desc)==776 && _Alignof(struct program_load_desc)==8,"qualified x86_64 non-TOFU descriptor ABI");
