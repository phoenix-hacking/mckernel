#ifdef MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE
extern int idle_halt;
extern int allow_oversubscribe;
extern int time_sharing;
#else
#line 568
int idle_halt = 0;
int allow_oversubscribe = 0;
int time_sharing = 1;
#endif
#line 571
