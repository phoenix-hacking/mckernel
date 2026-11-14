# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
def _m14_check_page_unmap_symbols(mem_symbols, rust_symbols, final_symbols):
    def rows(text, symbol):
        return [line.split() for line in text.splitlines() if line.split()[-1:] == [symbol]]
    def unique(text, symbol, allowed, size=None):
        found = rows(text, symbol)
        _fail(len(found) == 1 and found[0][-2] in allowed,
              'M14 page_unmap provider type/count: ' + symbol)
        if size is not None:
            _fail(len(found[0]) == 4 and int(found[0][1], 16) == size,
                  'M14 page_unmap immutable ABI geometry width: ' + symbol)
    _fail(not any(row[-2] == 'T' for row in rows(mem_symbols, 'page_unmap')),
          'M14 original C page_unmap wrapper selected')
    unique(rust_symbols, 'page_unmap', ('T',))
    unique(final_symbols, 'page_unmap', ('T',))
    for symbol, size in (('page_unmap_hash_shift', 4), ('page_unmap_hash_mask', 8),
                         ('page_unmap_lock_stride', 8)):
        unique(mem_symbols, symbol, ('R',), size)
        unique(rust_symbols, symbol, ('U',))
        unique(final_symbols, symbol, ('R',), size)
    for symbol in ('page_hash_lock_bridge', 'page_hash_unlock_bridge', 'page_unmap_log_bridge'):
        unique(mem_symbols, symbol, ('T',))
        unique(rust_symbols, symbol, ('U',))
        unique(final_symbols, symbol, ('T',))
    # The accepted GCC9 object uses COMMON for this unchanged tentative global;
    # default GCC14 can use BSS. Both require one allocated provider, never U.
    unique(mem_symbols, 'page_hash_locks', ('B', 'C'))
    unique(rust_symbols, 'page_hash_locks', ('U',))
    unique(final_symbols, 'page_hash_locks', ('B', 'C'))


def _validate_m14_page_unmap_contract(source_root, build, tools, env, timeout, command_rows, objects):
    row, args = _m14_selected_row(source_root, build, 'kernel/mem.c',
                                'MCKERNEL_RUST_PAGE_HELPERS', tools)
    obj = (Path(row['directory']) / args[args.index('-o') + 1]).resolve(strict=True)
    objects['kernel/mem.c'] = _artifact(obj, 'M14 actual default public page_unmap C consumer')
    out = build / 'm14-production'
    oi = args.index('-o')
    pp = _m14_observe(args[:oi] + ['-E', str(source_root / 'kernel/mem.c')],
                      'selected-mem-public-page-unmap-preprocess', out, tools, env, timeout, command_rows)
    _fail(re.search(r'\bint\s+page_unmap\s*\([^;{}]*\)\s*\{', pp, re.S) is None
          and re.search(r'\bint\s+page_unmap\s*\([^;{}]*\)\s*;', pp, re.S) is not None,
          'M14 selected public page_unmap C exclusion/declaration')
    texts = []
    for path, label in ((obj, 'default-mem-public-ownership'),
                        (build / 'kernel/rust/mckernel_rust.o', 'Rust-public-page-unmap-ownership'),
                        (build / 'kernel/mckernel.img', 'image-public-page-unmap-ownership')):
        texts.append(_m14_observe([tools['tools']['nm']['path'], '-S', '-g', str(path)],
                                 label, out, tools, env, timeout, command_rows))
    _m14_check_page_unmap_symbols(*texts)
    return dict(public_Rust_provider='page_unmap', C_wrapper_excluded=True,
                immutable_geometry_widths={'page_unmap_hash_shift': 4,
                                           'page_unmap_hash_mask': 8,
                                           'page_unmap_lock_stride': 8},
                callbacks=('page_hash_lock_bridge', 'page_hash_unlock_bridge', 'page_unmap_log_bridge'),
                default_mem_object=objects['kernel/mem.c'], native=False)
