/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source only: actual original C provider vs exact Rust provider; same formatter.
 */
#include <stdarg.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
static unsigned record_calls;
static char record_text[1024];
int kprintf(const char *format,...)
{
    va_list ap; va_start(ap,format);
    ++record_calls;
    int ret=vsnprintf(record_text,sizeof(record_text),format,ap);
    va_end(ap); assert(ret>=0 && (unsigned)ret<sizeof(record_text)); return ret;
}
/* Exact original static C definitions keep their __FUNCTION__ spelling; asm
 * label changes only the object symbol, allowing Rust globals in the same ELF.
 */
static void x86_clear_effect_log_bridge(int,unsigned long,unsigned long,size_t)
    __asm__("original_C_effect_log");
static void x86_clear_range_log_bridge(int,void*,unsigned long*,unsigned long,
    unsigned long,unsigned long,int,int,unsigned long)
    __asm__("original_C_range_log");
/* Include the two source-bound original-body .inc files using numeric #line
 * anchors before their definitions. Reference calls from this translation unit
 * name the original static C functions; exported fixture callers can select the
 * Rust globals through their distinct symbol names in a second translation unit.
 * Iterate actual __verbose entries by real file/function/line; set each original
 * and displaced descriptor's flag byte together for 0,1,2,128,255. Compare the
 * calls and exact record_text. Also vary each unrelated selector independently.
 * Cover every known/unknown event; levels21/30/other, signed32 errors, raw pointer
 * bits and high unsigned64 base/phys/size bits. No page or object is dereferenced.
 * This recorder proves logger argument/string/selection behavior, not the native
 * kernel formatter or debug-control synchronization.
 */
