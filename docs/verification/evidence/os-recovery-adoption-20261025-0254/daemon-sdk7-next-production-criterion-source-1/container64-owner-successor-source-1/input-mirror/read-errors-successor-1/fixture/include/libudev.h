#pragma once
struct udev;struct udev_monitor;struct udev_device;
struct udev *udev_new(void);struct udev *udev_unref(struct udev *);
struct udev_monitor *udev_monitor_new_from_netlink(struct udev *,const char *);
int udev_monitor_filter_add_match_subsystem_devtype(struct udev_monitor *,const char *,const char *);
int udev_monitor_enable_receiving(struct udev_monitor *);int udev_monitor_get_fd(struct udev_monitor *);
struct udev_device *udev_monitor_receive_device(struct udev_monitor *);
struct udev_monitor *udev_monitor_unref(struct udev_monitor *);
const char *udev_device_get_devnode(struct udev_device *);const char *udev_device_get_action(struct udev_device *);
struct udev_device *udev_device_unref(struct udev_device *);
