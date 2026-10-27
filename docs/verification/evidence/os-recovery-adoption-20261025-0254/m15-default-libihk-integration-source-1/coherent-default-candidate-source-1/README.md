Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

One coherent private default source candidate: `ihk/linux/user/CMakeLists.txt`,13474B/a21e1cfb, over exact current canonical10456B/b193917d. The4183B IHK patch is the only active CMake integration delta in this packet. Root alone may materialize/integrate it; there are no canonical/Git edits here.

This composes the existing daemon owner's exact e754 Rust default rule and PROGRAMS install with the frozen library runtime install split. The remaining grouped executable install contains ihkconfig/ihkosctl; ihklib has `ihklib_runtime`/`ihklib_development` components; ihkmond is installed by its own Rust branch. Output names, sbin/lib64 destinations and full install behavior are preserved. Daemon0c0b Rust is referenced from its owner/source-addition patch, not reimplemented. Library bodies, eventfd ownership semantics, source producer ON, external archive OFF and ABI/profile guards are unchanged.

The completed nine pure reuse tests and exact35-input/53-dependency accepted library tuple are reused without rerunning them. The accepted source-produced archive is b8074933; linked DSO is89639e9d. Both are historical artifacts with matching exact source/tool/ABI provenance. Actual after-configure graph evidence is still required and NULL here; an old snapshot is never a current observation.

`EXACT-SELECTED-DEFAULT-SUFFIX.RECIPE.NOT-RELEASED.json` contains the exact prospective command sequence and Root-only actual fields:

1. Configure the composed private source under the retained SDK cache/options and emit the selected graph; join the actual command.
2. Capture and pass the existing reuse eligibility gate on the new actual graph/tool/source/header/ABI/output tuple. Preserve both old full-source and new configure provenance.
3. Extract the exact generated ihkmond Rust command and all declared dependencies from that graph. Bind current SDK7 source0c0b/header/platform/compiler/libudev dependencies plus the passed89639 library. Only then may Root independently release that one downstream command through its owned capture. The expected literal argv in this packet is a comparison target, not proof that configure emitted it. This obtains scoped selected-rule acceptance; it is not a claim that full Make all ran.
4. Run the actual generated ihklib_runtime component install to a fresh DESTDIR.
5. Run the generated nested Unspecified user install for the daemon and retained CLI/header/man artifacts. Bind the retained CLI artifacts first; this is not whole-OS installation acceptance.
6. Run the existing exact installed-library/RPATH/76-provider checker and loader-only daemon resolution against the staged lib64. No daemon main/native call is proposed.

The actual existing Make edges are `/src/ihk/linux/user/CMakeLists.txt` and `CMakeCache.txt` in the archive producer rule. They remain intact. A normal `cmake --build` traverses them and can rerun the completed producer merely because the daemon/install CMake file or cache provenance changed. Do not use Make -o/-W, delete an edge, forge timestamps or treat a graph-only eligibility result as permission to run that producer. The scoped downstream command above requires its own complete current dependency validation and execution release; if Root requires a full Make-produced result, it must choose that separate build explicitly.

There is no genuine library source/compiler/ABI change in this static candidate. If the actual gate fails, its named field identifies the concrete changed source/header/config, compiler/BFD, producer argv, flags/link/dependency or generated/output artifact requiring new build qualification. Unknown actual changes remain held; the recipe does not convert them into a broad reuse pass.

All actual configure, graph, first-compiler, dependency-review, admission, execution, install and loader references remain NULL. No configure, compiler, native, Root, grant, cleanup or Git operation was executed. The same thread, existing credit run and fixed2026-10-27T11:24:50Z cutoff apply. M14/M15/file retirement remains open.
