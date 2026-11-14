savedcmd_drivers/misc/mckernel/mcctrl.o := RUST_MODFILE=drivers/misc/mckernel/mcctrl rustc --edition=2021 -Zbinary_dep_depinfo=y -Astable_features -Dunsafe_op_in_unsafe_fn -Dnon_ascii_idents -Wrust_2018_idioms -Wunreachable_pub -Wmissing_docs -Wrustdoc::missing_crate_level_docs -Wclippy::all -Wclippy::mut_mut -Wclippy::needless_bitwise_bool -Wclippy::needless_continue -Wclippy::no_mangle_with_rust_abi -Wclippy::dbg_macro -Cpanic=abort -Cembed-bitcode=n -Clto=n -Cforce-unwind-tables=n -Ccodegen-units=1 -Csymbol-mangling-version=v0 -Crelocation-model=static -Zfunction-sections=n -Wclippy::float_arithmetic --target=./scripts/target.json -Ctarget-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2 -Zcf-protection=branch -Zno-jump-tables -Ztune-cpu=generic -Cno-redzone=y -Ccode-model=kernel -Zfunction-return=thunk-extern -Zpatchable-function-entry=16,16 -Copt-level=2 -Cdebug-assertions=n -Coverflow-checks=n -Dwarnings -Cdebuginfo=2  --cfg MODULE  @./include/generated/rustc_cfg -Zallow-features=arbitrary_self_types,new_uninit,used_with_arg -Zcrate-attr=no_std -Zcrate-attr='feature(arbitrary_self_types,new_uninit,used_with_arg)' -Zunstable-options --extern force:alloc --extern kernel --crate-type rlib -L ./rust/ --crate-name mcctrl --sysroot=/dev/null --out-dir drivers/misc/mckernel/ --emit=dep-info=drivers/misc/mckernel/.mcctrl.o.d --emit=obj=drivers/misc/mckernel/mcctrl.o /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/mcctrl.rs  ; ./tools/objtool/objtool --hacks=jump_label --hacks=noinstr --hacks=skylake --ibt --mcount --mnop --orc --retpoline --rethunk --sls --static-call --uaccess --prefix=16 --werror  --link  --module drivers/misc/mckernel/mcctrl.o

source_drivers/misc/mckernel/mcctrl.o := /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/mcctrl.rs

deps_drivers/misc/mckernel/mcctrl.o := \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/mcctrl_exec.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/mcctrl_process.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/mcctrl_vm.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/user_string.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/application_image.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/abi/x86_64.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/abi/os_service.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/abi/application.rs \
  ./rust/libcore.rmeta \
  ./rust/libkernel.rmeta \
  ./rust/liballoc.rmeta \
  ./rust/libcompiler_builtins.rmeta \
  ./rust/libmacros.so \
  ./rust/libbindings.rmeta \
  ./rust/libuapi.rmeta \
  ./rust/libbuild_error.rmeta \

drivers/misc/mckernel/mcctrl.o: $(deps_drivers/misc/mckernel/mcctrl.o)

$(deps_drivers/misc/mckernel/mcctrl.o):

drivers/misc/mckernel/mcctrl.o: $(wildcard ./tools/objtool/objtool)
