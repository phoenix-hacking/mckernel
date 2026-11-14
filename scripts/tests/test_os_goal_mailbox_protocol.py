"""Offline contracts for exact, individually bounded mailbox transport."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_mailbox_protocol as protocol


class MailboxProtocolTests(unittest.TestCase):
    def assert_budget(self, chunk):
        self.assertTrue(chunk)
        self.assertLessEqual(len(json.dumps(chunk, ensure_ascii=True).encode("ascii")), 44000)
        escaped = chunk.replace("@", "\uff20").replace("<", "&lt;").replace(">", "&gt;")
        self.assertLessEqual(len(escaped.encode("utf-8")), 44000)
        payload = {"event_id": "a" * 64, "body": chunk}
        self.assertLessEqual(len(json.dumps(payload, ensure_ascii=True).encode("ascii")), 48000)
        marker = "<!-- mckernel-mailbox:" + "a" * 64 + " -->\n"
        self.assertLessEqual(len((marker + escaped).encode("utf-8")), 48000)

    def test_more_than_256_kib_unicode_roundtrips_exactly(self):
        text = ("\r\n  🐦漢字é e\u0301 العربية @<>\\\"\t\n" * 16000) + "\r\n \t"
        self.assertGreater(len(text.encode("utf-8")), 256 * 1024)
        chunks = protocol.split_message(text)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), text)
        for chunk in chunks:
            self.assert_budget(chunk)
        comments = protocol.format_instruction_comments(text)
        expected_id = hashlib.sha256(text.encode("utf-8")).hexdigest()
        payloads = []
        for index, comment in enumerate(comments, 1):
            command, separator, payload = comment.partition("\n")
            self.assertEqual(separator, "\n")
            self.assertEqual(protocol.parse_instruction_part(command),
                             {"message_id": expected_id, "index": index, "total": len(comments)})
            self.assertLessEqual(len(json.dumps(comment, ensure_ascii=True).encode("ascii")), 48000)
            payloads.append(payload)
        self.assertEqual("".join(payloads), text)

    def test_worst_case_dispatch_sizes_include_json_and_workflow_expansion(self):
        for character in ("x", "@", "<", ">", "\"", "\\", "\r", "\n", "\t", "é", "漢", "🛰"):
            with self.subTest(character=repr(character)):
                text = character * 90000
                chunks = protocol.split_message(text)
                self.assertEqual("".join(chunks), text)
                for chunk in chunks:
                    self.assert_budget(chunk)

    def test_normal_comment_preserves_every_message_character(self):
        text = "  leading\r\n/mckernel-resume\ntrailing \t\n\n"
        self.assertEqual(protocol.format_instruction_comments(text), ["/mckernel-instruct\n" + text])

    def test_only_complete_hashes_and_valid_one_based_part_numbers_parse(self):
        message_id = "abcdef01" * 8
        self.assertEqual(protocol.parse_instruction_part(f"/mckernel-instruct-part {message_id} 4/120000"),
                         {"message_id": message_id, "index": 4, "total": 120000})
        for command in ("/mckernel-instruct", "/mckernel-resume", "plain text", "", "/mckernel-instruct-partial"):
            self.assertIsNone(protocol.parse_instruction_part(command))
        for metadata in ("", f"{message_id[:-1]} 1/2", f"{message_id}0 1/2",
                         f"{message_id.upper()} 1/2", f"{message_id} 0/2", f"{message_id} 1/0",
                         f"{message_id} 2/1", f"{message_id} 01/2", f"{message_id} 1/02",
                         f"{message_id} 1/2 extra", f"{message_id} 1/2\nbody"):
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                protocol.parse_instruction_part("/mckernel-instruct-part" + (" " + metadata if metadata else ""))

    def test_empty_invalid_utf8_and_protocol_control_characters_are_rejected(self):
        for text in ("", "bad\x00text", "bad\x7ftext", "bad\x0btext", "bad\ud800text"):
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                protocol.split_message(text)
        self.assertEqual(protocol.split_message(" \t\r\n"), [" \t\r\n"])
        with self.assertRaises(ValueError):
            protocol.format_instruction_comments(" \t\r\n")


if __name__ == "__main__":
    unittest.main()
