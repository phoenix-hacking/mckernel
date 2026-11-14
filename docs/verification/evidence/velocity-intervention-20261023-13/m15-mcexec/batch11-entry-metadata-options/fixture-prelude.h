/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#define BUILDID "fixture-build-id"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sched.h>
#include <sys/mount.h>
#include <sys/resource.h>
#include <sys/ioctl.h>
#include <assert.h>
#include "reference-uprotocol.h"
extern int fd,debug;
extern cpu_set_t mcexec_partition_cpu_set_storage;
#define __dprintf(format,args...) do {if(debug){printf("%s: " format,__func__,##args);fflush(stdout);}} while(0)
int mcexec_main_body(int,char**);
int mcexec_main_entry_fixture(int,char**);
int mc_cmd_server_init(void);void mc_cmd_server_exit(void);
int ibmic_cmd_server_init(void);void ibmic_cmd_server_exit(void);
int dcfampi_cmd_server_init(void);void dcfampi_cmd_server_exit(void);
int isunshare(void);int numa_num_possible_cpus(void);
size_t mcexec_opendev_buildid_size_bridge(void);
const char *mcexec_opendev_buildid_bridge(void);
char *mcexec_opendev_query_result_bridge(void);
void mcexec_exit_cmd_servers_bridge(void);
int mcexec_main_cmd_servers_init_bridge(void);
int mcexec_main_bind_mount_bridge(void);
void mcexec_partition_debug_ikc_binding_bridge(void);
void mcexec_partition_debug_numa_binding_bridge(void);
