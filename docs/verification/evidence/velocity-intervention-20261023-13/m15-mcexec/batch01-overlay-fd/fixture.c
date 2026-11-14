/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Same driver/providers for exact extracted original C and candidate Rust.
 * Link --wrap=malloc,realloc,free,open,close. No native McKernel invocation.
 */
#include "fixture-prelude.h"
struct list_head overlay_fd_list = {&overlay_fd_list,&overlay_fd_list};
pthread_spinlock_t overlay_fd_lock;
int debug;
static int fail_malloc,fail_realloc,open_result,open_errno,opens,closes,frees;
void *__real_malloc(size_t);
void *__real_realloc(void *,size_t);
void __real_free(void *);
void *__wrap_malloc(size_t n) { if(fail_malloc) {fail_malloc=0;return NULL;} return __real_malloc(n); }
void *__wrap_realloc(void *p,size_t n) { if(fail_realloc) {fail_realloc=0;return NULL;} return __real_realloc(p,n); }
void __wrap_free(void *p) { if(p) frees++; __real_free(p); }
int __wrap_open(const char *p,int flags,...) { assert(flags==(O_RDONLY|O_DIRECTORY)); opens++; errno=open_errno; printf("open=%s,%d,%d\n",p,open_result,open_errno); return open_result; }
int __wrap_close(int fd) { closes++;printf("close=%d\n",fd);return 0; }
static void record(unsigned char *buf,int kind) { memset(buf,0,24);uint16_t len=24;memcpy(buf+16,&len,2);buf[kind?19:18]='x'; }
static void cache_state(void *p) {
 printf("cache=%zu,%zu,%zu,%s,%d\n",mcexec_overlay_getdents_pathlen_bridge(p),mcexec_overlay_getdents_mck_size_bridge(p),mcexec_overlay_getdents_linux_size_bridge(p),mcexec_overlay_getdents_linux_path_bridge(p),mcexec_overlay_getdents_hide_orig_bridge(p));
}
int main(void) {
 size_t abi[]={sizeof(struct overlay_fd),_Alignof(struct overlay_fd),offsetof(struct overlay_fd,link),offsetof(struct overlay_fd,linux_path),offsetof(struct overlay_fd,mck_path),offsetof(struct overlay_fd,pathlen),offsetof(struct overlay_fd,mck_dirents),offsetof(struct overlay_fd,mck_dirents_size),offsetof(struct overlay_fd,linux_dirents),offsetof(struct overlay_fd,linux_dirents_size)};
#ifdef RUST_IMPL
 extern void mcexec_overlay_fixture_abi(size_t *);
 size_t rustabi[10];mcexec_overlay_fixture_abi(rustabi);assert(!memcmp(abi,rustabi,sizeof abi));
#endif
 printf("abi=");for(int i=0;i<10;i++)printf("%zu,",abi[i]);puts("");
 pthread_spin_init(&overlay_fd_lock,0);
 assert(!mcexec_overlay_getdents_find_bridge(20));
 fail_malloc=1; printf("allocfail=%d\n",mcexec_overlay_addfd_publish_bridge(20,"/proc/task","/mck/task",10));
 assert(!mcexec_overlay_getdents_find_bridge(20));
 assert(!mcexec_overlay_addfd_publish_bridge(20,"/proc/task","/mck/task",10));
 void *p=mcexec_overlay_getdents_find_bridge(20);assert(p); cache_state(p);
 unsigned char buf[24];record(buf,1);
 fail_realloc=1;printf("upperoom=%d\n",mcexec_overlay_getdents_append_mck_bridge(p,buf,24,1));cache_state(p);
 printf("upper=%d\n",mcexec_overlay_getdents_append_mck_bridge(p,buf,24,1));cache_state(p);
 fail_realloc=1;printf("loweroom=%d\n",mcexec_overlay_getdents_append_linux_bridge(p,buf,24,1,37));cache_state(p);
 printf("lower=%d\n",mcexec_overlay_getdents_append_linux_bridge(p,buf,24,1,37));cache_state(p);
 uint64_t off;memcpy(&off,(char*)mcexec_overlay_getdents_mck_dirents_bridge(p)+8,8);printf("upperoff=%lu\n",off);
 memcpy(&off,(char*)mcexec_overlay_getdents_linux_dirents_bridge(p)+8,8);printf("loweroff=%lu\n",off);
 memset(buf,0,24);printf("badupper=%d\n",mcexec_overlay_getdents_append_mck_bridge(p,buf,24,1));cache_state(p);
 printf("badlower=%d\n",mcexec_overlay_getdents_append_linux_bridge(p,buf,24,1,37));cache_state(p);
 open_result=-1;open_errno=ENOENT;printf("missing=%d\n",mcexec_overlay_getdents_mck_fd_bridge(p));
 open_errno=EACCES;printf("denied=%d\n",mcexec_overlay_getdents_mck_fd_bridge(p));
 open_result=51;open_errno=0;printf("upperfd=%d\n",mcexec_overlay_getdents_mck_fd_bridge(p));
 printf("uppercached=%d\n",mcexec_overlay_getdents_mck_fd_bridge(p));
 open_result=52;printf("lowerfd=%d\n",mcexec_overlay_getdents_linux_fd_bridge(p));
 assert(!mcexec_overlay_addfd_publish_bridge(20,"/sys/task","/mck/sys",9));
 void *newer=mcexec_overlay_getdents_find_bridge(20);assert(newer!=p);cache_state(newer);
 mcexec_overlay_delfd_bridge(20);assert(mcexec_overlay_getdents_find_bridge(20)==p);
 mcexec_overlay_delfd_bridge(20);assert(!mcexec_overlay_getdents_find_bridge(20));
 mcexec_overlay_delfd_bridge(20);printf("resources=%d,%d,%d\n",opens,closes,frees);
 assert(overlay_fd_list.next==&overlay_fd_list && overlay_fd_list.prev==&overlay_fd_list);
 assert(opens==4 && closes==2 && frees==4);
 pthread_spin_destroy(&overlay_fd_lock);
 return 0;
}
