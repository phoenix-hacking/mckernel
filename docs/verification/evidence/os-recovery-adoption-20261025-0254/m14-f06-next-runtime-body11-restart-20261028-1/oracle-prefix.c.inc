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
