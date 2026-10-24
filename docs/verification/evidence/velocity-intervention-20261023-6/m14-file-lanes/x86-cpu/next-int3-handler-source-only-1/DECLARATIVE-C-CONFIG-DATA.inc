/* Declarative witness of this C translation unit's existing debug gate.
 * This immutable data is explicit remaining C debt, not a C helper body. */
#ifdef DEBUG_PRINT_CPU
const unsigned int x86_int3_debug_print_enabled = 1;
#else
const unsigned int x86_int3_debug_print_enabled = 0;
#endif
