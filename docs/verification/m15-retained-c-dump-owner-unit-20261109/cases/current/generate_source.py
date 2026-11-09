"""Exact retained dump prefix and COMPLETE out-tail; legacy BFD-success body fenced."""
from pathlib import Path
import hashlib,re

def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError(marker)

def generate(source):
 body=function(source,'int ihk_os_makedumpfile(');start=body.index('\n\tok = bfd_set_format(');end=body.rindex('\n out:');prefix=body[:start];tail=body[end:];skipped=body[start:end]
 marker=source.index('#else\n#define dnprintk(');macros=source[marker+len('#else\n'):source.index('\n#endif',marker)]+'\n'
 name=re.search(r'^#define PHYSMEM_NAME_SIZE[^\n]*',source,re.M).group(0)+'\n'
 mappings=[('ihklib_os_open','observation_os_open'),('ihk_os_get_status','observation_status'),('ioctl','observation_ioctl'),('close','observation_close'),('malloc','observation_malloc'),('free','observation_free'),('access','observation_access'),('bfd_init','observation_bfd_init'),('bfd_fopen','observation_bfd_fopen'),('bfd_close','observation_bfd_close')]
 aliases=''.join('#define '+original+' '+hook+'\n' for original,hook in mappings)
 generated='#include "observations.h"\n/* All actual headers and typed declarations are already visible above. */\n'+aliases+macros+name+prefix+'\n abort(); /* harness: only failed bfd_fopen is in this profile */\n'+tail
 proof={'scope':'EXACT actual C prefix through locally failed bfd_fopen plus COMPLETE actual common-out; not full legacy BFD success body qualification','actual_full_function_sha256':hashlib.sha256(body.encode()).hexdigest(),'actual_C_prefix':prefix,'actual_COMPLETE_common_out':tail,'actual_macros':macros,'actual_name_macro':name,'excluded_unreachable_BFD_success_region_sha256':hashlib.sha256(skipped.encode()).hexdigest(),'excluded_unreachable_BFD_success_region_bytes':len(skipped),'typed_post_header_hooks':dict(mappings),'generated_unit_sha256':hashlib.sha256(generated.encode()).hexdigest()}
 return generated,proof
