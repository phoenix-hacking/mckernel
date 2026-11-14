/* Data-only helpers for the sole Root's existing functions.exec capture.
 * They invoke no tool/process, issue no nonce/grant and write no state.
 * Root passes the ACTUAL complete exec_command/write_stdin argument/result
 * objects, persists every returned snapshot exclusively, and only selects a
 * completion after its outer functions.exec cell has also positively ended.
 */
function newFixed30Capture(argv) {
  return {
    schema: 'mckernel.fixed30.root-tool-capture.v1',
    scope: 'ROOT_CODE_INSTALL_ONLY',
    request_sha256: 'b6f20566657bad0feea6278daae7d8449a554180d020d7d035a900cc2dccf760',
    issuer_sha256: '8837418eb87d1f1c618b37a62b5ca9494d5f303081860583cb95dfd4f5f91a07',
    argv: JSON.parse(JSON.stringify(argv)), tool_calls: [], full_tool_result: null,
    primary_error: null, secondary_errors: [],
    full_Root_tool_and_streams_joined: false,
    native_release: false, native_currentfree: null
  };
}
function retainActualToolReply(capture, tool, actualArguments, actualResult) {
  // No replacement summary: retain the whole raw metadata, output and handle.
  capture.tool_calls.push(JSON.parse(JSON.stringify({
    tool: tool, arguments: actualArguments, result: actualResult
  })));
  if (actualResult && actualResult.exit_code !== undefined &&
      actualResult.exit_code !== null && actualResult.session_id == null) {
    capture.full_tool_result = JSON.parse(JSON.stringify(actualResult));
  }
  return capture;
}
function retainRootCaptureFailure(capture, phase, actualError) {
  const failure = { phase: phase, error: String(actualError) };
  if (capture.primary_error === null) capture.primary_error = failure;
  else capture.secondary_errors.push(failure);
  capture.full_Root_tool_and_streams_joined = false;
  return capture;
}
/* There is deliberately no mark_success or execute helper. After the actual
 * final reply, Root checks exit0/noSession, every original-session wait and
 * complete untruncated output, and records its real outer-tool completion.
 * Root then supplies actual_values/caller_terminal references containing
 * path,size,sha256,device,inode from the ACTUAL UID1000 files. Only then may
 * Root set full_Root_tool_and_streams_joined:true in its frozen completion.
 * This data entry is the Root provenance boundary, not source/native authority.
 */
