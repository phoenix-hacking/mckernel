#!/bin/sh
set -eu
root=/home/holden/mckernel-work/scratch/practical-file-stream-app-20261018-1
mkdir "$root/home" "$root/tmp"
exec /usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C LANG=C PYTHONDONTWRITEBYTECODE=1 \
    HOME="$root/home" TMPDIR="$root/tmp" \
    /usr/bin/taskset -c 7 /usr/bin/prlimit --as=1073741824 --cpu=150 \
    --nofile=256 --fsize=65536 --core=0 \
    /usr/bin/timeout --signal=TERM --kill-after=5s 180s \
    /home/holden/anaconda3/bin/python3 -B "$root/reference.py"
