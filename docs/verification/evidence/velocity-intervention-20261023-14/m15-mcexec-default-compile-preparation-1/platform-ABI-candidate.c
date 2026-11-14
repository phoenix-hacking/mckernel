/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * HOST-header candidate assertions; no executable body or state instructions. */
#define _GNU_SOURCE
#include <stddef.h>
#include <pthread.h>
#include <semaphore.h>
#include <sys/stat.h>
#include <sys/resource.h>
#include <getopt.h>
_Static_assert(sizeof(void*)==8 && sizeof(long)==8,"Linux LP64");
_Static_assert(sizeof(pthread_t)==8,"Rust pthread_t usize");
_Static_assert(sizeof(pthread_mutex_t)==40 && _Alignof(pthread_mutex_t)==8,"Rust MutexStorage");
_Static_assert(sizeof(pthread_barrier_t)==32 && _Alignof(pthread_barrier_t)==8,"Rust BarrierStorage");
_Static_assert(sizeof(pthread_spinlock_t)==4 && _Alignof(pthread_spinlock_t)==4,"Rust int spinlock");
_Static_assert(sizeof(sem_t)==32 && _Alignof(sem_t)==8,"Rust FullForkSync semaphore");
_Static_assert(sizeof(struct stat)==144 && _Alignof(struct stat)==8,"Rust StatStorage");
_Static_assert(offsetof(struct stat,st_mode)==24 && offsetof(struct stat,st_size)==48,"Rust stat read offsets");
_Static_assert(sizeof(struct rlimit)==16 && _Alignof(struct rlimit)==8,"Rust GlobalRlimit");
_Static_assert(sizeof(struct option)==32 && _Alignof(struct option)==8,"Rust GetOptOption");
_Static_assert(offsetof(struct option,name)==0 && offsetof(struct option,has_arg)==8 && offsetof(struct option,flag)==16 && offsetof(struct option,val)==24,"Rust option fields");
const unsigned long mcexec_candidate_platform_abi[]={sizeof(pthread_t),sizeof(pthread_mutex_t),_Alignof(pthread_mutex_t),sizeof(pthread_barrier_t),_Alignof(pthread_barrier_t),sizeof(sem_t),_Alignof(sem_t),sizeof(struct stat),offsetof(struct stat,st_mode),offsetof(struct stat,st_size),sizeof(struct rlimit),sizeof(struct option)};
