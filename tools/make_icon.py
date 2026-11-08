"""Yalnızca standart kütüphaneyle uygulama simgesi üretir: python make_icon.py çıktı.ico"""

import struct
import sys
import zlib

SIZE = 256
BG = (15, 108, 189, 255)
BAR = (255, 255, 255, 255)
BAR2 = (159, 208, 245, 255)
CLEAR = (0, 0, 0, 0)


def inside_rounded(x, y, x0, y0, x1, y1, r):
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return x0 <= x <= x1 and y0 <= y <= y1 and (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def pixel(x, y):
    if not inside_rounded(x, y, 8, 8, 247, 247, 48):
        return CLEAR
    if inside_rounded(x, y, 48, 142, 208, 168, 12):
        return BAR
    if inside_rounded(x, y, 48, 186, 150, 212, 12):
        return BAR2
    if inside_rounded(x, y, 164, 186, 208, 212, 12):
        return BAR
    # İndirme oku
    if 112 <= x <= 143 and 44 <= y <= 92:
        return BAR
    if 80 <= y <= 124 and abs(x - 127.5) <= 124 - y:
        return BAR
    return BG


def png():
    rows = b"".join(b"\0" + b"".join(bytes(pixel(x, y)) for x in range(SIZE)) for y in range(SIZE))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


def main(path):
    image = png()
    icon = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(image), 22) + image
    with open(path, "wb") as handle:
        handle.write(icon)


if __name__ == "__main__":
    main(sys.argv[1])
