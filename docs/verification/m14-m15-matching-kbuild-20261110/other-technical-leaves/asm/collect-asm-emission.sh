#!/usr/bin/bash
set -euo pipefail
umask 077
if test -n "$(/usr/bin/find /capture -mindepth 1 -maxdepth 1 -print -quit)"; then
  /usr/bin/printf '%s\n' 'fresh capture required' >&2
  exit 64
fi
/usr/bin/sha256sum --check --strict /input/actual-inputs.sha256 > /capture/input-identity.stdout 2> /capture/input-identity.stderr
run_read() {
  local phase="$1"
  shift
  local rc=0
  "$@" > "/capture/${phase}.stdout" 2> "/capture/${phase}.stderr" || rc=$?
  /usr/bin/printf '%s\t%d\n' "$phase" "$rc" >> /capture/exit-status.tsv
  if test "$rc" -ne 0; then
    exit "$rc"
  fi
}
run_read leaf-instructions /usr/bin/objdump -drt /output/build/drivers/misc/mckernel/m15_mmap_trace_gates.o /output/build/drivers/misc/mckernel/m15_mm_write_warning.o
run_read warning-bug-table /usr/bin/objdump -s --section=__bug_table /output/build/drivers/misc/mckernel/m15_mm_write_warning.o
run_read final-module-functions /usr/bin/objdump -dr --section=.text --start-address=0x9500 --stop-address=0x959b /output/build/drivers/misc/mckernel/mcctrl.ko
run_read final-module-tables /usr/bin/objdump -rs --section=__jump_table --section=__bug_table /output/build/drivers/misc/mckernel/mcctrl.ko
/usr/bin/printf '%s\n' 'PASSIVE_READS_COMPLETE; source/emission/owner qualification requires actual raw review'
