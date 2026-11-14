savedcmd_/candidate/modules/ihk-smp-x86_64.o := ld.lld -m elf_x86_64 -z noexecstack   -r -o /candidate/modules/ihk-smp-x86_64.o @/candidate/modules/ihk-smp-x86_64.mod  ; ./tools/objtool/objtool --hacks=jump_label --hacks=noinstr --hacks=skylake --ibt --mcount --mnop --orc --retpoline --rethunk --sls --static-call --uaccess --prefix=16  --link  --module /candidate/modules/ihk-smp-x86_64.o

/candidate/modules/ihk-smp-x86_64.o: $(wildcard ./tools/objtool/objtool)
