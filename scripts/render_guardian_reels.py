"""
Render real, web-optimized 9:16 vertical MP4 scambait showcase reels for Guardian Angel™.

Synthesizes distinct dual neural voices via edge-tts (scammer + Margaret AI), measures exact
turn durations with ffprobe, renders 720x1280 animated split-screen frames (live audio bar
spectrum, speaking state highlight, elapsed counter, and wrapped TikTok-style captions) via
Pillow, and encodes crisp H.264 + AAC MP4 files with faststart moov atom into assets/reels/.
"""

from __future__ import annotations

import asyncio
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import edge_tts
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "reels"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG_EXE = r"C:\Users\om\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.EXE"
FFPROBE_EXE = r"C:\Users\om\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffprobe.EXE"

WIDTH, HEIGHT = 720, 1280
FPS = 24

REEL_SPECS: List[Dict] = [
    {
        "id": "reel_irs_tea",
        "tag": "IRS ARREST SCAM",
        "scammer_label": "FAKE IRS OFFICER",
        "granny_label": "MARGARET AI (78yo)",
        "deflection_label": "TEA DEFLECTION LOOP ACTIVE",
        "wasted_counter": "38m WASTED",
        "turns": [
            ("scammer", "en-US-GuyNeural", "+14%", "Ma'am! A federal arrest warrant is active. Buy Target gift cards right now!"),
            ("margaret", "en-GB-SoniaNeural", "-8%", "Oh dear... wait till I find my spectacles. Fluffy just tipped over my Earl Grey tea."),
            ("scammer", "en-US-GuyNeural", "+18%", "Forget the cat! Do NOT hang up or sheriff deputies arrive in ten minutes!"),
            ("margaret", "en-GB-SoniaNeural", "-8%", "Would you like chamomile or peppermint dear? Harold loved a biscuit with tea."),
        ],
    },
    {
        "id": "reel_geeksquad_desk",
        "tag": "TECH SUPPORT SCAM",
        "scammer_label": "FAKE GEEK SQUAD",
        "granny_label": "MARGARET AI (78yo)",
        "deflection_label": "OAK DESK CONFUSION ACTIVE",
        "wasted_counter": "24m WASTED",
        "turns": [
            ("scammer", "en-US-GuyNeural", "+14%", "Your Geek Squad auto-renewed for 499 dollars! Open AnyDesk right now for refund!"),
            ("margaret", "en-GB-SoniaNeural", "-8%", "Any desk? Like the mahogany roll-top writing desk Harold built back in sixty-four?"),
            ("scammer", "en-US-GuyNeural", "+18%", "No ma'am! Software on your computer screen! Click install AnyDesk immediately!"),
            ("margaret", "en-GB-SoniaNeural", "-8%", "I'm polishing the brass drawer handles dear. Can your software buff oak varnish?"),
        ],
    },
    {
        "id": "reel_bail_kevin",
        "tag": "BAIL EXTORTION SCAM",
        "scammer_label": "SPOOFED GRANDSON",
        "granny_label": "MARGARET AI (78yo)",
        "deflection_label": "COUSIN KEVIN LOOP ACTIVE",
        "wasted_counter": "31m WASTED",
        "turns": [
            ("scammer", "en-US-GuyNeural", "+14%", "Grandma it's me! I'm in county jail. Wire three thousand dollars for bail right now!"),
            ("margaret", "en-GB-SoniaNeural", "-8%", "Kevin? Is that cousin Kevin from Shropshire? How is your parakeet's gout doing?"),
            ("scammer", "en-US-GuyNeural", "+18%", "Stop talking about birds! Do not call mom, just wire the cash immediately!"),
            ("margaret", "en-GB-SoniaNeural", "-8%", "Remember dear, you must never feed parakeets salted crackers before bedtime."),
        ],
    },
]


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


FONT_TAG = _load_font(22, True)
FONT_TITLE = _load_font(30, True)
FONT_SUB = _load_font(22, False)
FONT_CAPTION = _load_font(34, True)
FONT_SMALL = _load_font(19, True)


def _probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            FFPROBE_EXE,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    )
    return float(out.strip())


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_w: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


