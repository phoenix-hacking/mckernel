"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded exact selected export and event consumer edges; no unknown target skip.
"""
from pathlib import Path
import json, struct
D=Path(__file__).resolve().parent
ns={'__file__':str(D/'review_current112.py')}
source=(D/'review_current112.py').read_text().split('\nexports=[]')[0]
exec(compile(source,'retained CURRENT112 exact reader initialization','exec'),ns)
globals().update({k:v for k,v in ns.items() if k!='__file__'})
failed7={'f03_prlimit_body_result','syscall_do_prlimit64_bridge','f03_do_exit_supported_v2','f03_wait_release_thread','f03_ptrace_io_unlock','do_process_vm_read_writev','arch_rt_sigreturn_check_signal_bridge'}
allowed_tails={'futex26futex_dispatch_wake_bridge','procfs17procfs_thread_ctl','f03_prlimit10production9PROVIDERS','syscall_policy20f06_process_vm_entry22f06_process_vm_rw_copy','syscall_policy20f06_process_vm_entry22f06_process_vm_rw_vtop','syscall_policy20f06_process_vm_entry31f06_process_vm_rw_update_unlock','syscall_policy20f06_process_vm_entry29f06_process_vm_rw_update_lock','syscall_policy20f06_process_vm_entry29f06_process_vm_rw_read_unlock','syscall_policy20f06_process_vm_entry27f06_process_vm_rw_read_lock','syscall_policy25f03_check_signal_dispatch'}
def exact_target_table(elf,sec,final,address):
    raw=bytearray(elf.raw[sec['offset']:sec['offset']+sec['size']]);assert sec['flags']&7==2 and sec['align']==8
    other=old if elf is new else new;othersec=next(s for s in other.sections if s['name']==sec['name'])
    assert bytes(raw)==other.raw[othersec['offset']:othersec['offset']+othersec['size']]
    def table_shape(e,s):
        out=[]
        for rs in e.sections:
            if rs['type']!=4 or rs['info']!=s['index']:continue
            for at in range(rs['offset'],rs['offset']+rs['size'],24):
                off,info,a=struct.unpack_from('<QQq',e.raw,at);t=e.symbols[info>>32]
                out.append((off,info&0xffffffff,a,t['name'] or e.sections[t['shndx']]['name'],t['value']))
        return out
    assert table_shape(elf,sec)==table_shape(other,othersec)
    rsecs=[s for s in elf.sections if s['type']==4 and s['info']==sec['index']];records=[]
    for rs in rsecs:
        assert rs['size']%24==0
        for at in range(rs['offset'],rs['offset']+rs['size'],24):
            off,info,a=struct.unpack_from('<QQq',elf.raw,at);t=elf.symbols[info>>32];assert info&0xffffffff==1 and off+8<=len(raw)
            if t['name']:value=final.sym(t['name'])['value']+a;name=t['name']
            elif sec['name'].endswith('f03_prlimit10production9PROVIDERS'):
                tails={16:'f03_prlimit10production8forward4',24:'f03_prlimit10production11current_pid',56:'syscall_policy20f03_wait_writer_lock',64:'syscall_policy22f03_wait_writer_unlock',72:'syscall_policy20f03_wait_writer_lock',80:'syscall_policy22f03_wait_writer_unlock'}
                assert off in tails and a==0 and t['type']==3 and t['value']==0
                owners=[s for s in elf.symbols if s['shndx']==t['shndx'] and s['name'].endswith(tails[off]) and s['type']==2 and s['value']==0 and s['size']==elf.sections[t['shndx']]['size']]
                assert len(owners)==1;name=owners[0]['name'];f=final.sym(name);assert f['type']==2 and f['size']==owners[0]['size'] and f['bind']==0;value=f['value']
            else:
                assert t['type']==3 and t['shndx']==fn(elf,'f03_prlimit_body_result')['shndx'] and t['value']==0
                value=final.sym('f03_prlimit_body_result')['value']+a;name='f03_prlimit_body_result'
            struct.pack_into('<Q',raw,off,value);records.append(dict(offset=off,target=name,addend=a,positive_final_address=hex(value)))
    found,_=final.at(address,len(raw),True);assert found==bytes(raw)
    return dict(section=sec['name'],bytes=sec['size'],full_final_bytes_reproduced=True,targets=records,raw_hex=bytes(raw).hex())
def special(elf,name,final):
    s=fn(elf,name);raw=bytearray(data(elf,s));actual=final.bytes(final.sym(name));records=[]
    for r in rels(elf,s):
        off=r['offset'];t=r['target'];assert r['type']==1;value=struct.unpack_from('<Q',actual,off)[0]
        if t['name']:
            assert value==final.sym(t['name'])['value']+r['addend'];kind='NAMED';target=t['name'];detail={}
        else:
            sec=elf.sections[t['shndx']];assert t['type']==3 and t['value']==0
            if sec['name']=='.lrodata.str1.1':
                start=sec['offset']+r['addend'];literal=elf.raw[start:elf.raw.index(b'\0',start)+1];found,_=final.at(value,len(literal),True);assert found==literal
                kind='EXACT_SECTION_STRING';target=None;detail=dict(literal_hex=literal.hex())
            elif sec['name'] in ['.lrodata.f03_prlimit_body_result','.lrodata..Lswitch.table.f03_prlimit_body_result']:
                assert name=='f03_prlimit_body_result' and r['addend']==0 and sec['size']==128
                kind='EXACT_PRLIMIT_16_ENTRY_TABLE';target=sec['name'];detail=exact_target_table(elf,sec,final,value)
            else:
                owners=[v for v in elf.symbols if v['name'] and v['shndx']==t['shndx'] and v['value']==0 and v['size']==sec['size'] and v['type'] in (1,2)]
                assert len(owners)==1;owner=owners[0]
                assert any(owner['name'].endswith(tail) for tail in allowed_tails),(name,owner)
                f=final.sym(owner['name']);assert f['size']==owner['size'] and f['type']==owner['type'] and f['bind']==owner['bind']==0 and value==f['value']+r['addend']
                kind='EXACT_NAMED_LOCAL_SECTION_OWNER';target=owner['name'];detail=dict(input_owner=owner,final_owner=f)
                if owner['type']==1:detail['full_table']=exact_target_table(elf,sec,final,f['value'])
        struct.pack_into('<Q',raw,off,value);records.append(dict(offset=off,type=1,addend=r['addend'],kind=kind,target=target,actual_final_address=hex(value),**detail))
    assert bytes(raw)==actual
    return s,records
records=[]
for name in names:
    resolver=special if name in failed7 else patched
    s,rr=resolver(new,name,image);old_records=None
    if name not in newnames:
        before,br=resolver(old,name,oldimage);assert before['size']==s['size']
        a=bytearray(data(old,before));b=bytearray(data(new,s));assert len(br)==len(rr)
        for x,y in zip(br,rr):
            oldadd=x['addend']+(34 if x['kind']=='EXACT_SECTION_STRING' and x['addend']>=9566 else 0)
            assert (x['offset'],x['type'],oldadd,x['kind'],x.get('target'),x.get('literal_hex'))==(y['offset'],y['type'],y['addend'],y['kind'],y.get('target'),y.get('literal_hex'))
            a[x['offset']:x['offset']+8]=bytes(8);b[y['offset']:y['offset']+8]=bytes(8)
        assert a==b;old_records=br
    records.append(dict(name=name,final=image.sym(name),current_final_bytes_reproduced=True,targets=rr,accepted111_nonrelocated_body_equal=old_records is not None))
kc=Elf(B/'CMakeFiles/mckernel.img.dir/syscall.c.o');edges=[]
for s in kc.symbols:
    if s['type'] not in (1,2) or not s['shndx'] or not kc.sections[s['shndx']]['flags']&2:continue
    for r in rels(kc,s):
        name=r['target']['name']
        if name not in ['perf_event_set_period_bridge','perf_event_update_bridge']:continue
        assert r['type']==1 and r['addend']==0
        f=image.sym(s['name']);actual=struct.unpack_from('<Q',image.bytes(f),r['offset'])[0];assert actual==image.sym(name)['value']
        edges.append(dict(consumer=s['name'],consumer_type=s['type'],offset=r['offset'],Rust_provider=name,current_final_address=hex(actual)))
assert {r['Rust_provider'] for r in edges}=={'perf_event_set_period_bridge','perf_event_update_bridge'}
provider_names={'f03_perf_counter_providers_v1','f03_perf_read_providers_v1'};consumers=set()
for sec in new.sections:
    if sec['type']!=4 or new.sections[sec['info']]['flags']&6!=6:continue
    for at in range(sec['offset'],sec['offset']+sec['size'],24):
        off,info,addend=struct.unpack_from('<QQq',new.raw,at);target=new.symbols[info>>32]
        if target['name'] not in provider_names:continue
        for s in new.symbols:
            if s['shndx']==sec['info'] and s['type']==2 and s['value']<=off<s['value']+s['size']:consumers.add(s['name'])
assert consumers=={'perf_counter_set','perf_event_read_value','f03_perf_stop_v1','perf_start','perf_reset'}
event_consumers=[compare(name) for name in sorted(consumers)]
report=dict(scope=__doc__.splitlines()[0],independent=True,decision='PASS_EXACT_52_CURRENT_EXPORT_BODIES_AND_SELECTED_EVENT_CONSUMER_EDGES',current_Rust=ref(B/'rust/mckernel_rust.o'),current_image=ref(B/'mckernel.img'),all52_exports=records,current_event_C_consumer_edges=edges,current_five_Rust_event_table_consumers=event_consumers,anonymous_target_policy='Exact NUL strings; exact named LOCAL section owners from the finite listed providers; exact two128B prlimit tables. No unknown target accepted.',native_execution=False)
with (D/'SELECTED-EXPORT-AND-EVENT-CONSUMERS.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(ref(D/'SELECTED-EXPORT-AND-EVENT-CONSUMERS.json')))
