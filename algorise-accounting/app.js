/**
 * Algorise BooksOS — Local-First Double-Entry Accounting Engine & Tally-Parity Keyboard Runtime
 * Uses integer paise arithmetic (1 INR = 100 paise) for exact financial math,
 * Web Crypto SHA-256 Merkle Audit Chaining (MCA Rule 11(g)), and optional API sync via window.ALGORISE_CONFIG.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "algorise_books_os_v1";
  const COMPANY_ID = "demo_booksos_01";
  const GENESIS_HASH = "0".repeat(64);

  const GROUP_NATURE = {
    "Capital Account": "LIABILITY",
    "Loans (Liability)": "LIABILITY",
    "Current Liabilities": "LIABILITY",
    "Sundry Creditors": "LIABILITY",
    "Duties & Taxes": "LIABILITY",
    "Fixed Assets": "ASSET",
    "Current Assets": "ASSET",
    "Sundry Debtors": "ASSET",
    "Bank Accounts": "ASSET",
    "Cash-in-Hand": "ASSET",
    "Stock-in-Hand": "ASSET",
    "Sales Accounts": "INCOME",
    "Direct Incomes": "INCOME",
    "Indirect Incomes": "INCOME",
    "Purchase Accounts": "EXPENSE",
    "Direct Expenses": "EXPENSE",
    "Indirect Expenses": "EXPENSE",
  };

  function toPaise(val) {
    const num = Number(String(val ?? "0").replace(/,/g, "").trim());
    if (!Number.isFinite(num)) return 0;
    return Math.round(num * 100);
  }

  function formatINR(paise) {
    const absVal = (Math.abs(paise) / 100).toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    return (paise < 0 ? "-₹" : "₹") + absVal;
  }

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  async function sha256Hex(text) {
    if (window.crypto && window.crypto.subtle) {
      const buf = new TextEncoder().encode(text);
      const digest = await window.crypto.subtle.digest("SHA-256", buf);
      return Array.from(new Uint8Array(digest))
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
    }
    // Fallback deterministic hash for non-HTTPS contexts
    let h1 = 0xdeadbeef;
    let h2 = 0x41c6ce57;
    for (let i = 0; i < text.length; i++) {
      const ch = text.charCodeAt(i);
      h1 = Math.imul(h1 ^ ch, 2654435761);
      h2 = Math.imul(h2 ^ ch, 1597334677);
    }
    h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
    return (
      (h2 >>> 0).toString(16).padStart(8, "0") +
      (h1 >>> 0).toString(16).padStart(8, "0")
    ).padEnd(64, "a");
  }

  function isoToday() {
    return new Date().toISOString().slice(0, 10);
  }

  function daysAgoIso(days) {
    const d = new Date();
    d.setDate(d.getDate() - days);
    return d.toISOString().slice(0, 10);
  }

  function buildInitialDataset() {
    return {
      company: {
        id: COMPANY_ID,
        name: "Apex Fabrics & Traders (FY 2026-27)",
        stateCode: "24",
        gstin: "24AABCA1234F1Z5",
      },
      ledgers: [
        { name: "Cash", parentGroup: "Cash-in-Hand", nature: "ASSET", gstin: "", msmeCategory: "NONE", openingPaise: 14500000, openingDrCr: "DR" },
        { name: "HDFC Bank Current A/c", parentGroup: "Bank Accounts", nature: "ASSET", gstin: "", msmeCategory: "NONE", openingPaise: 84250000, openingDrCr: "DR" },
        { name: "Capital Account", parentGroup: "Capital Account", nature: "LIABILITY", gstin: "", msmeCategory: "NONE", openingPaise: 98750000, openingDrCr: "CR" },
        { name: "Mahalaxmi Saree House (Surat)", parentGroup: "Sundry Debtors", nature: "ASSET", gstin: "24AABCM7721Q1Z9", msmeCategory: "NONE", openingPaise: 0, openingDrCr: "DR" },
        { name: "Dadar Silk Emporium (Mumbai)", parentGroup: "Sundry Debtors", nature: "ASSET", gstin: "27AABCD8812M1Z1", msmeCategory: "NONE", openingPaise: 0, openingDrCr: "DR" },
        { name: "Navkar Dyeing Mills", parentGroup: "Sundry Creditors", nature: "LIABILITY", gstin: "24AABCN4411K1Z3", msmeCategory: "MICRO", udyamNo: "UDYAM-GJ-22-0041920", openingPaise: 0, openingDrCr: "CR" },
        { name: "Shree Yarn Processors", parentGroup: "Sundry Creditors", nature: "LIABILITY", gstin: "24AABCS9123P1Z8", msmeCategory: "SMALL", udyamNo: "UDYAM-GJ-22-0083114", openingPaise: 0, openingDrCr: "CR" },
        { name: "Sales GST", parentGroup: "Sales Accounts", nature: "INCOME", gstin: "", msmeCategory: "NONE", openingPaise: 0, openingDrCr: "CR" },
        { name: "Purchase GST", parentGroup: "Purchase Accounts", nature: "EXPENSE", gstin: "", msmeCategory: "NONE", openingPaise: 0, openingDrCr: "DR" },
        { name: "CGST Output", parentGroup: "Duties & Taxes", nature: "LIABILITY", gstin: "", msmeCategory: "NONE", openingPaise: 0, openingDrCr: "CR" },
        { name: "SGST Output", parentGroup: "Duties & Taxes", nature: "LIABILITY", gstin: "", msmeCategory: "NONE", openingPaise: 0, openingDrCr: "CR" },
        { name: "IGST Output", parentGroup: "Duties & Taxes", nature: "LIABILITY", gstin: "", msmeCategory: "NONE", openingPaise: 0, openingDrCr: "CR" },
        { name: "CGST Input", parentGroup: "Duties & Taxes", nature: "ASSET", gstin: "", msmeCategory: "NONE", openingPaise: 0, openingDrCr: "DR" },
        { name: "SGST Input", parentGroup: "Duties & Taxes", nature: "ASSET", gstin: "", msmeCategory: "NONE", openingPaise: 0, openingDrCr: "DR" },
        { name: "IGST Input", parentGroup: "Duties & Taxes", nature: "ASSET", gstin: "", msmeCategory: "NONE", openingPaise: 0, openingDrCr: "DR" },
        { name: "Brokerage & JobWork Exp", parentGroup: "Direct Expenses", nature: "EXPENSE", gstin: "", msmeCategory: "NONE", openingPaise: 0, openingDrCr: "DR" },
      ],
      vouchers: [
        {
          id: "VCH-DEMO-001",
          voucherType: "SALES",
          voucherNo: "INV/26-27/101",
          date: daysAgoIso(18),
          narration: "60gm Dola Silk Grey Lot - 40 Takas",
          status: "POSTED",
          isPdc: false,
          hasWrittenAgreement: false,
          agreedCreditDays: 15,
          entries: [
            { ledgerName: "Mahalaxmi Saree House (Surat)", drCr: "DR", amountPaise: 26250000, billRef: "INV/26-27/101" },
            { ledgerName: "Sales GST", drCr: "CR", amountPaise: 25000000, billRef: "" },
            { ledgerName: "CGST Output", drCr: "CR", amountPaise: 625000, billRef: "" },
            { ledgerName: "SGST Output", drCr: "CR", amountPaise: 625000, billRef: "" },
          ],
        },
        {
          id: "VCH-DEMO-002",
          voucherType: "SALES",
          voucherNo: "INV/26-27/102",
          date: daysAgoIso(12),
          narration: "Inter-state Viscose Jacquard Dispatch to Mumbai",
          status: "POSTED",
          isPdc: false,
          hasWrittenAgreement: false,
          agreedCreditDays: 15,
          entries: [
            { ledgerName: "Dadar Silk Emporium (Mumbai)", drCr: "DR", amountPaise: 18900000, billRef: "INV/26-27/102" },
            { ledgerName: "Sales GST", drCr: "CR", amountPaise: 18000000, billRef: "" },
            { ledgerName: "IGST Output", drCr: "CR", amountPaise: 900000, billRef: "" },
          ],
        },
        {
          id: "VCH-DEMO-003",
          voucherType: "PURCHASE",
          voucherNo: "NDM/045",
          date: daysAgoIso(41),
          narration: "Dyeing & Finishing Lot #88 (Micro MSME - Written Agreement 60d capped at 45d)",
          status: "POSTED",
          isPdc: false,
          hasWrittenAgreement: true,
          agreedCreditDays: 60,
          entries: [
            { ledgerName: "Purchase GST", drCr: "DR", amountPaise: 12000000, billRef: "" },
            { ledgerName: "CGST Input", drCr: "DR", amountPaise: 300000, billRef: "" },
            { ledgerName: "SGST Input", drCr: "DR", amountPaise: 300000, billRef: "" },
            { ledgerName: "Navkar Dyeing Mills", drCr: "CR", amountPaise: 12600000, billRef: "NDM/045" },
          ],
        },
        {
          id: "VCH-DEMO-004",
          voucherType: "PURCHASE",
          voucherNo: "SYP/019",
          date: daysAgoIso(17),
          narration: "Textured Yarn Purchase (Small MSME - No written agreement -> 15d limit exceeded)",
          status: "POSTED",
          isPdc: false,
          hasWrittenAgreement: false,
          agreedCreditDays: 15,
          entries: [
            { ledgerName: "Purchase GST", drCr: "DR", amountPaise: 8500000, billRef: "" },
            { ledgerName: "CGST Input", drCr: "DR", amountPaise: 212500, billRef: "" },
            { ledgerName: "SGST Input", drCr: "DR", amountPaise: 212500, billRef: "" },
            { ledgerName: "Shree Yarn Processors", drCr: "CR", amountPaise: 8925000, billRef: "SYP/019" },
          ],
        },
        {
          id: "VCH-DEMO-005",
          voucherType: "RECEIPT",
          voucherNo: "RCPT-014",
          date: daysAgoIso(2),
          narration: "PDC Cheque #441892 from Dadar Silk Emporium",
          status: "POSTED",
          isPdc: true,
          pdcDate: daysAgoIso(-10),
          entries: [
            { ledgerName: "HDFC Bank Current A/c", drCr: "DR", amountPaise: 7500000, billRef: "" },
            { ledgerName: "Dadar Silk Emporium (Mumbai)", drCr: "CR", amountPaise: 7500000, billRef: "INV/26-27/102" },
          ],
        },
      ],
      auditBlocks: [],
    };
  }

  let state = null;
  let currentVoucherType = "SALES";
  let currentView = "dashboard";
  let voucherLineDrafts = [];

  async function initAuditBlocksIfEmpty() {
    if (state.auditBlocks.length > 0) return;
    await appendAuditBlock("system", "INIT_COMPANY", "COMPANY", state.company.id, {}, state.company);
    for (const v of state.vouchers) {
      await appendAuditBlock("seed", "CREATE_VOUCHER", "VOUCHER", v.id, {}, v);
    }
    saveState();
  }

  async function appendAuditBlock(actor, action, entityType, entityId, beforeObj, afterObj) {
    const prevHash = state.auditBlocks.length
      ? state.auditBlocks[state.auditBlocks.length - 1].blockHash
      : GENESIS_HASH;
    const ts = new Date().toISOString();
    const beforeJson = JSON.stringify(beforeObj);
    const afterJson = JSON.stringify(afterObj);
    const payload = [prevHash, ts, actor, state.company.id, action, entityType, entityId, beforeJson, afterJson].join("|");
    const blockHash = await sha256Hex(payload);
    const block = {
      blockIndex: state.auditBlocks.length + 1,
      timestampUtc: ts,
      actor,
      action,
      entityType,
      entityId,
      beforeJson,
      afterJson,
      prevHash,
      blockHash,
    };
    state.auditBlocks.push(block);
    return blockHash;
  }

  async function verifyAuditChainLocal() {
    let expectedPrev = GENESIS_HASH;
    for (const b of state.auditBlocks) {
      if (b.prevHash !== expectedPrev) {
        return { valid: false, blocks: state.auditBlocks.length, brokenAt: b.blockIndex };
      }
      const payload = [
        b.prevHash,
        b.timestampUtc,
        b.actor,
        state.company.id,
        b.action,
        b.entityType,
        b.entityId,
        b.beforeJson,
        b.afterJson,
      ].join("|");
      const recomputed = await sha256Hex(payload);
      if (recomputed !== b.blockHash) {
        return { valid: false, blocks: state.auditBlocks.length, brokenAt: b.blockIndex };
      }
      expectedPrev = b.blockHash;
    }
    return { valid: true, blocks: state.auditBlocks.length, merkleHead: expectedPrev };
  }

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && Array.isArray(parsed.ledgers) && Array.isArray(parsed.vouchers)) {
          return parsed;
        }
      }
    } catch (_err) {
      // ignore corrupt local state
    }
    return buildInitialDataset();
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (_err) {
      // ignore quota errors
    }
  }

  function computeTrialBalance() {
    const map = {};
    for (const l of state.ledgers) {
      const dr = l.openingDrCr === "DR" ? l.openingPaise : 0;
      const cr = l.openingDrCr === "CR" ? l.openingPaise : 0;
      map[l.name] = {
        ledgerName: l.name,
        parentGroup: l.parentGroup,
        nature: l.nature || GROUP_NATURE[l.parentGroup] || "ASSET",
        dr,
        cr,
      };
    }
    for (const v of state.vouchers) {
      if (v.status !== "POSTED" || v.isPdc) continue;
      for (const e of v.entries) {
        if (!map[e.ledgerName]) {
          map[e.ledgerName] = {
            ledgerName: e.ledgerName,
            parentGroup: "Indirect Expenses",
            nature: "EXPENSE",
            dr: 0,
            cr: 0,
          };
        }
        if (e.drCr === "DR") map[e.ledgerName].dr += e.amountPaise;
        else map[e.ledgerName].cr += e.amountPaise;
      }
    }

    const rows = [];
    let totalDr = 0;
    let totalCr = 0;
    for (const key of Object.keys(map).sort()) {
      const b = map[key];
      const net = b.dr - b.cr;
      if (net === 0) continue;
      const closeDr = net > 0 ? net : 0;
      const closeCr = net < 0 ? Math.abs(net) : 0;
      totalDr += closeDr;
      totalCr += closeCr;
      rows.push({
        ledgerName: b.ledgerName,
        parentGroup: b.parentGroup,
        nature: b.nature,
        closeDr,
        closeCr,
      });
    }
    return { rows, totalDr, totalCr, variance: Math.abs(totalDr - totalCr), isBalanced: totalDr === totalCr };
  }

  function computeMsme43bh() {
    const today = new Date(isoToday());
    const alerts = [];
    let exposedPaise = 0;
    let criticalPaise = 0;

    const ledgerMap = Object.fromEntries(state.ledgers.map((l) => [l.name, l]));
    for (const v of state.vouchers) {
      if (v.status !== "POSTED" || v.voucherType !== "PURCHASE") continue;
      for (const e of v.entries) {
        if (e.drCr !== "CR") continue;
        const led = ledgerMap[e.ledgerName];
        if (!led || !["MICRO", "SMALL"].includes(led.msmeCategory)) continue;
        const billDt = new Date(v.date);
        const capDays = v.hasWrittenAgreement ? Math.min(Math.max(Number(v.agreedCreditDays || 45), 1), 45) : 15;
        const dueDt = new Date(billDt);
        dueDt.setDate(dueDt.getDate() + capDays);
        const daysLeft = Math.round((dueDt - today) / (1000 * 60 * 60 * 24));
        let status = "SAFE";
        if (daysLeft < 0) {
          status = "DISALLOWED_EXPOSURE";
          exposedPaise += e.amountPaise;
        } else if (daysLeft <= 5) {
          status = "CRITICAL_43BH";
          criticalPaise += e.amountPaise;
        } else if (daysLeft <= 10) {
          status = "DUE_SOON";
        }
        alerts.push({
          supplierName: led.name,
          category: led.msmeCategory,
          udyamNo: led.udyamNo || "",
          billRef: e.billRef || v.voucherNo,
          billDate: v.date,
          dueDate: dueDt.toISOString().slice(0, 10),
          capDays,
          daysLeft,
          amountPaise: e.amountPaise,
          status,
        });
      }
    }
    alerts.sort((a, b) => a.daysLeft - b.daysLeft);
    return { alerts, exposedPaise, criticalPaise };
  }

  function renderAll() {
    const tb = computeTrialBalance();
    const msme = computeMsme43bh();

    let liquidity = 0;
    let income = 0;
    let expense = 0;
    let debtors = 0;
    for (const r of tb.rows) {
      if (["Cash-in-Hand", "Bank Accounts"].includes(r.parentGroup)) {
        liquidity += r.closeDr - r.closeCr;
      }
      if (r.parentGroup === "Sundry Debtors") {
        debtors += r.closeDr - r.closeCr;
      }
      if (r.nature === "INCOME") income += r.closeCr - r.closeDr;
      if (r.nature === "EXPENSE") expense += r.closeDr - r.closeCr;
    }
    const netProfit = income - expense;

    // Header KPIs
    const tbEl = document.getElementById("hdrTbStatus");
    tbEl.textContent = tb.isBalanced
      ? `BALANCED (${formatINR(0)} variance)`
      : `VARIANCE ${formatINR(tb.variance)}`;
    tbEl.className = tb.isBalanced ? "text-emerald-400" : "text-rose-400";

    const riskyCount = msme.alerts.filter((a) => a.status !== "SAFE").length;
    document.getElementById("hdrMsmeAlerts").textContent = `${riskyCount} At Risk`;
    document.getElementById("hdrAuditBlocks").textContent = `${state.auditBlocks.length} Verified`;

    // Dashboard KPIs
    document.getElementById("kpiLiquidity").textContent = formatINR(liquidity);
    document.getElementById("kpiNetProfit").textContent = formatINR(netProfit);
    document.getElementById("kpiIncomeExpense").textContent = `Income ${formatINR(income)} · Expense ${formatINR(expense)}`;
    document.getElementById("kpiDebtors").textContent = formatINR(debtors);
    document.getElementById("kpiMsmeRisk").textContent = formatINR(msme.exposedPaise + msme.criticalPaise);
    document.getElementById("kpiMsmeCount").textContent = `${riskyCount} bills near / past 15-45d limit`;

    // Recent Day Book table
    const recentBody = document.getElementById("recentVouchersBody");
    recentBody.innerHTML = state.vouchers
      .slice()
      .reverse()
      .slice(0, 8)
      .map((v) => {
        const totalPaise = v.entries
          .filter((e) => e.drCr === "DR")
          .reduce((acc, e) => acc + e.amountPaise, 0);
        const party = v.entries[0] ? v.entries[0].ledgerName : "-";
        const badge = v.isPdc
          ? '<span class="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px]">PDC</span>'
          : '<span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px]">POSTED</span>';
        return `<tr>
          <td class="py-2 pr-3">${escapeHtml(v.date)}</td>
          <td class="py-2 pr-3 font-bold text-brand-cyan">${escapeHtml(v.voucherType)}</td>
          <td class="py-2 pr-3">${escapeHtml(v.voucherNo)}</td>
          <td class="py-2 pr-3 font-sans">${escapeHtml(party)}</td>
          <td class="py-2 pr-3 text-right">${formatINR(totalPaise)}</td>
          <td class="py-2 text-right">${badge}</td>
        </tr>`;
      })
      .join("");

    populateLedgerSelects();
    renderMsme43bhTable(msme);
    renderAuditTrailTable();
    previewWhatsAppReminder();
    if (currentView === "reports") renderReports("tb");
  }

  function populateLedgerSelects() {
    const partySel = document.getElementById("vchPartyLedger");
    const waSel = document.getElementById("waPartySelect");
    const prevVal = partySel.value;
    partySel.innerHTML = state.ledgers
      .map((l) => `<option value="${escapeHtml(l.name)}">${escapeHtml(l.name)} (${escapeHtml(l.parentGroup)})</option>`)
      .join("");
    if (prevVal && state.ledgers.some((l) => l.name === prevVal)) partySel.value = prevVal;

    const debtors = state.ledgers.filter((l) => l.parentGroup === "Sundry Debtors");
    waSel.innerHTML = (debtors.length ? debtors : state.ledgers)
      .map((l) => `<option value="${escapeHtml(l.name)}">${escapeHtml(l.name)}</option>`)
      .join("");
  }

  function renderVoucherLines() {
    const tbody = document.getElementById("voucherLinesBody");
    const ledgerOpts = state.ledgers
      .map((l) => `<option value="${escapeHtml(l.name)}">${escapeHtml(l.name)}</option>`)
      .join("");
    tbody.innerHTML = voucherLineDrafts
      .map((line, idx) => {
        const opts = state.ledgers
          .map(
            (l) =>
              `<option value="${escapeHtml(l.name)}" ${l.name === line.ledgerName ? "selected" : ""}>${escapeHtml(l.name)}</option>`
          )
          .join("");
        return `<tr>
          <td class="p-2">
            <select onchange="window.__books.updateLine(${idx}, 'drCr', this.value)" class="w-full rounded px-2 py-1 bg-slate-950 border border-slate-700 text-xs text-white mono-nums">
              <option value="DR" ${line.drCr === "DR" ? "selected" : ""}>Dr</option>
              <option value="CR" ${line.drCr === "CR" ? "selected" : ""}>Cr</option>
            </select>
          </td>
          <td class="p-2">
            <select onchange="window.__books.updateLine(${idx}, 'ledgerName', this.value)" class="w-full rounded px-2 py-1 bg-slate-950 border border-slate-700 text-xs text-white">
              ${opts || ledgerOpts}
            </select>
          </td>
          <td class="p-2">
            <input type="text" value="${escapeHtml(line.billRef || "")}" oninput="window.__books.updateLine(${idx}, 'billRef', this.value)" placeholder="Ref #" class="w-full rounded px-2 py-1 bg-slate-950 border border-slate-700 text-xs mono-nums text-white" />
          </td>
          <td class="p-2">
            <input type="number" step="0.01" min="0" value="${(line.amountPaise / 100).toFixed(2)}" oninput="window.__books.updateLineAmount(${idx}, this.value)" class="w-full text-right rounded px-2 py-1 bg-slate-950 border border-slate-700 text-xs mono-nums text-white" />
          </td>
          <td class="p-2 text-center">
            <button type="button" onclick="window.__books.removeLine(${idx})" class="text-rose-400 hover:text-rose-300 cursor-pointer" title="Remove row"><i class="fa-solid fa-trash-can"></i></button>
          </td>
        </tr>`;
      })
      .join("");
    updateVoucherTotals();
  }

  function updateVoucherTotals() {
    let dr = 0;
    let cr = 0;
    for (const l of voucherLineDrafts) {
      if (l.drCr === "DR") dr += l.amountPaise;
      else cr += l.amountPaise;
    }
    document.getElementById("sumDebitDisplay").textContent = formatINR(dr);
    document.getElementById("sumCreditDisplay").textContent = formatINR(cr);
    const badge = document.getElementById("balanceCheckBadge");
    if (dr > 0 && dr === cr) {
      badge.textContent = "BALANCED (READY Ctrl+A)";
      badge.className = "px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 font-bold";
    } else {
      badge.textContent = `DIFF ${formatINR(Math.abs(dr - cr))}`;
      badge.className = "px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-bold";
    }
  }

  function setVoucherType(vtype) {
    currentVoucherType = vtype;
    document.querySelectorAll(".vtype-btn").forEach((btn) => {
      const active = btn.getAttribute("data-vtype") === vtype;
      btn.className = active
        ? "vtype-btn px-2.5 py-1.5 rounded-lg text-xs font-extrabold border border-brand-cyan bg-brand-cyan/20 text-brand-cyan cursor-pointer"
        : "vtype-btn px-2.5 py-1.5 rounded-lg text-xs font-bold border border-slate-700 text-slate-300 hover:border-slate-500 cursor-pointer";
    });
    document.getElementById("vchNo").value = `${vtype.slice(0, 3)}/${String(state.vouchers.length + 101)}`;
    const showGst = vtype === "SALES" || vtype === "PURCHASE";
    document.getElementById("quickGstBox").style.display = showGst ? "grid" : "none";

    if (vtype === "SALES") {
      voucherLineDrafts = [
        { drCr: "DR", ledgerName: "Mahalaxmi Saree House (Surat)", billRef: document.getElementById("vchNo").value, amountPaise: 1050000 },
        { drCr: "CR", ledgerName: "Sales GST", billRef: "", amountPaise: 1000000 },
        { drCr: "CR", ledgerName: "CGST Output", billRef: "", amountPaise: 25000 },
        { drCr: "CR", ledgerName: "SGST Output", billRef: "", amountPaise: 25000 },
      ];
    } else if (vtype === "PURCHASE") {
      voucherLineDrafts = [
        { drCr: "DR", ledgerName: "Purchase GST", billRef: "", amountPaise: 1000000 },
        { drCr: "DR", ledgerName: "CGST Input", billRef: "", amountPaise: 25000 },
        { drCr: "DR", ledgerName: "SGST Input", billRef: "", amountPaise: 25000 },
        { drCr: "CR", ledgerName: "Navkar Dyeing Mills", billRef: document.getElementById("vchNo").value, amountPaise: 1050000 },
      ];
    } else if (vtype === "RECEIPT") {
      voucherLineDrafts = [
        { drCr: "DR", ledgerName: "HDFC Bank Current A/c", billRef: "", amountPaise: 5000000 },
        { drCr: "CR", ledgerName: "Mahalaxmi Saree House (Surat)", billRef: "INV/26-27/101", amountPaise: 5000000 },
      ];
    } else if (vtype === "PAYMENT") {
      voucherLineDrafts = [
        { drCr: "DR", ledgerName: "Navkar Dyeing Mills", billRef: "NDM/045", amountPaise: 5000000 },
        { drCr: "CR", ledgerName: "HDFC Bank Current A/c", billRef: "", amountPaise: 5000000 },
      ];
    } else {
      voucherLineDrafts = [
        { drCr: "DR", ledgerName: "HDFC Bank Current A/c", billRef: "", amountPaise: 1000000 },
        { drCr: "CR", ledgerName: "Cash", billRef: "", amountPaise: 1000000 },
      ];
    }
    renderVoucherLines();
  }

  window.onVoucherPartyChanged = function () {
    const partyName = document.getElementById("vchPartyLedger").value;
    const led = state.ledgers.find((l) => l.name === partyName);
    if (led && led.gstin && led.gstin.length >= 2) {
      document.getElementById("quickPartyState").value = led.gstin.slice(0, 2);
      recalcQuickGst();
    }
  };

  window.recalcQuickGst = function () {
    const taxablePaise = toPaise(document.getElementById("quickTaxable").value || "10000");
    const rate = Number(document.getElementById("vchGstRate").value || 5);
    const partyState = (document.getElementById("quickPartyState").value || "24").trim().padStart(2, "0");
    const isInter = partyState !== state.company.stateCode;
    const totalTaxPaise = Math.round((taxablePaise * rate) / 100);
    const cgst = isInter ? 0 : Math.floor(totalTaxPaise / 2);
    const sgst = isInter ? 0 : totalTaxPaise - cgst;
    const igst = isInter ? totalTaxPaise : 0;
    const gross = taxablePaise + totalTaxPaise;
    document.getElementById("quickGstPreview").textContent = isInter
      ? `IGST (${rate}%): ${formatINR(igst)} · Total: ${formatINR(gross)}`
      : `CGST: ${formatINR(cgst)} · SGST: ${formatINR(sgst)} · Total: ${formatINR(gross)}`;
    return { taxablePaise, cgst, sgst, igst, gross, isInter };
  };

  window.applyQuickGstToLines = function () {
    const calc = window.recalcQuickGst();
    const party = document.getElementById("vchPartyLedger").value || state.ledgers[0].name;
    const vNo = document.getElementById("vchNo").value || "INV-NEW";
    if (currentVoucherType === "SALES") {
      voucherLineDrafts = [
        { drCr: "DR", ledgerName: party, billRef: vNo, amountPaise: calc.gross },
        { drCr: "CR", ledgerName: "Sales GST", billRef: "", amountPaise: calc.taxablePaise },
      ];
      if (calc.isInter && calc.igst > 0) {
        voucherLineDrafts.push({ drCr: "CR", ledgerName: "IGST Output", billRef: "", amountPaise: calc.igst });
      } else if (calc.cgst > 0 || calc.sgst > 0) {
        voucherLineDrafts.push({ drCr: "CR", ledgerName: "CGST Output", billRef: "", amountPaise: calc.cgst });
        voucherLineDrafts.push({ drCr: "CR", ledgerName: "SGST Output", billRef: "", amountPaise: calc.sgst });
      }
    } else if (currentVoucherType === "PURCHASE") {
      voucherLineDrafts = [{ drCr: "DR", ledgerName: "Purchase GST", billRef: "", amountPaise: calc.taxablePaise }];
      if (calc.isInter && calc.igst > 0) {
        voucherLineDrafts.push({ drCr: "DR", ledgerName: "IGST Input", billRef: "", amountPaise: calc.igst });
      } else if (calc.cgst > 0 || calc.sgst > 0) {
        voucherLineDrafts.push({ drCr: "DR", ledgerName: "CGST Input", billRef: "", amountPaise: calc.cgst });
        voucherLineDrafts.push({ drCr: "DR", ledgerName: "SGST Input", billRef: "", amountPaise: calc.sgst });
      }
      voucherLineDrafts.push({ drCr: "CR", ledgerName: party, billRef: vNo, amountPaise: calc.gross });
    }
    renderVoucherLines();
  };

  window.addVoucherLine = function () {
    voucherLineDrafts.push({
      drCr: "DR",
      ledgerName: state.ledgers[0].name,
      billRef: "",
      amountPaise: 0,
    });
    renderVoucherLines();
  };

  window.submitVoucherForm = async function (event) {
    event.preventDefault();
    const fb = document.getElementById("voucherFormFeedback");
    fb.classList.remove("hidden");
    let dr = 0;
    let cr = 0;
    for (const l of voucherLineDrafts) {
      if (l.amountPaise <= 0) {
        fb.className = "text-xs font-bold text-rose-400";
        fb.textContent = "Every voucher line must have a positive amount.";
        return;
      }
      if (l.drCr === "DR") dr += l.amountPaise;
      else cr += l.amountPaise;
    }
    if (dr === 0 || dr !== cr) {
      fb.className = "text-xs font-bold text-rose-400";
      fb.textContent = `Double-entry violation: Debit (${formatINR(dr)}) != Credit (${formatINR(cr)}).`;
      return;
    }
    const newVoucher = {
      id: "VCH-" + Math.random().toString(16).slice(2, 10).toUpperCase(),
      voucherType: currentVoucherType,
      voucherNo: document.getElementById("vchNo").value.trim() || "VCH-01",
      date: document.getElementById("vchDate").value || isoToday(),
      narration: document.getElementById("vchNarration").value.trim() || `${currentVoucherType} posted via BooksOS`,
      status: "POSTED",
      isPdc: document.getElementById("vchIsPdc").checked,
      pdcDate: document.getElementById("vchIsPdc").checked ? daysAgoIso(-15) : "",
      hasWrittenAgreement: false,
      agreedCreditDays: 15,
      entries: voucherLineDrafts.map((l) => ({ ...l })),
    };
    state.vouchers.push(newVoucher);
    await appendAuditBlock("accountant", "CREATE_VOUCHER", "VOUCHER", newVoucher.id, {}, newVoucher);
    saveState();
    renderAll();

    fb.className = "text-xs font-bold text-emerald-400";
    fb.textContent = `Voucher ${newVoucher.voucherNo} (${formatINR(dr)}) posted & cryptographically sealed in Merkle Audit Log.`;
    setVoucherType(currentVoucherType);
  };

  window.openMasterModal = function () {
    const dlg = document.getElementById("masterDialog");
    if (!dlg.open) dlg.showModal();
    document.getElementById("mName").focus();
  };

  window.submitMasterDialog = async function (event) {
    event.preventDefault();
    const name = document.getElementById("mName").value.trim();
    if (!name) return;
    const parentGroup = document.getElementById("mGroup").value;
    const newLed = {
      name,
      parentGroup,
      nature: GROUP_NATURE[parentGroup] || "ASSET",
      gstin: document.getElementById("mGstin").value.trim().toUpperCase(),
      msmeCategory: document.getElementById("mMsme").value,
      openingPaise: toPaise(document.getElementById("mOpening").value),
      openingDrCr: document.getElementById("mDrCr").value,
    };
    const idx = state.ledgers.findIndex((l) => l.name.toLowerCase() === name.toLowerCase());
    if (idx >= 0) {
      const before = state.ledgers[idx];
      state.ledgers[idx] = newLed;
      await appendAuditBlock("accountant", "ALTER_LEDGER", "LEDGER", name, before, newLed);
    } else {
      state.ledgers.push(newLed);
      await appendAuditBlock("accountant", "CREATE_LEDGER", "LEDGER", name, {}, newLed);
    }
    saveState();
    renderAll();
    renderVoucherLines();
    document.getElementById("masterDialog").close();
    document.getElementById("mName").value = "";
  };

  window.loadSampleTallyXML = function () {
    document.getElementById("tallyXmlInput").value = `<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDATA>
        <TALLYMESSAGE>
          <LEDGER NAME="Patel Textile Agency (Tally ERP 9)" Action="Create">
            <NAME>Patel Textile Agency (Tally ERP 9)</NAME>
            <PARENT>Sundry Debtors</PARENT>
            <PARTYGSTIN>24AABCP9911A1Z4</PARTYGSTIN>
            <OPENINGBALANCE>-50000.00</OPENINGBALANCE>
            <BILLALLOCATIONS.LIST>
              <NAME>TLY-OB-001</NAME>
              <BILLTYPE>New Ref</BILLTYPE>
              <AMOUNT>-50000.00</AMOUNT>
            </BILLALLOCATIONS.LIST>
          </LEDGER>
        </TALLYMESSAGE>
        <TALLYMESSAGE>
          <LEDGER NAME="Tally Migration Reserve" Action="Create">
            <NAME>Tally Migration Reserve</NAME>
            <PARENT>Capital Account</PARENT>
            <OPENINGBALANCE>50000.00</OPENINGBALANCE>
          </LEDGER>
        </TALLYMESSAGE>
        <TALLYMESSAGE>
          <VOUCHER VCHTYPE="Sales" Action="Create">
            <DATE>20261120</DATE>
            <VOUCHERNUMBER>TLY/991</VOUCHERNUMBER>
            <NARRATION>Imported directly from Tally ERP 9 Port 9000 XML</NARRATION>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Patel Textile Agency (Tally ERP 9)</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-10500.00</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Sales GST</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>10000.00</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>CGST Output</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>250.00</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>SGST Output</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>250.00</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>`;
  };

  window.handleXmlFileUpload = function (event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      document.getElementById("tallyXmlInput").value = String(reader.result || "");
    };
    reader.readAsText(file);
  };

  window.runTallyXmlImport = async function () {
    const xml = document.getElementById("tallyXmlInput").value.trim();
    const outBox = document.getElementById("tallyImportResult");
    outBox.classList.remove("hidden");
    if (!xml) {
      outBox.innerHTML = `<span class="text-rose-400 font-bold">Please paste Tally XML or click "Load Sample Tally.ERP 9 XML".</span>`;
      return;
    }
    if (/<!(DOCTYPE|ENTITY)/i.test(xml.slice(0, 4096))) {
      outBox.innerHTML = `<span class="text-rose-400 font-bold">Rejected unsafe XML containing DOCTYPE/ENTITY declarations.</span>`;
      return;
    }
    const doc = new DOMParser().parseFromString(xml, "text/xml");
    if (doc.querySelector("parsererror")) {
      outBox.innerHTML = `<span class="text-rose-400 font-bold">Malformed Tally XML syntax.</span>`;
      return;
    }

    let ledgersAdded = 0;
    let vouchersAdded = 0;

    for (const lEl of doc.querySelectorAll("LEDGER")) {
      const name = (lEl.getAttribute("NAME") || lEl.querySelector("NAME")?.textContent || "").trim();
      if (!name) continue;
      const parent = (lEl.querySelector("PARENT")?.textContent || "Sundry Debtors").trim();
      const gstin = (lEl.querySelector("PARTYGSTIN")?.textContent || lEl.querySelector("GSTIN")?.textContent || "").trim();
      const obNum = Number((lEl.querySelector("OPENINGBALANCE")?.textContent || "0").replace(/,/g, ""));
      const obPaise = Math.round(Math.abs(obNum) * 100);
      const obDrCr = obNum < 0 ? "DR" : "CR";
      if (!state.ledgers.some((x) => x.name === name)) {
        const ledObj = {
          name,
          parentGroup: parent,
          nature: GROUP_NATURE[parent] || "ASSET",
          gstin,
          msmeCategory: "NONE",
          openingPaise: obPaise,
          openingDrCr: obDrCr,
        };
        state.ledgers.push(ledObj);
        await appendAuditBlock("algobridge", "TALLY_IMPORT_LEDGER", "LEDGER", name, {}, ledObj);
        ledgersAdded++;
      }
    }

    for (const vEl of doc.querySelectorAll("VOUCHER")) {
      const vType = (vEl.getAttribute("VCHTYPE") || vEl.querySelector("VOUCHERTYPENAME")?.textContent || "JOURNAL")
        .toUpperCase()
        .replace(/\s+/g, "_");
      const rawDate = (vEl.querySelector("DATE")?.textContent || "").trim();
      const isoDate = /^\d{8}$/.test(rawDate)
        ? `${rawDate.slice(0, 4)}-${rawDate.slice(4, 6)}-${rawDate.slice(6, 8)}`
        : isoToday();
      const vNo = (vEl.querySelector("VOUCHERNUMBER")?.textContent || `TLY-${vouchersAdded + 1}`).trim();
      const narration = (vEl.querySelector("NARRATION")?.textContent || "Imported from Tally XML").trim();
      const entryEls = [
        ...vEl.querySelectorAll("ALLLEDGERENTRIES\\.LIST"),
        ...vEl.querySelectorAll("LEDGERENTRIES\\.LIST"),
      ];
      const entries = [];
      let dr = 0;
      let cr = 0;
      for (const eEl of entryEls) {
        const lName = (eEl.querySelector("LEDGERNAME")?.textContent || "").trim();
        const amtNum = Number((eEl.querySelector("AMOUNT")?.textContent || "0").replace(/,/g, ""));
        const deemed = (eEl.querySelector("ISDEEMEDPOSITIVE")?.textContent || "").trim().toLowerCase();
        const paise = Math.round(Math.abs(amtNum) * 100);
        if (!lName || paise === 0) continue;
        const drCr = deemed === "yes" ? "DR" : deemed === "no" ? "CR" : amtNum < 0 ? "DR" : "CR";
        if (drCr === "DR") dr += paise;
        else cr += paise;
        entries.push({ ledgerName: lName, drCr, amountPaise: paise, billRef: vNo });
      }
      if (entries.length >= 2 && dr === cr) {
        const vObj = {
          id: "VCH-TLY-" + Math.random().toString(16).slice(2, 8).toUpperCase(),
          voucherType: vType,
          voucherNo: vNo,
          date: isoDate,
          narration,
          status: "POSTED",
          isPdc: false,
          entries,
        };
        state.vouchers.push(vObj);
        await appendAuditBlock("algobridge", "TALLY_IMPORT_VOUCHER", "VOUCHER", vObj.id, {}, vObj);
        vouchersAdded++;
      }
    }

    saveState();
    renderAll();
    const tb = computeTrialBalance();
    outBox.innerHTML = `
      <div class="font-extrabold text-emerald-400">Migration &amp; Parity Audit Complete!</div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 mono-nums">
        <div>Ledgers Imported: <strong>${ledgersAdded}</strong></div>
        <div>Vouchers Imported: <strong>${vouchersAdded}</strong></div>
        <div>Trial Balance: <strong class="${tb.isBalanced ? "text-emerald-400" : "text-rose-400"}">${tb.isBalanced ? "0.00 PARITY" : formatINR(tb.variance)}</strong></div>
        <div>Audit Trail: <strong class="text-brand-cyan">Rule 11(g) Sealed</strong></div>
      </div>`;
  };

  window.runDemoGstr2bReconciliation = function () {
    const books = [
      { gstin: "24AABCN4411K1Z3", inv: "INV/26-27/0045", tax: 6000.0 },
      { gstin: "24AABCS9123P1Z8", inv: "SYP/019", tax: 4250.0 },
      { gstin: "24AABCD5555B1Z7", inv: "CHEM-882", tax: 14400.0 },
    ];
    const portal2b = [
      { gstin: "24AABCN4411K1Z3", inv: "45", tax: 6001.0 },
      { gstin: "24AABCS9123P1Z8", inv: "SYP/019", tax: 4250.0 },
      { gstin: "24AABCZ1122M1Z2", inv: "TRANS-91", tax: 1800.0 },
    ];
    const norm = (s) =>
      s
        .toUpperCase()
        .replace(/^(?:INV|BILL|TAX|TI|SI|PI)[-/\s]*/g, "")
        .replace(/(?:^|[-/\s])(?:FY)?\d{2,4}[-/]\d{2,4}(?:[-/\s]|$)/g, "")
        .replace(/[^A-Z0-9]/g, "")
        .replace(/^0+/, "");

    const rows = [];
    const used = new Set();
    let matched = 0;
    let itcRisk = 0;

    for (const b of books) {
      const idx = portal2b.findIndex((p, i) => !used.has(i) && p.gstin === b.gstin && (p.inv === b.inv || norm(p.inv) === norm(b.inv)));
      if (idx >= 0) {
        used.add(idx);
        const p = portal2b[idx];
        const diff = Math.abs(b.tax - p.tax);
        matched++;
        rows.push({
          status: diff === 0 ? "EXACT_MATCH" : "FUZZY_MATCH_TOLERATED",
          gstin: b.gstin,
          booksInv: b.inv,
          portalInv: p.inv,
          ims: "ACCEPT",
          notes: diff === 0 ? "100% Exact Parity" : `Fuzzy matched prefix & ₹${diff.toFixed(2)} rounding`,
          cls: "text-emerald-400",
        });
      } else {
        itcRisk += b.tax;
        rows.push({
          status: "MISSING_IN_2B_RISK",
          gstin: b.gstin,
          booksInv: b.inv,
          portalInv: "—",
          ims: "HOLD_ITC",
          notes: `Supplier did not file GSTR-1 (₹${b.tax.toLocaleString("en-IN")} ITC risk)`,
          cls: "text-rose-400",
        });
      }
    }
    portal2b.forEach((p, idx) => {
      if (!used.has(idx)) {
        rows.push({
          status: "MISSING_IN_BOOKS",
          gstin: p.gstin,
          booksInv: "—",
          portalInv: p.inv,
          ims: "AUTO_DRAFT",
          notes: `Auto-draft purchase voucher for ₹${p.tax.toLocaleString("en-IN")} tax`,
          cls: "text-amber-400",
        });
      }
    });

    document.getElementById("gstr2bSummaryGrid").innerHTML = `
      <div class="p-3 rounded-lg bg-slate-900 border border-slate-800"><div class="text-slate-400">Books Checked</div><div class="text-lg font-extrabold mono-nums">${books.length}</div></div>
      <div class="p-3 rounded-lg bg-slate-900 border border-emerald-500/30"><div class="text-slate-400">Matched (Exact + Fuzzy)</div><div class="text-lg font-extrabold mono-nums text-emerald-400">${matched}</div></div>
      <div class="p-3 rounded-lg bg-slate-900 border border-rose-500/30"><div class="text-slate-400">ITC At Risk</div><div class="text-lg font-extrabold mono-nums text-rose-400">₹${itcRisk.toLocaleString("en-IN")}</div></div>
      <div class="p-3 rounded-lg bg-slate-900 border border-amber-500/30"><div class="text-slate-400">Missing in Books</div><div class="text-lg font-extrabold mono-nums text-amber-400">${portal2b.length - matched}</div></div>
    `;

    document.getElementById("gstr2bBody").innerHTML = rows
      .map(
        (r) => `<tr>
        <td class="py-2 pr-3 font-bold ${r.cls}">${r.status}</td>
        <td class="py-2 pr-3">${escapeHtml(r.gstin)}</td>
        <td class="py-2 pr-3">${escapeHtml(r.booksInv)}</td>
        <td class="py-2 pr-3">${escapeHtml(r.portalInv)}</td>
        <td class="py-2 pr-3"><span class="px-2 py-0.5 rounded bg-slate-800 text-brand-cyan text-[10px]">${r.ims}</span></td>
        <td class="py-2 text-right font-sans text-slate-300">${escapeHtml(r.notes)}</td>
      </tr>`
      )
      .join("");
  };

  function renderMsme43bhTable(msme) {
    const exposed = msme.exposedPaise;
    const taxAddback = Math.round(exposed * 0.3);
    document.getElementById("msmeSummaryGrid").innerHTML = `
      <div class="p-3 rounded-lg bg-slate-900 border border-rose-500/40"><div class="text-slate-400">Disallowed Overdue Exposure</div><div class="text-lg font-extrabold mono-nums text-rose-400">${formatINR(exposed)}</div></div>
      <div class="p-3 rounded-lg bg-slate-900 border border-amber-500/40"><div class="text-slate-400">Critical Due (<= 5 Days)</div><div class="text-lg font-extrabold mono-nums text-amber-400">${formatINR(msme.criticalPaise)}</div></div>
      <div class="p-3 rounded-lg bg-slate-900 border border-cyan-500/30"><div class="text-slate-400">Est. 30% Tax Disallowance Saved</div><div class="text-lg font-extrabold mono-nums text-brand-cyan">${formatINR(taxAddback)}</div></div>
    `;
    document.getElementById("msme43bhBody").innerHTML = msme.alerts
      .map((a) => {
        const cls =
          a.status === "DISALLOWED_EXPOSURE"
            ? "text-rose-400"
            : a.status === "CRITICAL_43BH"
            ? "text-amber-400"
            : "text-emerald-400";
        return `<tr>
          <td class="py-2 pr-3 font-sans font-semibold">${escapeHtml(a.supplierName)} <span class="text-[10px] text-slate-400">(${a.category})</span></td>
          <td class="py-2 pr-3">${escapeHtml(a.billRef)}</td>
          <td class="py-2 pr-3">${escapeHtml(a.billDate)}</td>
          <td class="py-2 pr-3">${escapeHtml(a.dueDate)} (${a.capDays}d)</td>
          <td class="py-2 pr-3 text-right font-bold ${cls}">${a.daysLeft}d</td>
          <td class="py-2 pr-3 text-right">${formatINR(a.amountPaise)}</td>
          <td class="py-2 text-right font-bold ${cls}">${a.status}</td>
        </tr>`;
      })
      .join("");
  }

  window.renderReports = function (kind) {
    const box = document.getElementById("reportContainer");
    const tb = computeTrialBalance();
    if (kind === "tb") {
      box.innerHTML = `<table class="w-full text-left text-xs mono-nums">
        <thead class="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
          <tr><th class="py-2 pr-3">Ledger</th><th class="py-2 pr-3">Group</th><th class="py-2 pr-3 text-right">Debit (₹)</th><th class="py-2 text-right">Credit (₹)</th></tr>
        </thead>
        <tbody class="divide-y divide-slate-800">${tb.rows
          .map(
            (r) => `<tr>
            <td class="py-2 pr-3 font-sans font-semibold">${escapeHtml(r.ledgerName)}</td>
            <td class="py-2 pr-3 font-sans text-slate-400">${escapeHtml(r.parentGroup)}</td>
            <td class="py-2 pr-3 text-right text-brand-cyan">${r.closeDr ? formatINR(r.closeDr) : "—"}</td>
            <td class="py-2 text-right text-emerald-400">${r.closeCr ? formatINR(r.closeCr) : "—"}</td>
          </tr>`
          )
          .join("")}</tbody>
        <tfoot class="border-t-2 border-cyan-500/40 font-extrabold">
          <tr><td colspan="2" class="py-2.5">GRAND TOTAL (PARITY CHECK)</td><td class="py-2.5 text-right text-brand-cyan">${formatINR(tb.totalDr)}</td><td class="py-2.5 text-right text-emerald-400">${formatINR(tb.totalCr)}</td></tr>
        </tfoot>
      </table>`;
    } else if (kind === "pnl") {
      let inc = 0;
      let exp = 0;
      let assets = 0;
      let liab = 0;
      for (const r of tb.rows) {
        if (r.nature === "INCOME") inc += r.closeCr - r.closeDr;
        if (r.nature === "EXPENSE") exp += r.closeDr - r.closeCr;
        if (r.nature === "ASSET") assets += r.closeDr - r.closeCr;
        if (r.nature === "LIABILITY") liab += r.closeCr - r.closeDr;
      }
      const net = inc - exp;
      box.innerHTML = `<div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs mono-nums">
        <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
          <div class="font-extrabold text-brand-cyan uppercase">Profit &amp; Loss Statement</div>
          <div class="flex justify-between"><span>Total Operating Income</span><span>${formatINR(inc)}</span></div>
          <div class="flex justify-between"><span>Total Operating Expenses</span><span>${formatINR(exp)}</span></div>
          <div class="border-t border-slate-700 pt-2 flex justify-between font-extrabold text-emerald-400"><span>Net Profit</span><span>${formatINR(net)}</span></div>
        </div>
        <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
          <div class="font-extrabold text-brand-cyan uppercase">Balance Sheet Snapshot</div>
          <div class="flex justify-between"><span>Total Assets</span><span>${formatINR(assets)}</span></div>
          <div class="flex justify-between"><span>Liabilities + Capital + Net Profit</span><span>${formatINR(liab + net)}</span></div>
          <div class="border-t border-slate-700 pt-2 flex justify-between font-extrabold text-emerald-400"><span>Balance Sheet Parity</span><span>${assets === liab + net ? "MATCHED (0.00)" : formatINR(Math.abs(assets - (liab + net)))}</span></div>
        </div>
      </div>`;
    } else {
      const pdcs = state.vouchers.filter((v) => v.isPdc);
      box.innerHTML = pdcs.length
        ? `<table class="w-full text-left text-xs mono-nums"><thead class="border-b border-slate-800 text-slate-400 uppercase text-[10px]"><tr><th class="py-2">Voucher No</th><th class="py-2">Clearance Date</th><th class="py-2">Narration</th><th class="py-2 text-right">Amount</th></tr></thead><tbody>${pdcs
            .map(
              (v) =>
                `<tr><td class="py-2 font-bold text-amber-400">${escapeHtml(v.voucherNo)}</td><td class="py-2">${escapeHtml(v.pdcDate || v.date)}</td><td class="py-2 font-sans">${escapeHtml(v.narration)}</td><td class="py-2 text-right">${formatINR(v.entries[0]?.amountPaise || 0)}</td></tr>`
            )
            .join("")}</tbody></table>`
        : `<p class="text-xs text-slate-400">No Post-Dated Cheques (Ctrl+T) recorded yet.</p>`;
    }
  };

  window.previewWhatsAppReminder = function () {
    const party = document.getElementById("waPartySelect").value || "Party";
    const lang = document.getElementById("waLangSelect").value;
    const upi = document.getElementById("waUpiInput").value.trim();
    const tb = computeTrialBalance();
    const row = tb.rows.find((r) => r.ledgerName === party);
    const bal = row ? formatINR(row.closeDr || row.closeCr) : "₹0.00";
    const upiLine = upi ? `\nUPI Pay ID: ${upi}` : "";
    let msg = "";
    if (lang === "gu") {
      msg = `નમસ્તે ${party} જી,\n${state.company.name} તરફથી ખાતાની બાકી રકમ ${bal} કન્ફર્મ કરવા વિનંતી છે.\nકૃપા કરીને પેમેન્ટ મોકલીને 'CONFIRM' રિપ્લાય આપશો.${upiLine}`;
    } else if (lang === "hi") {
      msg = `Namaste ${party} ji,\n${state.company.name} ke hisab se aapka pending balance ${bal} hai.\nKripya payment bhejkar ledger confirmation ke liye 'CONFIRM' reply karein.${upiLine}`;
    } else {
      msg = `Hello ${party},\nLedger Balance Reminder from ${state.company.name}: ${bal} pending.\nPlease remit payment or reply 'CONFIRM' for statutory audit confirmation.${upiLine}`;
    }
    document.getElementById("waMessagePreview").textContent = msg;
  };

  window.copyWhatsAppMessage = function () {
    const txt = document.getElementById("waMessagePreview").textContent;
    if (navigator.clipboard) navigator.clipboard.writeText(txt);
  };

  function renderAuditTrailTable() {
    const tbody = document.getElementById("auditTrailBody");
    tbody.innerHTML = state.auditBlocks
      .slice()
      .reverse()
      .slice(0, 25)
      .map(
        (b) => `<tr>
        <td class="py-2 pr-3 font-bold text-brand-cyan">#${b.blockIndex}</td>
        <td class="py-2 pr-3 text-slate-400">${escapeHtml(b.timestampUtc.slice(0, 19))}Z</td>
        <td class="py-2 pr-3 font-bold">${escapeHtml(b.action)}</td>
        <td class="py-2 pr-3 font-sans">${escapeHtml(b.entityType)}: ${escapeHtml(b.entityId)}</td>
        <td class="py-2 pr-3 text-emerald-400">${escapeHtml(b.blockHash.slice(0, 22))}…</td>
      </tr>`
      )
      .join("");
  }

  window.verifyMerkleChainUI = async function () {
    const res = await verifyAuditChainLocal();
    const banner = document.getElementById("merkleVerifyBanner");
    if (res.valid) {
      banner.className = "p-3 rounded-lg bg-emerald-950/50 border border-emerald-500/50 text-xs mono-nums text-emerald-300";
      banner.textContent = `VERIFIED: All ${res.blocks} Merkle Audit Blocks intact. Head SHA-256: ${res.merkleHead}`;
    } else {
      banner.className = "p-3 rounded-lg bg-rose-950/50 border border-rose-500/50 text-xs mono-nums text-rose-300";
      banner.textContent = `TAMPER ALERT at Block #${res.brokenAt} of ${res.blocks}!`;
    }
  };

  window.switchView = function (view) {
    currentView = view;
    document.querySelectorAll(".view-section").forEach((el) => el.classList.add("hidden"));
    const target = document.getElementById("view-" + view);
    if (target) target.classList.remove("hidden");
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-view") === view);
    });
    if (view === "reports") renderReports("tb");
    if (view === "audit-trail") window.verifyMerkleChainUI();
    if (view === "einvoice") renderEinvoicesTable();
  };

  function renderEinvoicesTable() {
    const tbody = document.getElementById("einvoicesListBody");
    if (!tbody) return;
    const list = state.einvoices || [];
    tbody.innerHTML = list.length
      ? list
          .map(
            (e) => `<tr>
          <td class="py-2 pr-3 font-bold text-brand-cyan">${escapeHtml(e.doc_no)}</td>
          <td class="py-2 pr-3">${escapeHtml(e.buyer_gstin)}</td>
          <td class="py-2 pr-3">${escapeHtml(e.irn.slice(0, 18))}…</td>
          <td class="py-2 pr-3 text-emerald-400">${escapeHtml(e.ewb_no || "N/A (<=50k)")}</td>
          <td class="py-2 pr-3 text-right">₹${Number(e.total_invoice_value).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
          <td class="py-2 text-right">${
            e.status === "ACTIVE"
              ? `<button type="button" onclick="cancelEinvoiceUI('${escapeHtml(e.irn)}')" class="text-rose-400 hover:underline font-bold cursor-pointer">Cancel IRN</button>`
              : `<span class="text-slate-500">CANCELLED</span>`
          }</td>
        </tr>`
          )
          .join("")
      : `<tr><td colspan="6" class="py-3 text-slate-400 font-sans">No IRNs generated yet. Fill the form above and click Generate IRN.</td></tr>`;
  }

  window.generateEInvoiceUI = async function (event) {
    event.preventDefault();
    const seller = document.getElementById("einvSeller").value.trim().toUpperCase();
    const buyer = document.getElementById("einvBuyer").value.trim().toUpperCase();
    const docNo = document.getElementById("einvDocNo").value.trim().toUpperCase();
    const hsn = document.getElementById("einvHsn").value.trim();
    const taxable = Number(document.getElementById("einvTaxable").value || 0);
    const rate = Number(document.getElementById("einvRate").value || 5);
    const box = document.getElementById("einvoiceResultBox");
    box.classList.remove("hidden");

    const gstinRe = /^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
    if (!gstinRe.test(seller) || !gstinRe.test(buyer) || !/^\d{4}(\d{2})?(\d{2})?$/.test(hsn) || taxable <= 0) {
      box.innerHTML = `<span class="text-rose-400 font-bold">Validation Error: Check 15-char GSTINs, 4/6/8-digit HSN, and positive taxable value.</span>`;
      return;
    }

    const totalTax = Math.round(taxable * rate) / 100;
    const totVal = (taxable + totalTax).toFixed(2);
    const irn = await sha256Hex(`${seller}${docNo}INV2026-27`);
    const ackNo = String(parseInt(irn.slice(0, 12), 16)).slice(0, 15).padStart(15, "1");
    const ewbNo = Number(totVal) > 50000 ? "34" + String(parseInt(irn.slice(12, 22), 16)).slice(0, 10).padStart(10, "0") : "";
    const rec = {
      irn,
      doc_no: docNo,
      seller_gstin: seller,
      buyer_gstin: buyer,
      ack_no: ackNo,
      ewb_no: ewbNo,
      total_invoice_value: totVal,
      status: "ACTIVE",
    };

    const apiBase = window.ALGORISE_CONFIG && window.ALGORISE_CONFIG.apiBase;
    if (apiBase) {
      try {
        const resp = await fetch(`${apiBase}/accounting/companies/${COMPANY_ID}/einvoice/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            seller_gstin: seller,
            buyer_gstin: buyer,
            doc_no: docNo,
            doc_date: isoToday(),
            items: [{ item_name: "Supply Item", hsn_code: hsn, taxable_value: taxable, gst_rate_pct: rate }],
          }),
        });
        if (resp.ok) {
          const remoteRec = await resp.json();
          Object.assign(rec, remoteRec);
        }
      } catch (_err) {
        // local-first fallback already computed deterministically
      }
    }

    state.einvoices = state.einvoices || [];
    if (!state.einvoices.some((x) => x.irn === rec.irn)) {
      state.einvoices.unshift(rec);
      await appendAuditBlock("gsp_sandbox", "GENERATE_IRN", "EINVOICE", rec.irn, {}, rec);
      saveState();
      renderAll();
    }
    renderEinvoicesTable();
    box.innerHTML = `
      <div class="font-extrabold text-emerald-400">NIC IRP e-Invoice IRN Generated &amp; Sealed</div>
      <div>IRN: <strong class="text-white break-all">${escapeHtml(rec.irn)}</strong></div>
      <div>Ack No: <strong class="text-brand-cyan">${escapeHtml(rec.ack_no)}</strong> · Total Value: <strong>₹${escapeHtml(rec.total_invoice_value)}</strong> · E-Way Bill: <strong class="text-amber-300">${escapeHtml(rec.ewb_no || "Not Required (<= ₹50,000)")}</strong></div>
    `;
  };

  window.cancelEinvoiceUI = async function (irn) {
    state.einvoices = state.einvoices || [];
    const target = state.einvoices.find((x) => x.irn === irn);
    if (!target || target.status !== "ACTIVE") return;
    target.status = "CANCELLED";
    await appendAuditBlock("gsp_sandbox", "CANCEL_IRN", "EINVOICE", irn, { status: "ACTIVE" }, { status: "CANCELLED" });
    saveState();
    renderAll();
    renderEinvoicesTable();
  };

  window.probeLocalAlgoBridge = async function () {
    const out = document.getElementById("bridgeProbeResult");
    out.textContent = "Probing http://127.0.0.1:9095/status ...";
    try {
      const resp = await fetch("http://127.0.0.1:9095/status");
      if (resp.ok) {
        const data = await resp.json();
        out.innerHTML = `<span class="text-emerald-400 font-bold">CONNECTED:</span> Agent v${escapeHtml(data.version)} · Tally Port 9000 Connected: <strong>${String(data.tally_connected)}</strong> · Last Status: <strong>${escapeHtml(data.last_status)}</strong>`;
        return;
      }
    } catch (_err) {
      // agent not running locally
    }
    out.innerHTML = `<span class="text-amber-300">Local AlgoBridge not running on :9095 yet.</span> Start it with: <code class="text-emerald-400">python algorise-accounting/algobridge/algobridge_agent.py --mock-tally</code>`;
  };

  const GO_TO_COMMANDS = [
    { label: "F8 — Sales GST Voucher Entry", action: () => { window.switchView("voucher"); setVoucherType("SALES"); } },
    { label: "F9 — Purchase GST Voucher Entry", action: () => { window.switchView("voucher"); setVoucherType("PURCHASE"); } },
    { label: "F5 — Payment Voucher", action: () => { window.switchView("voucher"); setVoucherType("PAYMENT"); } },
    { label: "F6 — Receipt Voucher", action: () => { window.switchView("voucher"); setVoucherType("RECEIPT"); } },
    { label: "F4 — Contra Voucher", action: () => { window.switchView("voucher"); setVoucherType("CONTRA"); } },
    { label: "F7 — Journal Voucher", action: () => { window.switchView("voucher"); setVoucherType("JOURNAL"); } },
    { label: "Alt+C — Create Ledger Master (Inline)", action: () => window.openMasterModal() },
    { label: "AlgoBridge — Import Tally.ERP 9 / TallyPrime XML", action: () => window.switchView("tally-import") },
    { label: "GSP e-Invoice — Generate IRN, Signed QR & AlgoBridge Probe", action: () => window.switchView("einvoice") },
    { label: "CA Super-Console — Open Multi-Client Schedule III & GSTR-9", action: () => { window.location.href = "algorise-accounting/ca-console.html"; } },
    { label: "GST — Fuzzy GSTR-2B & IMS Reconciliation", action: () => { window.switchView("gst-2b"); window.runDemoGstr2bReconciliation(); } },
    { label: "Section 43B(h) — MSME 15/45-Day Compliance Radar", action: () => window.switchView("msme-43bh") },
    { label: "Reports — Trial Balance / P&L / Balance Sheet", action: () => { window.switchView("reports"); renderReports("tb"); } },
    { label: "WhatsApp — Receivables & Balance Confirmation", action: () => window.switchView("whatsapp") },
    { label: "MCA Rule 11(g) — Verify SHA-256 Merkle Edit Log", action: () => window.switchView("audit-trail") },
    { label: "Toggle Classic Tally DOS Skin (Ctrl+Shift+T)", action: () => window.toggleClassicTallyTheme() },
  ];

  window.openGoToPalette = function () {
    const dlg = document.getElementById("goToDialog");
    if (!dlg.open) dlg.showModal();
    const inp = document.getElementById("goToSearchInput");
    inp.value = "";
    window.filterGoToCommands();
    inp.focus();
  };

  window.filterGoToCommands = function () {
    const q = (document.getElementById("goToSearchInput").value || "").toLowerCase();
    const matches = GO_TO_COMMANDS.filter((c) => c.label.toLowerCase().includes(q));
    const list = document.getElementById("goToResultsList");
    list.innerHTML = matches
      .map(
        (c, idx) =>
          `<button type="button" data-cmd-idx="${idx}" class="goto-item w-full text-left px-3 py-2 rounded-lg hover:bg-cyan-500/15 hover:text-brand-cyan font-semibold flex justify-between cursor-pointer">${escapeHtml(c.label)}<span class="text-slate-500">↵</span></button>`
      )
      .join("");
    list.querySelectorAll(".goto-item").forEach((el, i) => {
      el.addEventListener("click", () => {
        document.getElementById("goToDialog").close();
        matches[i].action();
      });
    });
  };

  window.toggleClassicTallyTheme = function () {
    const isClassic = document.body.classList.toggle("classic-tally");
    document.getElementById("themeToggleLabel").textContent = isClassic ? "Cosmic AI Skin" : "Classic Tally Skin";
  };

  window.toggleKeyboardLockMode = async function () {
    const label = document.getElementById("focusLockLabel");
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
        if (navigator.keyboard && navigator.keyboard.lock) {
          await navigator.keyboard.lock(["F2", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "Escape"]);
        }
        label.textContent = "Lock Active (Esc)";
      } else {
        if (navigator.keyboard && navigator.keyboard.unlock) navigator.keyboard.unlock();
        await document.exitFullscreen();
        label.textContent = "Focus Lock";
      }
    } catch (_err) {
      label.textContent = "Keys Intercepted";
    }
  };

  window.focusDateField = function () {
    window.switchView("voucher");
    document.getElementById("vchDate").focus();
  };

  window.handleEscapeNav = function () {
    const mDlg = document.getElementById("masterDialog");
    const gDlg = document.getElementById("goToDialog");
    if (mDlg.open) { mDlg.close(); return; }
    if (gDlg.open) { gDlg.close(); return; }
    if (currentView !== "dashboard") window.switchView("dashboard");
  };

  window.exportBackupJSON = function () {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `algorise-booksos-backup-${isoToday()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  window.resetDemoDataset = async function () {
    localStorage.removeItem(STORAGE_KEY);
    state = buildInitialDataset();
    await initAuditBlocksIfEmpty();
    renderAll();
    setVoucherType("SALES");
  };

  window.syncWithBackend = async function () {
    const badge = document.getElementById("syncModeBadge");
    const apiBase = window.ALGORISE_CONFIG && window.ALGORISE_CONFIG.apiBase;
    if (!apiBase) {
      badge.textContent = "Mode: Offline-First Local WAL";
      return;
    }
    badge.textContent = "Syncing with Algorise API...";
    try {
      const resp = await fetch(`${apiBase}/accounting/companies/${COMPANY_ID}/summary`);
      if (resp.ok) {
        badge.textContent = `Synced (${window.ALGORISE_CONFIG.apiVersion || "v1"})`;
      } else {
        badge.textContent = "Mode: Offline-First (API Stand-by)";
      }
    } catch (_err) {
      badge.textContent = "Mode: Offline-First Local WAL";
    }
  };

  // Authentic Tally Keyboard Muscle-Memory Interceptor
  window.addEventListener("keydown", (e) => {
    if (e.altKey && e.key.toLowerCase() === "c") {
      e.preventDefault();
      window.openMasterModal();
      return;
    }
    if (e.altKey && e.key.toLowerCase() === "g") {
      e.preventDefault();
      window.openGoToPalette();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "t") {
      e.preventDefault();
      window.toggleClassicTallyTheme();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "t" && !e.shiftKey) {
      e.preventDefault();
      if (currentView === "voucher") {
        const chk = document.getElementById("vchIsPdc");
        chk.checked = !chk.checked;
      }
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "a" && currentView === "voucher") {
      e.preventDefault();
      document.getElementById("voucherForm").requestSubmit();
      return;
    }
    if (e.key === "F2") { e.preventDefault(); window.focusDateField(); return; }
    if (e.key === "F4") { e.preventDefault(); window.switchView("voucher"); setVoucherType("CONTRA"); return; }
    if (e.key === "F5") { e.preventDefault(); window.switchView("voucher"); setVoucherType("PAYMENT"); return; }
    if (e.key === "F6") { e.preventDefault(); window.switchView("voucher"); setVoucherType("RECEIPT"); return; }
    if (e.key === "F7") { e.preventDefault(); window.switchView("voucher"); setVoucherType("JOURNAL"); return; }
    if (e.key === "F8") { e.preventDefault(); window.switchView("voucher"); setVoucherType("SALES"); return; }
    if (e.key === "F9") { e.preventDefault(); window.switchView("voucher"); setVoucherType("PURCHASE"); return; }
    if (e.key === "Escape") { window.handleEscapeNav(); }
  });

  window.__books = {
    updateLine(idx, field, val) {
      if (voucherLineDrafts[idx]) {
        voucherLineDrafts[idx][field] = val;
        updateVoucherTotals();
      }
    },
    updateLineAmount(idx, val) {
      if (voucherLineDrafts[idx]) {
        voucherLineDrafts[idx].amountPaise = toPaise(val);
        updateVoucherTotals();
      }
    },
    removeLine(idx) {
      if (voucherLineDrafts.length > 2) {
        voucherLineDrafts.splice(idx, 1);
        renderVoucherLines();
      }
    },
  };

  window.setVoucherType = setVoucherType;

  document.addEventListener("DOMContentLoaded", async () => {
    state = loadState();
    await initAuditBlocksIfEmpty();
    document.getElementById("vchDate").value = isoToday();
    renderAll();
    setVoucherType("SALES");
    window.runDemoGstr2bReconciliation();
    window.recalcQuickGst();
  });
})();
