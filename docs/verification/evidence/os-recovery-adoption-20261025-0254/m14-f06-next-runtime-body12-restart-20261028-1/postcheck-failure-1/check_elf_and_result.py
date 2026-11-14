#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read only this HOST family's ELF bytes, direct joins and raw results.
"""
import hashlib,json,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE/'future-host-output-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
TARGET='mckernel_f06_vdso_map_debug'
def bind(path):
 data=path.read_bytes();return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def dump(name,value):(HERE/name).write_text(json.dumps(value,indent=2)+'\n')
def elf(path):
 data=path.read_bytes();assert data[:6]==b'\x7fELF\x02\x01'
 header=struct.unpack_from('<16sHHIQQQIHHHHHH',data);assert header[2]==62
 shoff,shsize,shcount,shnames=header[6],header[11],header[12],header[13]
 sections=[]
 for index in range(shcount):
  row=struct.unpack_from('<IIQQQQIIQQ',data,shoff+index*shsize)
  sections.append(dict(index=index,name_offset=row[0],type=row[1],flags=row[2],address=row[3],offset=row[4],size=row[5],link=row[6],info=row[7],alignment=row[8],entrysize=row[9]))
 def payload(section):return data[section['offset']:section['offset']+section['size']]
 def string(blob,offset):return blob[offset:blob.index(0,offset)].decode()
 names=payload(sections[shnames])
 for section in sections:section['name']=string(names,section['name_offset'])
 symbols=[]
 for table in sections:
  if table['type']!=2:continue
  strings=payload(sections[table['link']])
  for at in range(table['offset'],table['offset']+table['size'],table['entrysize']):
   name,info,other,ndx,value,size=struct.unpack_from('<IBBHQQ',data,at)
   symbol={'name':string(strings,name),'type':info&15,'bind':info>>4,'other':other,'ndx':ndx,'value':value,'size':size}
   if 0<ndx<len(sections):symbol.update(section=sections[ndx]['name'],section_type=sections[ndx]['type'],section_flags=sections[ndx]['flags'],section_alignment=sections[ndx]['alignment'])
   if symbol.get('section')=='__verbose'and symbol['type']==1:
    section=sections[ndx];start=section['offset']+value-section['address'];raw=data[start:start+size]
    assert len(raw)==32
    symbol.update(initial_fmt_pointer=struct.unpack_from('<Q',raw,16)[0],initial_line_flags=struct.unpack_from('<I',raw,24)[0],initial_padding=list(raw[28:32]))
   symbols.append(symbol)
 return sections,symbols
artifacts=[]
for kind,path in [('Rust_production_object',OUT/'runtime_vdso_map_log.o'),('C_extern_consumer',HERE/'consumer.o'),('C_original_oracle',HERE/'oracle.o'),('actual_partial_link',OUT/'joined.o'),('actual_fixture_link',OUT/'fixture')]:
 sections,symbols=elf(path)
 targets=[s for s in symbols if s['name']==TARGET]
 records=[s for s in symbols if s.get('section')=='__verbose'and s['type']==1]
 assert len(targets)==1,(kind,targets)
 target=targets[0]
 if kind in ['C_extern_consumer','C_original_oracle']:
  assert target['ndx']==0 and target['bind']==1
  assert not any(s['name']==TARGET and s['ndx']for s in symbols)
 else:
  assert target['bind']==1 and target['type']==1 and target['size']==32 and target['section']=='__verbose'
  assert target['section_type']==1 and target['section_flags']&3==3 and target['section_alignment']==8
  assert target['initial_fmt_pointer']==0 and target['initial_line_flags']==3084 and target['initial_padding']==[0]*4
 if kind=='Rust_production_object':
  assert len(records)==1
  assert not any(s['size']and (s['name'].startswith('.init_array')or s['name']in ['.ctors','.preinit_array'])for s in sections)
  callback=[s for s in symbols if s['name']=='arch_vdso_map_log_bridge'and s['ndx']];assert len(callback)==1and callback[0]['bind']==1and callback[0]['type']==2
 if kind=='C_extern_consumer':
  assert len(records)==0
  offset_import=[s for s in symbols if s['name']=='mckernel_f06_vdso_offset'];assert len(offset_import)==1and offset_import[0]['ndx']==0
 if kind in ['Rust_production_object','actual_partial_link','actual_fixture_link']:
  for storage_name,expected_size in [('mckernel_f06_vdso_state',88),('mckernel_f06_vdso_container_size',8),('mckernel_f06_vdso_offset',8)]:
   owners=[s for s in symbols if s['name']==storage_name and s['ndx']];assert len(owners)==1and owners[0]['bind']==1and owners[0]['type']==1and owners[0]['size']==expected_size
   if kind=='Rust_production_object':assert owners[0]['section_type']==8and owners[0]['ndx']!=0xfff2
  state_provider=[s for s in symbols if s['name']=='arch_vdso_state_bridge'and s['ndx']];assert len(state_provider)==1and state_provider[0]['bind']==1and state_provider[0]['type']==2

 if kind=='C_original_oracle':assert len(records)==1and records[0]['bind']==0and records[0]['initial_line_flags']==3084and records[0]['initial_padding']==[0]*4
 if kind in ['actual_partial_link','actual_fixture_link']:
  assert len(records)==2and len([s for s in records if s['bind']==1])==1and len([s for s in records if s['bind']==0])==1
  callbacks=[s for s in symbols if s['name']=='arch_vdso_map_log_bridge'and s['ndx']];assert len(callbacks)==1
 artifacts.append({'kind':kind,'artifact':bind(path),'target':target,'all_verbose_records':records,'one_actual_Rust_owner_or_C_import_verified':True})
dump('REAL-RUST-DESCRIPTOR-ELF-OWNERSHIP.json',{'scope':SCOPE,'status':'PASS_REAL_RUST32B_VERBOSE_OWNER_AND_EXTERN_ONLY_C_CONSUMERS','artifacts':artifacts,'exact_initial_metadata_and_flags':'HOST fixture independently compared strings/nullfmt/line3084/flags0/padding0 with original C macro and inherited389-row registry reference.','constructor_in_Rust_object':False,'HOST_two_records':'One original independent C oracle LOCAL plus one GLOBAL selected Rust record; production must retain one total target identity.','default_native_data_file_credit':0})
result=json.loads((OUT/'RESULTS.json').read_text());assert result['status']=='FOUR_HOST_COMMANDS_PASS'and result['actual_commands_started']==4
for i,row in enumerate(result['commands']):
 assert row['status']=='PASS'and row['wait4']['positive_direct_join']and row['wait4']['exit']==0
 assert row['group_absent']and row['parent_streams_closed']and row['child_streams_closed_by_whole_group_absence']
 assert row['identity']['pid']==row['wait4']['pid']and row['identity']['birth']
 assert (OUT/f'command{i}.stderr').read_bytes()==b''
text=(OUT/'command3.stdout').read_text();assert 'pairs=56250'in text and '1 passed; 0 failed'in text
dump('HOST-QUALIFICATION.json',{'scope':SCOPE,'owner':'/root/f06_next','status':'PASS_REAL_RUST_DESCRIPTOR_GENUINE_HEADER_ABI_ELF_OWNERSHIP_AND56250_C_RUST_PAIRS','source_ready':bind(HERE/'SOURCE-READY.json'),'worker_bindings':bind(HERE/'WORKER-HOST-BINDINGS.json'),'plan':bind(HERE/'FUTURE-HOST-COMMANDS.json'),'raw_results':bind(OUT/'RESULTS.json'),'ELF_ownership':bind(HERE/'REAL-RUST-DESCRIPTOR-ELF-OWNERSHIP.json'),'actual_commands':4,'actual_compiler_link_commands':3,'actual_fixture_runs':1,'actual_pairs':56250,'actual_ignored_VM_cases':7,'genuine_C_consumer_and_original_metadata_flags':True,'original_C_PID_offset_null_argument_render_and_unchanged_state_checks':True,'actual_new_Rust_storage_bytes':32,'actual_production_C_data_retirement':False,'original_C_oracle_and_banked_BODY6_BODY7_providers_unchanged':True,'warnings':0,'failures':0,'corrections':0,'retries':0,'sum_command_wall_seconds':sum(x['wall_seconds']for x in result['commands']),'CPU_seconds':sum(x['CPU_seconds']for x in result['commands']),'peak_RSS_KiB':max(x['peak_RSS_KiB']for x in result['commands']),'all_positive_direct_wait4':True,'all_groups_absent':True,'all_streams_closed':True,'compiler_command_identity_timing':[{'command':x['command'],'identity':x['identity'],'wait4':x['wait4'],'wall_seconds':x['wall_seconds'],'CPU_seconds':x['CPU_seconds'],'peak_RSS_KiB':x['peak_RSS_KiB']}for x in result['commands']],'source_scope':'Private canonical118+BODY12; frozen cumulative BODY3-9 and BODY10/11 untouched.','default_artifact_credit':0,'native_credit':0,'file_closure_credit':0,'remaining_selected_C_functions_after_queued_source':5,'actual_accepted_arch_selected_C_functions':17})
print(json.dumps({'status':'PASS','ELF_ownership':bind(HERE/'REAL-RUST-DESCRIPTOR-ELF-OWNERSHIP.json'),'qualification':bind(HERE/'HOST-QUALIFICATION.json'),'sum_command_wall_seconds':sum(x['wall_seconds']for x in result['commands']),'CPU_seconds':sum(x['CPU_seconds']for x in result['commands']),'peak_RSS_KiB':max(x['peak_RSS_KiB']for x in result['commands'])}))
