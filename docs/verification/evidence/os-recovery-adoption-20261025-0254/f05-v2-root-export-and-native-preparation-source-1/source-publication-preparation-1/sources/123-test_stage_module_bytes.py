"""Actual retained-header stager function on small synthetic archives only."""
from pathlib import Path
import hashlib,importlib.util,json,stat
N=Path(__file__).resolve().parent
D=N/'stage-preparation-correction-1'
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
stage=load('actual_corrected_module_stage',D/'stage_launch_init.py')
b=json.loads((D/'STAGE-INPUTS.json').read_text());producer=load('accepted_header_producer',b['sources']['header_producer']['path']);ov=load('accepted_overlay',b['sources']['overlay_module']['path'])
entries=[('modules/'+n,('old-'+n).encode(),stat.S_IFREG|0o644) for n in stage.NAMES]+[('images/mckernel.img',b'unchanged-image',stat.S_IFREG|0o755)]
dirs=[(n,b'',stat.S_IFDIR|0o755) for n in ('modules','images','apps')]
base=ov._archive(dirs+entries);tail=ov._archive([('init',b'unchanged-collector',stat.S_IFREG|0o755),('apps/app0',b'unchanged-app0',stat.S_IFREG|0o755),('apps/app1',b'unchanged-app1',stat.S_IFREG|0o755)])
raw=base+tail
records,_=ov.parse_newc(raw);overlay=dict(base_cpio_size=len(base),base_cpio_sha256=producer.sha(base),final_map=ov._manifest(ov._replay_records(records)))
changes={name:(b'new-'+data,hashlib.sha256(data).hexdigest()) for name,data,mode in entries[:3]}
changed,suffix,final,members,headers,count=stage.stage_bytes(producer,ov,raw,overlay,changes)
assert suffix==tail and final==changed+tail and count==len(records) and len(headers)==3
assert all(members[name]['sha256']==producer.sha(data) for name,(data,sha) in changes.items())
assert all(members[name]==row for name,row in overlay['final_map'].items() if name not in changes)
results=['three_BASE_replacements_and_identical_suffix_and_untouched_metadata']
def refuses(label,call):
 try:call()
 except (ValueError,RuntimeError):results.append(label);return
 raise AssertionError('accepted negative '+label)
wrong=dict(changes);name=next(iter(wrong));wrong[name]=(wrong[name][0],'0'*64)
refuses('wrong_original_module_sha',lambda:stage.stage_bytes(producer,ov,raw,overlay,wrong))
refuses('missing_selected_member',lambda:stage.stage_bytes(producer,ov,raw,overlay,{k:v for k,v in changes.items() if k!=name}))
modified=raw[:-len(tail)]+tail.replace(b'unchanged-app0',b'UNchanged-app0')
refuses('changed_untouched_suffix_payload',lambda:stage.stage_bytes(producer,ov,modified,overlay,changes))
reordered=ov._archive(dirs+[entries[1],entries[0],*entries[2:]])+tail
refuses('original_BASE_order_change',lambda:stage.stage_bytes(producer,ov,reordered,overlay,changes))
dupbase=ov._archive(dirs+[*entries,entries[0]]);dupov=dict(base_cpio_size=len(dupbase),base_cpio_sha256=producer.sha(dupbase),final_map=overlay['final_map'])
refuses('duplicate_selected_BASE_member',lambda:stage.stage_bytes(producer,ov,dupbase+tail,dupov,changes))
print(json.dumps(dict(status='PASS_ACTUAL_STAGE_BYTES_SYNTHETIC',cases=len(results),checks=results,real_stage_runs=0,guest_runs=0)))
