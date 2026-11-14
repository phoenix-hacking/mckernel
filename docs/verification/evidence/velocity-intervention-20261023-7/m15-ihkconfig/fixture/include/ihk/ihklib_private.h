#pragma once
#include <ihk/ihklib.h>
int cpu_str2count(char *cpu_list);
int cpu_str2req(char *_cpu_list, int num_cpus, struct ihk_cpu_req *req);
char *cpu_req2str(struct ihk_cpu_req *req);
int mem_str2count(char *mem_list);
int mem_str2req(char *_mem_list, struct ihk_mem_req *req);
char *mem_req2str(struct ihk_mem_req *req);
int _ihk_reserve_cpu_str(int dev_index, char *list, char *err_msg);
int _ihk_reserve_mem_str(int dev_index, char *list, char *err_msg);
