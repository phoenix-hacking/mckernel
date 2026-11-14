"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite observation of new durably recorded ELF objects; no subprocess/hash/code execution.
"""
import struct


def need(ok, why):
    if not ok:
        raise ValueError(why)


class Elf:
    def __init__(self, path):
        self.data = path.read_bytes()
        need(self.data[:6] == b'\x7fELF\x02\x01', 'ELF64 little endian')
        header = struct.unpack_from('<16sHHIQQQIHHHHHH', self.data)
        need(header[1:3] == (1, 62) and header[11] == 64 and header[12], 'ordinary x86_64 relocatable')
        self.sections = [struct.unpack_from('<IIQQQQIIQQ', self.data, header[6]+i*64) for i in range(header[12])]
        self.names = self.payload(self.sections[header[13]])
        self.symbols, self.tables = {}, {}
        for index, section in enumerate(self.sections):
            if section[1] != 2:
                continue
            need(section[9] == 24 and section[5] % 24 == 0, 'symbol table shape')
            strings = self.payload(self.sections[section[6]])
            rows = []
            for offset in range(section[4], section[4]+section[5], 24):
                name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', self.data, offset)
                row = {'name': self.string(strings,name), 'info':info, 'section':shndx, 'value':value, 'size':size}
                rows.append(row)
                self.symbols.setdefault(row['name'],[]).append(row)
            self.tables[index] = rows

    @staticmethod
    def string(table, at):
        return table[at:table.index(b'\0',at)].decode('ascii')

    def payload(self, section):
        need(section[4]+section[5] <= len(self.data), 'section extent')
        return self.data[section[4]:section[4]+section[5]]

    def one(self, name):
        rows = self.symbols.get(name,[])
        need(len(rows)==1, ('one symbol',name,rows))
        return rows[0]

    def bytes(self, name, count):
        row = self.one(name)
        need(0 < row['section'] < len(self.sections) and row['size'] == count, 'defined exact-size data '+name)
        section = self.sections[row['section']]
        need(section[2]&2 and row['value']+count <= section[5], 'allocated data extent')
        start = section[4]+row['value']
        return self.data[start:start+count]

    def relocations(self):
        rows=[]
        for section in self.sections:
            if section[1]!=4:
                continue
            need(section[9]==24 and section[5]%24==0, 'RELA table shape')
            target=section[7]
            if not self.sections[target][2]&2:
                continue
            for offset in range(section[4],section[4]+section[5],24):
                address,info,addend=struct.unpack_from('<QQq',self.data,offset)
                symbol=self.tables[section[6]][info>>32]
                rows.append({'section':target,'offset':address,'name':symbol['name'],'type':info&0xffffffff,'addend':addend})
        return rows


def observe(rust_path, selected_path):
    rust, selected = Elf(rust_path), Elf(selected_path)
    entry = rust.one('__x86_wakeup')
    need(entry['section'] and entry['info']&15==2 and rust.sections[entry['section']][2]&6==6,
         'real allocated Rust entry body')
    need(selected.one('__x86_wakeup')['section']==0, 'actual selected C imports Rust entry')
    c_words=struct.unpack('<22Q',selected.bytes('M14_C_WAKEUP_TYPE_ABI',22*8))
    rust_words=struct.unpack('<22Q',rust.bytes('M14_RUST_WAKEUP_TYPE_ABI',22*8))
    need(c_words==rust_words, 'actual complete C TU and Rust 22-word type ABI')
    data={}
    for name,size in [('x86_wakeup_lapic_write_slot',8),('x86_wakeup_lapic_read_slot',8),
                      ('x86_wakeup_wait_slot',8),('x86_wakeup_first_page_slot',8),
                      ('x86_wakeup_boot_status_slot',8),('x86_wakeup_constants',20)]:
        row=selected.one(name)
        need(0 < row['section'] < len(selected.sections) and row['size']==size, 'actual typed C data '+name)
        section=selected.sections[row['section']]
        need(section[2]&2, 'allocated data provider '+name)
        data[name]={'size':size,'section':selected.string(selected.names,section[0]),
                    'relocatable_section_write_flag':bool(section[2]&1),
                    'final_link_readonly_qualification':'OPEN; C const declarations alone do not prove linked protection'}
    bridge=selected.one('x86_wakeup_bridge')
    calls=[r for r in selected.relocations() if r['name']=='__x86_wakeup'
           and r['section']==bridge['section'] and bridge['value']<=r['offset']<bridge['value']+bridge['size']]
    need(calls, 'actual allocated existing default bridge calls new Rust entry')
    return {'actual_complete_C_Rust_ABI_words':list(c_words),'allocated_default_bridge_relocations':calls,
            'declarative_C_data_debt':data,'native_AP_startup':'NOTEXECUTED','engineering_percentage':None}
