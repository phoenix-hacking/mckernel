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

void arch_vdso_map_log_bridge(int,int,struct process_vm *,unsigned long,unsigned long,unsigned long,unsigned long,int) __asm__("original_arch_vdso_map_log_bridge");
#line 3077 "/src/arch/x86_64/kernel/syscall.c"
void
arch_vdso_map_log_bridge(int event, int error, struct process_vm *vm,
		unsigned long a, unsigned long b, unsigned long c,
		unsigned long d, int pages)
{
	switch (event) {
	case ARCH_VDSO_MAP_LOG_NOT_AVAILABLE:
		dkprintf("arch_map_vdso(): not available\n");
		break;
	case ARCH_VDSO_MAP_LOG_ADD_VDSO_FAILED:
		ekprintf("ERROR: adding memory range for vdso. %d\n", error);
		break;
	case ARCH_VDSO_MAP_LOG_MAPPED:
		kprintf("mcexec_v10: vdso_map pid=%d container=0x%lx vdso=0x%lx vdso_end=0x%lx offset=0x%lx size=0x%lx pages=%d\n",
			vm && vm->proc ? vm->proc->pid : -1, a, b, c,
			(unsigned long)vdso_offset, d, pages);
		break;
	case ARCH_VDSO_MAP_LOG_SET_RANGE_FAILED:
		ekprintf("ihk_mc_pt_set_range failed. %d\n", error);
		break;
	case ARCH_VDSO_MAP_LOG_ADD_VVAR_FAILED:
		ekprintf("ERROR: adding memory range for vvar. %d\n", error);
		break;
	}
}


extern struct ddebug selected_map_debug __asm__("mckernel_f06_vdso_map_debug");
extern struct ddebug __start___verbose[],__stop___verbose[];
struct ddebug *fixture_original_descriptor(void){struct ddebug *found=0;for(unsigned long address=(unsigned long)__start___verbose;address<(unsigned long)__stop___verbose;address+=sizeof(struct ddebug)){struct ddebug *row=(struct ddebug *)address;if(row==&selected_map_debug)continue;if(found)return 0;found=row;}return found;}
size_t fixture_descriptor_count(void){return ((unsigned long)__stop___verbose-(unsigned long)__start___verbose)/sizeof(struct ddebug);}
