/* Functional McKernel OS/apps/Rust/allowed assembly only; NO SECURITY TESTING.
 * ONE normal load_interp publication/returned-ownership case, whole real object.
 * The genuine sameSDK loader input seal is UNISSUED; no substitute data/types.
 */
#define _GNU_SOURCE
#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <uprotocol.h>
/* Root supplies data-only macros/arrays from the exact genuine SDK loader.
 * This absent header deliberately prevents compilation before that input joins.
 */
#include "loader-input-seal.h"

extern struct program_load_desc *mcexec_load_alloc_desc_bridge(int);
extern struct program_load_desc *load_interp(struct program_load_desc *, FILE *);
extern void *__real_malloc(size_t);
extern void *__real_calloc(size_t,size_t);
extern void *__real_realloc(void *,size_t);
extern void __real_free(void *);
extern FILE *__real_fopen(const char *,const char *);
extern int __real_fclose(FILE *);
extern int __real_fflush(FILE *);

static const char input_path[] = "/lib64/ld-linux-x86-64.so.2";
enum phase { IDLE, ALLOCATE, OPEN_INPUT, VALIDATE_INPUT, LOAD_INTERP, CALLER_FREE, CLOSE_INPUT };
static enum phase phase;
static uintptr_t original_base,current_base,file_address;
static size_t current_size,expected_size;
static unsigned generation,live,failed,sequence;
static unsigned mallocs,callocs,reallocs,realloc_successes,realloc_moved;
static unsigned production_frees,caller_descriptor_frees,opens,callee_closes,caller_closes;
static unsigned callee_flushes,section_FILE_live_checks,load_count;
static unsigned allocation_order,open_order,realloc_order,return_order;
static unsigned last_descriptor_borrow_order,free_order,close_order;
static int input_fd = -1;
static struct stat input_identity;
static Elf64_Ehdr expected_header;
static Elf64_Phdr expected_loads[MCEXEC_LOADER_PHNUM];
static unsigned long expected_align;

static _Noreturn void refuse(const char *message)
{
    (void)write(STDERR_FILENO,message,strlen(message));
    _Exit(96);
}

static void remember_initial(void *result,size_t bytes)
{
    if (phase != ALLOCATE || mallocs+callocs != 1 || !result ||
        bytes != sizeof(struct program_load_desc)) failed=1;
    if (phase == ALLOCATE && result) {
        original_base=current_base=(uintptr_t)result;
        current_size=bytes; generation=live=1;
        allocation_order=++sequence;
    }
}

void *__wrap_malloc(size_t bytes)
{
    void *result=__real_malloc(bytes); int saved=errno;
    if (phase != IDLE) { ++mallocs; remember_initial(result,bytes); }
    errno=saved; return result;
}

void *__wrap_calloc(size_t count,size_t bytes)
{
    void *result=__real_calloc(count,bytes); int saved=errno;
    if (phase != IDLE) {
        ++callocs;
        if (count && bytes>SIZE_MAX/count) failed=1;
        else remember_initial(result,count*bytes);
    }
    errno=saved; return result;
}

void *__wrap_realloc(void *pointer,size_t bytes)
{
    uintptr_t incoming=(uintptr_t)pointer;
    unsigned tracked=phase==LOAD_INTERP && live && incoming==current_base;
    void *result=__real_realloc(pointer,bytes); int saved=errno;
    if (phase != IDLE) {
        ++reallocs;
        if (!tracked || incoming!=original_base || reallocs!=1 ||
            bytes!=expected_size || !result || generation!=1) failed=1;
        if (tracked && result) {
            ++realloc_successes;
            realloc_moved=(uintptr_t)result!=incoming;
            current_base=(uintptr_t)result; current_size=bytes;
            ++generation; realloc_order=++sequence;
        }
    }
    errno=saved; return result;
}

