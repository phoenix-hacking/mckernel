        let response = call.response.take().ok_or(-71)?;
        let retained = stability_retention_selected(response.verification_owner());
        let prepared = if retained {
            response
                .verification_prepare_retained(worker.worker.tid(), value)
                .map_err(|(response, error)| (Some(response), error))
        } else {
            response
                .prepare(worker.worker.tid(), value)
                .map_err(|error| (None, error))
        };
        match prepared {
            Ok(completion) => call.completion = Some(completion),
            Err((response, error)) => {
                // The selected original capability survives even a failed
                // post-write CAS. Quarantine prevents every later preparation.
                call.response = response;
                if retained {
                    crate::stability_phase::invalid(error);
                }
                self.quarantined = true;
                return Err(error);
            }
        }
