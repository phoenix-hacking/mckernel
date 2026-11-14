/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
extern int ihk_mc_perf_counter_mask_check(unsigned long);
extern int ihk_mc_perfctr_start(unsigned long);
extern int ihk_mc_perfctr_stop(unsigned long, int);
#include "paired-selectors.C.inc"
typedef int (*mask_callback)(unsigned long);
typedef int (*stop_callback)(unsigned long, int);
mask_callback f03_selected_mask = perf_counter_mask_check_bridge;
mask_callback f03_selected_start = perf_counter_start_bridge;
stop_callback f03_selected_stop = perf_counter_stop_bridge;
