"""
================================================================================
ALGORISE AI — ARIA CONTENT STUDIO: KAILASA TEMPLE VIRAL REEL RENDER ENGINE
================================================================================
Generates high-fidelity neural voiceover via edge-tts and composites a 9:16 
1080x1920 viral video reel using OpenCV, Pillow, and FFmpeg with full legal 
attribution watermarks.
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

FFMPEG_EXE = r"C:\Users\om\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.EXE"
FFPROBE_EXE = r"C:\Users\om\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffprobe.EXE"

OUTPUT_DIR = ROOT / "assets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_PATH = OUTPUT_DIR / "kailasa_aria_voiceover.mp3"
RAW_VIDEO_PATH = OUTPUT_DIR / "kailasa_raw_frames.mp4"
FINAL_REEL_PATH = OUTPUT_DIR / "kailasa_viral_reel_aria.mp4"

SCRIPT_TEXT = (
    "Did you know there is a 1,200-year-old temple carved from the TOP DOWN that is physically impossible to replicate today? "
    "Every building on Earth is built from the ground up. But Cave 16 at Ellora was carved top-down into a solid mountain of Deccan basalt. "
    "Over 400,000 tonnes of volcanic rock were chiseled away. One single fractured pillar, and the entire multi-story monument would collapse forever. "
    "Yet ancient Indian architects made zero mathematical errors. "
    "I am Aria — explore the full 4K documentary on Algorise AI."
)

async def generate_voiceover():
    import edge_tts
    print(f"[STAGE 1] Synthesizing Aria Neural Voiceover via Edge-TTS...")
    communicate = edge_tts.Communicate(SCRIPT_TEXT, "en-US-JennyNeural", rate="+3%", pitch="+0Hz")
    await communicate.save(str(AUDIO_PATH))
    print(f"  ✓ Voiceover saved: {AUDIO_PATH} ({AUDIO_PATH.stat().st_size} bytes)")

def get_audio_duration(audio_file: str) -> float:
    cmd = [
        FFPROBE_EXE, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_file
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

def create_cinematic_frames(duration_sec: float, fps: int = 30):
    print(f"[STAGE 2] Generating 1080x1920 Cinematic Animation Frames ({duration_sec:.1f}s @ {fps}fps)...")
    import cv2
    
    total_frames = int(duration_sec * fps)
    width, height = 1080, 1920

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(RAW_VIDEO_PATH), fourcc, fps, (width, height))

    # Base background gradient
    base_img = Image.new("RGB", (width, height), color=(10, 12, 18))
    draw = ImageDraw.Draw(base_img)

    for i in range(height):
        # Dark cosmic cyan/obsidian gradient
        ratio = i / height
        r = int(7 + ratio * 8)
        g = int(10 + ratio * 18)
        b = int(18 + ratio * 35)
        draw.line([(0, i), (width, i)], fill=(r, g, b))

    base_np = np.array(base_img)

    # Narrative slide cue boundaries
    for f in range(total_frames):
        t = f / fps
        frame = base_np.copy()
        pil_frame = Image.fromarray(frame)
        fdraw = ImageDraw.Draw(pil_frame)

        # Pulsing HUD Border
        alpha_pulse = int(128 + 60 * np.sin(t * 3.0))
        hud_color = (0, 242, 254)
        gold_color = (245, 215, 127)
        white_color = (255, 255, 255)

        # Top Header Badge
        fdraw.rectangle([40, 60, width - 40, 140], fill=(15, 23, 42), outline=hud_color, width=2)
        fdraw.text((60, 85), "🏛️ ARIA ANCIENT ENGINEERING DOSSIER #01", fill=gold_color)

        # Main Dynamic Visual Stage
        fdraw.rectangle([40, 180, width - 40, 1200], fill=(13, 17, 23), outline=(30, 41, 59), width=2)

        # Dynamic Content per chapter cue
        if t < 5.5:
            # Hook
            fdraw.text((80, 300), "THE IMPOSSIBLE", fill=hud_color)
            fdraw.text((80, 420), "MONOLITH", fill=gold_color)
            fdraw.text((80, 580), "Cave 16, Ellora Caves, India", fill=white_color)
            fdraw.text((80, 680), "400,000 Tonnes Basalt Carved TOP-DOWN", fill=(148, 163, 184))
            fdraw.rectangle([80, 800, width - 80, 810], fill=hud_color)
            fdraw.text((80, 860), "NO SCAFFOLDING  •  ZERO MARGIN FOR ERROR", fill=gold_color)
        elif t < 12.0:
            # Comparison
            fdraw.text((80, 300), "THE TOP-DOWN", fill=gold_color)
            fdraw.text((80, 420), "PARADOX", fill=hud_color)
            fdraw.text((80, 580), "Every building starts from ground up.", fill=white_color)
            fdraw.text((80, 660), "Kailasa was carved from the cliff SUMMIT.", fill=hud_color)
            fdraw.text((80, 780), "• Volcanic Deccan Basalt (Mohs 6.5)", fill=(148, 163, 184))
            fdraw.text((80, 860), "• 33 Meters Vertical Trench Excavation", fill=(148, 163, 184))
            fdraw.text((80, 940), "• One fractured pillar = Total Collapse", fill=(239, 68, 68))
        elif t < 18.0:
            # Mystery
            fdraw.text((80, 300), "400,000 TONNES", fill=hud_color)
            fdraw.text((80, 420), "DEBRIS ANOMALY", fill=gold_color)
            fdraw.text((80, 580), "Where did the excavated rock vanish?", fill=white_color)
            fdraw.text((80, 680), "Zero quarry waste found within 50 km.", fill=gold_color)
            fdraw.text((80, 780), "• Repurposed in regional medieval dams", fill=(148, 163, 184))
            fdraw.text((80, 860), "• Agricultural basalt mineral enrichment", fill=(148, 163, 184))
            fdraw.text((80, 940), "• High-precision stone acoustic conduits", fill=(148, 163, 184))
        else:
            # Conclusion & CTA
            fdraw.text((80, 300), "ANCIENT INDIAN", fill=gold_color)
            fdraw.text((80, 420), "INGENUITY", fill=hud_color)
            fdraw.text((80, 580), "Rashtrakuta Dynasty • King Krishna I", fill=white_color)
            fdraw.text((80, 680), "Baroda Copper Plate (812 CE):", fill=gold_color)
            fdraw.text((80, 760), "\"Oh, how was it that I built it?\"", fill=white_color)
            fdraw.text((80, 880), "SUBSCRIBE TO ARIA FOR FULL 4K EPISODE", fill=hud_color)

        # Active telemetry HUD
        fdraw.rectangle([40, 1240, width - 40, 1480], fill=(15, 23, 42), outline=(30, 41, 59), width=1)
        fdraw.text((70, 1270), f"TELEMETRY: TIMECODE {t:.2f}s / {duration_sec:.2f}s", fill=hud_color)
        fdraw.text((70, 1330), "COMPRESSION: 150-250 MPa | DENSITY: 2.85 g/cm³", fill=(148, 163, 184))
        fdraw.text((70, 1390), "ACOUSTIC RESONANCE: 110-130 Hz STANDING WAVE", fill=(148, 163, 184))

        # Legal Attribution Lower-Third Banner (STRICT COMPLIANCE)
        fdraw.rectangle([40, 1520, width - 40, 1720], fill=(7, 9, 14), outline=hud_color, width=2)
        fdraw.text((60, 1540), "⚖️ FAIR-USE ACADEMIC CITATION & ATTRIBUTION:", fill=gold_color)
        fdraw.text((60, 1595), "• Archaeological Survey of India (ASI) Official Records", fill=white_color)
        fdraw.text((60, 1640), "• Field Research References: Praveen Mohan & Global Scholars", fill=(148, 163, 184))
        fdraw.text((60, 1680), "• Full credits & links in description • Algorise AI", fill=hud_color)

        # Progress bar
        prog_width = int((width - 80) * (t / duration_sec))
        fdraw.rectangle([40, 1860, width - 40, 1875], fill=(30, 41, 59))
        fdraw.rectangle([40, 1860, 40 + prog_width, 1875], fill=hud_color)

        # Write frame
        out.write(cv2.cvtColor(np.array(pil_frame), cv2.COLOR_RGB2BGR))

    out.release()
    print(f"  ✓ Raw video frames rendered: {RAW_VIDEO_PATH}")

def mux_final_video():
    print(f"[STAGE 3] Muxing Video & Audio via FFmpeg...")
    cmd = [
        FFMPEG_EXE, "-y",
        "-i", str(RAW_VIDEO_PATH),
        "-i", str(AUDIO_PATH),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(FINAL_REEL_PATH)
    ]
    subprocess.run(cmd, check=True)
    print(f"  ✓ Final broadcast MP4 compiled: {FINAL_REEL_PATH} ({FINAL_REEL_PATH.stat().st_size} bytes)")

    # Copy to dist/assets for web serving
    dist_asset = ROOT / "dist" / "assets" / "kailasa_viral_reel_aria.mp4"
    dist_asset.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(FINAL_REEL_PATH, dist_asset)
    print(f"  ✓ Copied to dist/assets: {dist_asset}")

async def main():
    await generate_voiceover()
    dur = get_audio_duration(str(AUDIO_PATH))
    print(f"  ✓ Audio duration: {dur:.2f} seconds")
    create_cinematic_frames(dur, fps=30)
    mux_final_video()
    print("\n" + "=" * 80)
    print("  ARIA KAILASA TEMPLE MASTER VIDEO COMPLETED & READY TO PUBLISH")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
