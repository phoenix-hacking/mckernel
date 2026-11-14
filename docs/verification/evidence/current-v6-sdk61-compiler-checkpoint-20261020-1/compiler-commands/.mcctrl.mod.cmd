savedcmd_/candidate/modules/mcctrl.mod := printf '%s\n'   mcctrl.o | awk '!x[$$0]++ { print("/candidate/modules/"$$0) }' > /candidate/modules/mcctrl.mod
