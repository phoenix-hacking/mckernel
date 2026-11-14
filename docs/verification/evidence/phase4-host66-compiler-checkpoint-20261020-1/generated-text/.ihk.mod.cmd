savedcmd_/candidate/modules/ihk.mod := printf '%s\n'   ihk.o | awk '!x[$$0]++ { print("/candidate/modules/"$$0) }' > /candidate/modules/ihk.mod
