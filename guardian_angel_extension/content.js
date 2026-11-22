// Guardian Angel™ — In-Browser Scam & Lockup Sentinel (Manifest V3 Production Hardened)
(function() {
  const TECH_SUPPORT_SCAM_PATTERNS = [
    /windows defender alert/i,
    /call microsoft support/i,
    /your computer has been locked/i,
    /critical security warning/i,
    /call 1-8\d{2}-\d{3}-\d{4}/i,
    /do not restart your computer/i,
    /social security.*suspended/i,
    /dwp.*winter fuel.*payment/i,
    /tv licensing.*court summons/i
  ];

  const DECEPTIVE_DOMAIN_PATTERNS = [
    /track-usps/i,
    /royalmail-fee/i,
    /evri-redeliver/i,
    /login-hmrc/i,
    /claim-rebate/i,
    /claim-dwp/i,
    /tvlicence-pay/i,
    /secure-chase/i
  ];

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function runSentinelScan() {
    if (document.getElementById("ga-sentinel-host")) return; // already shielded

    // Use textContent with 50KB boundary to eliminate forced layout reflow (0ms latency)
    const pageText = document.body ? document.body.textContent.slice(0, 50000).toLowerCase() : "";
    const currentUrl = window.location.href.toLowerCase();

    let isScamDetected = false;
    let reason = "";

    for (let pattern of TECH_SUPPORT_SCAM_PATTERNS) {
      if (pattern.test(pageText)) {
        isScamDetected = true;
        reason = "Tech Support / Screen Lockup Scam Detected";
        break;
      }
    }

    if (!isScamDetected) {
      for (let pattern of DECEPTIVE_DOMAIN_PATTERNS) {
        if (pattern.test(currentUrl)) {
          isScamDetected = true;
          reason = "Deceptive Impersonation Domain (Phishing)";
          break;
        }
      }
    }

    if (isScamDetected) {
      // Pause any loud alarming audio or video loops
      try {
        document.querySelectorAll("audio, video").forEach(el => {
          el.pause();
          el.muted = true;
        });
      } catch (e) {}

      // Render inside closed Shadow DOM to prevent malicious script tampering
      const host = document.createElement("div");
      host.id = "ga-sentinel-host";
      host.style.cssText = "position:fixed;top:0;left:0;width:100%;z-index:2147483647;pointer-events:auto;";
      
      const shadow = host.attachShadow({ mode: "closed" });

      const banner = document.createElement("div");
      banner.style.cssText = `
        background: linear-gradient(135deg, #991b1b, #7f1d1d);
        color: #ffffff;
        padding: 18px 24px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        box-shadow: 0 10px 40px rgba(0,0,0,0.9);
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 3px solid #ef4444;
      `;

      banner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 16px;">
          <span style="font-size: 28px;">🛑</span>
          <div>
            <div style="font-size: 15px; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase;">
              GUARDIAN ANGEL ALERT: ${escapeHtml(reason)}
            </div>
            <div style="font-size: 13px; opacity: 0.95; margin-top: 3px;">
              Do NOT call any phone numbers on this screen, do not install remote software, and do not pay.
            </div>
          </div>
        </div>
        <button id="ga-close-btn" style="
          background: #ffffff;
          color: #991b1b;
          border: none;
          padding: 10px 20px;
          border-radius: 8px;
          font-weight: 800;
          cursor: pointer;
          font-size: 13px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        ">Leave Page Safely</button>
      `;

      shadow.appendChild(banner);
      (document.body || document.documentElement).appendChild(host);

      shadow.getElementById("ga-close-btn").addEventListener("click", function() {
        window.location.href = "about:blank";
      });
    }
  }

  // Initial scan
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", runSentinelScan);
  } else {
    runSentinelScan();
  }

  // Lightweight observer to catch dynamic scam modal injections
  let scanTimeout = null;
  const observer = new MutationObserver(() => {
    if (scanTimeout) return;
    scanTimeout = setTimeout(() => {
      runSentinelScan();
      scanTimeout = null;
    }, 500);
  });

  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
  }
})();
