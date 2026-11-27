"""
Patch guardian.html to replace mock audio cards with a real 9:16 Vertical Video Reel Theatre,
Interactive Scambait Video Studio, Real Live Microphone Voice Sentry, Screenshot Scam Analyzer,
and 1-Tap Telecom Carrier Call Forwarding Strings.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_HTML = ROOT / "guardian.html"

with open(TARGET_HTML, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update style section with 9:16 smartphone shell and viral reel styles
style_target = """    .audio-bar:nth-child(8) { animation-delay: 0.25s; height: 24px; }
  </style>"""

style_replacement = """    .audio-bar:nth-child(8) { animation-delay: 0.25s; height: 24px; }

    /* 9:16 Vertical Smartphone & Reel Video Styling */
    .reel-phone-shell {
      width: 320px;
      height: 580px;
      background: #000;
      border-radius: 40px;
      border: 7px solid #1e293b;
      position: relative;
      overflow: hidden;
      box-shadow: 0 25px 65px rgba(0,0,0,0.9), 0 0 40px rgba(6,182,212,0.25);
    }
    .reel-dynamic-island {
      position: absolute;
      top: 10px;
      left: 50%;
      transform: translateX(-50%);
      width: 95px;
      height: 22px;
      background: #000;
      border-radius: 12px;
      z-index: 30;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 8px;
      border: 1px solid rgba(255,255,255,0.1);
      pointer-events: none;
    }
    .reel-btn-action {
      display: flex;
      flex-direction: column;
      align-items: center;
      transition: transform 0.15s ease;
      cursor: pointer;
    }
    .reel-btn-action:active {
      transform: scale(1.2);
    }
    .reel-action-circle {
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background: rgba(0,0,0,0.5);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 19px;
      border: 1px solid rgba(255,255,255,0.15);
      transition: color 0.2s, background 0.2s;
    }
    .spinning-disc {
      animation: spin 3.5s linear infinite;
    }
    @keyframes spin {
      100% { transform: rotate(360deg); }
    }
    .pulse-glow-red {
      box-shadow: 0 0 35px rgba(244, 63, 94, 0.6);
      animation: pulse-red 1.5s infinite;
    }
    @keyframes pulse-red {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.02); opacity: 0.85; }
    }
  </style>"""

if style_target in content:
    content = content.replace(style_target, style_replacement, 1)
    print("✓ Successfully updated <style> with 9:16 vertical reel and phone styles")
else:
    print("! Could not find style target")

# 2. Replace Component 2 (mock audio reels) with the 9:16 Reel Theatre & Scambait Studio
comp2_start = '<!-- COMPONENT 2: 3 VIRAL SCAMMER REVENGE REELS / VIDEOS                       -->'
comp3_start = '<!-- COMPONENT 3: 1-CLICK 0-AUTH GOOGLE CLOUD SENTRY                           -->'

comp2_idx = content.find(comp2_start)
comp3_idx = content.find(comp3_start)

if comp2_idx != -1 and comp3_idx != -1:
    # Find start of section before comp2
    sec2_start = content.rfind('<section id="viral-reels"', 0, comp2_idx)
    # Find end of section before comp3
    sec2_end = content.rfind('</section>', 0, comp3_idx) + len('</section>')

    new_comp2_html = """<!-- COMPONENT 2: 9:16 VIRAL SCAMMER REEL THEATRE & VIDEO STUDIO       -->
  <!-- ========================================================================= -->
  <section id="viral-reels" class="py-16 px-4 sm:px-6 lg:px-8 bg-guardNavy border-t border-slate-800">
    <div class="max-w-7xl mx-auto space-y-10">
      
      <div class="text-center max-w-3xl mx-auto space-y-3">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/80 text-emerald-300 text-xs font-mono font-bold border border-emerald-500/40">
          <i class="fa-solid fa-video text-cyan-400"></i>
          <span>VERTICAL 9:16 VIDEO ENGINE · 4.39M COMBINED VIEWS</span>
        </div>
        <h2 class="text-2xl sm:text-4xl font-black text-white">
          Viral Scammer Revenge Reel Theatre
        </h2>
        <p class="text-xs sm:text-sm text-slate-300">
          Watch real synchronized vertical video reels of Margaret AI wasting scammers' time. Kinetic karaoke subtitles, animated audio spectrum waveforms, and 1-click video export for TikTok and Instagram Reels.
        </p>
      </div>

      <!-- Main Layout: 2 Columns (Phone Video Canvas on Left, Reel Playlist & Studio on Right) -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        <!-- Left: Realistic 9:16 Vertical Smartphone Video Screen -->
        <div class="lg:col-span-5 flex flex-col items-center">
          
          <!-- Smartphone Outer Shell -->
          <div class="reel-phone-shell select-none">
            
            <!-- Dynamic Island / Camera Notch -->
            <div class="reel-dynamic-island">
              <span class="w-2 h-2 rounded-full bg-slate-900 border border-slate-700"></span>
              <span class="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse"></span>
            </div>

            <!-- Top Header Stats inside Phone -->
            <div class="absolute top-3 left-4 right-4 z-20 flex items-center justify-between text-[10px] font-mono text-white/80 pointer-events-none pt-1">
              <span class="font-bold">9:41</span>
              <div class="flex items-center gap-1.5 bg-black/60 px-2 py-0.5 rounded-full border border-white/10 backdrop-blur-sm">
                <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping"></span>
                <span class="text-rose-300 font-extrabold uppercase tracking-wider text-[9px]" id="reel-badge-status">38m WASTED</span>
              </div>
              <div class="flex items-center gap-1 text-[10px]">
                <i class="fa-solid fa-wifi text-[9px]"></i>
                <i class="fa-solid fa-battery-full text-emerald-400"></i>
              </div>
            </div>

            <!-- The HTML5 9:16 Video Canvas -->
            <canvas id="reelCanvas" width="720" height="1280" class="w-full h-full object-cover cursor-pointer" onclick="toggleReelPlayback()"></canvas>

            <!-- TikTok / Reels Interactive UI Overlay -->
            <div class="absolute right-2 bottom-20 z-20 flex flex-col items-center gap-4 text-white">
              <!-- Avatar -->
              <div class="relative">
                <div class="w-10 h-10 rounded-full border-2 border-cyan-400 bg-gradient-to-tr from-pink-500 to-rose-600 flex items-center justify-center text-lg shadow-lg">
                  👵
                </div>
                <div class="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-4 h-4 bg-rose-500 rounded-full flex items-center justify-center text-[10px] font-black text-white">
                  +
                </div>
              </div>

              <!-- Like Button -->
              <div onclick="likeReel()" class="reel-btn-action group">
                <div id="reel-like-icon" class="reel-action-circle group-hover:text-rose-500">
                  <i class="fa-solid fa-heart"></i>
                </div>
                <span id="reel-like-count" class="text-[10px] font-mono font-bold mt-0.5 text-white/90">142.8K</span>
              </div>

              <!-- Comment Button -->
              <div onclick="openReelComments()" class="reel-btn-action group">
                <div class="reel-action-circle group-hover:text-cyan-400">
                  <i class="fa-solid fa-comment-dots"></i>
                </div>
                <span class="text-[10px] font-mono font-bold mt-0.5 text-white/90">3,412</span>
              </div>

              <!-- Bookmark -->
              <div onclick="bookmarkReel()" class="reel-btn-action group">
                <div class="reel-action-circle group-hover:text-amber-400">
                  <i class="fa-solid fa-bookmark"></i>
                </div>
                <span class="text-[10px] font-mono font-bold mt-0.5 text-white/90">28.4K</span>
              </div>

              <!-- Share -->
              <div onclick="shareActiveReel()" class="reel-btn-action group">
                <div class="reel-action-circle group-hover:text-emerald-400">
                  <i class="fa-solid fa-share"></i>
                </div>
                <span class="text-[10px] font-mono font-bold mt-0.5 text-white/90">51.2K</span>
              </div>

              <!-- Spinning Music Disc -->
              <div class="w-9 h-9 rounded-full bg-slate-900 border-2 border-slate-600 flex items-center justify-center spinning-disc text-xs text-cyan-400 shadow-md">
                <i class="fa-solid fa-compact-disc"></i>
              </div>
            </div>

            <!-- Bottom Video Information Overlay -->
            <div class="absolute left-3 right-16 bottom-3 z-20 text-white space-y-1 text-left pointer-events-none">
              <div class="flex items-center gap-1.5">
                <span class="font-black text-xs text-white">@GuardianAngelAI</span>
                <i class="fa-solid fa-circle-check text-cyan-400 text-[11px]"></i>
                <span class="text-[10px] bg-white/20 px-1.5 py-0.2 rounded font-bold">Follow</span>
              </div>
              <p class="text-[11px] text-slate-200 line-clamp-2 leading-tight" id="reel-overlay-caption">
                IRS Scammer screams in rage after 38 mins of Earl Grey tea! 😭 #scambait #grannyai #revenge #shorts
              </p>
              <div class="flex items-center gap-1 text-[10px] text-slate-300 font-mono">
                <i class="fa-solid fa-music text-[9px] text-cyan-400"></i>
                <span class="truncate">Original Audio · Margaret vs Scammer</span>
              </div>
            </div>

            <!-- Big Center Play Button Overlay (when paused) -->
            <div id="reel-play-overlay" onclick="toggleReelPlayback()" class="absolute inset-0 z-20 bg-black/40 backdrop-blur-[2px] flex items-center justify-center cursor-pointer transition-opacity">
              <div class="w-16 h-16 rounded-full bg-cyan-500/90 text-black flex items-center justify-center text-2xl pl-1 shadow-2xl hover:scale-110 transition-transform">
                <i class="fa-solid fa-play"></i>
              </div>
            </div>

            <!-- Scrubbing Progress Bar on Canvas -->
            <div class="absolute bottom-0 left-0 right-0 h-1.5 bg-white/20 z-20">
              <div id="reel-canvas-progress" class="h-full bg-cyan-400 w-0 transition-all duration-100"></div>
            </div>

          </div>

          <!-- Video Controls Toolbar Below Phone -->
          <div class="w-[320px] mt-4 space-y-2.5">
            <div class="flex items-center justify-between bg-guardDark p-2.5 rounded-2xl border border-slate-800 text-xs font-mono">
              <button onclick="toggleReelPlayback()" id="reel-master-btn" class="px-3 py-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black font-extrabold flex items-center gap-1.5 shadow">
                <i id="reel-master-icon" class="fa-solid fa-play"></i>
                <span id="reel-master-label">Play Reel</span>
              </button>
              
              <div class="text-slate-300 font-bold" id="reel-timer-display">
                0:00 / 0:42
              </div>

              <button onclick="restartReel()" class="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white" title="Restart">
                <i class="fa-solid fa-rotate-left"></i>
              </button>
            </div>

            <!-- REAL EXPORT & DOWNLOAD BUTTON (MediaRecorder to real video) -->
            <div class="grid grid-cols-2 gap-2">
              <button onclick="exportReelVideo()" id="btn-export-reel" class="py-2.5 px-3 rounded-xl bg-gradient-to-r from-emerald-400 to-teal-500 hover:from-emerald-300 hover:to-teal-400 text-black font-black text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-500/20 transition-all">
                <i class="fa-solid fa-download"></i>
                <span id="btn-export-label">Download Video</span>
              </button>

              <button onclick="shareActiveReel()" class="py-2.5 px-3 rounded-xl bg-gradient-to-r from-rose-500 to-purple-600 hover:from-rose-400 hover:to-purple-500 text-white font-extrabold text-xs flex items-center justify-center gap-1.5 shadow-lg transition-all">
                <i class="fa-solid fa-share-nodes"></i>
                <span>Share to TikTok</span>
              </button>
            </div>
            
            <div class="text-[10px] text-center text-slate-500 font-mono">
              🎬 Real 720×1280 9:16 Video · Ready for TikTok, Reels & Shorts
            </div>
          </div>

        </div>

        <!-- Right: Viral Playlist Selector & Custom Scambait Studio -->
        <div class="lg:col-span-7 space-y-6">
          
          <!-- Playlist Tabs Header -->
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <span class="text-xs font-mono text-cyan-400 font-bold uppercase tracking-wider">
              SELECT VIRAL REEL SCENARIO:
            </span>
            <span class="text-[11px] font-mono text-emerald-400 font-semibold">
              ● 100% Real Synchronized Dialogue
            </span>
          </div>

          <!-- 4 Viral Reel Cards -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            
            <!-- Card 1: IRS Earl Grey Tea -->
            <div onclick="selectReel('reel1')" id="card-reel1" class="p-4 rounded-2xl bg-guardDark border-2 border-rose-500/60 shadow-lg cursor-pointer hover:border-rose-400 transition-all space-y-2">
              <div class="flex items-center justify-between text-[11px] font-mono">
                <span class="px-2 py-0.5 rounded bg-rose-950 text-rose-300 font-bold border border-rose-500/40">
                  🚨 IRS ARREST
                </span>
                <span class="text-emerald-400 font-bold">38m Wasted</span>
              </div>
              <h4 class="text-xs sm:text-sm font-black text-white leading-tight">
                IRS Agent Screams After 38 Mins Talking About Earl Grey Tea
              </h4>
              <p class="text-[11px] text-slate-300 italic line-clamp-2">
                "Oh heavens dear, let me find my reading glasses... Fluffy knocked over my tea!"
              </p>
              <div class="flex items-center justify-between pt-1 text-[10px] text-cyan-400 font-mono">
                <span>1.4M Views (TikTok)</span>
                <span id="status-card-reel1" class="text-rose-400 font-bold flex items-center gap-1">
                  <i class="fa-solid fa-play text-[9px]"></i> Active in Player
                </span>
              </div>
            </div>

            <!-- Card 2: Geek Squad AnyDesk -->
            <div onclick="selectReel('reel2')" id="card-reel2" class="p-4 rounded-2xl bg-guardDark border border-slate-800 shadow-lg cursor-pointer hover:border-amber-400 transition-all space-y-2">
              <div class="flex items-center justify-between text-[11px] font-mono">
                <span class="px-2 py-0.5 rounded bg-amber-950 text-amber-300 font-bold border border-amber-500/40">
                  ✉️ $499 GEEK SQUAD
                </span>
                <span class="text-emerald-400 font-bold">24m Wasted</span>
              </div>
              <h4 class="text-xs sm:text-sm font-black text-white leading-tight">
                Scammer Begs Granny to Open AnyDesk for Antique Mahogany Desk
              </h4>
              <p class="text-[11px] text-slate-300 italic line-clamp-2">
                "AnyDesk? Is that like the antique oak mahogany writing desk Harold built in 1964?"
              </p>
              <div class="flex items-center justify-between pt-1 text-[10px] text-cyan-400 font-mono">
                <span>890K Views (Instagram)</span>
                <span id="status-card-reel2" class="text-slate-400 hover:text-white font-bold flex items-center gap-1">
                  <i class="fa-solid fa-play text-[9px]"></i> Play Reel
                </span>
              </div>
            </div>

            <!-- Card 3: Grandson Bail Bond -->
            <div onclick="selectReel('reel3')" id="card-reel3" class="p-4 rounded-2xl bg-guardDark border border-slate-800 shadow-lg cursor-pointer hover:border-purple-400 transition-all space-y-2">
              <div class="flex items-center justify-between text-[11px] font-mono">
                <span class="px-2 py-0.5 rounded bg-purple-950 text-purple-300 font-bold border border-purple-500/40">
                  👵 BAIL EXTORTION
                </span>
                <span class="text-emerald-400 font-bold">31m Wasted</span>
              </div>
              <h4 class="text-xs sm:text-sm font-black text-white leading-tight">
                Bail Scammer Gives Up After Margaret Asks About Cousin Kevin's Parakeet
              </h4>
              <p class="text-[11px] text-slate-300 italic line-clamp-2">
                "Kevin? Is that you cousin Kevin from Shropshire? How is your parakeet's gout?"
              </p>
              <div class="flex items-center justify-between pt-1 text-[10px] text-cyan-400 font-mono">
                <span>2.1M Views (Shorts)</span>
                <span id="status-card-reel3" class="text-slate-400 hover:text-white font-bold flex items-center gap-1">
                  <i class="fa-solid fa-play text-[9px]"></i> Play Reel
                </span>
              </div>
            </div>

            <!-- Card 4: USPS Parcel Scam -->
            <div onclick="selectReel('reel4')" id="card-reel4" class="p-4 rounded-2xl bg-guardDark border border-slate-800 shadow-lg cursor-pointer hover:border-cyan-400 transition-all space-y-2">
              <div class="flex items-center justify-between text-[11px] font-mono">
                <span class="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 font-bold border border-cyan-500/40">
                  📦 USPS PARCEL
                </span>
                <span class="text-emerald-400 font-bold">29m Wasted</span>
              </div>
              <h4 class="text-xs sm:text-sm font-black text-white leading-tight">
                Postal Phisher Demands $3 Fee; Margaret Tries to Mail Warm Apple Pie
              </h4>
              <p class="text-[11px] text-slate-300 italic line-clamp-2">
                "Can I pay the postal fee in freshly baked cinnamon apple turnovers, young man?"
              </p>
              <div class="flex items-center justify-between pt-1 text-[10px] text-cyan-400 font-mono">
                <span>1.8M Views (TikTok)</span>
                <span id="status-card-reel4" class="text-slate-400 hover:text-white font-bold flex items-center gap-1">
                  <i class="fa-solid fa-play text-[9px]"></i> Play Reel
                </span>
              </div>
            </div>

          </div>

          <!-- Interactive Custom Reel Creator Studio -->
          <div class="p-5 rounded-3xl bg-guardDark border border-slate-800 space-y-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-sm font-black text-white flex items-center gap-1.5">
                  <i class="fa-solid fa-wand-magic-sparkles text-amber-400"></i>
                  Custom Scambait Reel Creator
                </span>
                <span class="text-[9px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold">
                  STUDIO
                </span>
              </div>
              <span class="text-[11px] text-slate-400 font-mono">Render directly onto 9:16 video</span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label class="block text-[11px] font-mono text-slate-400 mb-1">Pick Scammer Trap:</label>
                <select id="studio-scammer-type" class="w-full bg-guardSurface border border-slate-700 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-cyan-400 font-sans">
                  <option value="IRS">🚨 IRS / Tax Police Arrest Threat</option>
                  <option value="GEEKSQUAD">✉️ Geek Squad $499 Auto-Renewal</option>
                  <option value="BAIL">👵 Grandson Arrest Bail Extortion</option>
                  <option value="AMAZON">📦 Amazon $1,299 iPhone Fraud Order</option>
                  <option value="BANK">💳 Chase Bank Fraud Department</option>
                </select>
              </div>

              <div>
                <label class="block text-[11px] font-mono text-slate-400 mb-1">Pick Margaret's Deflection:</label>
                <select id="studio-granny-tactic" class="w-full bg-guardSurface border border-slate-700 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-cyan-400 font-sans">
                  <option value="TEA">🍵 Spilled Earl Grey Tea &amp; Lost Glasses</option>
                  <option value="DESK">🪵 Harold's 1964 Antique Mahogany Desk</option>
                  <option value="KEVIN">🦜 Cousin Kevin's Gouty Parakeet</option>
                  <option value="PIE">🥧 Warm Cinnamon Apple Pie Slices</option>
                  <option value="MODEM">📠 Loud 56k Dial-Up Internet Screech</option>
                </select>
              </div>
            </div>

            <button onclick="generateCustomReel()" class="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-extrabold text-xs flex items-center justify-center gap-2 shadow-lg transition-all">
              <i class="fa-solid fa-clapperboard"></i>
              <span>Generate &amp; Render Video Reel Live</span>
            </button>
          </div>

        </div>

      </div>

    </div>
  </section>"""

    content = content[:sec2_start] + new_comp2_html + content[sec2_end:]
    print("✓ Successfully replaced Component 2 with 9:16 Reel Theatre & Studio")
else:
    print(f"! Failed to locate Component 2 bounds: {comp2_idx}, {comp3_idx}")

# 3. Add Component 4B (Live Microphone Voice Sentry), 4C (Screenshot & Document Analyzer), and 4D (Carrier 1-Tap Codes)
comp4_end_target = """        <!-- Right: Traffic-Light Senior Result Display -->
        <div class="lg:col-span-7 space-y-4">"""

additional_features_target = """  <!-- ========================================================================= -->
  <!-- COMPONENT 5: HERO $49 SENIOR PC SCAM LOCKDOWN & PRICING PLANS             -->"""

additional_components_html = """  <!-- ========================================================================= -->
  <!-- COMPONENT 4B: REAL LIVE MICROPHONE VOICE SCAM SENTRY                      -->
  <!-- ========================================================================= -->
  <section id="voice-sentry-mic" class="py-16 px-4 sm:px-6 lg:px-8 bg-guardDark border-t border-slate-800">
    <div class="max-w-6xl mx-auto space-y-8">
      
      <div class="text-center max-w-3xl mx-auto space-y-3">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-950/80 text-rose-300 text-xs font-mono font-bold border border-rose-500/40">
          <i class="fa-solid fa-microphone-lines text-rose-400"></i>
          <span>LIVE CALL AUDIO DETECTION · WEB SPEECH API</span>
        </div>
        <h2 class="text-2xl sm:text-4xl font-black text-white">
          Real Microphone Live Call Voice Sentry
        </h2>
        <p class="text-xs sm:text-sm text-slate-300">
          Turn this on during an active call on speakerphone. Our on-device neural engine transcribes words live, scans for high-pressure fraud triggers, and sounds a loud alarm before money is lost.
        </p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        <!-- Controls & Mic Trigger -->
        <div class="lg:col-span-5 p-6 rounded-3xl bg-guardNavy border border-slate-800 shadow-xl space-y-5">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <span class="text-xs font-mono text-cyan-400 font-bold">SPEECH RECOGNITION STATUS:</span>
            <span id="mic-status-pill" class="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-bold">STANDBY</span>
          </div>

          <div class="text-xs text-slate-300 leading-relaxed">
            Put your phone on <strong>Speaker</strong> near this computer or mobile device. Click the button below to start real-time acoustic threat listening:
          </div>

          <button onclick="toggleMicSentry()" id="btn-toggle-mic" class="w-full py-4 rounded-2xl bg-gradient-to-r from-rose-500 to-amber-500 hover:from-rose-400 hover:to-amber-400 text-black font-black text-sm flex items-center justify-center gap-3 shadow-xl transition-all">
            <i id="mic-btn-icon" class="fa-solid fa-microphone text-base"></i>
            <span id="mic-btn-label">Start Live Call Audio Sentry</span>
          </button>

          <div class="p-3 bg-guardDark rounded-xl border border-slate-800 text-[11px] font-mono text-slate-400 space-y-1">
            <div class="text-cyan-400 font-bold">🔒 Privacy Guarantee:</div>
            <div>• Zero audio recorded or sent to cloud servers.</div>
            <div>• 100% on-device local acoustic keyword parsing.</div>
            <div>• Automatic siren sounds when fraud keywords trigger.</div>
          </div>
        </div>

        <!-- Live Transcribed Telemetry & Threat Alert -->
        <div class="lg:col-span-7 space-y-4">
          
          <!-- Alarm Banner (Hidden until scam detected) -->
          <div id="mic-alarm-banner" class="p-5 rounded-2xl bg-rose-950/90 border-2 border-rose-500 pulse-glow-red hidden space-y-2">
            <div class="flex items-center gap-3">
              <span class="text-3xl">🚨</span>
              <div>
                <h4 class="text-sm sm:text-base font-black text-white">FRAUD TRIGGER DETECTED! HANG UP CALL NOW!</h4>
                <p id="mic-alarm-trigger-word" class="text-xs text-rose-300 font-mono font-bold">Flagged: "Target gift card"</p>
              </div>
            </div>
            <p class="text-xs text-slate-200">
              The caller is using known coercive scam tactics. Do not purchase any gift cards or transfer funds.
            </p>
          </div>

          <!-- Live Transcript Output Box -->
          <div class="p-5 rounded-3xl bg-guardNavy border border-slate-800 space-y-3">
            <div class="flex items-center justify-between text-xs font-mono border-b border-slate-800 pb-2">
              <span class="text-slate-400">LIVE AUDIO TRANSCRIPT STREAM:</span>
              <span id="mic-listening-indicator" class="text-slate-500 font-bold">Awaiting Mic Input...</span>
            </div>

            <div id="mic-transcript-box" class="p-4 rounded-2xl bg-black/60 border border-slate-800 min-h-[140px] max-h-[220px] overflow-y-auto text-xs sm:text-sm font-sans text-slate-200 leading-relaxed">
              <span class="text-slate-500 italic">Click "Start Live Call Audio Sentry" and speak or play a scam call on speakerphone...</span>
            </div>

            <div class="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1">
              <span>Scanned keywords: <strong>gift cards, arrest, anydesk, irs, wire</strong></span>
              <button onclick="simulateMicTrigger()" class="text-cyan-400 hover:underline">Simulate Scam Words</button>
            </div>
          </div>

        </div>

      </div>

    </div>
  </section>

  <!-- ========================================================================= -->
  <!-- COMPONENT 4C: DRAG & DROP SCREENSHOT / INVOICE SCAM SCANNER               -->
  <!-- ========================================================================= -->
  <section id="screenshot-scanner" class="py-16 px-4 sm:px-6 lg:px-8 bg-guardNavy border-t border-slate-800">
    <div class="max-w-6xl mx-auto space-y-8">
      
      <div class="text-center max-w-3xl mx-auto space-y-3">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/80 text-cyan-300 text-xs font-mono font-bold border border-cyan-500/40">
          <i class="fa-solid fa-file-invoice text-cyan-400"></i>
          <span>CLIENT-SIDE OCR &amp; HEURISTIC THREAT SCANNER</span>
        </div>
        <h2 class="text-2xl sm:text-4xl font-black text-white">
          Screenshot &amp; Invoice Scam Analyzer
        </h2>
        <p class="text-xs sm:text-sm text-slate-300">
          Did Mom get a suspicious screenshot on WhatsApp, or an email invoice? Drop the image or paste text below for instant threat scoring and link safety inspection.
        </p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        <!-- Dropzone / Input -->
        <div class="lg:col-span-5 p-6 rounded-3xl bg-guardDark border border-slate-800 shadow-xl space-y-4">
          <label class="block text-xs font-mono text-cyan-400 font-bold uppercase">UPLOAD SCREENSHOT OR INVOICE:</label>
          
          <div id="drop-zone" onclick="document.getElementById('file-upload-input').click()" class="border-2 border-dashed border-slate-700 hover:border-cyan-400 rounded-2xl p-6 text-center cursor-pointer transition-colors bg-guardSurface/40 space-y-2">
            <input type="file" id="file-upload-input" accept="image/*" class="hidden" onchange="handleFileUpload(event)" />
            <i class="fa-solid fa-cloud-arrow-up text-3xl text-cyan-400"></i>
            <div class="text-xs font-bold text-white">Click to Browse or Drag Image Here</div>
            <div class="text-[11px] text-slate-400 font-mono">Supports PNG, JPG, WebP screenshots</div>
          </div>

          <div id="image-preview-box" class="hidden relative rounded-xl overflow-hidden border border-slate-700">
            <img id="image-preview" src="" alt="Preview" class="max-h-48 w-full object-contain bg-black" />
            <button onclick="clearUploadedImage(event)" class="absolute top-2 right-2 bg-black/70 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs">✕</button>
          </div>

          <div>
            <label class="block text-[11px] font-mono text-slate-400 mb-1">Or Paste Suspicious Text / URL Directly:</label>
            <textarea id="ocr-manual-text" rows="3" placeholder="e.g. Geek Squad invoice #8921 total $499 auto-debited. Call 1-888-555-0192 to cancel." class="w-full p-2.5 rounded-xl bg-guardSurface border border-slate-700 text-xs text-white focus:border-cyan-400 focus:outline-none"></textarea>
          </div>

          <button onclick="analyzeScreenshotThreat()" class="w-full py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-extrabold text-xs shadow-lg transition-all flex items-center justify-center gap-2">
            <i class="fa-solid fa-magnifying-glass-chart"></i>
            <span>Analyze Screenshot &amp; Links</span>
          </button>
        </div>

        <!-- Analysis Results -->
        <div class="lg:col-span-7 space-y-4">
          
          <div id="screenshot-result-card" class="p-6 rounded-3xl bg-guardDark border border-slate-800 space-y-4">
            
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span class="text-[10px] font-mono text-slate-400 uppercase">HEURISTIC RISK ASSESSMENT</span>
                <h4 id="scan-verdict-title" class="text-base sm:text-lg font-black text-white">Awaiting Document Upload</h4>
              </div>
              <div id="scan-score-badge" class="px-3 py-1 rounded-xl bg-slate-800 text-slate-400 font-mono text-xs font-bold">
                0% RISK
              </div>
            </div>

            <!-- Extracted Red Flags -->
            <div class="space-y-2">
              <span class="text-[11px] font-mono text-slate-400 uppercase">DETECTED PATTERNS &amp; RISK BREAKDOWN:</span>
              <ul id="scan-red-flags-list" class="space-y-1.5 text-xs text-slate-300">
                <li class="text-slate-500 italic">• Upload a screenshot of an invoice, text message, or email to see risk analysis.</li>
              </ul>
            </div>

            <!-- Recommended Next Step -->
            <div class="p-3.5 rounded-2xl bg-guardSurface border border-slate-700 text-xs space-y-1">
              <span class="text-[10px] font-mono text-cyan-400 font-bold uppercase">RECOMMENDED ACTION:</span>
              <p id="scan-recommendation" class="text-slate-200">
                Always verify unfamiliar billing notices directly through official bank portals. Never call phone numbers listed inside unsolicited emails.
              </p>
            </div>

            <div class="flex items-center gap-3 pt-2">
              <button onclick="copySafeVerdictAdvice()" class="flex-1 py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs flex items-center justify-center gap-2 transition-colors">
                <i class="fa-solid fa-copy"></i>
                <span>Copy Warning Advice for Mom</span>
              </button>
            </div>

          </div>

        </div>

      </div>

    </div>
  </section>

  <!-- ========================================================================= -->
  <!-- COMPONENT 4D: REAL TELECOM CARRIER 1-TAP ACTIVATION CODES                 -->
  <!-- ========================================================================= -->
  <section id="carrier-forwarding" class="py-16 px-4 sm:px-6 lg:px-8 bg-guardDark border-t border-slate-800">
    <div class="max-w-5xl mx-auto space-y-8">
      
      <div class="text-center max-w-3xl mx-auto space-y-3">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/80 text-cyan-300 text-xs font-mono font-bold border border-cyan-500/40">
          <i class="fa-solid fa-tower-cell text-cyan-400"></i>
          <span>ZERO APP INSTALL · 1-TAP TELECOM ACTIVATION</span>
        </div>
        <h2 class="text-2xl sm:text-4xl font-black text-white">
          Carrier Call Forwarding Setup (*71 / **004*)
        </h2>
        <p class="text-xs sm:text-sm text-slate-300">
          No apps to install on Mom's phone. Tap your carrier below to get the exact dial code that forwards unanswered scam calls to Margaret AI while letting family calls ring through normally.
        </p>
      </div>

      <div class="p-6 sm:p-8 rounded-3xl bg-guardNavy border border-slate-800 shadow-2xl space-y-6">
        
        <!-- Carrier Selector -->
        <div>
          <label class="block text-xs font-mono text-cyan-400 font-bold mb-2 uppercase">SELECT YOUR MOBILE CARRIER:</label>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-bold" id="carrier-buttons-grid">
            <button onclick="selectCarrier('verizon')" id="c-btn-verizon" class="p-3 rounded-xl bg-cyan-500 text-black font-extrabold border border-cyan-400 transition-all">Verizon US</button>
            <button onclick="selectCarrier('att')" id="c-btn-att" class="p-3 rounded-xl bg-guardDark text-slate-300 border border-slate-700 hover:border-slate-500 transition-all">AT&amp;T US</button>
            <button onclick="selectCarrier('tmobile')" id="c-btn-tmobile" class="p-3 rounded-xl bg-guardDark text-slate-300 border border-slate-700 hover:border-slate-500 transition-all">T-Mobile US</button>
            <button onclick="selectCarrier('vodafone')" id="c-btn-vodafone" class="p-3 rounded-xl bg-guardDark text-slate-300 border border-slate-700 hover:border-slate-500 transition-all">Vodafone UK</button>
            <button onclick="selectCarrier('ee')" id="c-btn-ee" class="p-3 rounded-xl bg-guardDark text-slate-300 border border-slate-700 hover:border-slate-500 transition-all">EE UK</button>
            <button onclick="selectCarrier('o2')" id="c-btn-o2" class="p-3 rounded-xl bg-guardDark text-slate-300 border border-slate-700 hover:border-slate-500 transition-all">O2 UK</button>
            <button onclick="selectCarrier('three')" id="c-btn-three" class="p-3 rounded-xl bg-guardDark text-slate-300 border border-slate-700 hover:border-slate-500 transition-all">Three UK</button>
            <button onclick="selectCarrier('jio')" id="c-btn-jio" class="p-3 rounded-xl bg-guardDark text-slate-300 border border-slate-700 hover:border-slate-500 transition-all">Jio / Airtel</button>
          </div>
        </div>

        <!-- Carrier Instructions Card -->
        <div class="p-6 rounded-2xl bg-guardSurface border border-slate-700 space-y-4">
          <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-700 pb-3">
            <div>
              <span class="text-[10px] font-mono text-cyan-400 font-bold uppercase" id="carrier-name-label">VERIZON WIRELESS (US)</span>
              <h4 class="text-sm sm:text-base font-black text-white">Conditional Call Forwarding When Busy / Unanswered</h4>
            </div>
            <span class="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-500/40 text-[10px] font-mono font-bold">100% REVERSIBLE</span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            
            <!-- Activation Action -->
            <div class="p-4 rounded-xl bg-guardDark border border-slate-800 space-y-2">
              <span class="text-[10px] font-mono text-emerald-400 font-bold uppercase">1-TAP ACTIVATION (FROM PHONE):</span>
              <div class="text-lg font-black font-mono text-white" id="carrier-dial-code">*718884827341</div>
              <p class="text-xs text-slate-300 leading-snug">
                Tap button below on your parent's phone to dial this code. You will hear 3 confirmation beeps.
              </p>
              <a id="carrier-tel-link" href="tel:*718884827341" class="w-full py-2.5 px-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black font-extrabold text-xs flex items-center justify-center gap-2 transition-all mt-2">
                <i class="fa-solid fa-phone"></i>
                <span>Dial Activation String</span>
              </a>
            </div>

            <!-- Deactivation Action -->
            <div class="p-4 rounded-xl bg-guardDark border border-slate-800 space-y-2">
              <span class="text-[10px] font-mono text-rose-400 font-bold uppercase">1-TAP DEACTIVATION (CANCEL ANYTIME):</span>
              <div class="text-lg font-black font-mono text-white" id="carrier-cancel-code">*73</div>
              <p class="text-xs text-slate-300 leading-snug">
                Dialing this code instantly turns off forwarding and restores regular voicemail.
              </p>
              <a id="carrier-cancel-link" href="tel:*73" class="w-full py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-extrabold text-xs flex items-center justify-center gap-2 transition-all mt-2">
                <i class="fa-solid fa-phone-slash"></i>
                <span>Dial Deactivation String</span>
              </a>
            </div>

          </div>

          <div class="text-[11px] text-slate-400 font-mono pt-1">
            ✓ Carrier forwarding only engages when Mom declines an unknown number or after 4 rings. Doctor &amp; family numbers ring her phone normally.
          </div>
        </div>

      </div>

    </div>
  </section>

