#pragma once
#include <stdint.h>
int ihklib_device_open(int index);
void fixture_printk(const char *format,...);
#define printk(...) fixture_printk(__VA_ARGS__)
