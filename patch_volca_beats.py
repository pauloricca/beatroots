#!/usr/bin/env python3
"""Build the verified BEATROOTS v10c WAV from the official Korg 1.04 WAV.

Standalone: Python 3.4+ syntax/APIs, standard library only, no network/device IO.
Only the byte-exact official input is accepted. No complete firmware is embedded.
See README.md before installing the generated experimental firmware.
"""
from __future__ import print_function

import argparse
import binascii
import hashlib
import os
import struct
import sys

if sys.version_info < (3, 4):
    raise SystemExit("Please run this script with Python 3.4 or newer (python3 or py -3).")

STOCK_NAME = "volcabeats_sys_0104.wav"
OUTPUT_NAME = "INSTALL_BEATROOTS_V10C.wav"
STOCK_WAV_SIZE = 9782264
STOCK_WAV_SHA256 = "20b965026f95ca8781254489bd5e9de1c41385862c8ffd58bed3bedb9b716e44"
STOCK_SYS_SHA256 = "f4b2a947e2cd4c650dcf19166c91751bd4f977cfce3e2bf5a7bb9bf4ce445c15"
PATCHED_SYS_SHA256 = "9e29c6774a50e6b8521290e98fe0e0d1bfbcea71be2af62de01fa82340e60fc2"
OUTPUT_WAV_SHA256 = "0c633b7c3135bb09125b190377b8d1d90756e5099f58ac1a6fda4c9b03fdfd1d"
MAGIC = b"KORG SYSTEM FILE"

