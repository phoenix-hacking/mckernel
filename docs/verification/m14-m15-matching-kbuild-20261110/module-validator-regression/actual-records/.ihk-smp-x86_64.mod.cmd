savedcmd_drivers/misc/mckernel/ihk-smp-x86_64.mod := printf '%s\n'   ihk_smp_x86_64.o | awk '!x[$$0]++ { print("drivers/misc/mckernel/"$$0) }' > drivers/misc/mckernel/ihk-smp-x86_64.mod
