#ifdef MCKERNEL_RUST_PROCESS_HELPERS
static struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_extend_region_exists_debug = {
    .file = __FILE__, .func = "extend_process_region",
    .line = 3394, .flags = DDEBUG_DEFAULT,
};
static struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_extend_region_alloc_debug = {
    .file = __FILE__, .func = "extend_process_region",
    .line = 3411, .flags = DDEBUG_DEFAULT,
};
static struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_extend_region_success_debug = {
    .file = __FILE__, .func = "extend_process_region",
    .line = 3428, .flags = DDEBUG_DEFAULT,
};
unsigned long process_extend_region_body_result(
    struct process_vm *,unsigned long,unsigned long,unsigned long,
    size_t,int,unsigned long,size_t,unsigned long,unsigned long,unsigned long,
    int,unsigned long,unsigned long,unsigned long,int,const char *,int,int,
    struct ddebug *,struct ddebug *,struct ddebug *);
unsigned long extend_process_region(struct process_vm *vm,
        unsigned long end_allocated,unsigned long address,unsigned long flag)
{
    return process_extend_region_body_result(vm,end_allocated,address,flag,
        PAGE_SIZE,PAGE_SHIFT,PAGE_MASK,LARGE_PAGE_SIZE,LARGE_PAGE_MASK,
        LARGE_PAGE_P2ALIGN,PAGE_P2ALIGN,LARGE_PAGE_SHIFT,MPOL_NO_HEAP,
        IHK_MC_AP_NOWAIT,IHK_MC_AP_USER,IHK_MC_PG_USER,__FILE__,3408,3423,
        &process_extend_region_exists_debug,&process_extend_region_alloc_debug,
        &process_extend_region_success_debug);
}
#endif