async def render_one_reel(spec: Dict) -> Path:
    reel_id = spec["id"]
    final_mp4 = OUT_DIR / f"{reel_id}.mp4"
    print(f"[REEL] Rendering {reel_id} -> {final_mp4}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        audio_parts: List[Path] = []
        timeline: List[Tuple[float, float, str, str]] = []
        t_cursor = 0.0

        # 1. Generate each spoken line audio & record exact timestamps
        for idx, (speaker, voice, rate, line) in enumerate(spec["turns"]):
            part_mp3 = tmp_path / f"turn_{idx}.mp3"
            comm = edge_tts.Communicate(line, voice=voice, rate=rate)
            await comm.save(str(part_mp3))
            dur = _probe_duration(part_mp3)
            audio_parts.append(part_mp3)
            timeline.append((t_cursor, t_cursor + dur, speaker, line))
            t_cursor += dur

        total_dur = t_cursor
        concat_list = tmp_path / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in audio_parts), encoding="utf-8"
        )
        merged_audio = tmp_path / "merged.m4a"
        subprocess.run(
            [
                FFMPEG_EXE,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(merged_audio),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 2. Precompute static gradient background
        bg = Image.new("RGB", (WIDTH, HEIGHT), (7, 10, 19))
        bg_draw = ImageDraw.Draw(bg)
        for y in range(HEIGHT):
            r = int(6 + (y / HEIGHT) * 8)
            g = int(10 + (y / HEIGHT) * 16)
            b = int(20 + (y / HEIGHT) * 28)
            bg_draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

        # Subtle grid lines
        for gx in range(0, WIDTH, 60):
            bg_draw.line([(gx, 0), (gx, HEIGHT)], fill=(15, 28, 48))
        for gy in range(0, HEIGHT, 60):
            bg_draw.line([(0, gy), (WIDTH, gy)], fill=(15, 28, 48))

        # 3. Pipe raw RGB frames directly into ffmpeg (faster and zero lossless intermediates)
        ffmpeg_cmd = [
            FFMPEG_EXE,
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            f"{WIDTH}x{HEIGHT}",
            "-pix_fmt",
            "rgb24",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-i",
            str(merged_audio),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            "-shortest",
            str(final_mp4),
        ]
        proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        total_frames = int(math.ceil(total_dur * FPS))
        assert proc.stdin is not None
        for f_idx in range(total_frames):
            t = f_idx / FPS
            frame = bg.copy()
            d = ImageDraw.Draw(frame)

            # Active turn lookup
            cur_speaker, cur_text, line_start, line_end = "scammer", spec["turns"][0][3], 0.0, 1.0
            for s_t, e_t, spk, txt in timeline:
                if s_t <= t <= e_t:
                    cur_speaker, cur_text, line_start, line_end = spk, txt, s_t, e_t
                    break

            is_scammer = cur_speaker == "scammer"

            # Top live bar
            d.rounded_rectangle([32, 36, WIDTH - 32, 92], radius=18, fill=(13, 21, 38), outline=(6, 182, 212), width=2)
            d.ellipse([52, 55, 68, 71], fill=(244, 63, 94) if f_idx % 16 < 10 else (180, 30, 60))
            d.text((80, 52), f"{spec['tag']}  |  {spec['wasted_counter']}", fill=(226, 232, 240), font=FONT_TAG)

            # Scammer panel (upper)
            sc_outline = (244, 63, 94) if is_scammer else (51, 65, 85)
            sc_bg = (38, 13, 25) if is_scammer else (15, 23, 42)
            d.rounded_rectangle([32, 120, WIDTH - 32, 430], radius=26, fill=sc_bg, outline=sc_outline, width=4 if is_scammer else 2)
            # Scammer badge computed from exact text width
            th_lbl = "INCOMING THREAT"
            th_w = d.textbbox((0, 0), th_lbl, font=FONT_SMALL)[2] + 28
            d.rounded_rectangle([58, 148, 58 + th_w, 188], radius=10, fill=(244, 63, 94))
            d.text((72, 156), th_lbl, fill=(255, 255, 255), font=FONT_SMALL)
            d.text((58, 206), spec["scammer_label"], fill=(254, 202, 202), font=FONT_TITLE)
            d.text((58, 250), f"STATUS: {'SHOUTING DEMAND' if is_scammer else 'WAITING ON HOLD...'}", fill=(252, 165, 165), font=FONT_SUB)

            # Scammer audio waveform
            for b in range(24):
                amp = (18 + 38 * abs(math.sin(t * 14 + b * 0.6))) if is_scammer else 8
                bx = 58 + b * 24
                d.rounded_rectangle([bx, 395 - int(amp), bx + 14, 395], radius=4, fill=(244, 63, 94) if is_scammer else (71, 85, 105))

            # Center synchronized karaoke captions
            cap_outline = (244, 63, 94) if is_scammer else (6, 182, 212)
            d.rounded_rectangle([28, 464, WIDTH - 28, 824], radius=28, fill=(8, 12, 24), outline=cap_outline, width=3)
            pill_fill = (244, 63, 94) if is_scammer else (6, 182, 212)
            pill_fg = (255, 255, 255) if is_scammer else (0, 0, 0)
            d.rounded_rectangle([WIDTH // 2 - 140, 488, WIDTH // 2 + 140, 528], radius=14, fill=pill_fill)
            lbl = "SCAMMER CALLER" if is_scammer else "MARGARET AI REPLY"
            lb_box = d.textbbox((0, 0), lbl, font=FONT_SMALL)
            d.text(((WIDTH - (lb_box[2] - lb_box[0])) // 2, 497), lbl, fill=pill_fg, font=FONT_SMALL)

            lines = _wrap_lines(d, cur_text, FONT_CAPTION, WIDTH - 108)
            turn_progress = (t - line_start) / max(0.2, line_end - line_start)
            total_chars = max(1, len(cur_text))
            lit_chars = int(total_chars * min(1.0, turn_progress + 0.08))
            char_acc = 0
            y_text = 562
            for ln in lines[:5]:
                bbox = d.textbbox((0, 0), ln, font=FONT_CAPTION)
                lw = bbox[2] - bbox[0]
                x_text = (WIDTH - lw) // 2
                # Highlight already-spoken portion in vibrant gold/cyan
                if char_acc < lit_chars:
                    fill_col = (253, 224, 71) if is_scammer else (103, 232, 249)
                else:
                    fill_col = (248, 250, 252)
                d.text((x_text + 2, y_text + 2), ln, fill=(0, 0, 0), font=FONT_CAPTION)
                d.text((x_text, y_text), ln, fill=fill_col, font=FONT_CAPTION)
                char_acc += len(ln) + 1
                y_text += 46

            # Margaret AI panel (lower)
            mg_outline = (6, 182, 212) if not is_scammer else (51, 65, 85)
            mg_bg = (9, 34, 48) if not is_scammer else (15, 23, 42)
            d.rounded_rectangle([32, 858, WIDTH - 32, 1170], radius=26, fill=mg_bg, outline=mg_outline, width=4 if not is_scammer else 2)
            tw_lbl = "TIME-WASTER ACTIVE"
            tw_w = d.textbbox((0, 0), tw_lbl, font=FONT_SMALL)[2] + 28
            d.rounded_rectangle([58, 886, 58 + tw_w, 926], radius=10, fill=(16, 185, 129))
            d.text((72, 894), tw_lbl, fill=(0, 0, 0), font=FONT_SMALL)
            d.text((58, 944), spec["granny_label"], fill=(165, 243, 252), font=FONT_TITLE)
            d.text((58, 988), f"0 SENIOR INTERACTION  |  {spec['deflection_label']}", fill=(110, 231, 183), font=FONT_SUB)

            for b in range(24):
                amp = (16 + 32 * abs(math.sin(t * 7 + b * 0.45))) if not is_scammer else 8
                bx = 58 + b * 24
                d.rounded_rectangle([bx, 1134 - int(amp), bx + 14, 1134], radius=4, fill=(6, 182, 212) if not is_scammer else (71, 85, 105))

            # Bottom brand CTA + progress bar
            d.text((40, 1200), "Guardian Angel AI  •  algorise-ai.com", fill=(148, 163, 184), font=FONT_SMALL)
            pct = min(1.0, t / max(0.1, total_dur))
            d.rectangle([32, 1244, WIDTH - 32, 1254], fill=(30, 41, 59))
            d.rectangle([32, 1244, 32 + int((WIDTH - 64) * pct), 1254], fill=(6, 182, 212))

            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"FFmpeg exited with code {ret} for {reel_id}")
        print(f"  ✓ Rendered {final_mp4.name} ({final_mp4.stat().st_size // 1024} KB, {total_dur:.1f}s)")
        return final_mp4


async def main() -> None:
    for spec in REEL_SPECS:
        await render_one_reel(spec)


if __name__ == "__main__":
    asyncio.run(main())