# Replacement bytes ONLY where stock 1.04 differs from the verified v10c image.
# Offsets are in the decoded 32768-byte SYS image, not in the WAV.
# The internal checksum at 0x1FE is calculated separately.
PATCHES = (
    (0x0A98, "07"),
    (0x0A9A, "d118d35c8a885343064a5b0a32f810205343f7221b0a53431b0a8b60704720020020147c0000c6f30d2302f06dbb"),
    (0x0CC2, "06d870b50546674c0301e45c"),
    (0x0CCF, "f007b8704770b5054601f580744ff6ff710c22094b00fb02329180fff7d3fe1422044805fb02004a7802b10361214606f0e9bb00bfdc1a"),
    (0x0D07, "20"),
    (0x0E24, "4a781ab18968204606f0c9fc10bd090342f27d13b1fbf3f10902314306f062bb"),
    (0x0E5C, "03"),
    (0x0E5E, "02d8014b020199547047770500201146ff2f04d8c7f580734b4301eb132128237343"),
    (0x0E81, "f30f2c1a0e47f2043030f812300132282a08bf002230f81200c01a0cfb00f003eb2040a0f5"),
    (0x0EA7, "4006f089bcf8b50022ff2501264ff6ff772e4bdff8c8c003f1300e5cf822101d705e"),
    (0x0ECA, "5f800eeb821401c901c40230fbd301320833062af0d103e043f6706302f0fabd00f01fb87d217b239725d327312ab42c5c2f2d3229355238ab3b383f40f260420e460723b1fbf3f106f002bb013a46f1bf83000200f08db8103a48bf0022fff7dbbf0025144c114e2660a7802846fff7acfd0c340135042df6d1f8bd2d1a05f00f05013d05d103202146bde83840fff7bcbe38bd02eb52110831c6f3042347f24040034403f066bc"),
    (0x0F78, "ff01ff"),
    (0x0F7C, "40025de0"),
    (0x1034, "0130c0b2000170470e44c6f3170646f00046298901b900266e600902b1fbf4f1a208202a88bf20223b02b3fbf2f3994288bf19464843296980fb0101"),
    (0x1071, "0d"),
    (0x1073, "eac1202860d0bc06f057ba10b50a4a"),
    (0x1086, "508878b1094b1b781824b3fbf4f000fb143310795279121a534393fbf4f303440b70012010bd6c0500204c1b00205fea122cd2b217235a43120a0b3abb08ff2b01d940f2"),
    (0x10CB, "1303f0a9bb"),
    (0x3198, "40f2fc13"),
    (0x319D, "88"),
    (0x319F, "ba704703f5007301f04abb"),
    (0x31AC, "02aefff7f3ff3080"),
    (0x31B8, "708047f20033c0f279030193"),
    (0x31C8, "10b104f096fb00e0c043b080012226210220002401f020f82b4d"),
    (0x31E3, "e0"),
    (0x31EC, "01"),
    (0x31EE, "1e5d02ab33f8143093422ed002e0981afdf71dbf"),
    (0x3204, "64214843dbb2184400f056fc02e00020fdf729bf"),
    (0x3224, "04"),
    (0x3226, "74fa"),
    (0x324E, "00f30700fdf760be"),
    (0x36CE, "09"),
    (0x36DC, "05"),
    (0x3A6E, "d8b940f20e11"),
    (0x3A7C, "4833597a5868"),
    (0x3A86, "187ad2b25a72"),
    (0x3A8E, "04bf5c7201241a680906"),
    (0x3A9C, "1960"),
    (0x3A9F, "20fff730ff204610bd002010bda140012d3df4bfa903f028bd"),
    (0x3AD0, "eb5c934018438bb2083af5d530bd9a4288bf1a4603f057be"),
    (0x3AFA, "03e7"),
    (0x3B04, "68"),
    (0x3B0E, "0a"),
    (0x3B10, "fff7d4ff40f40000014620"),
    (0x3B1C, "bde81040f0e61868f0e70a23b0fbf3f080b2fff7c5fff1e7"),
    (0x47F0, "8030002201f07f0129e0064b1a68130ec2f317020bb1b2fbf3f202ebc2021209fcf787bba8180020"),
    (0x481C, "90307f22e8e7803b5343202093fbf0f37f335b43d90810310cfb01f1c90902f09ebf93f900004010fcf79abb00f00f00b03038b50d46"),
    (0x4854, "064b1b7843b1fff7fbfe2846fff7f8fe04f07f00fff7f4fe38bd00bf36180020bde8704001f05ebd"),
    (0x6004, "7af49faf01200023064a995ca14204d0013340000a2bf8d138bd0121bde83840fbf7c4bf"),
    (0x74D0, "00f0b7b8ff29"),
    (0x74D7, "bffe21002242600260"),
    (0x74E1, "f24062002d3df488a9012d39f40bad"),
    (0x74F1, "2d09d15200fe2900f20f8040f21013594345f69573194442ea02428260c1604ff000414160fdf7adb9c9b20c23b1fbf3f404fb1311"),
    (0x7527, "f0fbb8"),
    (0x75B6, "002c32"),
    (0x75BE, "c2024240d5e90101c5"),
    (0x75C8, "00"),
    (0x75CA, "e868a860c10c4840110a4a405040e8602969084060270740002c18d004334ff080641a68013a05d5586899684018586028bf52421a600c33013a92186441f0d3620854401f2020409149405c07434ff080400760f0bd00278e4b186859680029f5d00139"),
    (0x762F, "d19968c043186059601f2707402740bf00eae7d0b46e68"),
    (0x7647, "2e7bf5e3adc6f31706ea682b896c89e71a013b2b8100984ff48071013839f402ac023839f423ad79f527aaf9f774bc"),
    (0x7682, "182343435b4a1a4480016c4b034400201060f9201884704713f901cb6044fbf7d5bd18235843524a024450681169a0fb01014ff47900401a10607047a2f3500220e0182343434a4a1a4480015c4b03440020d06051604ff479"),
    (0x76DC, "401a000c1884704718235843424a02445058"),
    (0x76F2, "182358433f4c04440023e360a160e26010bc70474243121460e00c21e9e704b90149fcf7f6b87c7850780421e1e740f6ee63"),
    (0x7725, "f81110fcf7c0b918235843304a024489b20804084310617047007f7fa07f4ba0a0"),
    (0x7748, "182358432e4b034443480424847099605a614248847030bc70470344fbf74abd"),
    (0x7778, "7047c6f30642130947f23e70c0561b0103f5007302f00f02fff783bf70478b1c5a435a43120c1032fff7b2be"),
    (0x77B2, "14235843134b034458687047ea"),
    (0x77C0, "7de7142358430f4b0344196170474300c7e7"),
    (0x7C14, "009084c1"),
    (0x7C19, "d7ffff"),
    (0x7F54, "7c797778505c5c786d0000"),
)

def require(condition, message):
    # Explicit checks remain active even if Python is invoked with -O.
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def riff_chunks(raw):
    require(len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WAVE",
            "Expected a RIFF/WAVE file.")
    require(struct.unpack_from("<I", raw, 4)[0] + 8 == len(raw),
            "Incorrect RIFF length.")
    chunks = []
    cursor = 12
    while cursor < len(raw):
        require(cursor + 8 <= len(raw), "Truncated WAV chunk header.")
        tag, size = struct.unpack_from("<4sI", raw, cursor)
        end = cursor + 8 + size + (size & 1)
        require(end <= len(raw), "Truncated WAV chunk.")
        chunks.append((tag, raw[cursor + 8:cursor + 8 + size], raw[cursor:end]))
        cursor = end
    formats = [contents for tag, contents, original in chunks if tag == b"fmt "]
    audio = [contents for tag, contents, original in chunks if tag == b"data"]
    require(len(formats) == 1 and len(audio) == 1, "Expected one fmt and one data chunk.")
    require(len(formats[0]) >= 16, "Truncated WAV format.")
    require(struct.unpack_from("<HHIIHH", formats[0]) == (1, 1, 44100, 88200, 2, 16),
            "Expected mono 16-bit PCM at 44100 Hz.")
    return chunks, audio[0]


