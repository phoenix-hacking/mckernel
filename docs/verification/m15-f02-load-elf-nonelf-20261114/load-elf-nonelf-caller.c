/* Functional McKernel OS/apps/Rust/allowed assembly ONLY; NO SECURITY TESTING.
 * ONE public load_elf non-ELF regular-file early rejection. Whole real object.
 * No descriptor allocation, PHDR traversal, GET_CREDV, production main/backend.
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

extern struct program_load_desc *load_elf(FILE *,char **);
extern FILE *__real_fopen(const char *,const char *);
extern size_t __real_fread(void *,size_t,size_t,FILE *);
extern int __real_fclose(FILE *);
extern int __real_fflush(FILE *);
extern void *__real_malloc(size_t);
extern void *__real_calloc(size_t,size_t);
extern void *__real_realloc(void *,size_t);
extern void __real_free(void *);

static const char input_path[]="/retained/main-desc-source.txt";
enum phase { IDLE, OPEN_INPUT, LOAD_ELF, VALIDATE_INPUT, CLOSE_INPUT };
static enum phase phase;
static uintptr_t file_address;
static int input_fd=-1;
static struct stat input_identity;
static char **interp_slot;
static unsigned opens,reads,full_reads,output_reset_before_read,flushes;
static unsigned callee_closes,caller_closes,project_heap_calls,failed,sequence;
static unsigned read_order,flush_order,return_order,last_FILE_borrow_order,close_order;
static unsigned char actual_first4[4];

static _Noreturn void refuse(const char *message)
{
    (void)write(STDERR_FILENO,message,strlen(message));
    _Exit(96);
}

FILE *__wrap_fopen(const char *path,const char *mode)
{
    FILE *result=__real_fopen(path,mode); int saved=errno;
    if (phase!=IDLE) {
        ++opens;
        if (phase!=OPEN_INPUT || opens!=1 || strcmp(path,input_path) ||
            strcmp(mode,"rb") || !result) failed=1;
        if (result) {
            file_address=(uintptr_t)result; input_fd=fileno(result);
            if (input_fd<0 || fstat(input_fd,&input_identity) ||
                !S_ISREG(input_identity.st_mode) || input_identity.st_size!=12679)
                failed=1;
        }
    }
    errno=saved; return result;
}

size_t __wrap_fread(void *out,size_t bytes,size_t count,FILE *stream)
{
    if (phase!=LOAD_ELF || (uintptr_t)stream!=file_address ||
        !out || bytes!=sizeof(Elf64_Ehdr) || count!=1 || reads)
        refuse("REFUSED: unexpected subject read/PHDR boundary\n");
    if (interp_slot && !*interp_slot) ++output_reset_before_read;
    else failed=1;
    size_t result=__real_fread(out,bytes,count,stream); int saved=errno;
    ++reads;
    if (result==1) {
        ++full_reads;
        memcpy(actual_first4,out,sizeof(actual_first4));
        if (memcmp(actual_first4,"/* F",4)) failed=1;
    } else failed=1;
    read_order=++sequence;
    errno=saved; return result;
}

int __wrap_fflush(FILE *stream)
{
    int result=__real_fflush(stream); int saved=errno;
    if (phase==LOAD_ELF) {
        ++flushes;
        if (stream!=stderr || result) failed=1;
        flush_order=++sequence;
    }
    errno=saved; return result;
}

int __wrap_fclose(FILE *stream)
{
    unsigned tracked=file_address && (uintptr_t)stream==file_address;
    int fd=input_fd;
    if (tracked && phase!=CLOSE_INPUT) ++callee_closes;
    int result=__real_fclose(stream); int saved=errno;
    if (tracked) {
        int fd_result,fd_error;
        if (phase==CLOSE_INPUT) ++caller_closes;
        errno=0; fd_result=fcntl(fd,F_GETFD); fd_error=errno;
        if (result || fd_result!=-1 || fd_error!=EBADF) failed=1;
        file_address=0; close_order=++sequence;
    }
    errno=saved; return result;
}

static void heap_boundary(void)
{
    if (phase==LOAD_ELF) {
        ++project_heap_calls;
        refuse("REFUSED: descriptor/heap boundary after non-ELF input\n");
    }
}
void *__wrap_malloc(size_t bytes) { heap_boundary(); return __real_malloc(bytes); }
void *__wrap_calloc(size_t count,size_t bytes) { heap_boundary(); return __real_calloc(count,bytes); }
void *__wrap_realloc(void *p,size_t bytes) { heap_boundary(); return __real_realloc(p,bytes); }
void __wrap_free(void *p) { heap_boundary(); __real_free(p); }

int __wrap_ioctl(int fd,unsigned long operation,...)
{
    (void)fd; (void)operation;
    refuse("REFUSED: unexpected GET_CREDV/ioctl/backend boundary\n");
}

static int same_input(const struct stat *now)
{
    return now->st_dev==input_identity.st_dev && now->st_ino==input_identity.st_ino &&
        now->st_mode==input_identity.st_mode && now->st_size==input_identity.st_size &&
        now->st_mtim.tv_sec==input_identity.st_mtim.tv_sec &&
        now->st_mtim.tv_nsec==input_identity.st_mtim.tv_nsec &&
        now->st_ctim.tv_sec==input_identity.st_ctim.tv_sec &&
        now->st_ctim.tv_nsec==input_identity.st_ctim.tv_nsec;
}

int __wrap_main(int argc,char **argv)
{
    char sentinel=0,*interp=&sentinel;
    struct program_load_desc *desc;
    struct stat now,path_now;
    FILE *fp;
    long position;
    int subject_errno,close_result,status=0;
    if (argc!=1 || !argv) return 80;
    phase=OPEN_INPUT; fp=__wrap_fopen(input_path,"rb");
    if (!fp || failed || stat(input_path,&path_now) || !same_input(&path_now))
        refuse("REFUSED: genuine readonly regular input differs\n");
    interp_slot=&interp;
    phase=LOAD_ELF;
    desc=load_elf(fp,&interp);
    subject_errno=errno; return_order=++sequence;
    phase=VALIDATE_INPUT;
    if (desc || interp || reads!=1 || full_reads!=1 || output_reset_before_read!=1 ||
        flushes!=1 || project_heap_calls || !(read_order<flush_order && flush_order<return_order))
        failed=1;
    if (!file_address || callee_closes)
        refuse("REFUSED: public loader consumed borrowed FILE\n");
    position=ftell(fp);
    if (position!=64 || ferror(fp) || fcntl(input_fd,F_GETFD)<0 ||
        fstat(input_fd,&now) || !same_input(&now) || stat(input_path,&path_now) ||
        !same_input(&path_now)) failed=1;
    last_FILE_borrow_order=++sequence;
    phase=CLOSE_INPUT; close_result=__wrap_fclose(fp);
    phase=IDLE;
    if (close_result || opens!=1 || caller_closes!=1 || callee_closes || file_address ||
        close_order<=last_FILE_borrow_order) failed=1;
    if (printf("{\"case\":\"load_elf_non_ELF_header\",\"null_result\":%s,"
        "\"interp_reset_before_read\":%u,\"full_header_reads\":%u,\"read_bytes\":64,"
        "\"first4_hex\":\"%02x%02x%02x%02x\",\"logical_FILE_position\":%ld,"
        "\"diagnostic_flushes\":%u,\"actual_subject_errno\":%d,\"project_heap_calls\":%u,"
        "\"callee_FILE_closes\":%u,\"caller_FILE_closes\":%u,\"caller_descriptor_frees\":0,"
        "\"case_pass\":%s}\n",desc?"false":"true",output_reset_before_read,full_reads,
        (unsigned)actual_first4[0],(unsigned)actual_first4[1],
        (unsigned)actual_first4[2],(unsigned)actual_first4[3],position,flushes,subject_errno,
        project_heap_calls,callee_closes,caller_closes,failed?"false":"true")<0) status=82;
    if (failed) status=81;
    if (__wrap_fflush(stdout)||__wrap_fflush(stderr)) status=82;
    if (__wrap_fclose(stdout)) status=82;
    if (__wrap_fclose(stderr)) status=82;
    return status;
}

_Static_assert(sizeof(Elf64_Ehdr)==64,"selected actual complete ELF64 header read");
_Static_assert(sizeof(struct program_load_desc)==776 && _Alignof(struct program_load_desc)==8,"qualified public descriptor declaration only");
