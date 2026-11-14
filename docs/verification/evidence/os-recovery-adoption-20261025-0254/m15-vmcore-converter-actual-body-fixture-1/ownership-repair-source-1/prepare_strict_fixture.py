"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Derive strict ownership callback oracle from immutable actual-body fixture.
"""
from pathlib import Path
import hashlib
HERE=Path(__file__).resolve().parent
old=HERE.parent/'fixture.c'
s=old.read_text()
assert hashlib.sha256(old.read_bytes()).hexdigest()=='618ec740c124adafe311be086afacfb74518a2f316de44e4fd76946ee540576b'

def replace(a,b):
 global s
 assert s.count(a)==1,a
 s=s.replace(a,b)
replace('#include <assert.h>','#include <assert.h>\n#include <stdbool.h>')
replace('static int bfd_token;','static void *owned_handle;\nstatic int handle_live,handles_opened,handles_destroyed,abort_closes,name_checks,last_bfd_event;\nstatic int fail_open,fail_format,fail_time,fail_localtime,fail_make,fail_size,fail_flags,fail_get_phys,fail_abort;\nstatic int make_calls,size_calls,flag_calls;\nstatic char primary_bfd_error[128],primary_perror[128];')
replace('        allocations[i].live=0;allocations[i].freed=1;','        if(allocations[i].size==40||allocations[i].size==72||allocations[i].size==0x100000)assert(!handle_live);\n        allocations[i].live=0;allocations[i].freed=1;')
replace('time_t __wrap_time(time_t *out){assert(!out);return 12345;}','time_t __wrap_time(time_t *out){assert(!out);return fail_time?-1:12345;}')
replace('struct tm *__wrap_localtime(const time_t *t){assert(*t==12345);return &tm_storage;}','struct tm *__wrap_localtime(const time_t *t){assert(*t==12345);return fail_localtime?NULL:&tm_storage;}')
replace('void __wrap_perror(const char *s){++event;assert(s);}','void __wrap_perror(const char *s){++event;assert(s&&strlen(s)<sizeof(primary_perror));strcpy(primary_perror,s);}')
a=s.index('void bfd_init(void)');b=s.index('int bfd_set_section_contents(',a)
s=s[:a]+'''static void validate_borrowed_names(void){
    for(int j=0;j<nsections;j++){
        const char *name=sections[j].name;
        if(j<4){assert(!strcmp(name,(const char*[]){"date","hostname","user","physchunks"}[j]));continue;}
        int owner_live=0;
        for(int i=0;i<nalloc;i++)if(allocations[i].live&&(uintptr_t)name>=(uintptr_t)allocations[i].ptr&&(uintptr_t)name<(uintptr_t)allocations[i].ptr+allocations[i].size)owner_live=1;
        assert(owner_live);char expected[32];snprintf(expected,sizeof(expected),"physmem%d",j-4);assert(!strcmp(name,expected));++name_checks;
    }
}
static void check_handle(void *bfd){assert(handle_live&&bfd==owned_handle);validate_borrowed_names();last_bfd_event=event;}
void bfd_init(void){++event;}
void *bfd_fopen(const char *filename,const char *target,const char *mode,int fd){
    ++event;assert(!strcmp(filename,output_path)&&target==NULL&&!strcmp(mode,"w")&&fd==-1);
    if(fail_open)return NULL;
    assert(!handle_live);owned_handle=__real_malloc(8);assert(owned_handle);handle_live=1;++handles_opened;return owned_handle;
}
void bfd_perror(const char *s){++event;++bfd_errors;assert(s&&strlen(s)<sizeof(primary_bfd_error));strcpy(primary_bfd_error,s);}
int bfd_set_format(void *bfd,int format){++event;check_handle(bfd);assert(format==1);return !fail_format;}
struct section *bfd_make_section_anyway(void *bfd,const char *name){
    ++event;check_handle(bfd);++make_calls;if(fail_make==make_calls)return NULL;
    assert(nsections<10);struct section *s=&sections[nsections++];s->name=name;validate_borrowed_names();return s;
}
int bfd_set_section_size(void *bfd,struct section *s,unsigned long size){++event;check_handle(bfd);if(fail_size==++size_calls)return 0;s->size=size;return 1;}
int bfd_set_section_flags(void *bfd,struct section *s,unsigned flags){++event;check_handle(bfd);if(fail_flags==++flag_calls)return 0;s->flags=flags;return 1;}
struct section *bfd_get_section_by_name(void *bfd,const char *name){
    ++event;check_handle(bfd);
    if(missing_physchunks&&!strcmp(name,"physchunks"))return NULL;
    if(!strncmp(name,"physmem",7)&&fail_get_phys==atoi(name+7)+1)return NULL;
    for(int i=0;i<nsections;i++)if(!strcmp(name,sections[i].name))return &sections[i];
    assert(!"unexpected section lookup");return NULL;
}
''' +s[b:]
replace('    assert(bfd==&bfd_token&&data&&offset==0);++event;++writes;','    ++event;check_handle(bfd);assert(data&&offset==0);++writes;')
replace('int bfd_close(void *bfd){assert(bfd==&bfd_token);++event;++closes;close_event=event;return !fail_close;}','''static void consume_handle(void *bfd){check_handle(bfd);__real_free(owned_handle);owned_handle=NULL;handle_live=0;++handles_destroyed;}
int bfd_close(void *bfd){++event;++closes;close_event=event;consume_handle(bfd);return !fail_close;}
bool bfd_close_all_done(void *bfd){++event;++abort_closes;consume_handle(bfd);return !fail_abort;}''')
replace('    else if(!strcmp(kind,"allocation"))fail_alloc=position;','''    else if(!strcmp(kind,"allocation"))fail_alloc=position;
    else if(!strcmp(kind,"open"))fail_open=1;
    else if(!strcmp(kind,"format"))fail_format=1;
    else if(!strcmp(kind,"time"))fail_time=1;
    else if(!strcmp(kind,"localtime"))fail_localtime=1;
    else if(!strcmp(kind,"make"))fail_make=position;
    else if(!strcmp(kind,"size"))fail_size=position;
    else if(!strcmp(kind,"flags"))fail_flags=position;
    else if(!strcmp(kind,"get-phys"))fail_get_phys=position;
    else if(!strcmp(kind,"abort-false")){fail_format=1;fail_abort=1;}''')
replace('assert(close_event>0&&close_event<payload_free_event&&payload_free_event<chunks_free_event&&chunks_free_event<ack_event);','assert(close_event>0&&close_event<payload_free_event&&payload_free_event<chunks_free_event&&chunks_free_event<ack_event&&name_checks>0);')
replace('    if(!strcmp(kind,"close")){assert(closes==1&&bfd_errors==1&&!payload_free_event&&!chunks_free_event);}','    if(!strcmp(kind,"close")){assert(closes==1&&bfd_errors==1&&payload_free_event>close_event&&chunks_free_event>payload_free_event&&!abort_closes);}')
anchor='    printf("{\\"kind\\":'
pos=s.index(anchor)
s=s[:pos]+'''    assert(live==0&&live_bytes==0&&!handle_live&&handles_opened==handles_destroyed);
    assert(closes+abort_closes==handles_opened);
    if(!strcmp(kind,"write"))assert(abort_closes==1);
    if(!strcmp(kind,"open"))assert(!handles_opened&&!closes&&!abort_closes&&!strcmp(primary_bfd_error,"bfd_fopen"));
    if(!strcmp(kind,"format")||!strcmp(kind,"abort-false"))assert(abort_closes==1&&!strcmp(primary_bfd_error,"bfd_set_format"));
    if(!strcmp(kind,"time"))assert(abort_closes==1&&!strcmp(primary_perror,"time"));
    if(!strcmp(kind,"localtime"))assert(abort_closes==1&&!strcmp(primary_perror,"localtime"));
    if(!strcmp(kind,"make")){const char *names[]={"date","hostname","user","physchunks","physmem","physmem","physmem"};char expected[128];snprintf(expected,sizeof(expected),"bfd_make_section_anyway(%s)",names[position-1]);assert(abort_closes==1&&!strcmp(primary_bfd_error,expected));}
    if(!strcmp(kind,"size"))assert(abort_closes==1&&!strcmp(primary_bfd_error,"bfd_set_section_size"));
    if(!strcmp(kind,"flags"))assert(abort_closes==1&&!strcmp(primary_bfd_error,"bfd_set_setction_flags"));
    if(!strcmp(kind,"get-phys"))assert(abort_closes==1&&!strcmp(primary_bfd_error,"err bfd_get_section_by_name(physmem_name)"));
    fprintf(stderr,"STRICT_OWNERSHIP handles=%d destroyed=%d normal_close=%d abort_close=%d name_checks=%d last_bfd_event=%d live_project=%d\\n",handles_opened,handles_destroyed,closes,abort_closes,name_checks,last_bfd_event,live);
''' +s[pos:]
# Test reporting uses libc fprintf, which is wrapped for body diagnostics. Write
# the strict ownership row through printf instead, before the original JSON row.
s=s.replace('    fprintf(stderr,"STRICT_OWNERSHIP handles=', '    printf("STRICT_OWNERSHIP handles=')
# No harness reclamation can make a failing producer pass the strict live check.
start=s.index('    /* Reclaim test process allocations only AFTER recording producer ownership. */')
end=s.index('    return 0;',start)
s=s[:start]+s[end:]
(HERE/'strict_fixture.c').write_text(s)
(HERE/'dump-layout.h').write_bytes((HERE.parent/'dump-layout.h').read_bytes())
print('strict fixture bytes',len(s.encode()))
