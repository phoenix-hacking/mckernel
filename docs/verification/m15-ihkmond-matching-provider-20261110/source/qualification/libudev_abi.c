/* NONSHIPPED compile-only libudev ABI witness: no main/calls/implementation.
 * Use the actual selected native header, never the old HOST header as substitute.
 */
#include <libudev.h>
_Static_assert(sizeof(void *) == 8 && sizeof(int) == 4, "selected Linux x86_64 ABI");
#define API(name, type) _Static_assert(_Generic(&name, type: 1, default: 0), #name " exact selected C type")
API(udev_new, struct udev *(*)(void));
API(udev_unref, struct udev *(*)(struct udev *));
API(udev_monitor_new_from_netlink, struct udev_monitor *(*)(struct udev *, const char *));
API(udev_monitor_filter_add_match_subsystem_devtype, int (*)(struct udev_monitor *, const char *, const char *));
API(udev_monitor_enable_receiving, int (*)(struct udev_monitor *));
API(udev_monitor_get_fd, int (*)(struct udev_monitor *));
API(udev_monitor_receive_device, struct udev_device *(*)(struct udev_monitor *));
API(udev_monitor_unref, struct udev_monitor *(*)(struct udev_monitor *));
API(udev_device_get_devnode, const char *(*)(struct udev_device *));
API(udev_device_get_action, const char *(*)(struct udev_device *));
API(udev_device_unref, struct udev_device *(*)(struct udev_device *));
