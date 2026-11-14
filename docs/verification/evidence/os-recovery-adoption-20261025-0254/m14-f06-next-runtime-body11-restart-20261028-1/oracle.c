/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual dkprintf macro and original function name; hardware/output is mocked. */
#include <types.h>
#include <prctl.h>
#include <ihk/debug.h>
#include <stdarg.h>
extern int vsnprintf(char *,size_t,const char *,va_list);
struct fixture_trace{unsigned long calls;int cpu,printer_return;unsigned long value;char format[96],rendered[128];int rendered_length,padding;};
static struct fixture_trace trace;
static int configured_return;
void fixture_reset(int printer_return)
{
    unsigned char *bytes=(unsigned char *)&trace;
    for(size_t i=0;i<sizeof(trace);i++)bytes[i]=0;
    configured_return=printer_return;
}
int kprintf(const char *format,...)
{
    trace.calls++;size_t length=0;while(format[length]&&length<95){trace.format[length]=format[length];length++;}trace.format[length]=0;
    va_list arguments,render_arguments;va_start(arguments,format);va_copy(render_arguments,arguments);
    trace.cpu=va_arg(arguments,int);trace.value=va_arg(arguments,unsigned long);
    trace.rendered_length=vsnprintf(trace.rendered,sizeof(trace.rendered),format,render_arguments);
    va_end(render_arguments);va_end(arguments);trace.printer_return=configured_return;return configured_return;
}
void fixture_read_trace(struct fixture_trace *out){*out=trace;}

extern struct ddebug arch_prctl_log_debug __asm__("mckernel_f06_arch_prctl_debug");

void arch_prctl_log_bridge(int event,int cpu,unsigned long value) __asm__("original_arch_prctl_log_bridge");
#line 665 "/src/arch/x86_64/kernel/syscall.c"
void
arch_prctl_log_bridge(int event, int cpu, unsigned long value)
{
	if (event == ARCH_SET_FS) {
		dkprintf("[%d] arch_prctl: ARCH_SET_FS: 0x%lX\n", cpu, value);
	}
}

extern struct ddebug __start___verbose[],__stop___verbose[];
struct ddebug *fixture_original_descriptor(void)
{
    struct ddebug *found=0;
    for(unsigned long address=(unsigned long)__start___verbose;address<(unsigned long)__stop___verbose;address+=sizeof(struct ddebug)){
        struct ddebug *row=(struct ddebug *)address;
        if(row==&arch_prctl_log_debug)continue;
        if(found)return 0;found=row;
    }
    return found;
}
size_t fixture_descriptor_count(void){return ((unsigned long)__stop___verbose-(unsigned long)__start___verbose)/sizeof(struct ddebug);}
void fixture_set_flags(struct ddebug *descriptor,unsigned int flags){descriptor->flags=flags;}
unsigned int fixture_original_flag_field(struct ddebug *descriptor){return descriptor->flags;}
