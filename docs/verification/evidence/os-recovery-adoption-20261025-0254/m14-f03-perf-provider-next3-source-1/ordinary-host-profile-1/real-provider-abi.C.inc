/* Literal original provider/header declarations; no backend algorithm. */
#include <stdint.h>
struct mc_perf_event;
#ifdef POSTK_DEBUG_TEMP_FIX_29
int ihk_mc_perfctr_init_raw(int counter, uint64_t config, int mode);
#else
int ihk_mc_perfctr_init_raw(int counter, unsigned int code, int mode);
#endif/*POSTK_DEBUG_TEMP_FIX_29*/
int ihk_mc_perfctr_set_extra(struct mc_perf_event *event);
typedef struct {
	long counter64;
} ihk_atomic64_t;

long ihk_atomic64_read(const ihk_atomic64_t *v);
