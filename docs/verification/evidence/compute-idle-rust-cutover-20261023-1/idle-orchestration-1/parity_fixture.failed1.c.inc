/* Ordinary actual-header fixture only: every primitive below is a safe stub. */
static struct cpu_local_var cpu;
static struct thread threads[4];
static struct ihk_os_cpu_monitor monitor;
static int scenario, phase, irq_on, held, bad, events_used;
struct event {
	unsigned long code, cpu_status, current_index, current_status, flags;
	unsigned long monitor_status, monitor_counter, irq, held;
};
static struct event events[64];
static struct cpu_local_var *test_current_cpu(void) { return &cpu; }
static unsigned long test_current_cpu_ulong(void) { return (unsigned long)&cpu; }
static void event(unsigned long code)
{
	if (events_used >= 64) { bad++; return; }
	struct event *e = &events[events_used++];
	e->code=code; e->cpu_status=cpu.status; e->current_index=cpu.current-threads;
	e->current_status=cpu.current->status; e->flags=cpu.flags;
	e->monitor_status=monitor.status; e->monitor_counter=monitor.counter;
	e->irq=irq_on; e->held=held;
}
static void queue_running(void)
{
	threads[3].status=PS_RUNNING;
	cpu.runq.next=&threads[3].sched_list; cpu.runq.prev=&threads[3].sched_list;
	threads[3].sched_list.next=&cpu.runq; threads[3].sched_list.prev=&cpu.runq;
}
static unsigned long test_lock(unsigned long address)
{
	if(address!=(unsigned long)&cpu.runq_lock || irq_on || held) bad++;
	event('L'); held=1;
	if(scenario==4) queue_running();
	return 0x11223344UL;
}
static void test_unlock(unsigned long address, unsigned long irqstate)
{
	if(address!=(unsigned long)&cpu.runq_lock || !held) bad++;
	if(irqstate!=(phase==0?0x5a5aUL:0x11223344UL)) bad++;
	event('U'); held=0; irq_on=0;
	if(phase && scenario==5) cpu.status=CPU_STATUS_RUNNING;
}
static unsigned long test_lock_pointer(ihk_spinlock_t *address)
{ return test_lock((unsigned long)address); }
static void test_unlock_pointer(ihk_spinlock_t *address, unsigned long irqstate)
{ test_unlock((unsigned long)address,irqstate); }
static void test_enable(void) { event('E'); irq_on=1; }
static void test_disable(void)
{
	if(cpu.current->status!=PS_RUNNING) bad++;
	event('D'); irq_on=0;
}
static void test_schedule(void)
{
	if(cpu.current->status!=PS_STOPPED) bad++;
	event('S');
	if(scenario==1) cpu.current=&threads[1];
	if(scenario==7) cpu.status=CPU_STATUS_RESERVED;
}
static void test_migrate(void)
{
	if(irq_on) bad++;
	event('M'); cpu.flags|=0x80;
	if(scenario==6) cpu.status=CPU_STATUS_RUNNING;
}
static void test_consolidate(void)
{
	if(irq_on || held || cpu.current->status!=PS_RUNNING) bad++;
	event('C');
}
static void test_zero(void)
{
	if(irq_on || held || cpu.current->status!=PS_RUNNING) bad++;
	event('Z');
}
static void *test_node(int distance)
{ if(distance) bad++; return &monitor; }
static void test_zero_pages(void *node)
{ if(node!=&monitor) bad++; test_zero(); }
static void test_halt(void)
{
	if(irq_on || held || monitor.status!=IHK_OS_MONITOR_IDLE ||
	   cpu.current->status!=PS_INTERRUPTIBLE) bad++;
	event('H'); irq_on=1;
	if(scenario==2) cpu.current=&threads[2];
}

/* ACTUAL PRODUCER DESCRIPTORS INSERTED HERE */

static void reset_case(int selected_scenario, int status, int queue)
{
	memset(&cpu,0,sizeof(cpu)); memset(threads,0,sizeof(threads));
	memset(&monitor,0,sizeof(monitor)); memset(events,0,sizeof(events));
	scenario=selected_scenario; phase=0; irq_on=0; held=1; bad=0; events_used=0;
	cpu.current=&threads[0]; cpu.monitor=&monitor; cpu.status=status;
	cpu.runq_irqstate=0x5a5aUL; cpu.runq.next=&cpu.runq; cpu.runq.prev=&cpu.runq;
	threads[0].status=PS_RUNNING; monitor.status=IHK_OS_MONITOR_KERNEL;
	monitor.counter=scenario==8?~0UL:17UL;
	if(scenario==3 || scenario==6) cpu.flags=CPU_FLAG_NEED_MIGRATE|0x40;
	if(queue) {
		queue_running();
		if(queue==1) { threads[3].status=PS_STOPPED; threads[3].spin_sleep=1; }
	}
}
struct snapshot {
	struct cpu_local_var cpu;
	struct thread threads[4];
	struct ihk_os_cpu_monitor monitor;
	struct event events[64];
	int irq_on,held,bad,events_used;
};
static struct snapshot expected,actual;
static void snapshot(struct snapshot *state)
{
	memset(state,0,sizeof(*state));
	memcpy(&state->cpu,&cpu,sizeof(cpu)); memcpy(state->threads,threads,sizeof(threads));
	memcpy(&state->monitor,&monitor,sizeof(monitor)); memcpy(state->events,events,sizeof(events));
	state->irq_on=irq_on; state->held=held; state->bad=bad; state->events_used=events_used;
}

/* EXACT ORIGINAL C BEGIN/ITERATION INSERTED HERE */

extern long write(int fd,const void *buffer,unsigned long bytes);
int main(void)
{
	int checked=0;
	const int states[]={CPU_STATUS_DISABLE,CPU_STATUS_IDLE,CPU_STATUS_RESERVED,CPU_STATUS_RUNNING};
	for(int s=0;s<9;s++) for(unsigned i=0;i<4;i++) for(int q=0;q<3;q++) {
		reset_case(s,states[i],q); original_begin(); phase=1; original_iteration(); snapshot(&expected);
		if(expected.bad) return 51;
		reset_case(s,states[i],q);
		sched_idle_begin_body_result((unsigned long)&cpu,&process_idle_offsets,&process_idle_values,&process_idle_callbacks);
		phase=1;
		sched_idle_iteration_body_result((unsigned long)&cpu,(unsigned long)&monitor,
			&process_idle_offsets,&process_idle_values,&process_idle_callbacks);
		snapshot(&actual);
		if(actual.bad) return 52;
		if(memcmp(&expected,&actual,sizeof(actual))) return 53;
		if((s==3 || s==6) && cpu.flags!=(0x40|0x80)) return 54;
		checked++;
	}
	if(checked!=108) return 55;
	static const char message[]="PASS 108 original-C/Rust idle state and callback-order cases; actual production headers\n";
	if(write(1,message,sizeof(message)-1)!=(long)(sizeof(message)-1)) return 56;
	return 0;
}
