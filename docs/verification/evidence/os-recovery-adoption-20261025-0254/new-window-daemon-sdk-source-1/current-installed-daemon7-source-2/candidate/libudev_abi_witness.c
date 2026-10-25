/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Compile only against the actual, complete pinned libudev development header.
 * The fixture's hand-written header is never an ABI oracle for this witness.
 */
#include <libudev.h>
#define CHECK_TYPE(symbol, type) \
    _Static_assert(__builtin_types_compatible_p(__typeof__(&(symbol)), type), #symbol " type")

CHECK_TYPE(udev_new, struct udev *(*)(void));
CHECK_TYPE(udev_unref, struct udev *(*)(struct udev *));
CHECK_TYPE(udev_monitor_new_from_netlink,
           struct udev_monitor *(*)(struct udev *, const char *));
CHECK_TYPE(udev_monitor_filter_add_match_subsystem_devtype,
           int (*)(struct udev_monitor *, const char *, const char *));
CHECK_TYPE(udev_monitor_enable_receiving, int (*)(struct udev_monitor *));
CHECK_TYPE(udev_monitor_get_fd, int (*)(struct udev_monitor *));
CHECK_TYPE(udev_monitor_receive_device, struct udev_device *(*)(struct udev_monitor *));
CHECK_TYPE(udev_monitor_unref, struct udev_monitor *(*)(struct udev_monitor *));
CHECK_TYPE(udev_device_get_devnode, const char *(*)(struct udev_device *));
CHECK_TYPE(udev_device_get_action, const char *(*)(struct udev_device *));
CHECK_TYPE(udev_device_unref, struct udev_device *(*)(struct udev_device *));

const unsigned long m15_daemon_udev_pointer_size = sizeof(struct udev *);
