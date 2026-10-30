        if use_requester < 0 {
            // No send or host access occurred. Roll back this entry's local
            // accounting while preserving the exact preparation error result.
            if syscall_offload_counted_result(number, exit_group) != 0 {
                let count = addr_of_mut!((*thread).in_syscall_offload);
                write_volatile(count, read_volatile(count).wrapping_sub(1));
            }
            write_volatile(addr_of_mut!((*monitor).status), old_monitor_status);
            return use_requester as CLong;
        }
