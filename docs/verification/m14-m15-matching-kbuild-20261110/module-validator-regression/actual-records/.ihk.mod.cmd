savedcmd_drivers/misc/mckernel/ihk.mod := printf '%s\n'   ihk.o | awk '!x[$$0]++ { print("drivers/misc/mckernel/"$$0) }' > drivers/misc/mckernel/ihk.mod
