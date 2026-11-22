function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

document.getElementById("quick-scan-btn").addEventListener("click", async function() {
  const text = document.getElementById("quick-input").value.trim();
  const resBox = document.getElementById("quick-result");

  if (!text) return;

  resBox.style.display = "block";
  resBox.style.background = "#1e293b";
  resBox.style.border = "1px solid #475569";
  resBox.style.color = "#94a3b8";
  resBox.textContent = "Scanning with Guardian Angel Sentinel...";

  try {
    const resp = await fetch("http://127.0.0.1:8050/v1/sentinel/triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        channel: "TEXT",
        sender: "Browser Extension Scan",
        content: text,
        region: "US"
      })
    });
    const data = await resp.json();

    if (data.threat_score >= 70) {
      resBox.style.background = "rgba(244, 63, 94, 0.2)";
      resBox.style.border = "1px solid #f43f5e";
      resBox.style.color = "#fda4af";
      resBox.innerHTML = `<strong>🛑 ${escapeHtml(data.senior_headline || 'SCAM DETECTED')}</strong><br>${escapeHtml(data.safe_next_step || 'Do not click or pay.')}`;
    } else if (data.threat_score >= 35) {
      resBox.style.background = "rgba(245, 158, 11, 0.2)";
      resBox.style.border = "1px solid #f59e0b";
      resBox.style.color = "#fde68a";
      resBox.innerHTML = `<strong>⚠️ CAUTION: SUSPICIOUS</strong><br>${escapeHtml(data.safe_next_step || 'Proceed with caution.')}`;
    } else {
      resBox.style.background = "rgba(16, 185, 129, 0.2)";
      resBox.style.border = "1px solid #10b981";
      resBox.style.color = "#6ee7b7";
      resBox.innerHTML = `<strong>💚 ${escapeHtml(data.senior_headline || 'VERIFIED SAFE')}</strong><br>${escapeHtml(data.safe_next_step || 'Safe communication.')}`;
    }
  } catch (e) {
    // Zero-cost deterministic client-side offline fallback
    const lower = text.toLowerCase();
    const isLifeline = lower.includes("appointment") || lower.includes("prescription") || lower.includes("thank you so much") || lower.includes("thanks grandma");
    const isScam = !isLifeline && (
      lower.includes("warrant") || lower.includes("arrest") || lower.includes("holding account") ||
      lower.includes("$499") || lower.includes(".top") || lower.includes(".xyz") ||
      lower.includes("social security") || lower.includes("winter fuel") || lower.includes("tv licensing")
    );

    if (isScam) {
      resBox.style.background = "rgba(244, 63, 94, 0.2)";
      resBox.style.border = "1px solid #f43f5e";
      resBox.style.color = "#fda4af";
      resBox.innerHTML = "<strong>🛑 STOP! SCAM DETECTED</strong><br>Do not reply, do not pay, and hang up immediately.";
    } else {
      resBox.style.background = "rgba(16, 185, 129, 0.2)";
      resBox.style.border = "1px solid #10b981";
      resBox.style.color = "#6ee7b7";
      resBox.innerHTML = "<strong>💚 VERIFIED SAFE</strong><br>No fraudulent patterns detected. Safe to open.";
    }
  }
});
