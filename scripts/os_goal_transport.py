"""Pure classification of observed read-only usage reporting failures."""
import json
from typing import Optional

READ_ONLY_RPC_METHODS = frozenset({
    'initialize', 'config/read', 'model/list', 'account/read', 'account/rateLimits/read',
    'thread/goal/get', 'thread/read', 'thread/list', 'thread/turns/list', 'thread/loaded/list',
})


def classify_service_failure(error) -> Optional[str]:
    """The two existing temporary model-service classes, with real hold vetoes."""
    if not isinstance(error, dict):
        return None
    info = error.get('codexErrorInfo')
    if not isinstance(info, str) or info not in {'serverOverloaded', 'rateLimitExceeded'}:
        return None
    remaining = {key: value for key, value in error.items() if key != 'codexErrorInfo'}
    protected = ('policy', 'quota', 'usagelimit', 'budget', 'credit', 'auth', 'billing',
                 'forbidden', 'spendcontrol', 'spend control', 'spending control')
    try:
        text = json.dumps(remaining, allow_nan=False).lower()
    except (ValueError, TypeError):
        return None
    if any(word in text for word in protected):
        return None
    return info


def classify_rpc_failure(message: str) -> Optional[str]:
    """Recognize generic communication diagnostics, excluding mutating RPC timeouts."""
    if not isinstance(message, str):
        return None
    if message == 'Codex app server disconnected; see retained stderr.':
        return 'disconnected'
    prefix = 'App-server request timed out: '
    if message.startswith(prefix) and message[len(prefix):] in READ_ONLY_RPC_METHODS:
        return 'rpc_timeout'
    return None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate error member')
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError('non-JSON error constant: ' + value)


def classify_usage_failure(message: str) -> Optional[str]:
    """Return a narrow transport class; never authorize inference or replay."""
    if not isinstance(message, str) or len(message) > 65536:
        return None
    if message == 'App-server request timed out: account/rateLimits/read':
        return 'timeout'
    for label in ('disconnected', 'broken_pipe', 'connection_reset'):
        if message == 'Local account/rateLimits/read transport: ' + label:
            return 'local_' + label
    prefix = 'account/rateLimits/read: '
    if not message.startswith(prefix):
        return None
    try:
        detail = json.loads(message[len(prefix):], object_pairs_hook=_unique_object,
                            parse_constant=_invalid_constant)
    except (ValueError, TypeError, RecursionError):
        return None
    if (not isinstance(detail, dict) or type(detail.get('code')) is not int
            or detail['code'] != -32603 or not isinstance(detail.get('message'), str)):
        return None
    # An outage indication never overrides a simultaneous explicit service hold.
    protected = ('policy', 'quota', 'usagelimit', 'budget', 'ratelimit', 'rate limit exceeded',
                 'rate limit reached', 'credit', 'spending',
                 'auth', 'unauthorized', 'forbidden', 'billing', 'spendcontrol',
                 'spend control', '401', '403', '429')
    if any(word in json.dumps(detail).lower() for word in protected):
        return None
    text = detail['message']
    endpoint = 'https://chatgpt.com/backend-api/wham/usage'
    http = 'failed to fetch codex rate limits: GET ' + endpoint + ' failed: '
    for status, reason in ((500, 'Internal Server Error'), (502, 'Bad Gateway'),
                           (503, 'Service Unavailable'), (504, 'Gateway Timeout')):
        if text.startswith(http + str(status) + ' ' + reason + ';'):
            return 'http_' + str(status)
    if text == ('failed to fetch codex rate limits: error sending request for url ('
                + endpoint + ')'):
        return 'connection_send'
    return None
