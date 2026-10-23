    pub(super) fn wait_syscall(&self, argument: usize, compat: bool) -> Result<isize> {
        match self.registered() {
            Ok(registration) => {
                let result = registration.wait_syscall(argument, compat);
                if let Err(error) = &result {
                    if *error != EINTR {
                        pr_info!("application_wait=failed os={} generation={} pid={} phase=operation errno={}\n",
                            self.slot, self.generation, registration.pid, error.to_errno());
                    }
                }
                result
            }
            Err(error) => {
                if error != EINTR {
                    pr_info!("application_wait=failed os={} generation={} pid=unknown phase=registration errno={}\n",
                        self.slot, self.generation, error.to_errno());
                }
                Err(error)
            }
        }
    }