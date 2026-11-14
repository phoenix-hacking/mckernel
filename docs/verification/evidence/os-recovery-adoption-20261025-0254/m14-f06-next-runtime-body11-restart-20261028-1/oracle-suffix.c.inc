extern struct ddebug __start___verbose[],__stop___verbose[];
struct ddebug *fixture_original_descriptor(void)
{
    struct ddebug *found=0;
    for(unsigned long address=(unsigned long)__start___verbose;address<(unsigned long)__stop___verbose;address+=sizeof(struct ddebug)){
        struct ddebug *row=(struct ddebug *)address;
        if(row==&arch_prctl_log_debug)continue;
        if(found)return 0;found=row;
    }
    return found;
}
size_t fixture_descriptor_count(void){return ((unsigned long)__stop___verbose-(unsigned long)__start___verbose)/sizeof(struct ddebug);}
void fixture_set_flags(struct ddebug *descriptor,unsigned int flags){descriptor->flags=flags;}
unsigned int fixture_original_flag_field(struct ddebug *descriptor){return descriptor->flags;}
