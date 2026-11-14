/* Functional McKernel OS/apps/Rust/allowed assembly ONLY; NO SECURITY TESTING.
 * ONE real normal mcexec_prepare_main_desc_body publication/ownership case.
 * Stop before finish_main_image_body/PREPARE_IMAGE. No production main/backend.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/types.h>
#include <unistd.h>
#include <uprotocol.h>

extern struct program_load_desc *mcexec_load_alloc_desc_bridge(int);
extern int mcexec_flatten_strings_result(char *,char **,char **);
extern void mcexec_prepare_main_desc_body(struct program_load_desc *,char **,char **,
                                        int,char *,int,int);
extern void *__real_malloc(size_t);
extern void *__real_calloc(size_t,size_t);
extern void *__real_realloc(void *,size_t);
extern void __real_free(void *);
extern int __real_getrlimit(__rlimit_resource_t,struct rlimit *);

enum phase { IDLE, DESC_ALLOC, PREFIX_ALLOC, ENV_FLATTEN, PREPARE, VALIDATE, CALLER_FREE };
enum role { NONE, DESC, PREFIX, ENV, TEMP, ARGS, ROLE_COUNT };
static enum phase phase;
static struct allocation {
    uintptr_t base;
    size_t bytes;
    unsigned live,production_frees,caller_frees,copy_order,free_order;
} owners[ROLE_COUNT];
static struct program_load_desc *descriptor;
static unsigned failed,sequence,allocations,prepare_allocations,reallocs;
static unsigned rlimit_calls,prepare_return_order,last_descriptor_borrow_order;
static struct rlimit observed_limits[16],before_limits[16],after_limits[16];
static const int resources[16]={9,4,0,2,1,10,8,12,13,7,6,5,14,15,11,3};
static const size_t capacities[ROLE_COUNT]={0,776,26,32,40,56};

static _Noreturn void refuse(const char *message)
{
    (void)write(STDERR_FILENO,message,strlen(message));
    _Exit(96);
}

static void record_allocation(void *pointer,size_t bytes)
{
    enum role role=NONE;
    if (phase==DESC_ALLOC) role=DESC;
    else if (phase==PREFIX_ALLOC) role=PREFIX;
    else if (phase==ENV_FLATTEN) role=ENV;
    else if (phase==PREPARE) {
        if (prepare_allocations==0) role=TEMP;
        else if (prepare_allocations==1) role=ARGS;
        ++prepare_allocations;
    }
    if (role==NONE || !pointer || owners[role].base || bytes!=capacities[role])
        refuse("REFUSED: unexpected real allocation role/capacity\n");
    for (unsigned i=DESC;i<ROLE_COUNT;++i)
        if (owners[i].live && owners[i].base==(uintptr_t)pointer)
            refuse("REFUSED: duplicate live allocation owner\n");
    owners[role]=(struct allocation){(uintptr_t)pointer,bytes,1,0,0,0,0};
    ++allocations; ++sequence;
}

void *__wrap_malloc(size_t bytes)
{
    void *result=__real_malloc(bytes); int saved=errno;
    if (phase!=IDLE) record_allocation(result,bytes);
    errno=saved; return result;
}

void *__wrap_calloc(size_t count,size_t bytes)
{
    void *result=__real_calloc(count,bytes); int saved=errno;
    if (phase!=IDLE) {
        size_t total;
        if (__builtin_mul_overflow(count,bytes,&total))
            refuse("REFUSED: real calloc size overflow\n");
        /* Genuine compiler calloc lowering is observed, never substituted. */
        record_allocation(result,total);
    }
    errno=saved; return result;
}

void *__wrap_realloc(void *pointer,size_t bytes)
{
    void *result=__real_realloc(pointer,bytes); int saved=errno;
    if (phase!=IDLE) { ++reallocs; failed=1; }
    errno=saved; return result;
}

static int flat_matches(enum role role,const intptr_t *words,size_t word_count,
                        const char *payload,size_t payload_bytes,size_t end)
{
    const unsigned char *base;
    if (!owners[role].live || owners[role].bytes<end || word_count*sizeof(intptr_t)>end)
        return 0;
    base=(const unsigned char *)owners[role].base;
    if (memcmp(base,words,word_count*sizeof(intptr_t)) ||
        memcmp(base+word_count*sizeof(intptr_t),payload,payload_bytes)) return 0;
    for (size_t i=end;i<owners[role].bytes;++i) if (base[i]) return 0;
    return 1;
}

static int env_matches(void)
{
    static const intptr_t words[]={1,24,28};
    return flat_matches(ENV,words,3,"X=1",4,28);
}

static int temp_matches(void)
{
    static const intptr_t words[]={1,24,34};
    return flat_matches(TEMP,words,3,"/bin/true",10,34);
}

