#!/usr/bin/bash
set -euo pipefail
set -o noclobber
umask 022
/usr/bin/test -s /output/signal.alternate-repeat
/usr/bin/test -d /output/runtime/lib64
/usr/bin/test ! -e /output/runtime/lib64/ld-linux-x86-64.so.2
/usr/bin/test ! -e /output/runtime/lib64/libc.so.6
/usr/bin/cp --no-clobber --dereference --preserve=mode /lib64/ld-linux-x86-64.so.2 /output/runtime/lib64/ld-linux-x86-64.so.2
/usr/bin/cp --no-clobber --dereference --preserve=mode /lib64/libc.so.6 /output/runtime/lib64/libc.so.6
/usr/bin/readelf -W -h -l -S -n -s -d -V /output/signal.alternate-repeat > /evidence/payload-ELF.stdout
/usr/bin/nm -n /output/signal.alternate-repeat > /evidence/payload-nm.stdout
/usr/bin/cat /output/signal.alternate-repeat.d > /evidence/payload-source-dependencies.d
/usr/bin/cat /output/signal.alternate-repeat.map > /evidence/payload-link.map
/usr/bin/sha256sum /input/signal.alternate-repeat.c /output/signal.alternate-repeat /output/signal.alternate-repeat.d /output/signal.alternate-repeat.map /output/runtime/lib64/ld-linux-x86-64.so.2 /output/runtime/lib64/libc.so.6 > /evidence/payload-and-runtime.sha256
/usr/bin/stat --format='%a %s %n' /output/signal.alternate-repeat /output/runtime/lib64/ld-linux-x86-64.so.2 /output/runtime/lib64/libc.so.6 > /evidence/payload-and-runtime-modes.stdout
