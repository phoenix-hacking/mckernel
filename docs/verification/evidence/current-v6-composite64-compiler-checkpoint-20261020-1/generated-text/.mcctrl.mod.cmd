savedcmd_/candidate/modules/mcctrl.mod := printf '%s\n'   mcctrl_rust.o mcctrl_vm_write_compat.o | awk '!x[$$0]++ { print("/candidate/modules/"$$0) }' > /candidate/modules/mcctrl.mod
