"""Create a static design preview without requiring a graphical display."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1440, 610
LABEL_WIDTH = 215
TOP = 155
ROW_HEIGHT = 56
NOW_HOUR = 11 + 42 / 60
WINDOW_START = NOW_HOUR - 0.5
WINDOW_HOURS = 6
COLORS = ["#26c6da", "#42a5f5", "#7e57c2", "#ec407a", "#ff7043", "#ffca28"]


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def x_for(hour: float) -> float:
    ratio = (hour - WINDOW_START) / WINDOW_HOURS
    return LABEL_WIDTH + (WIDTH - LABEL_WIDTH - 18) * ratio


def main() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#071019")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 106), fill="#111b24")
    draw.text((24, 21), "MISSION CONTROL", font=font(27, True), fill="#ffffff")
    draw.text(
        (24, 62),
        "SJC (PROVISÓRIA)  •  -23.20890°, -45.86090°  •  MÁSCARA 10.0°",
        font=font(13),
        fill="#78909c",
    )

    draw.rounded_rectangle((805, 24, 927, 78), 8, fill="#1d303d")
    draw.text((824, 41), "LISTA NORAD", font=font(12, True), fill="#e8f1f5")
    draw.rounded_rectangle((938, 24, 1037, 78), 8, fill="#1d303d")
    draw.text((954, 41), "ATUALIZAR", font=font(11, True), fill="#e8f1f5")
    draw.rounded_rectangle((1048, 24, 1162, 78), 8, fill="#1d303d")
    draw.text((1072, 41), "ESTAÇÃO", font=font(13, True), fill="#e8f1f5")
    draw.text((1182, 43), "JANELA", font=font(11, True), fill="#78909c")
    draw.rounded_rectangle((1260, 24, 1388, 78), 7, fill="#09141d", outline="#29495b")
    draw.text((1295, 41), "6 h    ▼", font=font(13, True), fill="#e8f1f5")

    draw.rectangle((0, 106, WIDTH, TOP), fill="#0c1720")
    draw.text(
        (24, 121),
        "JANELA MÓVEL 6 H  •  17/07/2026 11:12 — 17:12  •  30 MIN DE HISTÓRICO",
        font=font(14, True),
        fill="#e6f0f5",
    )
    draw.text(
        (1030, 123),
        "6 SATÉLITES  •  9 PASSAGENS  •  CELESTRAK 17/07 16:42",
        font=font(12),
        fill="#78909c",
    )

    draw.rectangle((0, TOP, WIDTH, TOP + 60), fill="#0d1822")
    draw.text((16, TOP + 28), "SATÉLITE", font=font(12, True), fill="#78909c")

    tick = 11.5
    while tick <= 17.0:
        x = x_for(tick)
        is_hour = tick.is_integer()
        color = "#29495b" if is_hour else "#18303f"
        draw.line((x, TOP + 31, x, HEIGHT - 36), fill=color, width=1)
        if is_hour:
            draw.text(
                (x + 4, TOP + 9),
                f"{int(tick):02d}:00",
                font=font(11, True),
                fill="#dce8ef",
            )
        tick += 0.5

    satellites = [
        ("ISS (ZARYA)", 25544, [(11.58, 11.80, 64), (15.30, 15.48, 38)]),
        ("NOAA 19", 33591, [(12.15, 12.38, 72)]),
        ("FO-29", 24278, [(14.70, 14.90, 55)]),
        ("SO-50", 27607, [(13.05, 13.22, 43), (16.25, 16.42, 29)]),
        ("AO-91", 43017, [(11.25, 11.43, 47), (15.05, 15.23, 28)]),
        ("NANOSATC-BR2", 44868, [(12.75, 12.95, 81)]),
    ]
    for row, (name, catalog, windows) in enumerate(satellites):
        y0 = TOP + 60 + row * ROW_HEIGHT
        y1 = y0 + ROW_HEIGHT
        draw.rectangle(
            (0, y0, WIDTH, y1), fill="#09141d" if row % 2 == 0 else "#071019"
        )
        draw.rectangle((0, y0, LABEL_WIDTH, y1), fill="#0c1821")
        draw.line((0, y1, WIDTH, y1), fill="#152a37")
        draw.text((16, y0 + 8), name, font=font(13, True), fill="#dce8ef")
        draw.text((16, y0 + 31), f"NORAD {catalog}", font=font(10), fill="#78909c")
        for begin, end, elevation in windows:
            x0 = max(x_for(begin), LABEL_WIDTH)
            x1 = min(x_for(end), WIDTH - 18)
            draw.rounded_rectangle(
                (x0, y0 + 10, x1, y1 - 10),
                4,
                fill=COLORS[row],
                outline="#e9f7fb",
            )
            if x1 - x0 > 31:
                text = f"{elevation}°"
                box = draw.textbbox((0, 0), text, font=font(10, True))
                draw.text(
                    ((x0 + x1 - (box[2] - box[0])) / 2, y0 + 20),
                    text,
                    font=font(10, True),
                    fill="#041017",
                )
            if name == "ISS (ZARYA)" and begin <= NOW_HOUR < end:
                draw.text(
                    (x1 + 9, y0 + 20),
                    "EL 42.7°  AZ 138.4°  LOS −05:31",
                    font=font(10, True),
                    fill="#7be3aa",
                )

    now_x = x_for(NOW_HOUR)
    draw.line((now_x, TOP + 31, now_x, HEIGHT - 36), fill="#ff334f", width=3)
    draw.polygon(
        ((now_x - 7, TOP + 49), (now_x + 7, TOP + 49), (now_x, TOP + 59)),
        fill="#ff334f",
    )
    draw.rounded_rectangle(
        (now_x - 37, TOP + 31, now_x + 37, TOP + 49), 3, fill="#0d1822"
    )
    draw.text(
        (now_x - 31, TOP + 33),
        "11:42:16",
        font=font(11, True),
        fill="#ff334f",
    )

    card_x = x_for(12.38) + 10
    card_y = TOP + 87
    card_w, card_h = 350, 196
    draw.rounded_rectangle(
        (card_x, card_y, card_x + card_w, card_y + card_h),
        5,
        fill="#0d1822",
        outline="#38586a",
        width=2,
    )
    draw.text(
        (card_x + 15, card_y + 12), "NOAA 19", font=font(14, True), fill="#ffffff"
    )
    draw.text((card_x + 15, card_y + 35), "NORAD 33591", font=font(9), fill="#78909c")
    popup_rows = [
        ("CONT.", "AOS EM 27:14"),
        ("AOS", "12:09:00   AZ 214°"),
        ("MÁX", "12:15:42   EL 72.0°   AZ 148°"),
        ("LOS", "12:22:48   AZ  71°"),
        ("DIST", "482 km no ponto de máxima"),
    ]
    for index, (label, value) in enumerate(popup_rows):
        y = card_y + 63 + index * 24
        draw.text((card_x + 15, y), label, font=font(9, True), fill="#78909c")
        draw.text((card_x + 69, y), value, font=font(10, True), fill="#dce8ef")

    output = Path(__file__).resolve().parents[1] / "preview.png"
    image.save(output)
    print(output)


if __name__ == "__main__":
    main()