def decode_wave(raw):
    """Recognize exact 10/20-sample tone cycles; retain every transport bit.

    The pinned official WAV uses one repeated waveform for each bit. Learn both
    from its leader/first low cycle; require every cycle to match exactly.
    This is deliberately not a general decoder for recordings/resampled WAVs.
    """
    chunks, audio = riff_chunks(raw)
    require(len(audio) >= 60, "WAV has no update stream.")
    one = audio[:20]  # 10 samples, two bytes per sample
    cursor = 0
    while audio.startswith(one, cursor):
        cursor += 20
    zero = audio[cursor:cursor + 40]  # 20 samples
    require(cursor >= 2000 and len(zero) == 40 and not zero.startswith(one),
            "Missing or ambiguous update tone leader.")
    # Verify that the inferred waveforms really are symmetric half-cycle runs.
    for waveform, half in ((one, 5), (zero, 10)):
        samples = struct.unpack("<" + "h" * (half * 2), waveform)
        signs = [value >= 0 for value in samples]
        require(all(value == signs[0] for value in signs[:half]) and
                all(value != signs[0] for value in signs[half:]),
                "Unexpected update waveform.")
    bits = bytearray()
    cursor = 0
    while cursor < len(audio):
        if audio.startswith(one, cursor):
            bits.append(1)
            cursor += 20
        elif audio.startswith(zero, cursor):
            bits.append(0)
            cursor += 40
        else:
            raise ValueError("Unrecognized waveform at audio byte {0}.".format(cursor))
    return chunks, bits, (zero, one)


def read_bytes(bits, offset, count):
    require(offset >= 0 and offset + count * 8 <= len(bits), "Truncated transport.")
    result = bytearray()
    for start in range(offset, offset + count * 8, 8):
        value = 0
        for shift in range(8):
            value |= bits[start + shift] << shift
        result.append(value)
    return bytes(result)


def crc16(data):
    crc = 0xffff
    for value in bytearray(data):
        crc ^= value
        for unused in range(8):
            crc = (crc >> 1) ^ (0x8408 if crc & 1 else 0)
    return crc


def crc_footer(image):
    return struct.pack("<32H", *[crc16(image[i:i + 1024]) for i in range(0, 32768, 1024)])


def validate_transport(bits):
    """Validate the exact full-packet SYS 1.04 transport used by this release."""
    leader = 0
    while leader < len(bits) and bits[leader]:
        leader += 1
    require(leader >= 100 and read_bytes(bits, leader + 1, 1) == b"\xa9",
            "Missing update header marker.")
    magic_offset = leader + 9
    header = read_bytes(bits, magic_offset, 33)
    require(header[:16] == MAGIC, "Missing KORG SYSTEM FILE header.")
    require(sum(bytearray(header[:32])) & 255 == header[32], "Header checksum failed.")
    require(header[16:24] == binascii.unhexlify("a82f00ff00ff0104") and
            header[24:32] == b"\x00" * 8,
            "Unsupported device, block or version; expected Beats SYS 1.04.")
    cursor = magic_offset + 264
    payload_offsets = []
    packets = []
    footer_offset = None
    for index in range(129):
        gap = 4000 if index == 0 else 350
        require(cursor + gap < len(bits) and all(bits[cursor:cursor + gap]) and
                bits[cursor + gap] == 0, "Packet gap/sync failed.")
        cursor += gap + 1
        require(read_bytes(bits, cursor, 1) == b"\xa9", "Packet marker failed.")
        cursor += 8
        if index < 128:
            packet = read_bytes(bits, cursor, 260)
            payload = packet[:256]
            require(packet[256:259] == b"\x55" * 3, "Packet trailer failed.")
            require(sum(bytearray(payload)) & 255 == packet[259], "Packet checksum failed.")
            payload_offsets.append(cursor)
            packets.append(payload)
            cursor += 260 * 8
        else:
            footer_offset = cursor
            packet = read_bytes(bits, cursor, 65)
            require(sum(bytearray(packet[:64])) & 255 == packet[64], "Footer checksum failed.")
            cursor += 65 * 8
    image = b"".join(packets)
    require(packet[:64] == crc_footer(image), "Firmware CRC footer failed.")
    require(sum(struct.unpack("<16384H", image)) & 65535 == 0, "Internal firmware checksum failed.")
    require(all(bits[cursor:]), "Unexpected data after CRC footer.")
    return image, payload_offsets, footer_offset


