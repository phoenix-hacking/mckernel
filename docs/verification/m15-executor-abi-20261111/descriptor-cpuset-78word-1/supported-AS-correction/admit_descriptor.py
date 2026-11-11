def admit(label,need):
 stamp=guard();available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;rss=overhead();hf=shutil.disk_usage(ROOT).free;sf=shutil.disk_usage(HERE).free
 assert available>=26*2**30 and rss+need<=4*2**30 and hf>=17*2**30 and sf>=13*2**30
 save(label+'-ADMISSION.json',dict(at=now(),guard_updated_at=stamp,MemAvailable_bytes=available,all_current_overhead_bytes=rss,this_phase_bytes=need,HOST_total=4*2**30,maxjobs=3,hostfree=hf,scratchfree=sf,disk_growth_reserved=1*2**30,historical_claims_and_all_native_UNKNOWNs_unchanged=True,Root_actual_external_admission_required=True))