static int published_args_env_match(void)
{
    static const intptr_t words[]={2,32,42,49};
    static const char payload[]="/bin/true\0script";
    if (!owners[DESC].live || !owners[ARGS].live || !owners[ENV].live ||
        descriptor->args!=(char *)owners[ARGS].base || descriptor->args_len!=49 ||
        descriptor->envs!=(char *)owners[ENV].base || descriptor->envs_len!=28 ||
        descriptor->cpu!=7 || descriptor->enable_vdso!=1) return 0;
    return env_matches() && flat_matches(ARGS,words,4,payload,sizeof(payload),49);
}

void __wrap_free(void *pointer)
{
    int entering_errno=errno;
    enum role role=NONE;
    uintptr_t address=(uintptr_t)pointer;
    if (phase!=IDLE && pointer) {
        for (unsigned i=DESC;i<ROLE_COUNT;++i)
            if (owners[i].live && owners[i].base==address) { role=(enum role)i; break; }
        if (role==NONE) refuse("REFUSED: unknown/interior/double allocation free\n");
        if (phase==PREPARE) {
            if (role!=PREFIX && role!=TEMP)
                refuse("REFUSED: production consumed published/borrowed owner\n");
            if (!published_args_env_match() || !temp_matches()) failed=1;
            if (role==PREFIX) {
                char **table=(char **)owners[PREFIX].base;
                if (table[0]!=(char *)(owners[PREFIX].base+2*sizeof(char *)) ||
                    table[1] || memcmp(table[0],"/bin/true",10) ||
                    owners[TEMP].production_frees) failed=1;
            } else if (owners[PREFIX].live || owners[PREFIX].production_frees!=1) {
                failed=1;
            }
            owners[role].copy_order=++sequence;
        } else if (phase==CALLER_FREE) {
            if ((role!=ARGS && role!=ENV && role!=DESC) ||
                !prepare_return_order || !last_descriptor_borrow_order ||
                owners[role].caller_frees || owners[role].production_frees)
                refuse("REFUSED: invalid returned/retained caller cleanup\n");
        } else {
            refuse("REFUSED: allocation free outside its ownership handoff\n");
        }
        owners[role].live=0;
    }
    errno=entering_errno;
    __real_free(pointer);
    if (role!=NONE) {
        if (phase==PREPARE) ++owners[role].production_frees;
        if (phase==CALLER_FREE) ++owners[role].caller_frees;
        owners[role].free_order=++sequence;
    }
}

int __wrap_getrlimit(__rlimit_resource_t resource,struct rlimit *limit)
{
    int result=__real_getrlimit(resource,limit); int saved=errno;
    if (phase!=PREPARE) {
        failed=1;
    } else {
        unsigned slot=rlimit_calls++;
        if (slot>=16 || !owners[DESC].live || result) {
            failed=1;
        } else if ((int)resource!=resources[slot] || limit!=&descriptor->rlimit[slot]) {
            failed=1;
        } else {
            observed_limits[slot]=*limit;
        }
    }
    errno=saved; return result;
}

int __wrap_ioctl(int fd,unsigned long operation,...)
{
    (void)fd; (void)operation;
    refuse("REFUSED: forbidden PREPARE_IMAGE/ioctl/backend boundary\n");
}

static int read_host_limits(struct rlimit *limits)
{
    for (unsigned i=0;i<16;++i)
        if (__real_getrlimit((__rlimit_resource_t)resources[i],&limits[i])) return -1;
    return 0;
}

static int same_limit(const struct rlimit *a,const struct rlimit *b)
{
    return a->rlim_cur==b->rlim_cur && a->rlim_max==b->rlim_max;
}

