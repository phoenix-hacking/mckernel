savedcmd_/candidate/modules/mcctrl.o := ld.lld -m elf_x86_64 -z noexecstack   -r -o /candidate/modules/mcctrl.o @/candidate/modules/mcctrl.mod  ; ./tools/objtool/objtool --hacks=jump_label --hacks=noinstr --hacks=skylake --ibt --mcount --mnop --orc --retpoline --rethunk --sls --static-call --uaccess --prefix=16  --link  --module /candidate/modules/mcctrl.o

/candidate/modules/mcctrl.o: $(wildcard ./tools/objtool/objtool)
