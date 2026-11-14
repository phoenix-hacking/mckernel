        // Run before the completed/kernel early returns or any cancellation
        // mutation. A failed/abandoned host operation never opens retention.
        stability_retention_cancel(
            call.response.as_ref().and_then(Response::verification_owner)
                .or_else(|| call.completion.as_ref().and_then(Completion::verification_owner)),
        )?;