int __wrap_main(int argc,char **argv)
{
    char env_text[]="X=1",tail_text[]="script";
    char *env_vector[]={env_text,NULL},*tail[]={tail_text,NULL};
    char *env_flat=NULL,*args_to_free;
    char **owned_prefix;
    unsigned long published_args_len,published_env_len;
    int published_cpu,published_vdso;
    int env_len,status=0;
    if (argc!=1 || !argv || read_host_limits(before_limits)) return 80;

    phase=DESC_ALLOC;
    descriptor=mcexec_load_alloc_desc_bridge(0);
    if (!descriptor || (uintptr_t)descriptor!=owners[DESC].base ||
        descriptor->magic!=PLD_MAGIC || descriptor->num_sections || descriptor->stack_prot!=7)
        refuse("REFUSED: actual descriptor allocator result differs\n");

    phase=PREFIX_ALLOC;
    owned_prefix=__wrap_malloc(2*sizeof(char *)+sizeof("/bin/true"));
    owned_prefix[0]=(char *)owned_prefix+2*sizeof(char *);
    owned_prefix[1]=NULL;
    memcpy(owned_prefix[0],"/bin/true",sizeof("/bin/true"));

    phase=ENV_FLATTEN;
    env_len=mcexec_flatten_strings_result(NULL,env_vector,&env_flat);
    if (env_len!=28 || env_flat!=(char *)owners[ENV].base || !env_matches())
        refuse("REFUSED: actual environment flatten result differs\n");

    phase=PREPARE;
    mcexec_prepare_main_desc_body(descriptor,tail,owned_prefix,env_len,env_flat,7,1);
    prepare_return_order=++sequence;
    /* owned_prefix was consumed; never dereference/free its stale pointer. */
    phase=VALIDATE;
    if (!published_args_env_match() || allocations!=5 || prepare_allocations!=2 || reallocs ||
        rlimit_calls!=16 || owners[PREFIX].live || owners[TEMP].live ||
        owners[PREFIX].production_frees!=1 || owners[TEMP].production_frees!=1 ||
        !(owners[PREFIX].copy_order<owners[PREFIX].free_order &&
          owners[PREFIX].free_order<owners[TEMP].copy_order &&
          owners[TEMP].copy_order<owners[TEMP].free_order &&
          owners[TEMP].free_order<prepare_return_order) || read_host_limits(after_limits))
        failed=1;
    for (unsigned i=0;i<16;++i)
        if (!same_limit(&before_limits[i],&after_limits[i]) ||
            !same_limit(&observed_limits[i],&before_limits[i]) ||
            !same_limit(&descriptor->rlimit[i],&observed_limits[i])) failed=1;
    if (memcmp(env_text,"X=1",4) || memcmp(tail_text,"script",7) ||
        !owners[DESC].live || !owners[ENV].live || !owners[ARGS].live)
        refuse("REFUSED: retained/published owner or borrowed input lifetime differs\n");
    args_to_free=descriptor->args;
    published_args_len=descriptor->args_len; published_env_len=descriptor->envs_len;
    published_cpu=descriptor->cpu; published_vdso=descriptor->enable_vdso;
    last_descriptor_borrow_order=++sequence;

    /* Explicit existing wrapper calls make observer dependencies visible to C.
     * These three caller-owned allocations are NOT temporary-free compensation.
     */
    phase=CALLER_FREE;
    __wrap_free(args_to_free);
    __wrap_free(env_flat);
    __wrap_free(descriptor);
    phase=IDLE;
    for (unsigned i=DESC;i<ROLE_COUNT;++i) {
        if (owners[i].live) failed=1;
        if (i==PREFIX || i==TEMP) {
            if (owners[i].production_frees!=1 || owners[i].caller_frees) failed=1;
        } else if (owners[i].production_frees || owners[i].caller_frees!=1 ||
                   owners[i].free_order<=last_descriptor_borrow_order) failed=1;
    }
    if (printf("{\"case\":\"normal_main_descriptor_preparation\",\"rlimit_slots\":%u,"
        "\"args_len\":%lu,\"args_capacity\":%zu,\"env_len\":%lu,\"env_capacity\":%zu,"
        "\"cpu\":%d,\"vdso\":%d,\"production_prefix_frees\":%u,\"production_temp_frees\":%u,"
        "\"caller_args_frees\":%u,\"caller_env_frees\":%u,\"caller_desc_frees\":%u,"
        "\"rlimits\":[",rlimit_calls,published_args_len,owners[ARGS].bytes,
        published_env_len,owners[ENV].bytes,published_cpu,published_vdso,owners[PREFIX].production_frees,
        owners[TEMP].production_frees,owners[ARGS].caller_frees,owners[ENV].caller_frees,
        owners[DESC].caller_frees)<0) status=82;
    for (unsigned i=0;i<16;++i)
        if (printf("%s[%d,%ju,%ju,%ju,%ju,%ju,%ju]",i?",":"",resources[i],
            (uintmax_t)before_limits[i].rlim_cur,(uintmax_t)before_limits[i].rlim_max,
            (uintmax_t)observed_limits[i].rlim_cur,(uintmax_t)observed_limits[i].rlim_max,
            (uintmax_t)after_limits[i].rlim_cur,(uintmax_t)after_limits[i].rlim_max)<0) status=82;
    if (printf("],\"case_pass\":%s}\n",failed?"false":"true")<0) status=82;
    if (failed) status=81;
    if (fflush(stdout)||fflush(stderr)) status=82;
    if (fclose(stdout)) status=82;
    if (fclose(stderr)) status=82;
    return status;
}

_Static_assert(sizeof(struct program_load_desc)==776 && _Alignof(struct program_load_desc)==8,"qualified x86_64 non-TOFU descriptor ABI");
_Static_assert(sizeof(intptr_t)==8 && sizeof(char *)==8 && sizeof(struct rlimit)==16,"qualified native flat words and rlimit ABI");
_Static_assert(MCK_RLIM_MAX>=16,"real provider snapshot has16 slots");
