/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Genuine C headers/macro/original function. All storage/output is own HOST mock. */
#include <types.h>
#include <process.h>
#include <ihk/debug.h>
#include <stdarg.h>
extern int vsnprintf(char *,size_t,const char *,va_list);
#define ARCH_VDSO_MAP_LOG_NOT_AVAILABLE 1
#define ARCH_VDSO_MAP_LOG_ADD_VDSO_FAILED 2
#define ARCH_VDSO_MAP_LOG_MAPPED 3
#define ARCH_VDSO_MAP_LOG_SET_RANGE_FAILED 4
#define ARCH_VDSO_MAP_LOG_ADD_VVAR_FAILED 5
static ptrdiff_t vdso_offset;
struct fixture_trace{unsigned long calls;int kind,first,last,printer_return;unsigned long values[5];char format[160],rendered[256];int rendered_length,padding;};
static struct fixture_trace trace;
static int configured_return;
void fixture_reset(int result){unsigned char *bytes=(unsigned char *)&trace;for(size_t i=0;i<sizeof(trace);i++)bytes[i]=0;configured_return=result;}
int kprintf(const char *format,...)
{
    trace.calls++;size_t length=0;while(format[length]&&length<159){trace.format[length]=format[length];length++;}trace.format[length]=0;
    va_list args,render_args;va_start(args,format);va_copy(render_args,args);
    if(format[0]=='m'){trace.kind=2;trace.first=va_arg(args,int);for(int i=0;i<5;i++)trace.values[i]=va_arg(args,unsigned long);trace.last=va_arg(args,int);}
    else if(format[0]=='E'||format[0]=='i'){trace.kind=1;trace.first=va_arg(args,int);}
    trace.rendered_length=vsnprintf(trace.rendered,sizeof(trace.rendered),format,render_args);
    va_end(render_args);va_end(args);trace.printer_return=configured_return;return configured_return;
}
void fixture_read_trace(struct fixture_trace *out){*out=trace;}
void fixture_set_original_offset(ptrdiff_t offset){vdso_offset=offset;}
ptrdiff_t fixture_read_original_offset(void){return vdso_offset;}