void __wrap_free(void *pointer)
{
    int entering_errno=errno;
    unsigned tracked=pointer && live && (uintptr_t)pointer==current_base;
    if (phase!=IDLE && pointer) {
        if (!tracked || (phase!=LOAD_INTERP && phase!=CALLER_FREE))
            refuse("REFUSED: unexpected/interior/double descriptor free\n");
        if (phase==CALLER_FREE && (generation!=2 || caller_descriptor_frees ||
            production_frees || !last_descriptor_borrow_order)) failed=1;
        live=0;
    }
    errno=entering_errno;
    __real_free(pointer);
    if (tracked && phase==LOAD_INTERP) ++production_frees;
    if (tracked && phase==CALLER_FREE) {
        ++caller_descriptor_frees; free_order=++sequence;
    }
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
                !S_ISREG(input_identity.st_mode) ||
                input_identity.st_size!=(off_t)MCEXEC_LOADER_FILE_BYTES) failed=1;
            open_order=++sequence;
        }
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

int __wrap_fflush(FILE *stream)
{
    int result=__real_fflush(stream); int saved=errno;
    if (phase==LOAD_INTERP) ++callee_flushes;
    errno=saved; return result;
}

int __wrap_ioctl(int fd,unsigned long operation,...)
{
    (void)fd; (void)operation;
    refuse("REFUSED: unexpected ioctl/device boundary\n");
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

static int check_sealed_headers(FILE *fp)
{
    Elf64_Phdr phdr;
    size_t section_bytes;
    expected_align=1;
    if (fread(&expected_header,sizeof(expected_header),1,fp)!=1 ||
        memcmp(&expected_header,mcexec_loader_sealed_ehdr,sizeof(expected_header)) ||
        memcmp(expected_header.e_ident,ELFMAG,SELFMAG) ||
        expected_header.e_ident[EI_CLASS]!=ELFCLASS64 ||
        expected_header.e_ident[EI_DATA]!=ELFDATA2LSB || expected_header.e_type!=ET_DYN ||
        expected_header.e_machine!=EM_X86_64 || expected_header.e_ehsize!=sizeof(expected_header) ||
        expected_header.e_phentsize!=sizeof(phdr) || expected_header.e_phnum!=MCEXEC_LOADER_PHNUM ||
        expected_header.e_phoff>LONG_MAX || fseek(fp,(long)expected_header.e_phoff,SEEK_SET))
        return -1;
    for (unsigned i=0;i<expected_header.e_phnum;++i) {
        if (fread(&phdr,sizeof(phdr),1,fp)!=1 ||
            memcmp(&phdr,mcexec_loader_sealed_phdrs+i*sizeof(phdr),sizeof(phdr)) ||
            phdr.p_type==PT_INTERP) return -1;
        if (phdr.p_type==PT_LOAD) {
            expected_loads[load_count++]=phdr;
            if (phdr.p_align>expected_align) expected_align=phdr.p_align;
        }
    }
    if (!load_count || load_count>INT_MAX ||
        __builtin_mul_overflow((size_t)load_count,sizeof(struct program_image_section),&section_bytes) ||
        __builtin_add_overflow(sizeof(struct program_load_desc),section_bytes,&expected_size))
        return -1;
    return fseek(fp,0,SEEK_SET);
}

static int verify_live_descriptor(struct program_load_desc *desc,FILE *fp)
{
    struct stat now;
    if (desc->magic!=PLD_MAGIC || desc->num_sections!=(int)load_count ||
        desc->stack_prot!=7 || desc->entry!=expected_header.e_entry ||
        desc->interp_align!=expected_align) return -1;
    for (unsigned i=0;i<load_count;++i) {
        const Elf64_Phdr *p=&expected_loads[i];
        const struct program_image_section *s=&desc->sections[i];
        int prot=((p->p_flags&PF_R)?PROT_READ:0)|((p->p_flags&PF_W)?PROT_WRITE:0)|
                 ((p->p_flags&PF_X)?PROT_EXEC:0);
        if (s->vaddr!=p->p_vaddr || s->filesz!=p->p_filesz || s->offset!=p->p_offset ||
            s->len!=p->p_memsz || s->prot!=prot || s->interp!=1 || s->fp!=fp ||
            fileno(s->fp)!=input_fd || fstat(input_fd,&now) || !same_input(&now) ||
            ferror(s->fp)) return -1;
        ++section_FILE_live_checks;
    }
    /* Unwritten remote_pa/padding are outside this publication contract. */
    return 0;
}

int __wrap_main(int argc,char **argv)
{
    struct program_load_desc *base,*desc;
    struct stat now,path_now;
    FILE *fp;
    int status=0;
    if (argc!=1 || !argv) return 80;
    phase=ALLOCATE; base=mcexec_load_alloc_desc_bridge(0);
    if (!base || failed || mallocs+callocs!=1 || (uintptr_t)base!=current_base ||
        base->magic!=PLD_MAGIC || base->num_sections!=0 || base->stack_prot!=7)
        refuse("REFUSED: actual initial descriptor differs\n");
    phase=OPEN_INPUT; fp=fopen(input_path,"rb");
    if (!fp || failed) refuse("REFUSED: genuine sealed sameSDK loader unavailable\n");
    phase=VALIDATE_INPUT;
    if (stat(input_path,&path_now) || !same_input(&path_now) || check_sealed_headers(fp))
        refuse("REFUSED: actual loader differs from genuine input seal\n");
    phase=LOAD_INTERP; desc=load_interp(base,fp); return_order=++sequence;
    /* Successful realloc consumed base. Only the actual returned generation is used. */
    if (!desc || !live || (uintptr_t)desc!=current_base || generation!=2 ||
        current_size!=expected_size || mallocs+callocs!=1 || reallocs!=1 ||
        realloc_successes!=1 || production_frees || callee_closes || !file_address ||
        callee_flushes || !(allocation_order<open_order && open_order<realloc_order &&
        realloc_order<return_order))
        refuse("REFUSED: successful interpreter return/ownership differs\n");
    phase=VALIDATE_INPUT;
    if (verify_live_descriptor(desc,fp) || fstat(input_fd,&now) || !same_input(&now) ||
        stat(input_path,&path_now) || !same_input(&path_now) ||
        ftell(fp)!=(long)(expected_header.e_phoff+expected_header.e_phnum*sizeof(Elf64_Phdr)))
        failed=1;
    last_descriptor_borrow_order=++sequence;
    phase=CALLER_FREE; __wrap_free(desc); /* Legitimate transferred ownership, not error compensation. */
    phase=CLOSE_INPUT;
    if (fclose(fp)) failed=1;
    phase=IDLE;
    if (live || production_frees || caller_descriptor_frees!=1 || opens!=1 ||
        callee_closes || caller_closes!=1 || file_address || section_FILE_live_checks!=load_count ||
        !(return_order<last_descriptor_borrow_order && last_descriptor_borrow_order<free_order &&
          free_order<close_order)) failed=1;
    if (printf("{\"case\":\"load_interp_success\",\"PT_LOADs\":%u,\"realloc_bytes\":%zu,"
        "\"generation\":%u,\"realloc_moved\":%s,\"published_FILE_borrows\":%u,"
        "\"production_frees\":%u,\"caller_returned_descriptor_frees\":%u,"
        "\"callee_FILE_closes\":%u,\"caller_FILE_closes\":%u,\"case_pass\":%s}\n",
        load_count,current_size,generation,realloc_moved?"true":"false",section_FILE_live_checks,
        production_frees,caller_descriptor_frees,callee_closes,caller_closes,failed?"false":"true")<0)
        status=82;
    if (failed) status=81;
    if (fflush(stdout)||fflush(stderr)) status=82;
    if (fclose(stdout)) status=82;
    if (fclose(stderr)) status=82;
    return status;
}

_Static_assert(sizeof(struct program_load_desc)==776 && _Alignof(struct program_load_desc)==8,"qualified x86_64 non-TOFU descriptor ABI");
_Static_assert(sizeof(struct program_image_section)==56 && _Alignof(struct program_image_section)==8,"qualified image section ABI");
_Static_assert(MCEXEC_LOADER_PHNUM>0 && MCEXEC_LOADER_PHNUM<=USHRT_MAX,"actual sealed loader phnum");
_Static_assert(sizeof(mcexec_loader_sealed_ehdr)==sizeof(Elf64_Ehdr),"actual sealed ELF header bytes");
_Static_assert(sizeof(mcexec_loader_sealed_phdrs)==MCEXEC_LOADER_PHNUM*sizeof(Elf64_Phdr),"actual sealed program-header bytes");
