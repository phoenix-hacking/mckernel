"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact authenticated closed35/21 fixture role; no prefix or general import waiver.
"""
import hashlib,json,re,struct
from pathlib import Path

def validate(contract, Elf, object_bytes, owning, auth, need):
    for row in contract['authenticated_inputs']:
        auth(row)
    old=Elf(Path(contract['old_syscall']['path']))
    actual=Elf(Path(contract['actual_syscall']['path']))
    names=set(contract['D_removed']);removed_U=set(contract['U_removed'])
    need(len(names)==35 and len(removed_U)==21,'closed35/21 cardinality differs')
    D=lambda e:{s['name'] for s in e.symbols if s['name'] and s['shndx'] and s['bind'] in (1,2)}
    U=lambda e:{s['name'] for s in e.symbols if s['name'] and not s['shndx']}
    need(D(old)-D(actual)==names and not D(actual)-D(old),'closed35 exact D delta differs')
    need(U(old)-U(actual)==removed_U and not U(actual)-U(old),'closed21 exact U delta differs')
    need(set(f['name'] for f in contract['closed35_objects'])==names,'closed35 object membership differs')
    intervals=[];pointer_targets=set();count=0
    for f in contract['closed35_objects']:
        s=old.sym(f['name']);sec=old.sections[s['shndx']]
        need(s==f['symbol'] and sec==f['section'] and s['bind']==1 and s['type']==1
             and sec['flags']&2 and not sec['flags']&4,'exact fixture storage shape differs')
        need(object_bytes(old,s).hex()==f['bytes_hex'],'exact fixture initializer differs')
        actual_RELA=owning(old,s)
        need(actual_RELA==f['outgoing_RELA'],'exact fixture outgoing RELA differs')
        for row in actual_RELA:
            t=row['target']
            need(len(actual_RELA)==1 and s['size']==8 and row['offset']==0 and row['type']==1
                 and row['addend']==0 and t['shndx']==0 and bool(t['name']), 'not exact eight-byte R64 witness pointer')
            pointer_targets.add(t['name']);count+=1
        intervals.append((s['shndx'],s['value'],s['value']+s['size']))
    need(count==22 and pointer_targets==set(contract['undefined_targets_from_closed35'])
         and removed_U<=pointer_targets and pointer_targets-removed_U=={'syscall_do_kill_thread_bridge'},'closed22 pointer/21 U target set differs')
    incoming=[];removed_U_owners=[]
    for sec in old.sections:
        if sec['type'] not in (4,9):
            continue
        need(sec['type']==4 and sec['entsize']==24 and sec['size']%24==0 and sec['link']==old.table['index'],'old RELA format differs')
        allocated=bool(old.sections[sec['info']]['flags']&2)
        for index in range(sec['size']//24):
            offset,info,addend=struct.unpack_from('<QQq',old.raw,sec['offset']+24*index)
            t=old.symbols[info>>32];kind=info&0xffffffff
            if t['name'] in removed_U:
                owners=[f for f in contract['closed35_objects'] if f['outgoing_RELA'] and f['symbol']['shndx']==sec['info'] and f['symbol']['value']<=offset<f['symbol']['value']+f['symbol']['size']]
                need(len(owners)==1 and kind==1 and offset==owners[0]['symbol']['value'] and addend==0,'removed U has genuine/nonfixture relocation consumer')
                removed_U_owners.append(dict(name=t['name'],fixture=owners[0]['name'],offset=offset,type=kind,addend=addend))
            if allocated:
                need(t['name'] not in names,'named allocated fixture consumer')
                addresses={t['value']+addend}
                if kind in (2,4):
                    addresses.add(t['value']+addend+4)
                need(not any(t['shndx']==section and any(start<=a<end for a in addresses) for section,start,end in intervals),'SECTION+addend allocated fixture consumer')
    need(sorted(removed_U_owners,key=lambda x:x['name'])==contract['exact_removed_U_relocation_owners'],'removed U relocation ownership rows differ')
    input_proofs=[]
    for row in contract['five_actual_partial_inputs']+[contract['actual_partial']]:
        e=Elf(Path(row['path']))
        need(all(s['name'] not in names for s in e.symbols),'actual input/partial has fixture definition/import')
        count=0
        for sec in e.sections:
            if sec['type'] not in (4,9) or not e.sections[sec['info']]['flags']&2:
                continue
            need(sec['type']==4 and sec['entsize']==24 and sec['size']%24==0 and sec['link']==e.table['index'],'actual ALLOC RELA format differs')
            for i in range(sec['size']//24):
                offset,info,addend=struct.unpack_from('<QQq',e.raw,sec['offset']+24*i)
                need(e.symbols[info>>32]['name'] not in names,'actual named fixture consumer')
                count+=1
        input_proofs.append(dict(input=row,ALLOC_RELA_count=count))
    need(input_proofs==contract['actual_input_consumer_proofs'],'actual input proof membership/count differs')
    need(U(Elf(Path(contract['actual_partial']['path'])))==set(contract['strict_partial_U19']) and len(contract['strict_partial_U19'])==19,'strict partial19 imports differ')
    source=auth(contract['old_source']).decode().splitlines(keepends=True)
    tail=contract['complete_source_append']
    need(''.join(source[tail['first_line']-1:tail['last_line']])==tail['exact_text'],'complete original witness source append differs')
    for f in contract['closed35_objects']:
        need(any(f['name'] in line for line in source[tail['first_line']-1:tail['last_line']]),'fixture declaration absent from full exact source tail')
    util=contract['util_exact_line_immediates']
    need(old.sym('util_thread')==util['old_symbol'] and actual.sym('util_thread')==util['new_symbol'],'util exact symbol shape differs')
    a,b=object_bytes(old,old.sym('util_thread')),object_bytes(actual,actual.sym('util_thread'))
    need(a.hex()==util['old_bytes_hex'] and b.hex()==util['new_bytes_hex'] and len(a)==len(b)==1510,'util exact machine bytes differ')
    need(owning(old,old.sym('util_thread'))==util['old_function_RELA'] and owning(actual,actual.sym('util_thread'))==util['new_function_RELA'],'util exact complete RELA differs')
    old_lines=auth(contract['old_source']).decode().splitlines()
    new_lines=auth(contract['current_source']).decode().splitlines()
    def logical(lines,physical):
        value=1;directive=None
        for n,text in enumerate(lines[:physical],1):
            match=re.match(r'\s*#\s*(?:line\s+)?(\d+)(?:\s+"([^"]*)")?',text)
            if n==physical:
                return dict(physical_line=n,logical_line=value,text=text,latest_directive=directive)
            if match:
                value=int(match.group(1));directive=dict(physical_line=n,text=text,next_logical_line=value)
            else:
                value+=1
    allowed=set()
    for row in util['exact_six_instruction_source_bindings']:
        i=row['function_relative_instruction_offset']
        need(a[i:i+5].hex()==row['old_instruction_hex'] and b[i:i+5].hex()==row['new_instruction_hex'],'util exact line instruction differs')
        need(a[i]==b[i]==row['opcode'] and row['opcode'] in (0xb9,0xba)
             and int.from_bytes(b[i+1:i+5],'little')-int.from_bytes(a[i+1:i+5],'little')==27,'util line immediate/opcode differs')
        left,right=row['old_source_line'],row['new_source_line']
        need(logical(old_lines,left['physical_line'])==left and logical(new_lines,right['physical_line'])==right
             and left['text']==right['text'] and '__FILE__' in right['text'] and '__LINE__' in right['text']
             and ('kmalloc_tracked(' in right['text'] or 'kfree_tracked(' in right['text'])
             and int.from_bytes(a[i+1:i+5],'little')==left['logical_line']
             and int.from_bytes(b[i+1:i+5],'little')==right['logical_line'],'util exact source trace callsite differs')
        allowed.update(range(i+1,i+5))
    need(len(util['exact_six_instruction_source_bindings'])==6 and sum(x!=y for x,y in zip(a,b))==8
         and all(x==y or i in allowed for i,(x,y) in enumerate(zip(a,b))),'util changed beyond six exact line immediates')
    for f in util['other30_global_functions']:
        left,right=old.sym(f['name']),actual.sym(f['name'])
        need((left['bind'],left['type'],left['size'])==(right['bind'],right['type'],right['size'])==(1,2,f['size'])
             and object_bytes(old,left)==object_bytes(actual,right)
             and hashlib.sha256(object_bytes(old,left)).hexdigest()==f['machine_sha256'],'other runtime function bytes differ')
    need(len(util['other30_global_functions'])==30,'other30 runtime function set differs')
    need(util_semantic_relocations(old,actual,contract['old_source'],contract['current_source'],object_bytes,owning,need)==contract['util_semantic_relocations'],'util exact semantic relocation proof differs')
    return names,removed_U,dict(closed_D35=sorted(names),closed_U21=sorted(removed_U),exact_witness_pointer_RELA22=22,actual_input_consumer_proofs=input_proofs,util_exact_six_line_immediates=True,util_changed_bytes=8,other30_runtime_functions_unchanged=True,no_generic_allowance=True)


def util_semantic_relocations(old,new,old_source,new_source,object_bytes,owning,need):
    """Closed six-caller data targets, never a local-symbol-prefix allowance."""
    local_map={'ddebug.17891':'ddebug.17941','ddebug.17894':'ddebug.17944',
               'ddebug.17895':'ddebug.17945','ddebug.17896':'ddebug.17946',
               '__FUNCTION__.17893':'__FUNCTION__.17943'}
    debug_names={'ddebug.17891','ddebug.17894','ddebug.17895','ddebug.17896'}
    strings={'.LC2','.LC118','.LC117','.LC121','.LC122','.LC119','.LC120'}
    source_names=(old_source['path'].encode()+b'\0',new_source['path'].encode()+b'\0')
    old_lines=Path(old_source['path']).read_text().splitlines();new_lines=Path(new_source['path']).read_text().splitlines()
    def cstring(e,row):
        t=row['target'];sec=e.sections[t['shndx']]
        need(0<t['shndx']<len(e.sections) and sec['flags']&2 and not sec['flags']&4 and sec['type']!=8,'util target is not allocated string storage')
        data=e.payload(sec);start=t['value']+row['addend'];end=data.find(b'\0',start)
        need(0<=start<=end<len(data),'util string target is not bounded')
        return data[start:end+1]
    def string_pair(a,b):
        need(a==b or (a,b)==source_names,'util string changed beyond exact two compiler source paths')
        return dict(old_hex=a.hex(),new_hex=b.hex(),exact_source_path_change=(a,b)==source_names and a!=b)
    before,after=owning(old,old.sym('util_thread')),owning(new,new.sym('util_thread'))
    need(len(before)==len(after)==40,'util semantic RELA40 set differs')
    proof=[];seen=set()
    for left,right in zip(before,after):
        need((left['offset'],left['type'],left['addend'])==(right['offset'],right['type'],right['addend']),'util semantic relocation location/type/addend changed')
        a,b=left['target'],right['target'];name=a['name']
        need(b['name']==local_map.get(name,name) and (a['bind'],a['type'],a['size'])==(b['bind'],b['type'],b['size']),'util target changed beyond closed local map')
        row=dict(offset=left['offset'],type=left['type'],addend=left['addend'],old_name=name,new_name=b['name'])
        if name in debug_names:
            seen.add(name);x,y=object_bytes(old,a),object_bytes(new,b)
            need(len(x)==len(y)==32 and x[:24]==y[:24] and x[27:]==y[27:]
                 and int.from_bytes(y[24:27],'little')-int.from_bytes(x[24:27],'little')==27,'util exact ddebug line storage differs')
            lo,ln=int.from_bytes(x[24:27],'little'),int.from_bytes(y[24:27],'little')
            need(old_lines[lo+96]==new_lines[ln+96] and 'dkprintf(' in old_lines[lo+96],'util ddebug source attribution differs')
            pa,pb=owning(old,a),owning(new,b)
            need(len(pa)==len(pb)==2,'util ddebug complete pointer set differs')
            pointers=[]
            for u,v in zip(pa,pb):
                need((u['offset'],u['type'])==(v['offset'],v['type']) and u['type']==1,'util ddebug pointer slot differs')
                pointers.append(dict(offset=u['offset'],type=u['type'],strings=string_pair(cstring(old,u),cstring(new,v))))
            row.update(role='exact_ddebug_source_line',old_bytes_hex=x.hex(),new_bytes_hex=y.hex(),old_logical_line=lo,new_logical_line=ln,exact_source_call=old_lines[lo+96],old_pointer_RELA=pa,new_pointer_RELA=pb,pointer_strings=pointers)
        elif name=='__FUNCTION__.17893':
            seen.add(name);need(object_bytes(old,a)==object_bytes(new,b)==b'util_thread\0' and not owning(old,a) and not owning(new,b),'util exact function string differs')
            row.update(role='exact_function_name',bytes_hex=object_bytes(old,a).hex())
        elif name in strings:
            row.update(role='exact_compiler_literal',strings=string_pair(cstring(old,left),cstring(new,right)))
        elif a['shndx'] in (0,0xfff2):
            need(a['shndx']==b['shndx'] and a['value']==b['value'],'util import/common owner shape differs')
            row.update(role='same_named_import_or_common',bind=a['bind'],symbol_type=a['type'],size=a['size'],value=a['value'])
        else:
            need(a['type']==b['type']==2 and object_bytes(old,a)==object_bytes(new,b),'util defined runtime target changed')
            row.update(role='exact_defined_function',size=a['size'],machine_sha256=hashlib.sha256(object_bytes(old,a)).hexdigest())
        proof.append(row)
    need(seen==set(local_map),'closed util local targets were not fully bound')
    return proof
