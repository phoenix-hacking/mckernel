#pragma once
#define IHK_KMSG_SIZE ((4<<20)-4096)
#define IHK_DEVICE_GET_KMSG_BUF       0x112908
#define IHK_DEVICE_READ_KMSG_BUF      0x112909
#define IHK_DEVICE_RELEASE_KMSG_BUF   0x11290a
#define IHK_DEVICE_DETECT_HUNGUP      0x11290f
struct ihk_device_get_kmsg_buf_desc {
	int os_index; /* IN: OS index */
	void* handle; /* OUT: "Pointer" to kmsg_buf container */
};
struct ihk_device_read_kmsg_buf_desc {
	void* handle; /* IN: "Pointer" to kmsg_buf container */
	int shift;    /* IN: Empty the buffer or not */
	char* buf;    /* OUT: Buffer */
};