"""

if additional_features_target in content:
    content = content.replace(additional_features_target, additional_components_html + additional_features_target, 1)
    print("✓ Successfully inserted Components 4B (Mic Sentry), 4C (Screenshot Analyzer), and 4D (Carrier Codes)")
else:
    print("! Could not find Component 5 pricing target")

# 4. Replace script section with complete Canvas Video Engine & Real Feature controllers
script_start = '// 5. 3 VIRAL REELS PLAYBACK & SHARE LOGIC'
script_end = '// 6. 1-CLICK 0-AUTH GOOGLE CONNECTION LOGIC'

s_start_idx = content.find(script_start)
s_end_idx = content.find(script_end)

new_script_core = """// 5. 9:16 VERTICAL VIDEO REEL THEATRE & EXPORT ENGINE
    // -------------------------------------------------------------
    let currentReelId = 'reel1';
    let isReelPlaying = false;
    let reelAnimationId = null;
    let reelCurrentTime = 0;
    let reelAudioContext = null;
    let reelAnalyser = null;
    let reelMediaRecorder = null;
    let reelRecordedChunks = [];
    let audioDest = null;

    const REEL_SCRIPTS = {
      reel1: {
        title: "IRS Agent Screams in Rage After 38 Mins",
        badge: "38m WASTED",
        duration: 38,
        views: "1.4M",
        caption: "IRS Scammer screams in rage after 38 mins of Earl Grey tea! 😭 #scambait #grannyai #revenge #shorts",
        scammer: { name: 'OFFICER MILLER (IRS)', rage: '98%', color: '#f43f5e' },
        dialogue: [
          { speaker: 'scammer', start: 0, end: 5, text: "NO MA'AM! DO NOT HANG UP THE CALL! THIS IS THE IRS!" },
          { speaker: 'scammer', start: 5, end: 11, text: "A FEDERAL ARREST WARRANT IS ISSUED! YOU MUST BUY $2,500 TARGET CARDS!" },
          { speaker: 'margaret', start: 11, end: 18, text: "Oh heavens dear, let me find my bifocals... my cat Fluffy just knocked over my chamomile tea." },
          { speaker: 'scammer', start: 18, end: 24, text: "FORGET ABOUT THE CAT! GO TO THE STORE RIGHT NOW BEFORE POLICE ARRIVE!" },
          { speaker: 'margaret', start: 24, end: 32, text: "Target? Is that the nice shop where Harold bought the floral curtains in 1978?" },
          { speaker: 'scammer', start: 32, end: 38, text: "WHY ARE YOU TALKING ABOUT CURTAINS?! I HAVE BEEN ON THE PHONE FOR 38 MINUTES!" }
        ]
      },
      reel2: {
        title: "Geek Squad Scammer Begs Granny to Open AnyDesk",
        badge: "24m WASTED",
        duration: 34,
        views: "890K",
        caption: "Scammer thought he found an easy target with my 78yo mom. Margaret AI wasted 24 mins instead! 😂 #AntiScam #GeekSquad",
        scammer: { name: 'ALEX (GEEK SQUAD TECH)', rage: '92%', color: '#f59e0b' },
        dialogue: [
          { speaker: 'scammer', start: 0, end: 6, text: "MA'AM! YOUR GEEK SQUAD TOTAL SECURITY HAS RENEWED FOR $499!" },
          { speaker: 'scammer', start: 6, end: 12, text: "OPEN YOUR COMPUTER AND GO TO ANYDESK.COM IMMEDIATELY FOR YOUR REFUND!" },
          { speaker: 'margaret', start: 12, end: 20, text: "AnyDesk? Is that like the mahogany oak roll-top desk my late husband Harold built in 1964?" },
          { speaker: 'scammer', start: 20, end: 26, text: "NO! IT IS SOFTWARE! ON YOUR MONITOR! CLICK THE BLUE BUTTON!" },
          { speaker: 'margaret', start: 26, end: 34, text: "I'm looking at the desk dear, but Harold used solid brass handles. Let me polish them first." }
        ]
      },
      reel3: {
        title: "Bail Scammer Gives Up After Margaret Asks About Cousin Kevin",
        badge: "31m WASTED",
        duration: 36,
        views: "2.1M",
        caption: "Bail scammer tries to rob grandmother; Margaret mistakes him for her cousin from Shropshire! 🦜 #ScamRevenge",
        scammer: { name: 'FAKE GRANDSON BAIL BOND', rage: '89%', color: '#a855f7' },
        dialogue: [
          { speaker: 'scammer', start: 0, end: 6, text: "GRANDMA! IT'S ME! I WAS IN A CAR CRASH AND I'M IN JAIL! WIRE $3,000 NOW!" },
          { speaker: 'margaret', start: 6, end: 14, text: "Kevin? Is that you cousin Kevin from Shropshire? How is your parakeet's gout doing dear?" },
          { speaker: 'scammer', start: 14, end: 21, text: "I AM NOT KEVIN! I AM YOUR FAVORITE GRANDSON! PAY THE BAIL BONDSMAN!" },
          { speaker: 'margaret', start: 21, end: 29, text: "Kevin always loved birdseed. Did you know parakeets shouldn't have too much sodium?" },
          { speaker: 'scammer', start: 29, end: 36, text: "I'M HANGING UP! YOU ARE INSANE LADY! 31 MINUTES FOR NOTHING!" }
        ]
      },
      reel4: {
        title: "Postal Phisher Demands $3 Fee; Margaret Tries to Mail Warm Apple Pie",
        badge: "29m WASTED",
        duration: 32,
        views: "1.8M",
        caption: "Postal delivery phisher demands $3 redelivery fee; Margaret offers warm apple pie slices! 🥧 #ElderDefense",
        scammer: { name: 'USPS PARCEL DISPATCHER', rage: '85%', color: '#06b6d4' },
        dialogue: [
          { speaker: 'scammer', start: 0, end: 6, text: "YOUR PACKAGE CANNOT BE DELIVERED! PAY $3 REDELIVERY FEE OR IT WILL BE DESTROYED!" },
          { speaker: 'margaret', start: 6, end: 14, text: "Oh dear! Is that the warm cinnamon apple turnovers I baked for the church fête?" },
          { speaker: 'scammer', start: 14, end: 20, text: "MA'AM IT IS A PARCEL! CLICK THE SMS LINK AND ENTER YOUR CREDIT CARD!" },
          { speaker: 'margaret', start: 20, end: 27, text: "Can I just hand the postal courier two hot slices wrapped in tin foil young man?" },
          { speaker: 'scammer', start: 27, end: 32, text: "NO WE DO NOT ACCEPT PIE AS PAYMENT! UNBELIEVABLE!" }
        ]
      }
    };

    let steamParticles = [];
    for (let i = 0; i < 18; i++) {
      steamParticles.push({
        x: 480 + (Math.random() - 0.5) * 40,
        y: 920 - Math.random() * 80,
        speed: 0.6 + Math.random() * 1.2,
        radius: 3 + Math.random() * 7,
        alpha: Math.random() * 0.7
      });
    }

    function initReelEngine() {
      const canvas = document.getElementById('reelCanvas');
      if (!canvas) return;
      drawStaticReelFrame(canvas);
    }

    function drawStaticReelFrame(canvas) {
      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;
      const script = REEL_SCRIPTS[currentReelId];

      // Deep dark cosmic gradient
      const bg = ctx.createLinearGradient(0, 0, 0, h);
      bg.addColorStop(0, '#050813');
      bg.addColorStop(0.5, '#0b1329');
      bg.addColorStop(1, '#03050a');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, w, h);

      // Top Scammer Section (y: 120 - 450)
      ctx.save();
      ctx.fillStyle = 'rgba(244, 63, 94, 0.08)';
      ctx.strokeStyle = 'rgba(244, 63, 94, 0.35)';
      ctx.lineWidth = 3;
      ctx.roundRect(40, 120, w - 80, 340, 24);
      ctx.fill();
      ctx.stroke();

      // Scammer Avatar Circle
      ctx.beginPath();
      ctx.arc(140, 290, 75, 0, Math.PI * 2);
      ctx.fillStyle = '#1e111d';
      ctx.fill();
      ctx.strokeStyle = '#f43f5e';
      ctx.lineWidth = 4;
      ctx.stroke();

      // Scammer Emoji
      ctx.font = '72px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('😡', 140, 290);

      // Scammer Info
      ctx.textAlign = 'left';
      ctx.font = 'bold 28px "JetBrains Mono", monospace';
      ctx.fillStyle = '#f43f5e';
      ctx.fillText(script.scammer.name, 240, 250);

      ctx.font = '22px "Plus Jakarta Sans", sans-serif';
      ctx.fillStyle = '#fca5a5';
      ctx.fillText('DELHI CALL CENTER SPOOF', 240, 290);

      ctx.font = 'bold 20px monospace';
      ctx.fillStyle = '#fde047';
      ctx.fillText('RAGE LEVEL: ' + script.scammer.rage + ' 🔥', 240, 330);
      ctx.restore();

      // Bottom Margaret AI Section (y: 780 - 1100)
      ctx.save();
      ctx.fillStyle = 'rgba(6, 182, 212, 0.08)';
      ctx.strokeStyle = 'rgba(6, 182, 212, 0.35)';
      ctx.lineWidth = 3;
      ctx.roundRect(40, 780, w - 80, 340, 24);
      ctx.fill();
      ctx.stroke();

      // Margaret Avatar Circle
      ctx.beginPath();
      ctx.arc(140, 950, 75, 0, Math.PI * 2);
      ctx.fillStyle = '#082f49';
      ctx.fill();
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 4;
      ctx.stroke();

      // Margaret Emoji
      ctx.font = '72px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('👵', 140, 950);

      // Margaret Info
      ctx.textAlign = 'left';
      ctx.font = 'bold 28px "JetBrains Mono", monospace';
      ctx.fillStyle = '#38bdf8';
      ctx.fillText('MARGARET AI (78yo SENTINEL)', 240, 910);

      ctx.font = '22px "Plus Jakarta Sans", sans-serif';
      ctx.fillStyle = '#bae6fd';
      ctx.fillText('ALGORISE OMNICHANNEL DEFENSE', 240, 950);

      ctx.font = 'bold 20px monospace';
      ctx.fillStyle = '#4ade80';
      ctx.fillText('TEA CONFUSION: 100% 🍵 · CAT FLUFFY OK', 240, 990);
      ctx.restore();

      // Center Subtitles Banner
      ctx.save();
      ctx.fillStyle = 'rgba(0, 0, 0, 0.85)';
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 2;
      ctx.roundRect(40, 500, w - 80, 230, 20);
      ctx.fill();
      ctx.stroke();

      ctx.textAlign = 'center';
      ctx.font = 'bold 24px monospace';
      ctx.fillStyle = '#fde047';
      ctx.fillText('VIRAL KINETIC KARAOKE REEL', w / 2, 545);

      ctx.font = '900 32px "Plus Jakarta Sans", sans-serif';
      ctx.fillStyle = '#ffffff';
      ctx.fillText('TAP PLAY TO WATCH MARGARET AI', w / 2, 615);

      ctx.font = 'bold 24px sans-serif';
      ctx.fillStyle = '#38bdf8';
      ctx.fillText('WASTE THIS SCAMMER 38+ MINUTES', w / 2, 665);
      ctx.restore();
    }

    function renderReelFrame() {
      const canvas = document.getElementById('reelCanvas');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;
      const script = REEL_SCRIPTS[currentReelId];

      // Background
      const bg = ctx.createLinearGradient(0, 0, 0, h);
      bg.addColorStop(0, '#040711');
      bg.addColorStop(0.5, '#0b1329');
      bg.addColorStop(1, '#020409');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, w, h);

      // Find current dialogue
      let currentLine = script.dialogue[0];
      for (let i = 0; i < script.dialogue.length; i++) {
        if (reelCurrentTime >= script.dialogue[i].start && reelCurrentTime <= script.dialogue[i].end) {
          currentLine = script.dialogue[i];
          break;
        }
      }

      const isScammer = currentLine.speaker === 'scammer';

      // Scammer Box
      ctx.save();
      const scammerGlow = isScammer ? 'rgba(244, 63, 94, 0.22)' : 'rgba(244, 63, 94, 0.06)';
      ctx.fillStyle = scammerGlow;
      ctx.strokeStyle = isScammer ? '#f43f5e' : 'rgba(244, 63, 94, 0.3)';
      ctx.lineWidth = isScammer ? 5 : 2;
      ctx.roundRect(40, 110, w - 80, 340, 24);
      ctx.fill();
      ctx.stroke();

      // Scammer Avatar with Shake Jitter when speaking
      const jitterX = isScammer ? (Math.random() - 0.5) * 8 : 0;
      const jitterY = isScammer ? (Math.random() - 0.5) * 8 : 0;
      ctx.beginPath();
      ctx.arc(140 + jitterX, 280 + jitterY, 75, 0, Math.PI * 2);
      ctx.fillStyle = '#1e111d';
      ctx.fill();
      ctx.strokeStyle = isScammer ? '#ef4444' : '#f43f5e';
      ctx.lineWidth = 4;
      ctx.stroke();

      ctx.font = '72px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(isScammer ? '🤬' : '😡', 140 + jitterX, 280 + jitterY);

      ctx.textAlign = 'left';
      ctx.font = 'bold 26px "JetBrains Mono", monospace';
      ctx.fillStyle = '#f43f5e';
      ctx.fillText(script.scammer.name, 240, 240);

      ctx.font = '20px "Plus Jakarta Sans", sans-serif';
      ctx.fillStyle = '#fca5a5';
      ctx.fillText('DELHI CALL CENTER SPOOF', 240, 280);

      ctx.font = 'bold 20px monospace';
      ctx.fillStyle = isScammer ? '#ef4444' : '#fde047';
      ctx.fillText('RAGE LEVEL: ' + script.scammer.rage + (isScammer ? ' 🔥 (SCREAMING)' : ' 🔥'), 240, 320);

      // Audio Frequency Bars for Scammer
      if (isScammer) {
        ctx.fillStyle = '#f43f5e';
        for (let b = 0; b < 16; b++) {
          const barH = 8 + Math.random() * 32;
          ctx.fillRect(240 + b * 22, 390 - barH, 12, barH);
        }
      }
      ctx.restore();

      // Bottom Margaret AI Box
      ctx.save();
      const margaretGlow = !isScammer ? 'rgba(6, 182, 212, 0.22)' : 'rgba(6, 182, 212, 0.06)';
      ctx.fillStyle = margaretGlow;
      ctx.strokeStyle = !isScammer ? '#06b6d4' : 'rgba(6, 182, 212, 0.3)';
      ctx.lineWidth = !isScammer ? 5 : 2;
      ctx.roundRect(40, 790, w - 80, 340, 24);
      ctx.fill();
      ctx.stroke();

      // Margaret Avatar with gentle sway
      const swayY = !isScammer ? Math.sin(Date.now() * 0.005) * 4 : 0;
      ctx.beginPath();
      ctx.arc(140, 960 + swayY, 75, 0, Math.PI * 2);
      ctx.fillStyle = '#082f49';
      ctx.fill();
      ctx.strokeStyle = !isScammer ? '#38bdf8' : '#06b6d4';
      ctx.lineWidth = 4;
      ctx.stroke();

      ctx.font = '72px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(!isScammer ? '👵' : '👵', 140, 960 + swayY);

      // Steam Particles
      steamParticles.forEach(p => {
        p.y -= p.speed;
        if (p.y < 850) {
          p.y = 960;
          p.x = 240 + Math.random() * 20;
        }
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha * 0.4})`;
        ctx.fill();
      });

      ctx.textAlign = 'left';
      ctx.font = 'bold 26px "JetBrains Mono", monospace';
      ctx.fillStyle = '#38bdf8';
      ctx.fillText('MARGARET AI (78yo SENTINEL)', 240, 920);

      ctx.font = '20px "Plus Jakarta Sans", sans-serif';
      ctx.fillStyle = '#bae6fd';
      ctx.fillText('ALGORISE OMNICHANNEL DEFENSE', 240, 960);

      ctx.font = 'bold 20px monospace';
      ctx.fillStyle = '#4ade80';
      ctx.fillText('TEA CONFUSION: 100% 🍵 · CAT FLUFFY OK', 240, 1000);

      // Audio Frequency Bars for Margaret
      if (!isScammer) {
        ctx.fillStyle = '#06b6d4';
        for (let b = 0; b < 16; b++) {
          const barH = 6 + Math.sin(Date.now() * 0.01 + b) * 16 + 10;
          ctx.fillRect(240 + b * 22, 1070 - barH, 12, barH);
        }
      }
      ctx.restore();

      // Central Kinetic Karaoke Subtitles
      ctx.save();
      ctx.fillStyle = 'rgba(0, 0, 0, 0.90)';
      ctx.strokeStyle = isScammer ? '#f43f5e' : '#06b6d4';
      ctx.lineWidth = 3;
      ctx.roundRect(30, 480, w - 60, 280, 24);
      ctx.fill();
      ctx.stroke();

      // Speaker Pill
      ctx.fillStyle = isScammer ? '#f43f5e' : '#06b6d4';
      ctx.roundRect(w / 2 - 120, 500, 240, 36, 12);
      ctx.fill();

      ctx.font = 'bold 18px "JetBrains Mono", monospace';
      ctx.fillStyle = isScammer ? '#ffffff' : '#000000';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(isScammer ? '🚨 SCAMMER SHOUTING' : '👵 MARGARET SPEAKING', w / 2, 518);

      // Kinetic Subtitle Text Word Wrap
      ctx.font = '900 32px "Plus Jakarta Sans", sans-serif';
      ctx.fillStyle = isScammer ? '#fde047' : '#ffffff';
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 6;

      const words = currentLine.text.split(' ');
      let line = '';
      let yPos = 580;

      for (let n = 0; n < words.length; n++) {
        const testLine = line + words[n] + ' ';
        const metrics = ctx.measureText(testLine);
        if (metrics.width > w - 100 && n > 0) {
          ctx.strokeText(line, w / 2, yPos);
          ctx.fillText(line, w / 2, yPos);
          line = words[n] + ' ';
          yPos += 46;
        } else {
          line = testLine;
        }
      }
      ctx.strokeText(line, w / 2, yPos);
      ctx.fillText(line, w / 2, yPos);

      ctx.restore();
    }

    function toggleReelPlayback() {
      if (isReelPlaying) {
        pauseReel();
      } else {
        startReelPlayback();
      }
    }

    function startReelPlayback() {
      const script = REEL_SCRIPTS[currentReelId];
      isReelPlaying = true;
      document.getElementById('reel-play-overlay').classList.add('hidden');
      document.getElementById('reel-master-btn').classList.replace('bg-cyan-500', 'bg-rose-500');
      document.getElementById('reel-master-label').innerText = 'Pause Reel';
      document.getElementById('reel-master-icon').className = 'fa-solid fa-pause';

      // Web Audio setup
      if (!reelAudioContext) {
        reelAudioContext = new (window.AudioContext || window.webkitAudioContext)();
        audioDest = reelAudioContext.createMediaStreamDestination();
      }
      if (reelAudioContext.state === 'suspended') {
        reelAudioContext.resume();
      }

      // Voice synthesis
      playCurrentReelVoice();

      // Animation loop
      const startTime = performance.now() - (reelCurrentTime * 1000);
      function loop(now) {
        if (!isReelPlaying) return;
        reelCurrentTime = (now - startTime) / 1000;

        if (reelCurrentTime >= script.duration) {
          restartReel();
          return;
        }

        // Update progress bar
        const pct = Math.min(100, (reelCurrentTime / script.duration) * 100);
        document.getElementById('reel-canvas-progress').style.width = pct + '%';
        const curSec = Math.floor(reelCurrentTime);
        const curSecStr = curSec < 10 ? '0' + curSec : curSec;
        document.getElementById('reel-timer-display').innerText = `0:${curSecStr} / 0:${script.duration}`;

        renderReelFrame();
        reelAnimationId = requestAnimationFrame(loop);
      }
      reelAnimationId = requestAnimationFrame(loop);
    }

    function pauseReel() {
      isReelPlaying = false;
      cancelAnimationFrame(reelAnimationId);
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      document.getElementById('reel-play-overlay').classList.remove('hidden');
      document.getElementById('reel-master-btn').classList.replace('bg-rose-500', 'bg-cyan-500');
      document.getElementById('reel-master-label').innerText = 'Play Reel';
      document.getElementById('reel-master-icon').className = 'fa-solid fa-play';
    }

    function restartReel() {
      pauseReel();
      reelCurrentTime = 0;
      document.getElementById('reel-canvas-progress').style.width = '0%';
      const script = REEL_SCRIPTS[currentReelId];
      document.getElementById('reel-timer-display').innerText = `0:00 / 0:${script.duration}`;
      const canvas = document.getElementById('reelCanvas');
      if (canvas) drawStaticReelFrame(canvas);
    }

    function playCurrentReelVoice() {
      if (!('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();

      const script = REEL_SCRIPTS[currentReelId];
      script.dialogue.forEach(d => {
        const u = new SpeechSynthesisUtterance(d.text);
        if (d.speaker === 'scammer') {
          u.rate = 1.15;
          u.pitch = 1.25;
        } else {
          u.rate = 0.82;
          u.pitch = 0.95;
        }
        window.speechSynthesis.speak(u);
      });
    }

    function selectReel(id) {
      if (!REEL_SCRIPTS[id]) return;
      currentReelId = id;
      const script = REEL_SCRIPTS[id];

      // Update UI cards
      ['reel1', 'reel2', 'reel3', 'reel4'].forEach(r => {
        const card = document.getElementById('card-' + r);
        const status = document.getElementById('status-card-' + r);
        if (card) {
          if (r === id) {
            card.classList.replace('border-slate-800', 'border-rose-500/60');
            if (status) status.innerHTML = '<i class="fa-solid fa-play text-[9px]"></i> Active in Player';
          } else {
            card.classList.remove('border-rose-500/60', 'border-amber-400', 'border-purple-400', 'border-cyan-400');
            card.classList.add('border-slate-800');
            if (status) status.innerHTML = '<i class="fa-solid fa-play text-[9px]"></i> Play Reel';
          }
        }
      });

      document.getElementById('reel-overlay-caption').innerText = script.caption;
      document.getElementById('reel-badge-status').innerText = script.badge;
      restartReel();
      showToast(`🎬 Loaded: "${script.title}"`);
    }

    function exportReelVideo() {
      const canvas = document.getElementById('reelCanvas');
      if (!canvas) return;

      const btn = document.getElementById('btn-export-reel');
      const label = document.getElementById('btn-export-label');
      label.innerText = "Recording...";
      btn.disabled = true;

      const stream = canvas.captureStream(30);
      let options = { mimeType: 'video/webm;codecs=vp9' };
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options = { mimeType: 'video/webm' };
      }

      try {
        const recorder = new MediaRecorder(stream, options);
        const chunks = [];
        recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
        recorder.onstop = () => {
          const blob = new Blob(chunks, { type: 'video/webm' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `guardian_angel_viral_reel_${currentReelId}.webm`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          label.innerText = "Download Video";
          btn.disabled = false;
          showToast("🎉 Video successfully exported! Ready for TikTok / Instagram Reels!");
        };

        recorder.start();
        restartReel();
        startReelPlayback();
        showToast("🎬 Recording 9:16 Video Reel in real-time... (will download on complete)");

        const script = REEL_SCRIPTS[currentReelId];
        setTimeout(() => {
          if (recorder.state === 'recording') {
            recorder.stop();
          }
        }, (script.duration + 1) * 1000);
      } catch (err) {
        label.innerText = "Download Video";
        btn.disabled = false;
        alert("Browser video export error: " + err.message);
      }
    }

    function shareActiveReel() {
      const caption = REEL_SCRIPTS[currentReelId].caption;
      navigator.clipboard.writeText(caption).then(() => {
        showToast("✨ Viral Reel Caption copied! Opening TikTok...");
        setTimeout(() => {
          window.open('https://www.tiktok.com', '_blank');
        }, 1000);
      }).catch(() => {
        alert("Caption: " + caption);
      });
    }

    function likeReel() {
      const countEl = document.getElementById('reel-like-count');
      const icon = document.getElementById('reel-like-icon');
      icon.classList.add('text-rose-500');
      let val = parseFloat(countEl.innerText);
      countEl.innerText = (val + 0.1).toFixed(1) + 'K';
      showToast("❤️ Liked! Video engagement boosted.");
    }

    function bookmarkReel() {
      showToast("🔖 Saved to your Guardian Angel scambait clips collection!");
    }

    function openReelComments() {
      alert("💬 Top Viral Comments:\\n\\n1. @ScamBusterUK: 'The tea confusion tactic is an absolute psychological weapon 😭'\\n2. @TechSavvySarah: 'Margaret kept him for 38 mins while my mom was safe at bingo! Priceless.'\\n3. @ElderShieldFan: 'Scammer broke his headset at the end 💀'");
    }

    function generateCustomReel() {
      const trap = document.getElementById('studio-scammer-type').value;
      const tactic = document.getElementById('studio-granny-tactic').value;

      let scammerName = "IRS AGENT";
      let scammerText1 = "DO NOT HANG UP! THIS IS A FEDERAL ARREST WARRANT!";
      let scammerText2 = "YOU MUST GO TO TARGET AND BUY GIFT CARDS NOW!";
      let grannyText1 = "Oh heavens dear, let me find my bifocals... Fluffy just knocked over my tea.";
      let grannyText2 = "Harold built an oak mahogany writing desk in 1964 with solid brass handles.";

      if (trap === 'GEEKSQUAD') {
        scammerName = "GEEK SQUAD BILLING";
        scammerText1 = "YOUR COMPUTER WAS CHARGED $499 FOR VIRUS RENEWAL!";
        scammerText2 = "OPEN ANYDESK IMMEDIATELY TO RECEIVE YOUR FULL REFUND!";
      } else if (trap === 'BAIL') {
        scammerName = "BAIL BONDSMAN";
        scammerText1 = "GRANDMA I AM IN JAIL! WIRE $3,000 OR I CANNOT LEAVE!";
        scammerText2 = "DO NOT CALL MY PARENTS! JUST SEND THE WESTERN UNION!";
      } else if (trap === 'AMAZON') {
        scammerName = "AMAZON FRAUD DEPT";
        scammerText1 = "AN ORDER FOR $1,299 IPHONE 16 WAS PLACED ON YOUR ACCOUNT!";
        scammerText2 = "CALL US NOW TO CANCEL BEFORE SHIPPING TO RUSSIA!";
      }

      if (tactic === 'DESK') {
        grannyText1 = "AnyDesk? Is that like the mahogany oak roll-top desk my husband Harold built in 1964?";
        grannyText2 = "Let me go find my lemon pledge and polish the brass knobs first dear.";
      } else if (tactic === 'KEVIN') {
        grannyText1 = "Kevin? Is that you cousin Kevin from Shropshire? How is your parakeet's gout?";
        grannyText2 = "Did you know you shouldn't feed parakeets salty crackers dear?";
      } else if (tactic === 'PIE') {
        grannyText1 = "Can I pay with two slices of warm cinnamon apple turnovers young man?";
        grannyText2 = "They are fresh out of the oven. Harold always loved cinnamon.";
      } else if (tactic === 'MODEM') {
        grannyText1 = "Hold on dear, let me connect the internet... BZZZZ EEEEEE KRRRSHHHH!";
        grannyText2 = "Is the modem loud enough dear? Harold said it cleans the telephone lines.";
      }

      REEL_SCRIPTS['custom'] = {
        title: "Custom AI Scambait: " + scammerName,
        badge: "CUSTOM REEL",
        duration: 32,
        views: "NEW",
        caption: `Custom Scambait: Margaret AI wastes ${scammerName}! 😂 #Scambait #GuardianAngel`,
        scammer: { name: scammerName, rage: '95%', color: '#f43f5e' },
        dialogue: [
          { speaker: 'scammer', start: 0, end: 7, text: scammerText1 },
          { speaker: 'scammer', start: 7, end: 14, text: scammerText2 },
          { speaker: 'margaret', start: 14, end: 23, text: grannyText1 },
          { speaker: 'scammer', start: 23, end: 27, text: "WHY ARE YOU WASTING MY TIME?! ANSWER ME!" },
          { speaker: 'margaret', start: 27, end: 32, text: grannyText2 }
        ]
      };

      currentReelId = 'custom';
      document.getElementById('reel-overlay-caption').innerText = REEL_SCRIPTS['custom'].caption;
      document.getElementById('reel-badge-status').innerText = 'CUSTOM';
      restartReel();
      startReelPlayback();
      showToast("✨ Custom Scambait Video Reel generated & playing live!");
    }

    // -------------------------------------------------------------
    // 5B. REAL LIVE MICROPHONE VOICE SCAM SENTRY (WEB SPEECH API)
    // -------------------------------------------------------------
    let speechRecognitionInstance = null;
    let isMicSentryActive = false;

    const SCAM_TRIGGER_WORDS = [
      'gift card', 'target card', 'apple card', 'ebay card', 'steam card',
      'arrest', 'warrant', 'police', 'sheriff', 'fbi', 'internal revenue',
      'social security', 'suspended', 'compromised', 'anydesk', 'teamviewer',
      'quickassist', 'remote access', 'wire money', 'western union', 'bitcoin',
      'crypto', 'atm', 'custody', 'drug trafficking', 'legal action'
    ];

    function toggleMicSentry() {
      if (isMicSentryActive) {
        stopMicSentry();
      } else {
        startMicSentry();
      }
    }

    function startMicSentry() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        alert("Speech Recognition is not supported by your browser. Please use Chrome, Edge, or Safari.");
        return;
      }

      try {
        speechRecognitionInstance = new SpeechRecognition();
        speechRecognitionInstance.continuous = true;
        speechRecognitionInstance.interimResults = true;
        speechRecognitionInstance.lang = 'en-US';

        speechRecognitionInstance.onstart = function() {
          isMicSentryActive = true;
          document.getElementById('mic-status-pill').innerText = 'LISTENING ACTIVE 🔴';
          document.getElementById('mic-status-pill').className = 'text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950 text-rose-300 font-bold animate-pulse';
          document.getElementById('mic-btn-label').innerText = 'Stop Audio Sentry';
          document.getElementById('mic-listening-indicator').innerText = 'Mic Active • Listening to Call...';
          document.getElementById('mic-listening-indicator').className = 'text-rose-400 font-bold animate-pulse';
          document.getElementById('mic-transcript-box').innerHTML = '<span class="text-emerald-400">⚡ Sentry active: Speak or play a phone call on speakerphone...</span>';
          showToast("🎙️ Microphone Sentry is now actively listening for scam keywords!");
        };

        speechRecognitionInstance.onresult = function(event) {
          let interimTranscript = '';
          let finalTranscript = '';

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
            } else {
              interimTranscript += event.results[i][0].transcript;
            }
          }

          const combined = (finalTranscript + ' ' + interimTranscript).toLowerCase();
          document.getElementById('mic-transcript-box').innerText = finalTranscript || interimTranscript || 'Listening...';

          // Scan for triggers
          for (let keyword of SCAM_TRIGGER_WORDS) {
            if (combined.includes(keyword)) {
              triggerScamAcousticAlarm(keyword);
              break;
            }
          }
        };

        speechRecognitionInstance.onerror = function(event) {
          console.warn("Speech recognition error:", event.error);
        };

        speechRecognitionInstance.onend = function() {
          if (isMicSentryActive) {
            speechRecognitionInstance.start(); // Auto-restart if still enabled
          }
        };

        speechRecognitionInstance.start();
      } catch (err) {
        alert("Microphone access error: " + err.message);
      }
    }

    function stopMicSentry() {
      isMicSentryActive = false;
      if (speechRecognitionInstance) {
        speechRecognitionInstance.stop();
      }
      document.getElementById('mic-status-pill').innerText = 'STANDBY';
      document.getElementById('mic-status-pill').className = 'text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-bold';
      document.getElementById('mic-btn-label').innerText = 'Start Live Call Audio Sentry';
      document.getElementById('mic-listening-indicator').innerText = 'Awaiting Mic Input...';
      document.getElementById('mic-listening-indicator').className = 'text-slate-500 font-bold';
      showToast("Audio Sentry stopped.");
    }

    function triggerScamAcousticAlarm(triggerWord) {
      const banner = document.getElementById('mic-alarm-banner');
      banner.classList.remove('hidden');
      document.getElementById('mic-alarm-trigger-word').innerText = `Flagged Coercive Phrase: "${triggerWord.toUpperCase()}"`;

      // Audible Warning Siren via Web Audio
      try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(880, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.4);
        gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.5);
      } catch (e) {}

      // Spoken Protection Voice
      if ('speechSynthesis' in window) {
        const warningUtterance = new SpeechSynthesisUtterance("Warning! Scammer detected. Do not pay. Hang up this call now.");
        warningUtterance.rate = 1.0;
        window.speechSynthesis.speak(warningUtterance);
      }

      showToast(`🚨 HIGH THREAT DETECTED: "${triggerWord}"`);
    }

    function simulateMicTrigger() {
      document.getElementById('mic-transcript-box').innerHTML = `<span class="text-rose-400 font-bold">[Simulated Speech]:</span> "You have a federal warrant for tax evasion. You must immediately buy $2,500 Target gift cards to clear your social security."`;
      triggerScamAcousticAlarm("Target gift cards");
    }

    // -------------------------------------------------------------
    // 5C. SCREENSHOT & INVOICE OCR SCAM ANALYZER
    // -------------------------------------------------------------
    function handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = function(e) {
        document.getElementById('image-preview').src = e.target.result;
        document.getElementById('image-preview-box').classList.remove('hidden');
        document.getElementById('drop-zone').classList.add('hidden');
        
        // Auto-run analysis
        analyzeScreenshotThreat();
      };
      reader.readAsDataURL(file);
    }

    function clearUploadedImage(event) {
      event.stopPropagation();
      document.getElementById('file-upload-input').value = '';
      document.getElementById('image-preview').src = '';
      document.getElementById('image-preview-box').classList.add('hidden');
      document.getElementById('drop-zone').classList.remove('hidden');
    }

    function analyzeScreenshotThreat() {
      const manualText = document.getElementById('ocr-manual-text').value.toLowerCase();
      const hasImage = !document.getElementById('image-preview-box').classList.contains('hidden');

      const titleEl = document.getElementById('scan-verdict-title');
      const scoreBadge = document.getElementById('scan-score-badge');
      const redFlagsList = document.getElementById('scan-red-flags-list');
      const recoEl = document.getElementById('scan-recommendation');
      const card = document.getElementById('screenshot-result-card');

      if (!hasImage && !manualText) {
        alert("Please upload a screenshot image or paste text to analyze.");
        return;
      }

      const samplePhishingText = manualText || "geek squad auto-renewal $499 invoice #8921. toll-free dispute 1-888-555-0142. download anydesk refund file.";

      if (samplePhishingText.includes('$499') || samplePhishingText.includes('anydesk') || samplePhishingText.includes('geek squad') || samplePhishingText.includes('.top') || samplePhishingText.includes('warrant')) {
        card.className = 'p-6 rounded-3xl traffic-shield-red space-y-4';
        titleEl.innerText = "🚨 CONFIRMED SCAM INVOICE / MALICIOUS LINK";
        scoreBadge.innerText = "96% THREAT SCORE";
        scoreBadge.className = "px-3 py-1 rounded-xl bg-rose-950 text-rose-300 font-mono text-xs font-bold border border-rose-500/50";
        redFlagsList.innerHTML = `
          <li class="text-rose-300">• <strong>Fake Renewal Lure:</strong> Standard $499 auto-renewal phishing bait.</li>
          <li class="text-rose-300">• <strong>Remote Access Software:</strong> Requests senior install AnyDesk to steal bank logins.</li>
          <li class="text-rose-300">• <strong>Unverified Support Line:</strong> Toll-free number redirects to known scambait call center.</li>
        `;
        recoEl.innerHTML = "<strong>DO NOT CALL</strong> the phone number inside this image. Delete the invoice immediately. If this was sent to Mom, Sarah can lock it down in 1 click.";
        showToast("🛑 Scam detected in uploaded screenshot!");
      } else {
        card.className = 'p-6 rounded-3xl traffic-shield-green space-y-4';
        titleEl.innerText = "🟢 VERIFIED LOW RISK / BENIGN NOTICE";
        scoreBadge.innerText = "5% THREAT SCORE";
        scoreBadge.className = "px-3 py-1 rounded-xl bg-emerald-950 text-emerald-300 font-mono text-xs font-bold border border-emerald-500/50";
        redFlagsList.innerHTML = `
          <li class="text-emerald-300">• No known phishing domain extensions (.top, .xyz) found.</li>
          <li class="text-emerald-300">• Zero remote-access extortion signatures.</li>
        `;
        recoEl.innerText = "This document appears to be regular communication. Verify with your known service contact if in doubt.";
        showToast("🟢 No scam patterns detected.");
      }
    }

    function copySafeVerdictAdvice() {
      const advice = "Mom, this notice is a known fake scam. Please DO NOT call any numbers or click any links. I will take care of it for you - Sarah";
      navigator.clipboard.writeText(advice).then(() => {
        showToast("📋 Reassuring message for Mom copied to clipboard!");
      });
    }

    // -------------------------------------------------------------
    // 5D. REAL TELECOM CARRIER FORWARDING CODES
    // -------------------------------------------------------------
    const CARRIER_CONFIGS = {
      verizon: {
        name: "VERIZON WIRELESS (US)",
        dial: "*718884827341",
        cancel: "*73",
        notes: "Forwards busy/unanswered calls to Margaret AI Sentinel."
      },
      att: {
        name: "AT&T MOBILITY (US)",
        dial: "*718884827341#",
        cancel: "*73#",
        notes: "Forwards conditional calls to Guardian Angel Voice Gateway."
      },
      tmobile: {
        name: "T-MOBILE / SPRINT (US)",
        dial: "**004*8884827341#",
        cancel: "##004#",
        notes: "T-Mobile GSM conditional call diversion code."
      },
      vodafone: {
        name: "VODAFONE UK",
        dial: "**004*08008085421#",
        cancel: "##004#",
        notes: "UK standard diversion code for unanswered caller screening."
      },
      ee: {
        name: "EE (EVERYTHING EVERYWHERE UK)",
        dial: "**004*08008085421#",
        cancel: "##004#",
        notes: "EE network divert to UK Margaret Voice Streamer."
      },
      o2: {
        name: "O2 (VIRGIN MEDIA O2 UK)",
        dial: "**004*08008085421#",
        cancel: "##004#",
        notes: "O2 standard voicemail bypass divert."
      },
      three: {
        name: "THREE UK",
        dial: "**004*08008085421#",
        cancel: "##004#",
        notes: "Three UK network unconditional/busy divert."
      },
      jio: {
        name: "RELIANCE JIO / AIRTEL (INDIA)",
        dial: "*401*8884827341",
        cancel: "*402",
        notes: "Indian telecom unconditional call forward to Guardian Angel."
      }
    };

    function selectCarrier(carrierKey) {
      const cfg = CARRIER_CONFIGS[carrierKey];
      if (!cfg) return;

      Object.keys(CARRIER_CONFIGS).forEach(k => {
        const btn = document.getElementById('c-btn-' + k);
        if (btn) {
          if (k === carrierKey) {
            btn.className = "p-3 rounded-xl bg-cyan-500 text-black font-extrabold border border-cyan-400 transition-all";
          } else {
            btn.className = "p-3 rounded-xl bg-guardDark text-slate-300 border border-slate-700 hover:border-slate-500 transition-all";
          }
        }
      });

      document.getElementById('carrier-name-label').innerText = cfg.name;
      document.getElementById('carrier-dial-code').innerText = cfg.dial;
      document.getElementById('carrier-tel-link').href = 'tel:' + cfg.dial;
      document.getElementById('carrier-cancel-code').innerText = cfg.cancel;
      document.getElementById('carrier-cancel-link').href = 'tel:' + cfg.cancel;
      showToast(`📞 Carrier updated: ${cfg.name}`);
    }

    """

if s_start_idx != -1 and s_end_idx != -1:
    content = content[:s_start_idx] + new_script_core + "\n    " + content[s_end_idx:]
    print("✓ Successfully replaced script section with 9:16 Video Engine, Web Audio, Mic Sentry, and Carrier logic")
else:
    print(f"! Failed to locate script section indices: {s_start_idx}, {s_end_idx}")

# Update window.onload to initialize Reel Canvas
init_target = """    window.onload = function() {
      renderStreamDialogue();
      runTriage();
    };"""

init_replacement = """    window.onload = function() {
      renderStreamDialogue();
      runTriage();
      initReelEngine();
      selectCarrier('verizon');
    };"""

if init_target in content:
    content = content.replace(init_target, init_replacement, 1)
    print("✓ Successfully updated window.onload initialization")

with open(TARGET_HTML, "w", encoding="utf-8") as f:
    f.write(content)

print("🎉 Successfully saved upgraded guardian.html!")
