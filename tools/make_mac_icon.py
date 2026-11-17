"""macOS simgesini (icon.icns) make_icon.py'deki amblem çiziminden üretir.

    python tools/make_mac_icon.py src-tauri/icons/icon.icns

macOS simgeleri 1024'lük tuvalde 824'lük yuvarlatılmış kare içinde durur (Apple'ın simge ızgarası);
çevresi saydamdır. Büyük boyutlar saf Python ile çok yavaş çizileceği için numpy kullanılır
(yalnızca bu araç için gerekir; derleme sırasında çalışmaz, çıktı depoda durur).
"""

import io
import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_icon as m  # noqa: E402

CANVAS = 1024
INNER = (100.0, 924.0)  # Yuvarlatılmış karenin tuvaldeki yeri
DESIGN = (8.0, 247.0)  # make_icon'daki yuvarlatılmış karenin yeri (256'lık çizim)
SS = 4  # Kenar yumuşatma için piksel başına SS x SS örnek
# icns türleri: (tür, kenar)
TYPES = (("icp4", 16), ("icp5", 32), ("icp6", 64), ("ic07", 128), ("ic08", 256), ("ic09", 512), ("ic10", 1024))


def design_coords(n):
    """n x n görüntünün alt örneklerini 256'lık çizim koordinatlarına çevirir."""
    step = CANVAS / n
    offsets = (np.arange(SS) + 0.5) / SS
    axis = (np.arange(n)[:, None] + offsets[None, :]).reshape(-1) * step
    scale = (DESIGN[1] - DESIGN[0]) / (INNER[1] - INNER[0])
    d = DESIGN[0] + (axis - INNER[0]) * scale
    return np.meshgrid(d, d)  # x, y (satır = y)


def render(n):
    x, y = design_coords(n)
    cx, cy = m.CENTER
    # Yuvarlatılmış kare
    r = 48.0
    qx = np.clip(x, DESIGN[0] + r, DESIGN[1] - r)
    qy = np.clip(y, DESIGN[0] + r, DESIGN[1] - r)
    inside = (x >= DESIGN[0]) & (x <= DESIGN[1]) & (y >= DESIGN[0]) & (y <= DESIGN[1]) & ((x - qx) ** 2 + (y - qy) ** 2 <= r * r)
    dx, dy = x - cx, y - cy
    dist = np.hypot(dx, dy)
    # Güneş ve ışınlar
    count, start, end, half = m.RAYS
    step = 2 * math.pi / count
    offset = (np.arctan2(dy, dx) + step / 2) % step - step / 2
    along, across = dist * np.cos(offset), dist * np.sin(offset)
    nearest = np.clip(along, start, end)
    sun = (dist <= m.SUN) | ((dist >= start - half) & (dist <= end + half) & (np.hypot(along - nearest, across) <= half))
    # Çelenk: dal ve yapraklar
    laurel = (np.abs(dist - m.RADIUS) <= m.STEM) & (np.degrees(np.arctan2(np.abs(dx), dy)) <= 150)
    for lx, ly, phi in m.LEAVES:
        rad = math.radians(phi)
        u = (x - lx) * math.cos(rad) + (y - ly) * math.sin(rad)
        v = -(x - lx) * math.sin(rad) + (y - ly) * math.cos(rad)
        laurel |= (u / m.LEAF[0]) ** 2 + (v / m.LEAF[1]) ** 2 <= 1
    # Çelengin rengi
    turn = (np.arctan2(dy, dx) / (2 * math.pi)) % 1 * len(m.ORB)
    index = turn.astype(int) % len(m.ORB)
    strength = 0.75 * np.sin(math.pi * (turn % 1)) ** 2
    orb = np.array(m.ORB, dtype=float)[index]
    yellow = np.array(m.YELLOW, dtype=float)
    laurel_rgb = yellow * (1 - strength[..., None]) + orb * strength[..., None]
    rgb = np.broadcast_to(np.array(m.BG, dtype=float), x.shape + (3,)).copy()
    rgb[laurel] = laurel_rgb[laurel]
    rgb[sun] = yellow
    alpha = inside.astype(float)
    # Alt örneklerin ortalaması (renk alfa ile ağırlıklı)
    rgb = (rgb * alpha[..., None]).reshape(n, SS, n, SS, 3).sum(axis=(1, 3))
    alpha = alpha.reshape(n, SS, n, SS).sum(axis=(1, 3))
    with np.errstate(invalid="ignore", divide="ignore"):
        color = np.where(alpha[..., None] > 0, rgb / alpha[..., None], 0)
    a = alpha / (SS * SS)
    return np.dstack([np.round(color), np.round(a * 255)]).astype(np.uint8)


def png(pixels):
    rows = b"".join(b"\0" + row.tobytes() for row in pixels)
    n = pixels.shape[0]

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


def main(path):
    body = io.BytesIO()
    for kind, n in TYPES:
        data = png(render(n))
        body.write(kind.encode() + struct.pack(">I", len(data) + 8) + data)
    blob = body.getvalue()
    Path(path).write_bytes(b"icns" + struct.pack(">I", len(blob) + 8) + blob)


if __name__ == "__main__":
    main(sys.argv[1])
