/* Exactly ten rounds, one already-booted OS. No repeat/duration interface. */
static int pair_round_empty(void)
{
    uint64_t begin=now_ns(),end=bounded_deadline(begin+5000*MS,0);
    while(begin) {
        uint64_t current=now_ns();if(!current || current>=end)return 0;
        int state=retired_at("/proc/mcos0");if(state==1)return 1;if(state<0)return 0;
        struct timespec pause={0,10000000};nanosleep(&pause,NULL);
    }
    return 0;
}
