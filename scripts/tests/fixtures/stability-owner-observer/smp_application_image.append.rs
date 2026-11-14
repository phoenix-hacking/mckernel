// VERIFICATION OVERLAY ONLY. BootPages physical identities are owned metadata.
#[allow(dead_code)]
impl Preparation {
    pub(crate) fn verification_image(&self) -> crate::stability_observer::Image {
        crate::stability_observer::Image {
            exchange: self.exchange.verification_rpc(),
            result: self.result,
            thread: self.thread,
            page_table: self.page_table,
            buffers_retained: self.buffers.is_some(),
            descriptor: self
                .buffers
                .as_ref()
                .map(|value| value.descriptor.physical()),
            args: self.buffers.as_ref().map(|value| value._args.physical()),
            envs: self.buffers.as_ref().map(|value| value._envs.physical()),
        }
    }
}
