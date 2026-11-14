"""Execute the notification workflow's actual JS with isolated fake GitHub APIs."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/mckernel-mailbox-notify.yml'
EVENT = 'a' * 64
NUMBER = 3
BOT = {'type': 'Bot', 'login': 'github-actions[bot]'}
TRANSPORT_BYTES = 48000


def comment_body(message, event_id=EVENT):
    escaped = message.replace('@', '\uff20').replace('<', '&lt;').replace('>', '&gt;')
    return '<!-- mckernel-mailbox:' + event_id + ' -->\n' + escaped

NODE_RUNNER = r'''
let text = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => text += chunk);
process.stdin.on('end', async () => {
  const input = JSON.parse(text), calls = [], messages = [];
  const github = {
    rest: {
      pulls: {get: async args => {calls.push({method:'pulls.get', args}); return {data:input.mailbox};}},
      issues: {
        listComments: function listComments() {},
        createComment: async args => {
          calls.push({method:'issues.createComment', args});
          if (input.createError) throw new Error('Synthetic lost response');
          return {data:{id:789}};
        }
      }
    },
    paginate: {iterator: async function* (method, args) {
      if (method !== github.rest.issues.listComments) throw new Error('Wrong API');
      calls.push({method:'issues.listComments', args});
      for (const data of input.pages) {
        if (input.pageError) throw new Error('Synthetic read failure');
        calls.push({method:'page'});
        yield {data};
      }
    }}
  };
  const core = {info: message => messages.push(message)};
  const limitedRequire = name => {
    if (name !== 'crypto') throw new Error('Unexpected module');
    return require('crypto');
  };
  const AsyncFunction = Object.getPrototypeOf(async function() {}).constructor;
  try {
    const value = await new AsyncFunction('github','context','core','require','Buffer',input.script)(
      github,input.context,core,limitedRequire,Buffer);
    process.stdout.write(JSON.stringify({value,calls,messages,sideEffect:global.__mailboxSideEffect || false}));
  } catch (error) {
    process.stdout.write(JSON.stringify({error:error.message,calls,messages}));
  }
});
'''


class MailboxWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text()
        cls.workflow = yaml.safe_load(cls.text)
        cls.step = cls.workflow['jobs']['notify']['steps'][0]
        cls.script = cls.step['with']['script']
        cls.node = shutil.which('node')
        if not cls.node:
            raise RuntimeError('Node is required to execute the workflow regression tests')

    def fixture(self):
        return {
            'script': re.sub(r'const MAILBOX_NUMBER = \d+;',
                             'const MAILBOX_NUMBER = %d;' % NUMBER, self.script),
            'context': {
                'repo': {'owner': 'phoenix-hacking', 'repo': 'mckernel'},
                'actor': 'phoenix-hacking', 'ref': 'refs/heads/development',
                'eventName': 'workflow_dispatch',
                'payload': {'sender': {'id': 175406809}, 'inputs': {
                    'event_id': EVENT, 'body': 'Blocked: missing supported source.\nAction: supply the exact input.'}},
            },
            'mailbox': {'number': NUMBER, 'user': {'id': 175406809},
                        'base': {'repo': {'full_name': 'phoenix-hacking/mckernel'}},
                        'state': 'open', 'draft': True, 'merged': False},
            'pages': [[]],
        }

    def run_script(self, fixture):
        result = subprocess.run([self.node, '-e', NODE_RUNNER],
                                input=json.dumps(fixture), text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def posts(self, result):
        return [row['args'] for row in result['calls'] if row['method'] == 'issues.createComment']

    def test_workflow_is_fixed_scope_and_has_no_checkout_or_shell(self):
        triggers = self.workflow.get('on', self.workflow.get(True))
        self.assertEqual(set(triggers), {'workflow_dispatch'})
        self.assertEqual(set(triggers['workflow_dispatch']['inputs']), {'event_id', 'body'})
        self.assertEqual(self.workflow['permissions'], {'contents': 'read', 'pull-requests': 'write'})
        self.assertEqual(self.workflow['concurrency'], {
            'group': "mckernel-mailbox-${{ github.event.inputs.event_id }}", 'cancel-in-progress': False})
        self.assertEqual(len(self.workflow['jobs']['notify']['steps']), 1)
        self.assertEqual(self.step['uses'], 'actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd')
        self.assertEqual(self.step['with']['retries'], 0)
        self.assertNotIn('${{', self.script)
        self.assertNotIn('run', self.step)
        condition = self.workflow['jobs']['notify']['if']
        for expected in ("github.event_name == 'workflow_dispatch'",
                         "github.repository == 'phoenix-hacking/mckernel'",
                         "github.actor == 'phoenix-hacking'",
                         "github.triggering_actor == 'phoenix-hacking'"):
            self.assertIn(expected, condition)
        self.assertEqual(set(re.findall(r"github.ref == '([^']+)'", condition)), {
            'refs/heads/development', 'refs/heads/codex/local-native-staging-repair'})

    def test_dispatch_posts_only_supplied_message_with_existing_safe_escaping(self):
        fixture = self.fixture()
        message = (
            '\n Missing input @someone / @org/team <script>.\r\n'
            '`global.__mailboxSideEffect=true` $(touch /never-executed)\n'
            '<!-- mckernel-mailbox:' + EVENT + ' -->\t \n')
        fixture['context']['payload']['inputs']['body'] = message
        result = self.run_script(fixture)
        self.assertEqual(result['value']['status'], 'posted')
        self.assertFalse(result['sideEffect'])
        post, = self.posts(result)
        self.assertEqual((post['owner'], post['repo'], post['issue_number']),
                         ('phoenix-hacking', 'mckernel', NUMBER))
        self.assertEqual(post['body'], comment_body(message))
        self.assertEqual(post['body'].count('<!-- mckernel-mailbox:' + EVENT + ' -->'), 1)
        self.assertNotIn('@', post['body'])
        self.assertFalse(any('Missing input' in line for line in result['messages']))

    def test_both_exact_branch_refs_accept_utf8_chunks_larger_than_six_kilobytes(self):
        message = 'é🙂 plain text\n' * 500
        self.assertGreater(len(message.encode('utf-8')), 6000)
        for ref in ('refs/heads/development', 'refs/heads/codex/local-native-staging-repair'):
            with self.subTest(ref=ref):
                fixture = self.fixture()
                fixture['context']['ref'] = ref
                fixture['context']['payload']['inputs']['body'] = message
                result = self.run_script(fixture)
                self.assertEqual(result['value']['status'], 'posted')
                self.assertEqual(self.posts(result)[0]['body'], comment_body(message))

    def test_nonempty_whitespace_chunk_is_preserved(self):
        fixture = self.fixture()
        message = ' \t\r\n  \n'
        fixture['context']['payload']['inputs']['body'] = message
        result = self.run_script(fixture)
        self.assertEqual(result['value']['status'], 'posted')
        self.assertEqual(self.posts(result)[0]['body'], comment_body(message))

    def test_full_escaped_comment_at_transport_boundary_is_accepted(self):
        fixture = self.fixture()
        message = 'x' * (TRANSPORT_BYTES - len(comment_body('').encode('utf-8')))
        fixture['context']['payload']['inputs']['body'] = message
        self.assertEqual(len(comment_body(message).encode('utf-8')), TRANSPORT_BYTES)
        result = self.run_script(fixture)
        self.assertEqual(result['value']['status'], 'posted')
        self.assertEqual(self.posts(result)[0]['body'], comment_body(message))

    def test_transport_bound_counts_json_escaping_and_comment_escaping_separately(self):
        for message, exceeded in (('x\n' * 16000, 'json'), ('<' * 12000, 'comment'),
                                  ('@' * 16000, 'comment')):
            with self.subTest(exceeded=exceeded, character=message[0]):
                fixture = self.fixture()
                inputs = fixture['context']['payload']['inputs']
                inputs['body'] = message
                json_size = len(json.dumps(inputs, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
                comment_size = len(comment_body(message).encode('utf-8'))
                if exceeded == 'json':
                    self.assertGreater(json_size, TRANSPORT_BYTES)
                    self.assertLessEqual(comment_size, TRANSPORT_BYTES)
                else:
                    self.assertGreater(comment_size, TRANSPORT_BYTES)
                    self.assertLessEqual(json_size, TRANSPORT_BYTES)
                result = self.run_script(fixture)
                self.assertIn('error', result)
                self.assertEqual(result['calls'], [])

    def test_existing_bot_marker_on_later_page_prevents_duplicate(self):
        fixture = self.fixture()
        fixture['pages'] = [[{'user': BOT, 'body': 'earlier unrelated notice'}],
                            [{'user': BOT, 'body': '<!-- mckernel-mailbox:' + EVENT + ' -->'}]]
        result = self.run_script(fixture)
        self.assertEqual(result['value']['status'], 'already_posted')
        self.assertEqual(self.posts(result), [])
        self.assertEqual(sum(row['method'] == 'page' for row in result['calls']), 2)

    def test_distinct_chunk_marker_does_not_suppress_the_next_message(self):
        fixture = self.fixture()
        fixture['pages'] = [[{'user': BOT, 'body': comment_body('Previous chunk')}]]
        fixture['context']['payload']['inputs']['event_id'] = 'b' * 64
        result = self.run_script(fixture)
        self.assertEqual(result['value']['status'], 'posted')
        self.assertIn('<!-- mckernel-mailbox:' + 'b' * 64 + ' -->', self.posts(result)[0]['body'])

    def test_human_cannot_spoof_bot_deduplication_receipt(self):
        fixture = self.fixture()
        fixture['pages'] = [[{'user': {'type': 'User', 'login': 'phoenix-hacking'},
                              'body': '<!-- mckernel-mailbox:' + EVENT + ' -->'}]]
        self.assertEqual(len(self.posts(self.run_script(fixture))), 1)

    def test_invalid_inputs_are_rejected_before_any_api_access(self):
        cases = [
            {'event_id': EVENT.upper(), 'body': 'reason'},
            {'event_id': EVENT, 'body': ''},
            {'event_id': EVENT, 'body': 'bad\x00body'},
            {'event_id': EVENT, 'body': 'bad\x7fbody'},
            {'event_id': EVENT, 'body': 'reason', 'mailbox_number': 999},
            {'event_id': EVENT, 'body': {'command': 'invalid'}},
            {'body': 'reason'},
        ]
        for inputs in cases:
            with self.subTest(inputs=str(inputs)[:90]):
                fixture = self.fixture()
                fixture['context']['payload']['inputs'] = inputs
                result = self.run_script(fixture)
                self.assertIn('error', result)
                self.assertEqual(result['calls'], [])

    def test_context_scope_and_immutable_sender_id_are_required(self):
        for field, value in (('actor', 'other-user'), ('ref', 'refs/heads/work'),
                             ('ref', 'refs/heads/codex/local-native-staging-repair-extra'),
                             ('eventName', 'pull_request'), ('eventName', 'push')):
            with self.subTest(field=field):
                fixture = self.fixture()
                fixture['context'][field] = value
                result = self.run_script(fixture)
                self.assertEqual(result['calls'], [])
                self.assertIn('error', result)
        for mutate in (lambda c: c['repo'].update(owner='other'),
                       lambda c: c['repo'].update(repo='other'),
                       lambda c: c['payload']['sender'].update(id=1),
                       lambda c: c['payload']['sender'].update(id='175406809'),
                       lambda c: c['payload'].pop('sender')):
            fixture = self.fixture()
            mutate(fixture['context'])
            result = self.run_script(fixture)
            self.assertEqual(result['calls'], [])
            self.assertIn('error', result)

    def test_fixed_destination_must_still_be_the_dedicated_open_draft(self):
        for changes in ({'number': 999}, {'state': 'closed'}, {'draft': False},
                        {'merged': True}, {'user': {'id': 1}},
                        {'base': {'repo': {'full_name': 'other/repository'}}}):
            with self.subTest(changes=changes):
                fixture = self.fixture()
                fixture['mailbox'].update(changes)
                result = self.run_script(fixture)
                self.assertIn('error', result)
                self.assertEqual(self.posts(result), [])

    def test_uncertain_create_response_has_no_automatic_resend(self):
        fixture = self.fixture()
        fixture['createError'] = True
        result = self.run_script(fixture)
        self.assertIn('error', result)
        self.assertEqual(len(self.posts(result)), 1)
        # A lost POST response can still mean the comment exists. Reconcile its
        # marker on replay before trying to create another comment.
        fixture.pop('createError')
        fixture['pages'] = [[{'user': BOT, 'body': self.posts(result)[0]['body']}]]
        replay = self.run_script(fixture)
        self.assertEqual(replay['value']['status'], 'already_posted')
        self.assertEqual(self.posts(replay), [])

    def test_incomplete_comment_scan_never_creates_notice(self):
        fixture = self.fixture()
        fixture['pageError'] = True
        result = self.run_script(fixture)
        self.assertIn('error', result)
        self.assertEqual(self.posts(result), [])

    def test_setup_push_cannot_create_a_notification(self):
        fixture = self.fixture()
        fixture['context']['eventName'] = 'push'
        fixture['context']['payload'].pop('inputs')
        result = self.run_script(fixture)
        self.assertIn('error', result)
        self.assertEqual(result['calls'], [])

    def test_unconfigured_destination_fails_closed(self):
        fixture = self.fixture()
        fixture['script'] = re.sub(r'const MAILBOX_NUMBER = \d+;',
                                   'const MAILBOX_NUMBER = 0;', self.script)
        result = self.run_script(fixture)
        self.assertIn('error', result)
        self.assertEqual(result['calls'], [])


if __name__ == '__main__':
    unittest.main()

