static const unsigned long ABI_C[10]={
    sizeof(struct ddebug),
    __alignof__(struct ddebug),
    __builtin_offsetof(struct ddebug,file),
    __builtin_offsetof(struct ddebug,func),
    __builtin_offsetof(struct ddebug,fmt),
    __builtin_offsetof(struct ddebug,fmt)+sizeof(const char *),
    sizeof(int),
    sizeof(unsigned long),
    sizeof(descriptor_logger_t),
    sizeof f03_util_register_desc_debug_v1/sizeof(struct ddebug)
};
