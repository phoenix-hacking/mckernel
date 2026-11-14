savedcmd_drivers/misc/mckernel/mcctrl.o := ld.lld -m elf_x86_64 -z noexecstack   -r -o drivers/misc/mckernel/mcctrl.o @drivers/misc/mckernel/mcctrl.mod  ; ./tools/objtool/objtool --hacks=jump_label --hacks=noinstr --hacks=skylake --ibt --mcount --mnop --orc --retpoline --rethunk --sls --static-call --uaccess --prefix=16 --werror  --link  --module drivers/misc/mckernel/mcctrl.o

drivers/misc/mckernel/mcctrl.o: $(wildcard ./tools/objtool/objtool)
