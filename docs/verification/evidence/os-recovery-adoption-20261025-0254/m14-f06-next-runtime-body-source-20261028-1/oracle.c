/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <limits.h>
#include "original-vdso-layout.c.inc"
struct ikc_scd_packet { uint64_t header; int msg,err; unsigned long reply; unsigned char body[104]; };
_Static_assert(sizeof(struct ikc_scd_packet)==128,"actual packet128");
_Static_assert(offsetof(struct ikc_scd_packet,msg)==8,"actual msg8");
_Static_assert(offsetof(struct ikc_scd_packet,body)+16==40,"actual traditional arg40");
_Static_assert(sizeof(struct vdso)==88,"actual VDSO88");
_Static_assert(offsetof(struct vdso,busy)==0,"busy0");
_Static_assert(offsetof(struct vdso,vdso_npages)==8,"pages8");
_Static_assert(offsetof(struct vdso,vgtod_virt)==80,"vgtod80");
static struct vdso vdso;
static int prep_error,send_error,pause_limit,pages;
static int pauses,sends,preps,physical_calls;
static int64_t events[64];
static size_t event_count;
static const uintptr_t channel_value=0x12345000UL;
struct fake_cpu { void *ikc2linux; };
static struct fake_cpu cpu;
static void note(int event,int error) {
 events[event_count++]=event;
 events[event_count++]=error;
 events[event_count++]=vdso.busy;
 events[event_count++]=vdso.vdso_npages;
}
#define SCD_MSG_GET_VDSO_INFO 0xb
#define dkprintf(fmt,...) do { if (!strcmp(fmt,"vdso_get_vdso_info()\n")) note(0,0); else note(3,error); } while(0)
#define ekprintf(fmt,...) do { if (strstr(fmt,"packet prepare")) note(1,error); else note(2,error); } while(0)
static struct fake_cpu *get_this_cpu_local_var(void) { return &cpu; }
unsigned long fixture_physical(void *p) { ++physical_calls;return (uintptr_t)p ^ 0x123456780000UL; }
#define virt_to_phys fixture_physical
int fixture_prepare(struct ikc_scd_packet *packet,int msg,unsigned long arg) {
 ++preps;packet->msg=msg;memcpy(packet->body+16,&arg,sizeof(arg));return prep_error;
}
#define x86_vdso_packet_prepare_result fixture_prepare
int fixture_send(void *channel,struct ikc_scd_packet *packet,int flags) {
 unsigned long arg=0;++sends;memcpy(&arg,packet->body+16,sizeof(arg));
 if (channel!=(void*)channel_value || flags || packet->msg!=0xb || arg!=((uintptr_t)&vdso ^ 0x123456780000UL)) return 0x456;
 /* Make response visibility and error-only page-count clearing observable. */
 vdso.vdso_npages=pages;vdso.vvar_phys=LONG_MIN+77;
 if(!send_error && pause_limit==0)vdso.busy=0;
 return send_error;
}
#define ihk_ikc_send fixture_send
void fixture_pause(void) { ++pauses;if(pauses==pause_limit)vdso.busy=0; }
#define cpu_pause fixture_pause
#include "original-vdso-info.c.inc"
void fixture_log(int event,int error) { note(event,error); }
void fixture_reset(int p,int s,int delay,int n) {
 memset(&vdso,0xa5,sizeof(vdso));memset(events,0,sizeof(events));event_count=0;
 prep_error=p;send_error=s;pause_limit=delay;pages=n;pauses=sends=preps=physical_calls=0;
 cpu.ikc2linux=(void*)channel_value;
}
void *fixture_state(void) { return &vdso; }
void *fixture_channel(void) { return cpu.ikc2linux; }
int fixture_run_c(void) { return vdso_get_vdso_info(); }
struct snapshot { unsigned char state[88]; int64_t events[64]; uint64_t event_count; int pauses,sends,preps,physical_calls; };
void fixture_snapshot(struct snapshot *out) {
 memset(out,0,sizeof(*out));memcpy(out->state,&vdso,88);memcpy(out->events,events,sizeof(events));
 out->event_count=event_count;out->pauses=pauses;out->sends=sends;out->preps=preps;out->physical_calls=physical_calls;
}
