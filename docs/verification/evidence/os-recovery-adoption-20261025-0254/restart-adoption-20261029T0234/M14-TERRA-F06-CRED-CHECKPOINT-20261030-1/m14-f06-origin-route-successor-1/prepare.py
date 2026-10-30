from pathlib import Path
s=Path('preimage/kernel/CMakeLists.txt').read_text()
old='''				set(MCKERNEL_F06_ORIGIN_PROFILE "${PROJECT_SOURCE_DIR}/scripts/f06_origin_command_profile.json")'''
new='''				# The e6a guarded producer and its exact source are selected together.
				# Default-off retains the existing predecessor producer and profile.
				if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
					set(MCKERNEL_F06_ORIGIN_PROFILE "${PROJECT_SOURCE_DIR}/scripts/f06_origin_command_profile_e6a_guarded.json")
					set(MCKERNEL_F06_ORIGIN_PRODUCER "${PROJECT_SOURCE_DIR}/scripts/derive_f06_origin_e6a_guarded.py")
				else()
					set(MCKERNEL_F06_ORIGIN_PROFILE "${PROJECT_SOURCE_DIR}/scripts/f06_origin_command_profile.json")
					set(MCKERNEL_F06_ORIGIN_PRODUCER "${PROJECT_SOURCE_DIR}/scripts/derive_f06_origin.py")
				endif()'''
assert s.count(old)==1;s=s.replace(old,new)
old='''
				set(MCKERNEL_F06_ORIGIN_PRODUCER "${PROJECT_SOURCE_DIR}/scripts/derive_f06_origin.py")'''
assert s.count(old)==1;s=s.replace(old,'')
Path('postimage/kernel/CMakeLists.txt').write_text(s)
