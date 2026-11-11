"""Yalnızca standart kütüphaneyle program amblemini üretir.

    python make_icon.py çıktı.ico            uygulama simgesi (koyu zeminde defne çelengi ve güneş)
    python make_icon.py çıktı.ico çelenk.svg  ayrıca arayüzün maske olarak kullandığı SVG

Çelengin geometrisi tek yerde (laurel) tanımlıdır; simge de SVG de ondan çizilir.
src/altyazi/web/laurel.svg bu betikle üretilmiştir; geometri değişirse yeniden üretin.
"""

import math
import struct
import sys
import zlib

SIZE = 256
CENTER = (128.0, 124.0)
RADIUS = 80.0
STEM = 2.6  # Dal kalınlığının yarısı
LEAF = (6.5, 17.0)  # Yaprağın yarı eni ve yarı boyu
SUN = 25.0  # Çelengin ortasındaki güneşin yarıçapı
RAYS = (12, 33.0, 45.0, 3.0)  # Işın sayısı, başlangıç ve bitiş uzaklığı, yarı kalınlık
BG = (12, 11, 16)
YELLOW = (255, 208, 0)
ORB = ((255, 6, 6), (21, 255, 0), (255, 47, 0))  # Amblemin içinde dönen ışığın renkleri


def laurel():
    """Yaprakları (merkez x, merkez y, derece) olarak döndürür; açı yukarıdan saat yönündedir."""
    leaves = []
    steps = 9
    for side in (-1, 1):  # Sol ve sağ dal birbirinin aynadaki görüntüsüdür
        for i in range(steps):
            a = math.radians(20 + i * 130 / (steps - 1))  # En alttan dal boyunca açı
            x = CENTER[0] + side * RADIUS * math.sin(a)
            y = CENTER[1] + RADIUS * math.cos(a)
            along = math.degrees(a) - 90  # Dalın o noktadaki yönü
            spreads = (-32, 32) if i < steps - 1 else (-32, 0, 32)  # Uçta ortada bir yaprak daha
            for spread in spreads:
                phi = -side * (along + spread)
                rad = math.radians(phi)
                leaves.append((x + math.sin(rad) * LEAF[1] * 0.95, y - math.cos(rad) * LEAF[1] * 0.95, phi))
    return leaves


LEAVES = laurel()


def in_sun(x, y):
    dx, dy = x - CENTER[0], y - CENTER[1]
    distance = math.hypot(dx, dy)
    if distance <= SUN:
        return True
    count, start, end, half = RAYS
    if not start - half <= distance <= end + half:
        return False
    # En yakın ışının eksenine göre konum: boyunca (along) ve yanal (across) uzaklık
    step = 2 * math.pi / count
    offset = (math.atan2(dy, dx) + step / 2) % step - step / 2
    along, across = distance * math.cos(offset), distance * math.sin(offset)
    nearest = min(max(along, start), end)
    return math.hypot(along - nearest, across) <= half


def in_laurel(x, y):
    dx, dy = x - CENTER[0], y - CENTER[1]
    # Dal: en alttan 150 dereceye kadar uzanan ince yay
    if abs(math.hypot(dx, dy) - RADIUS) <= STEM and math.degrees(math.atan2(abs(dx), dy)) <= 150:
        return True
    for cx, cy, phi in LEAVES:
        rad = math.radians(phi)
        u = (x - cx) * math.cos(rad) + (y - cy) * math.sin(rad)
        v = -(x - cx) * math.sin(rad) + (y - cy) * math.cos(rad)
        if (u / LEAF[0]) ** 2 + (v / LEAF[1]) ** 2 <= 1:
            return True
    return False


def inside_rounded(x, y, x0, y0, x1, y1, r):
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return x0 <= x <= x1 and y0 <= y <= y1 and (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def laurel_color(x, y):
    """Sarı zemin üzerine, merkez çevresinde kırmızı-yeşil-turuncu ışık lekeleri."""
    turn = (math.atan2(y - CENTER[1], x - CENTER[0]) / (2 * math.pi)) % 1 * len(ORB)
    orb = ORB[int(turn) % len(ORB)]
    strength = 0.75 * math.sin(math.pi * (turn % 1)) ** 2  # Lekelerin arasında sarı görünür
    return tuple(round(YELLOW[i] * (1 - strength) + orb[i] * strength) for i in range(3))


def pixel(x, y):
    if not inside_rounded(x, y, 8, 8, 247, 247, 48):
        return (0, 0, 0, 0)
    # Kenarlar tırtıklı olmasın diye çelenk 2x2 alt örnekle çizilir.
    points = [(x + ox, y + oy) for ox in (0.25, 0.75) for oy in (0.25, 0.75)]
    sun = sum(in_sun(*p) for p in points) / 4
    cover = sun or sum(in_laurel(*p) for p in points) / 4
    if not cover:
        return BG + (255,)
    color = YELLOW if sun else laurel_color(x, y)  # Güneş düz sarıdır, ışık yalnızca çelenkte gezer
    return tuple(round(BG[i] * (1 - cover) + color[i] * cover) for i in range(3)) + (255,)


def png():
    rows = b"".join(b"\0" + b"".join(bytes(pixel(x, y)) for x in range(SIZE)) for y in range(SIZE))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


def svg():
    """Maske olarak kullanılan tek renkli çelenk."""
    cx, cy = CENTER
    arc = []
    for side in (-1, 1):
        end = math.radians(150)
        arc.append(
            f'<path d="M{cx:g} {cy + RADIUS:g}A{RADIUS:g} {RADIUS:g} 0 0 {1 if side < 0 else 0} '
            f'{cx + side * RADIUS * math.sin(end):.2f} {cy + RADIUS * math.cos(end):.2f}" '
            f'fill="none" stroke="#000" stroke-width="{STEM * 2:g}" stroke-linecap="round"/>'
        )
    leaves = "".join(
        f'<ellipse cx="{x:.2f}" cy="{y:.2f}" rx="{LEAF[0]:g}" ry="{LEAF[1]:g}" transform="rotate({phi:.2f} {x:.2f} {y:.2f})"/>'
        for x, y, phi in LEAVES
    )
    count, start, end, half = RAYS
    rays = "".join(
        f'<line x1="{cx + start * math.cos(t):.2f}" y1="{cy + start * math.sin(t):.2f}" '
        f'x2="{cx + end * math.cos(t):.2f}" y2="{cy + end * math.sin(t):.2f}" '
        f'stroke="#000" stroke-width="{half * 2:g}" stroke-linecap="round"/>'
        for t in (2 * math.pi * i / count for i in range(count))
    )
    sun = f'<circle cx="{cx:g}" cy="{cy:g}" r="{SUN:g}"/>{rays}'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}">{"".join(arc)}{leaves}{sun}</svg>\n'


def main(icon_path, svg_path=None):
    image = png()
    icon = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(image), 22) + image
    with open(icon_path, "wb") as handle:
        handle.write(icon)
    if svg_path:
        with open(svg_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(svg())


if __name__ == "__main__":
    main(*sys.argv[1:3])