def patch_image(image):
    require(sha256(image) == STOCK_SYS_SHA256, "Decoded firmware is not the official Beats SYS 1.04.")
    patched = bytearray(image)
    previous_end = 512
    for offset, hex_bytes in PATCHES:
        replacement = binascii.unhexlify(hex_bytes)
        require(previous_end <= offset and offset + len(replacement) <= len(image),
                "Invalid embedded patch layout.")
        patched[offset:offset + len(replacement)] = replacement
        previous_end = offset + len(replacement)
    patched[510:512] = b"\x00\x00"
    checksum = (-sum(struct.unpack("<16384H", patched))) & 65535
    struct.pack_into("<H", patched, 510, checksum)
    result = bytes(patched)
    require(sha256(result) == PATCHED_SYS_SHA256, "Patched firmware differs from the verified v10c build.")
    return result


def write_bits(bits, offset, data):
    require(offset >= 0 and offset + len(data) * 8 <= len(bits), "Patch outside transport.")
    for value in bytearray(data):
        for shift in range(8):
            bits[offset] = (value >> shift) & 1
            offset += 1


def build(raw):
    require(len(raw) == STOCK_WAV_SIZE and sha256(raw) == STOCK_WAV_SHA256,
            "Input is not the exact official volcabeats_sys_0104.wav. "
            "Download version 1.04 from Korg and unzip it; do not resave or convert the WAV.")
    chunks, bits, waveforms = decode_wave(raw)
    image, offsets, footer_offset = validate_transport(bits)
    patched = patch_image(image)
    for index, offset in enumerate(offsets):
        payload = patched[index * 256:(index + 1) * 256]
        write_bits(bits, offset, payload + b"\x55" * 3 + bytes(bytearray([sum(bytearray(payload)) & 255])))
    footer = crc_footer(patched)
    write_bits(bits, footer_offset, footer + bytes(bytearray([sum(bytearray(footer)) & 255])))
    audio = b"".join(waveforms[bit] for bit in bits)
    encoded_chunks = []
    for tag, contents, original in chunks:
        if tag == b"data":
            encoded_chunks.append(tag + struct.pack("<I", len(audio)) + audio +
                                  (b"\x00" if len(audio) & 1 else b""))
        else:
            encoded_chunks.append(original)
    body = b"WAVE" + b"".join(encoded_chunks)
    result = b"RIFF" + struct.pack("<I", len(body)) + body
    # Decode the complete result, not just the pre-encoding payload.
    unused_chunks, final_bits, unused_waveforms = decode_wave(result)
    final_image, unused_offsets, unused_footer = validate_transport(final_bits)
    require(final_image == patched, "Finished WAV failed its decode round trip.")
    require(sha256(result) == OUTPUT_WAV_SHA256, "Finished WAV differs from the verified v10c update.")
    return result


def save_new_file(path, data):
    # Exclusive creation prevents overwriting input, existing output or symlinks.
    # Validation is complete before this function is called.
    with open(path, "xb") as handle:
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            handle.close()
            os.unlink(path)
            raise
    try:
        with open(path, "rb") as handle:
            require(sha256(handle.read()) == OUTPUT_WAV_SHA256, "Saved output failed verification.")
    except BaseException:
        os.unlink(path)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="official WAV (default: beside this script)")
    parser.add_argument("-o", "--output", help="output WAV (default: beside the input WAV)")
    parser.add_argument("--check-only", action="store_true", help="perform all checks without writing a file")
    args = parser.parse_args(argv)
    source = os.path.abspath(args.input or os.path.join(os.path.dirname(os.path.abspath(__file__)), STOCK_NAME))
    target = os.path.abspath(args.output or os.path.join(os.path.dirname(source), OUTPUT_NAME))
    try:
        require(os.path.realpath(source) != os.path.realpath(target), "Input and output must be different files.")
        if os.path.lexists(target) and not args.check_only:
            raise ValueError("Output already exists; nothing was overwritten. Move it or choose --output with a new filename.")
        require(os.path.getsize(source) == STOCK_WAV_SIZE, "Wrong input size; use the unmodified official 1.04 WAV.")
        with open(source, "rb") as handle:
            raw = handle.read()
        print("Verifying the official input, applying v10c, and checking the finished WAV...")
        result = build(raw)
        if args.check_only:
            print("All checks passed. No file written.")
        else:
            save_new_file(target, result)
            print("Created: {0}".format(target))
        print("Output SHA-256: {0}".format(OUTPUT_WAV_SHA256))
        print("This is experimental firmware. Read README.md before installing.")
        print("Keep the original Korg WAV for restoring stock firmware.")
        return 0
    except (OSError, ValueError, struct.error, binascii.Error) as error:
        print("Error: {0}".format(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
