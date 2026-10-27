#pragma once
#include <ihk/ihk_host_user.h>
#define IHK_OS_EVENTFD_TYPE_STATUS 2
#define IHK_OS_EVENTFD_TYPE_KMSG 101
int ihk_os_get_eventfd(int index,int type);
