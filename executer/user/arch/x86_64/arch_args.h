#ifndef ARCH_ARGS_H
#define ARCH_ARGS_H

typedef struct user_regs_struct syscall_args;

int get_syscall_args(int pid, syscall_args *args);
int set_syscall_args(int pid, syscall_args *args);
unsigned long get_syscall_number(syscall_args *args);
unsigned long get_syscall_return(syscall_args *args);
unsigned long get_syscall_arg1(syscall_args *args);
unsigned long get_syscall_arg2(syscall_args *args);
unsigned long get_syscall_arg3(syscall_args *args);
unsigned long get_syscall_arg4(syscall_args *args);
unsigned long get_syscall_arg5(syscall_args *args);
unsigned long get_syscall_arg6(syscall_args *args);
unsigned long get_syscall_rip(syscall_args *args);
void set_syscall_number(syscall_args *args, unsigned long value);
void set_syscall_return(syscall_args *args, unsigned long value);
void set_syscall_arg1(syscall_args *args, unsigned long value);
void set_syscall_arg2(syscall_args *args, unsigned long value);
void set_syscall_arg3(syscall_args *args, unsigned long value);
void set_syscall_arg4(syscall_args *args, unsigned long value);
void set_syscall_arg5(syscall_args *args, unsigned long value);
void set_syscall_arg6(syscall_args *args, unsigned long value);
int syscall_enter(syscall_args *args);
#endif
