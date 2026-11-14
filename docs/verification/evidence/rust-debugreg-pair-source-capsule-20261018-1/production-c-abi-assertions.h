_Static_assert(sizeof(unsigned long)==8,"unsigned long width");
_Static_assert(_Alignof(unsigned long)==8,"unsigned long alignment");
extern void clear_debugreg(void);
extern void save_debugreg(unsigned long *);
extern void restore_debugreg(unsigned long *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&save_debugreg),void(*)(unsigned long*)),"SAVE ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&restore_debugreg),void(*)(unsigned long*)),"RESTORE ABI");
