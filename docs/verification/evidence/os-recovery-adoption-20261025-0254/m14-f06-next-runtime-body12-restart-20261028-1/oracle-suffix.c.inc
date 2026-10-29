
extern struct ddebug selected_map_debug __asm__("mckernel_f06_vdso_map_debug");
extern struct ddebug __start___verbose[],__stop___verbose[];
struct ddebug *fixture_original_descriptor(void){struct ddebug *found=0;for(unsigned long address=(unsigned long)__start___verbose;address<(unsigned long)__stop___verbose;address+=sizeof(struct ddebug)){struct ddebug *row=(struct ddebug *)address;if(row==&selected_map_debug)continue;if(found)return 0;found=row;}return found;}
size_t fixture_descriptor_count(void){return ((unsigned long)__stop___verbose-(unsigned long)__start___verbose)/sizeof(struct ddebug);}
