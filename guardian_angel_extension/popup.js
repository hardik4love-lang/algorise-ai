function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

const GUARDIAN_CLOUD_API = "https://algorise-ai-backend.onrender.com/api/v1/guardian/triage";

document.getElementById("quick-scan-btn").addEventListener("click", async function() {
  const text = document.getElementById("quick-input").value.trim();
  const resBox = document.getElementById("quick-result");
  if (!text) return;

  resBox.style.display = "block";
  resBox.style.background = "#1e293b";
  resBox.style.border = "1px solid #475569";
  resBox.style.color = "#cbd5e1";
  resBox.textContent = "Scanning link/text with Guardian Angel Sentinel...";

  try {
    const resp = await fetch(GUARDIAN_CLOUD_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        channel: /^https?:\/\//i.test(text) ? "URL" : "TEXT",
        sender: "Chrome Extension Scanner",
        content: text,
        region: "US"
      })
    });
    if (!resp.ok) throw new Error("API status " + resp.status);
    const data = await resp.json();

    if (data.threat_score >= 70) {
      resBox.style.background = "rgba(244, 63, 94, 0.22)";
      resBox.style.border = "1px solid #f43f5e";
      resBox.style.color = "#fda4af";
      resBox.innerHTML = `<strong>HIGH THREAT (${data.threat_score}%)</strong><br>${escapeHtml(data.senior_headline)}<br><small>${escapeHtml(data.safe_next_step)}</small>`;
    } else if (data.threat_score >= 35) {
      resBox.style.background = "rgba(245, 158, 11, 0.2)";
      resBox.style.border = "1px solid #f59e0b";
      resBox.style.color = "#fde68a";
      resBox.innerHTML = `<strong>CAUTION (${data.threat_score}%)</strong><br>${escapeHtml(data.senior_headline)}<br><small>${escapeHtml(data.safe_next_step)}</small>`;
    } else {
      resBox.style.background = "rgba(16, 185, 129, 0.2)";
      resBox.style.border = "1px solid #10b981";
      resBox.style.color = "#6ee7b7";
      resBox.innerHTML = `<strong>SAFE (${data.threat_score}%)</strong><br>${escapeHtml(data.senior_headline)}<br><small>${escapeHtml(data.safe_next_step)}</small>`;
    }
  } catch (e) {
    const lower = text.toLowerCase();
    const isLifeline = /(appointment|prescription|thank you|love you)/.test(lower);
    const isScam = !isLifeline && /(\.(top|xyz|buzz|icu|click|cyou)\b|warrant|arrest|holding account|\$499|anydesk|teamviewer|social security|tv licensing|gift card)/.test(lower);

    if (isScam) {
      resBox.style.background = "rgba(244, 63, 94, 0.22)";
      resBox.style.border = "1px solid #f43f5e";
      resBox.style.color = "#fda4af";
      resBox.innerHTML = "<strong>OFFLINE ALERT: SCAM PATTERN DETECTED</strong><br>Do not click links, call numbers, or pay.";
    } else {
      resBox.style.background = "rgba(16, 185, 129, 0.2)";
      resBox.style.border = "1px solid #10b981";
      resBox.style.color = "#6ee7b7";
      resBox.innerHTML = "<strong>OFFLINE CHECK: NO KNOWN THREAT SIGNATURES</strong><br>Still verify independently if unsure.";
    }
  }
});
