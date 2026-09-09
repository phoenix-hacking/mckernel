#define _GNU_SOURCE

#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (*get_fn)(void); typedef void (*set_fn)(int);
struct worker_args { get_fn get; set_fn set; int assigned; int observed; };
static void *worker(void *arg) { struct worker_args *w = arg; int initial = w->get(); w->set(w->assigned); w->observed = (initial == 7 && w->get() == w->assigned); return NULL; }
int main(void) {
    void *h = dlopen("/apps/libloader-tls.so", RTLD_NOW | RTLD_LOCAL); if (!h) return EXIT_FAILURE;
    get_fn get = (get_fn)dlsym(h, "fixture_tls_get"); set_fn set = (set_fn)dlsym(h, "fixture_tls_set");
    if (!get || !set || dlerror() != NULL) return EXIT_FAILURE;
    int parent_initial = get(); set(19);
    struct worker_args a = {get, set, 11, 0}, b = {get, set, 13, 0}; pthread_t ta, tb;
    if (pthread_create(&ta, NULL, worker, &a) != 0 || pthread_create(&tb, NULL, worker, &b) != 0) return EXIT_FAILURE;
    pthread_join(ta, NULL); pthread_join(tb, NULL); int parent_final = get(); int valid = parent_initial == 7 && a.observed && b.observed && parent_final == 19;
    dlclose(h); printf("parent_initial=%d thread_a=%d thread_b=%d parent_final=%d valid=%d\n", parent_initial, a.observed, b.observed, parent_final, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
