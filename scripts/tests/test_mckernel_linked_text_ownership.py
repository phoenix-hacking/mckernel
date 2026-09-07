import json
import tempfile
import unittest
from pathlib import Path

from scripts import mckernel_linked_text_ownership as ownership


class LinkedTextOwnershipTests(unittest.TestCase):
    COMMIT = "0123456789abcdef0123456789abcdef01234567"

    def write_elf(
        self,
        path,
        elf_type,
        text_size=100,
        fixup_size=4,
        machine=62,
        vsyscall_size=0,
    ):
        names = b"\0.text\0.fixup\0.data\0.vsyscall\0.shstrtab\0"
        name_offsets = {
            ".text": names.index(b".text"),
            ".fixup": names.index(b".fixup"),
            ".data": names.index(b".data"),
            ".vsyscall": names.index(b".vsyscall"),
            ".shstrtab": names.index(b".shstrtab"),
        }
        text_offset = 0x80
        fixup_offset = text_offset + text_size
        data_offset = fixup_offset + fixup_size
        vsyscall_offset = data_offset + 8
        names_offset = vsyscall_offset + vsyscall_size
        section_offset = (names_offset + len(names) + 0x3F) & ~0x3F
        section_count = 5 + int(vsyscall_size > 0)
        string_table_index = section_count - 1
        ident = b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
        header = ownership.ELF64_HEADER.pack(
            ident,
            elf_type,
            machine,
            1,
            0x1000 if elf_type == ownership.ET_EXEC else 0,
            0,
            section_offset,
            0,
            ownership.ELF64_HEADER.size,
            0,
            0,
            ownership.ELF64_SECTION.size,
            section_count,
            string_table_index,
        )
        sections = [bytes(ownership.ELF64_SECTION.size)]
        sections.append(
            ownership.ELF64_SECTION.pack(
                name_offsets[".text"],
                ownership.SHT_PROGBITS,
                ownership.SHF_ALLOC | ownership.SHF_EXECINSTR,
                0x1000,
                text_offset,
                text_size,
                0,
                0,
                16,
                0,
            )
        )
        sections.append(
            ownership.ELF64_SECTION.pack(
                name_offsets[".fixup"],
                ownership.SHT_PROGBITS,
                ownership.SHF_ALLOC | ownership.SHF_EXECINSTR,
                0x1000 + text_size,
                fixup_offset,
                fixup_size,
                0,
                0,
                1,
                0,
            )
        )
        if vsyscall_size:
            sections.append(
                ownership.ELF64_SECTION.pack(
                    name_offsets[".vsyscall"],
                    ownership.SHT_PROGBITS,
                    ownership.SHF_ALLOC
                    | ownership.SHF_EXECINSTR
                    | 0x1,
                    0x3000,
                    vsyscall_offset,
                    vsyscall_size,
                    0,
                    0,
                    4096,
                    0,
                )
            )
        sections.append(
            ownership.ELF64_SECTION.pack(
                name_offsets[".data"],
                ownership.SHT_PROGBITS,
                ownership.SHF_ALLOC,
                0x2000,
                data_offset,
                8,
                0,
                0,
                8,
                0,
            )
        )
        sections.append(
            ownership.ELF64_SECTION.pack(
                name_offsets[".shstrtab"],
                ownership.SHT_STRTAB,
                0,
                0,
                names_offset,
                len(names),
                0,
                0,
                1,
                0,
            )
        )
        image = bytearray(section_offset + section_count * ownership.ELF64_SECTION.size)
        image[: len(header)] = header
        image[text_offset : text_offset + text_size] = b"\x90" * text_size
        image[fixup_offset : fixup_offset + fixup_size] = b"\xcc" * fixup_size
        image[data_offset : data_offset + 8] = b"D" * 8
        image[vsyscall_offset : vsyscall_offset + vsyscall_size] = (
            b"\xf4" * vsyscall_size
        )
        image[names_offset : names_offset + len(names)] = names
        for index, section in enumerate(sections):
            start = section_offset + index * ownership.ELF64_SECTION.size
            image[start : start + len(section)] = section
        path.write_bytes(image)

    def make_inputs(self, directory, map_text):
        root = Path(directory)
        image = root / "mckernel.img"
        rust_object = root / "rust" / "mckernel_rust.o"
        link_map = root / "mckernel.img.map"
        rust_object.parent.mkdir()
        self.write_elf(image, ownership.ET_EXEC)
        self.write_elf(rust_object, ownership.ET_REL)
        link_map.write_text(
            map_text.format(rust_object=rust_object), encoding="utf-8"
        )
        return image, link_map, rust_object

    def basic_map(self):
        return """\
Discarded input sections
 .text.dead    0x0000000000000000 0x10 {rust_object}

Linker script and memory map

.text          0x0000000000001000 0x64
 *(.text)
 .text.c       0x0000000000001000 0x28 c.o
 .text.rust    0x0000000000001028 0x30 {rust_object}
 *fill*        0x0000000000001058 0x0c
.fixup         0x0000000000001064 0x4
 .fixup        0x0000000000001064 0x4 assembly.o
"""

    def test_report_uses_all_final_executable_bytes_and_exact_rust_contributions(self):
        with tempfile.TemporaryDirectory() as directory:
            image, link_map, rust_object = self.make_inputs(
                directory, self.basic_map()
            )
            report = ownership.build_report(
                image, link_map, rust_object, self.COMMIT
            )

        self.assertEqual(report["total_executable_text_bytes"], 104)
        self.assertEqual(report["rust_executable_text_bytes"], 48)
        self.assertEqual(report["non_rust_or_padding_executable_text_bytes"], 56)
        self.assertEqual(report["rust_executable_text_percent"], "46.153846")
        self.assertEqual(report["rust_input_contribution_count"], 1)
        self.assertEqual(
            [(item["name"], item["rust_input_bytes"]) for item in report["executable_sections"]],
            [(".text", 48), (".fixup", 0)],
        )

    def test_writable_executable_progbits_is_included_in_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "mckernel.img"
            self.write_elf(
                image,
                ownership.ET_EXEC,
                text_size=100,
                fixup_size=4,
                vsyscall_size=4096,
            )
            sections = ownership.executable_progbits_sections(image)

        self.assertEqual(
            [(section["name"], section["size_bytes"]) for section in sections],
            [(".text", 100), (".fixup", 4), (".vsyscall", 4096)],
        )

    def test_wrapped_input_section_and_relative_object_path_are_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "mckernel.img"
            rust_object = root / "rust" / "mckernel_rust.o"
            link_map = root / "mckernel.img.map"
            rust_object.parent.mkdir()
            self.write_elf(image, ownership.ET_EXEC)
            self.write_elf(rust_object, ownership.ET_REL)
            link_map.write_text(
                """\
.text          0x0000000000001000 0x64
 .text._RNvVeryLongRustInputSectionName
                0x0000000000001010 0x20 rust/mckernel_rust.o
.fixup         0x0000000000001064 0x4
 .fixup        0x0000000000001064 0x4 assembly.o
""",
                encoding="utf-8",
            )
            report = ownership.build_report(
                image, link_map, rust_object, self.COMMIT.upper()
            )

        self.assertEqual(report["rust_executable_text_bytes"], 32)
        self.assertEqual(report["source_commit"], self.COMMIT)

    def test_discarded_rust_and_linker_fill_never_enter_numerator(self):
        with tempfile.TemporaryDirectory() as directory:
            image, link_map, rust_object = self.make_inputs(
                directory, self.basic_map()
            )
            sections = ownership.executable_progbits_sections(image)
            contributions, rust_bytes, count = ownership.parse_link_map(
                link_map, sections, rust_object
            )

        self.assertEqual(rust_bytes, 48)
        self.assertEqual(count, 1)
        self.assertEqual(len(contributions[".text"]), 1)

    def test_missing_exact_rust_object_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            image, link_map, rust_object = self.make_inputs(
                directory,
                """\
.text          0x0000000000001000 0x64
 .text.other   0x0000000000001000 0x40 other/mckernel_rust.o
.fixup         0x0000000000001064 0x4
 .fixup        0x0000000000001064 0x4 assembly.o
""",
            )
            with self.assertRaisesRegex(ValueError, "no executable bytes"):
                ownership.build_report(
                    image, link_map, rust_object, self.COMMIT
                )

    def test_map_and_elf_output_size_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            image, link_map, rust_object = self.make_inputs(
                directory,
                """\
.text          0x0000000000001000 0x63
 .text.rust    0x0000000000001000 0x20 {rust_object}
.fixup         0x0000000000001064 0x4
 .fixup        0x0000000000001064 0x4 assembly.o
""",
            )
            with self.assertRaisesRegex(ValueError, "link map size"):
                ownership.build_report(
                    image, link_map, rust_object, self.COMMIT
                )

    def test_out_of_range_or_overlapping_rust_contributions_are_rejected(self):
        cases = (
            (
                """\
.text          0x0000000000001000 0x64
 .text.rust    0x0000000000000ff0 0x20 {rust_object}
.fixup         0x0000000000001064 0x4
 .fixup        0x0000000000001064 0x4 assembly.o
""",
                "outside output section",
            ),
            (
                """\
.text          0x0000000000001000 0x64
 .text.rust1   0x0000000000001010 0x20 {rust_object}
 .text.rust2   0x0000000000001020 0x20 {rust_object}
.fixup         0x0000000000001064 0x4
 .fixup        0x0000000000001064 0x4 assembly.o
""",
                "overlap",
            ),
        )
        for map_text, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                with tempfile.TemporaryDirectory() as directory:
                    image, link_map, rust_object = self.make_inputs(
                        directory, map_text
                    )
                    with self.assertRaisesRegex(ValueError, expected_error):
                        ownership.build_report(
                            image, link_map, rust_object, self.COMMIT
                        )

    def test_non_x86_image_and_invalid_commit_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            image, link_map, rust_object = self.make_inputs(
                directory, self.basic_map()
            )
            self.write_elf(image, ownership.ET_EXEC, machine=183)
            with self.assertRaisesRegex(ValueError, "not an x86_64"):
                ownership.build_report(
                    image, link_map, rust_object, self.COMMIT
                )
            self.write_elf(image, ownership.ET_EXEC)
            with self.assertRaisesRegex(ValueError, "exact 40-hex"):
                ownership.build_report(image, link_map, rust_object, "HEAD")

    def test_report_json_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            image, link_map, rust_object = self.make_inputs(
                directory, self.basic_map()
            )
            first = ownership.build_report(
                image, link_map, rust_object, self.COMMIT
            )
            second = ownership.build_report(
                image, link_map, rust_object, self.COMMIT
            )
            first_json = json.dumps(first, indent=2, sort_keys=True) + "\n"
            second_json = json.dumps(second, indent=2, sort_keys=True) + "\n"

        self.assertEqual(first_json, second_json)


if __name__ == "__main__":
    unittest.main()
