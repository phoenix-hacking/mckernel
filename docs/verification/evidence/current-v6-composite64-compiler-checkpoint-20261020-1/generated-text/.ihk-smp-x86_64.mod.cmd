savedcmd_/candidate/modules/ihk-smp-x86_64.mod := printf '%s\n'   ihk_smp_x86_64.o | awk '!x[$$0]++ { print("/candidate/modules/"$$0) }' > /candidate/modules/ihk-smp-x86_64.mod
