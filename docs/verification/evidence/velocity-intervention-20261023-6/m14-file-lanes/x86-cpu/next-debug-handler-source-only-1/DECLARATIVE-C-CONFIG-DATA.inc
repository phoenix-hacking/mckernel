/* Immutable witness of this C translation unit's existing debug gate;
 * declarative remaining C data, not a C helper implementation. */
#ifdef DEBUG_PRINT_CPU
const unsigned int x86_debug_handler_debug_print_enabled = 1;
#else
const unsigned int x86_debug_handler_debug_print_enabled = 0;
#endif
