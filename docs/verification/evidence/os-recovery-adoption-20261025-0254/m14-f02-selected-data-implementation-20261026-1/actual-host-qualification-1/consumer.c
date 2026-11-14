#include <process.h>
#include "actual-control-block.c.inc"
_Static_assert(sizeof(int)==4 && _Alignof(int)==4, "C int ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(idle_halt),int), "idle_halt type");
_Static_assert(__builtin_types_compatible_p(__typeof__(allow_oversubscribe),int), "oversubscribe type");
_Static_assert(__builtin_types_compatible_p(__typeof__(time_sharing),int), "time_sharing type");
extern int f02_read_control(unsigned int);
extern void f02_write_control(unsigned int,int);
extern void *f02_control_address(unsigned int);
extern int puts(const char *);
int main(void) {
    int *controls[]={&idle_halt,&allow_oversubscribe,&time_sharing};
    const int defaults[]={0,0,1};
    const int values[]={(-2147483647-1),-1,0,1,2147483647};
    unsigned int checks=0;
    for(unsigned int i=0;i<3;i++) {
        if(*controls[i]!=defaults[i] || f02_read_control(i)!=defaults[i]) return 10+i;
        if((void *)controls[i]!=f02_control_address(i) || (unsigned long)controls[i]%4) return 20+i;
        if(controls[i]==controls[(i+1)%3]) return 30+i;
        checks+=3;
        for(unsigned int j=0;j<5;j++) {
            *controls[i]=values[j];
            if(f02_read_control(i)!=values[j]) return 40+i;
            f02_write_control(i,values[4-j]);
            if(*controls[i]!=values[4-j]) return 50+i;
            checks+=2;
        }
        *controls[i]=defaults[i];
    }
    if(checks!=39) return 60;
    puts("PASS HOST three actual control flags: defaults0/0/1, address/align/independence, five signed values C-to-Rust and Rust-to-C; 39 checks");
    return 0;
}
