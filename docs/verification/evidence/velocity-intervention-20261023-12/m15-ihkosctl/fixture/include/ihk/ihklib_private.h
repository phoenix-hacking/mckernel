#pragma once
#include <ihk/ihklib.h>
enum ihklib_os_query_mem_type { IHKLIB_OS_QUERY_MEM_TOTAL,IHKLIB_OS_QUERY_MEM_FREE };
extern const char *ihklib_os_query_mem_type_str[];
int cpu_str2count(char *cpu_list);
int cpu_str2req(char *_cpu_list, int num_cpus, struct ihk_cpu_req *req);
char *cpu_req2str(struct ihk_cpu_req *req);
int mem_str2count(char *mem_list);
int mem_str2req(char *_mem_list, struct ihk_mem_req *req);
char *mem_req2str(struct ihk_mem_req *req);
int ikc_str2count(char *ikc_list);
int ikc_str2req(char *_ikc_list, int num_cpus, struct ihk_ikc_req *req);
char *ikc_req2str(struct ihk_ikc_req *req);
int ihklib_os_query_mem_sysfs(int index, char *result, ssize_t sz_result,
			      const char *kind);
