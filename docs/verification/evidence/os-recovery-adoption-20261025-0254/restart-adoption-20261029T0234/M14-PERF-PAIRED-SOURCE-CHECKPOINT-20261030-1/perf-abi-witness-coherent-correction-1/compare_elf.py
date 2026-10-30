#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Unreviewed source-only comparator; 31-word comparison and raw relocation inventory.
Caller owns stdout/stderr captures. Target, C ABI, link and native proof remain separate.
"""
import sys
try:
    import argparse, hashlib, io, json, os, re, stat, struct
    from elftools.elf.elffile import ELFFile
    from elftools.elf.relocation import RelocationSection
except ImportError as exc:
    sys.stderr.write('{"status":"ERROR","error":"required module unavailable"}\n')
    sys.exit(2)

NAMES=['copy_from','attr_freq','event_alloc','counter_alloc','syscall','allocate','read','ioctl','mmap','close','fcntl','lock','unlock']
MAX_OBJECT_BYTES=256*1024*1024

def load(path,expected,symbol,size):
    if not re.fullmatch(r'[0-9a-f]{64}',expected): raise ValueError('expected sha256 must be 64 lower-case hex digits')
    # Capture one exact byte sequence from one open descriptor. The parser never reopens the pathname.
    with open(path,'rb') as source:
        before=os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size>MAX_OBJECT_BYTES: raise ValueError('object must be a bounded regular file')
        content=source.read(MAX_OBJECT_BYTES+1)
        after=os.fstat(source.fileno())
    identity=(before.st_dev,before.st_ino)
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or len(content)!=before.st_size: raise ValueError('object changed while being captured')
    actual=hashlib.sha256(content).hexdigest()
    if actual!=expected: raise ValueError('object hash mismatch: '+path)
    stream=io.BytesIO(content); e=ELFFile(stream)
    if e.elfclass!=64 or not e.little_endian or e['e_machine']!='EM_X86_64' or e['e_type']!='ET_REL': raise ValueError('unsupported ELF identity')
    symtabs=[s for s in e.iter_sections() if s['sh_type']=='SHT_SYMTAB']
    if len(symtabs)!=1: raise ValueError('missing or ambiguous symtab')
    syms=symtabs[0].get_symbol_by_name(symbol) or []
    if len(syms)!=1: raise ValueError('missing or ambiguous symbol '+symbol)
    sym=syms[0];idx=sym['st_shndx']
    if not isinstance(idx,int) or sym['st_size']!=size: raise ValueError('bad symbol section or size '+symbol)
    sec=e.get_section(idx)
    if sec is None or sec['sh_type']!='SHT_PROGBITS': raise ValueError('not file-backed symbol '+symbol)
    off=sym['st_value'];blob=sec.data()
    if off<0 or off+size>len(blob): raise ValueError('symbol exceeds section')
    reloc=[]
    for section in e.iter_sections():
        if isinstance(section,RelocationSection) and section['sh_info']==idx:
            table=e.get_section(section['sh_link'])
            if table is None or table['sh_type']!='SHT_SYMTAB': raise ValueError('relocation table has invalid symbol table')
            for r in section.iter_relocations():
                pos=r['r_offset']-off
                if 0<=pos<size:
                    target=table.get_symbol(r['r_info_sym'])
                    reloc.append({'offset':pos,'type':r['r_info_type'],'symbol':target.name,'symbol_type':target['st_info']['type'],'symbol_section':target['st_shndx'],'symbol_value':target['st_value'],'addend':r['r_addend'] if section.is_RELA() else None})
    return {'identity':identity,'bytes':blob[off:off+size],'relocations':reloc,'sha256':actual}

class ContractParser(argparse.ArgumentParser):
    def error(self,message):
        self.exit(2,json.dumps({'status':'ERROR','error':'invalid arguments: '+message})+'\n')

def main():
    p=ContractParser()
    for prefix in ('c','rust_witness','rust_production'):
        p.add_argument('--'+prefix.replace('_','-'),required=True)
        p.add_argument('--'+prefix.replace('_','-')+'-sha256',required=True)
    a=p.parse_args()
    c=load(a.c,a.c_sha256,'f03_perf_entry_c_header_witness_v1',248)
    w=load(a.rust_witness,a.rust_witness_sha256,'f03_perf_entry_rust_scalar_witness_v1',248)
    r=load(a.rust_production,a.rust_production_sha256,'f03_perf_entry_binding_v1',352)
    if len({v['identity'] for v in (c,w,r)})!=3: raise ValueError('object inputs alias by device and inode')
    if c['relocations'] or w['relocations'] or any(x['offset']<248 for x in r['relocations']): raise ValueError('scalar values have relocations')
    values=[list(struct.unpack('<31Q',v['bytes'][:248])) for v in (c,w,r)]
    if values[0]!=values[1] or values[0]!=values[2]:
        mismatch=[{'index':i,'c':values[0][i],'rust_witness':values[1][i],'rust_binding':values[2][i]} for i in range(31) if len({values[0][i],values[1][i],values[2][i]})!=1]
        print(json.dumps({'status':'SCALAR_MISMATCH','mismatches':mismatch},indent=2));return 1
    inventory=[]
    for i,name in enumerate(NAMES):
        found=[x for x in r['relocations'] if x['offset']==248+i*8]
        if len(found)!=1: raise ValueError('missing or ambiguous callback relocation: '+name)
        inventory.append({'index':i,'slot':name,**found[0]})
    if len(r['relocations'])!=13: raise ValueError('unexpected binding relocation count')
    print(json.dumps({'status':'SCALARS_PASS_CALLBACK_RELOCATION_INVENTORY_ONLY','object_sha256':{'c':c['sha256'],'rust_witness':w['sha256'],'rust_production':r['sha256']},'object_device_inode':{'c':c['identity'],'rust_witness':w['identity'],'rust_production':r['identity']},'scalar_count':31,'scalar_values':values[0],'callback_relocations':inventory,'limitations':'No callback target resolution, C/Rust type equivalence, linked-image verification, provider uniqueness, header provenance or native behavior accepted.'},indent=2));return 0

if __name__=='__main__':
    try: sys.exit(main())
    except Exception as exc:
        print(json.dumps({'status':'ERROR','error':str(exc)}),file=sys.stderr);sys.exit(2)
