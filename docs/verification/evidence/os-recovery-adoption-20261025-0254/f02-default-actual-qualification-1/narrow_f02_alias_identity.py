"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow artifact identity predicate for only two independently reviewed F02 slots.
"""
TARGETS=['sched_idle_current_cpu_bridge','process_spin_lock_bridge','process_spin_unlock_bridge','cpu_enable_interrupt','cpu_disable_interrupt','schedule','sched_do_migrate_public','kmalloc_consolidate_free_list','process_sched_zero_free_bridge','cpu_safe_halt']
ALIASES={8:('process_spin_lock_bridge','mem_kmalloc_remote_lock_bridge'),16:('process_spin_unlock_bridge','mem_kmalloc_remote_unlock_bridge')}
def validate(rows):
    if len(rows)!=10:raise RuntimeError('exact ten callback slots required')
    alias_rows=[]
    for i,row in enumerate(rows):
        if (row['offset'],row['type'],row['addend'],row['original_name'])!=(i*8,1,0,TARGETS[i]):raise RuntimeError('exact original slots and R64 zero addends required')
        actual=row['actual_name'];original=row['original_name']
        if actual!=original and ALIASES.get(row['offset'])!=(original,actual):raise RuntimeError('unreviewed alias pair or slot')
        a=row['original_object_symbol'];b=row['actual_object_symbol'];fa=row['original_final_symbol'];fb=row['actual_final_symbol']
        keys=('bind','type','shndx','value','size','other')
        if a['bind']!=1 or a['type']!=2 or a['other']!=0 or a['size']<=0 or a['shndx']==0 or tuple(a[k] for k in keys)!=tuple(b[k] for k in keys):raise RuntimeError('exact GLOBAL FUNC object identity required')
        if fa['bind']!=1 or fa['type']!=2 or fa['other']!=0 or fa['size']!=a['size'] or fa['shndx']==0 or tuple(fa[k] for k in keys)!=tuple(fb[k] for k in keys):raise RuntimeError('exact GLOBAL FUNC final identity required')
        if len(bytes.fromhex(row['original_object_code_hex']))!=a['size'] or row['original_object_code_hex']!=row['actual_object_code_hex']:raise RuntimeError('exact object function code required')
        if len(bytes.fromhex(row['original_final_code_hex']))!=fa['size'] or row['original_final_code_hex']!=row['actual_final_code_hex']:raise RuntimeError('exact final function code required')
        if row['final_table_pointer']!=fa['value']:raise RuntimeError('original named final function pointer required')
        if actual!=original:alias_rows.append(dict(offset=row['offset'],original=original,actual=actual))
    if alias_rows!=[dict(offset=k,original=v[0],actual=v[1]) for k,v in ALIASES.items()]:raise RuntimeError('exact two reviewed aliases required')
    return dict(status='PASS_ONLY_TWO_REVIEWED_ALIAS_PAIRS_WITH_FULL_OBJECT_FINAL_IDENTITY',aliases=alias_rows,all_ten_original_named_final_function_addresses=True)
