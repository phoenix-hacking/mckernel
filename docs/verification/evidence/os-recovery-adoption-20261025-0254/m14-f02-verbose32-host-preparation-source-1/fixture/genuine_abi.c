/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <ihk/debug.h>
_Static_assert(sizeof(struct ddebug)==32,"Ddebug32");
_Static_assert(__alignof__(struct ddebug)==8,"Ddebugalign8");
_Static_assert(__builtin_offsetof(struct ddebug,file)==0,"file0");
_Static_assert(__builtin_offsetof(struct ddebug,func)==8,"func8");
_Static_assert(__builtin_offsetof(struct ddebug,fmt)==16,"fmt16");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct ddebug*)0)->file),const char *),"file pointer ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct ddebug*)0)->func),const char *),"func pointer ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct ddebug*)0)->fmt),const char *),"fmt pointer ABI");
const struct ddebug f02_genuine_bitfield_witness={.file=0,.func=0,.fmt=0,.line=0x123456,.flags=1};
