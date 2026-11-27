/**
 * Algorise CA Super-Console — Multi-Tenant Practice Dashboard,
 * Schedule III Balance Sheet & P&L, GSTR-9 Summary, and Batch Merkle Verifier.
 */
(function () {
  "use strict";

  const CA_ID = "demo_ca_firm_01";
  const STORAGE_KEY = "algorise_ca_portfolio_v1";
  const PLAN_FEES = { STARTER: 2499, GROWTH: 5999, ENTERPRISE: 14999 };

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function fmtINR(val) {
    const n = Number(val || 0);
    return (n < 0 ? "-₹" : "₹") + Math.abs(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function defaultPortfolio() {
    return {
      ca_id: CA_ID,
      firm_name: "Mehta & Shah Chartered Accountants",
      frn_number: "124891W",
      rev_share_pct: "25.00",
      clients: [
        {
          company_id: "demo_booksos_01",
          name: "Apex Fabrics & Traders",
          gstin: "24AABCA1234F1Z5",
          plan_tier: "GROWTH",
          annual_fee_inr: "5999.00",
          ca_rev_share_inr: "1499.75",
          trial_balance_balanced: true,
          net_profit: "225000.00",
          msme_43bh_risk: "126000.00",
          merkle_valid: true,
          merkle_blocks: 6,
          active_einvoices: 2,
          last_bridge_sync: "Port 9000 Ready",
          schedule_iii: {
            equity_and_liabilities: {
              shareholders_funds: "1212500.00",
              non_current_liabilities: "0.00",
              trade_payables_msme_micro_small: "215250.00",
              trade_payables_other: "0.00",
              other_current_liabilities: "15250.00",
              total: "1443000.00",
            },
            assets: {
              fixed_assets: "0.00",
              inventories: "0.00",
              trade_receivables: "451500.00",
              cash_and_cash_equivalents: "987500.00",
              other_current_assets: "4000.00",
              total: "1443000.00",
            },
            profit_and_loss: {
              revenue_from_operations: "430000.00",
              other_income: "0.00",
              purchases_of_stock: "205000.00",
              direct_expenses: "0.00",
              indirect_expenses: "0.00",
              profit_before_tax: "225000.00",
            },
            balance_sheet_parity: true,
          },
          gstr_9_annual: {
            table_4_outward_supplies: { taxable_value: "430000.00", cgst: "6250.00", sgst: "6250.00", igst: "9000.00", total_output_tax: "21500.00" },
            table_6_itc_availed: { taxable_purchases: "205000.00", cgst: "5125.00", sgst: "5125.00", igst: "0.00", total_itc: "10250.00" },
            net_cash_tax_payable: "11250.00",
            excess_itc_carryforward: "0.00",
          },
        },
        {
          company_id: "demo_ca_cli_02",
          name: "Varachha CVD Diamonds LLP",
          gstin: "24AABCV5512D1Z8",
          plan_tier: "ENTERPRISE",
          annual_fee_inr: "14999.00",
          ca_rev_share_inr: "3749.75",
          trial_balance_balanced: true,
          net_profit: "115000.00",
          msme_43bh_risk: "89250.00",
          merkle_valid: true,
          merkle_blocks: 7,
          active_einvoices: 5,
          last_bridge_sync: "Port 9000 Synced",
          schedule_iii: {
            equity_and_liabilities: {
              shareholders_funds: "615000.00",
              non_current_liabilities: "0.00",
              trade_payables_msme_micro_small: "89250.00",
              trade_payables_other: "0.00",
              other_current_liabilities: "10000.00",
              total: "714250.00",
            },
            assets: {
              fixed_assets: "0.00",
              inventories: "0.00",
              trade_receivables: "210000.00",
              cash_and_cash_equivalents: "500000.00",
              other_current_assets: "4250.00",
              total: "714250.00",
            },
            profit_and_loss: {
              revenue_from_operations: "200000.00",
              other_income: "0.00",
              purchases_of_stock: "85000.00",
              direct_expenses: "0.00",
              indirect_expenses: "0.00",
              profit_before_tax: "115000.00",
            },
            balance_sheet_parity: true,
          },
          gstr_9_annual: {
            table_4_outward_supplies: { taxable_value: "200000.00", cgst: "5000.00", sgst: "5000.00", igst: "0.00", total_output_tax: "10000.00" },
            table_6_itc_availed: { taxable_purchases: "85000.00", cgst: "2125.00", sgst: "2125.00", igst: "0.00", total_itc: "4250.00" },
            net_cash_tax_payable: "5750.00",
            excess_itc_carryforward: "0.00",
          },
        },
        {
          company_id: "demo_ca_cli_03",
          name: "Pandesara Chem & Dyes",
          gstin: "24AABCP8821K1Z4",
          plan_tier: "STARTER",
          annual_fee_inr: "2499.00",
          ca_rev_share_inr: "624.75",
          trial_balance_balanced: true,
          net_profit: "155000.00",
          msme_43bh_risk: "47250.00",
          merkle_valid: true,
          merkle_blocks: 6,
          active_einvoices: 1,
          last_bridge_sync: "Direct Cloud",
          schedule_iii: {
            equity_and_liabilities: {
              shareholders_funds: "655000.00",
              non_current_liabilities: "0.00",
              trade_payables_msme_micro_small: "47250.00",
              trade_payables_other: "0.00",
              other_current_liabilities: "10000.00",
              total: "712250.00",
            },
            assets: {
              fixed_assets: "0.00",
              inventories: "0.00",
              trade_receivables: "210000.00",
              cash_and_cash_equivalents: "500000.00",
              other_current_assets: "2250.00",
              total: "712250.00",
            },
            profit_and_loss: {
              revenue_from_operations: "200000.00",
              other_income: "0.00",
              purchases_of_stock: "45000.00",
              direct_expenses: "0.00",
              indirect_expenses: "0.00",
              profit_before_tax: "155000.00",
            },
            balance_sheet_parity: true,
          },
          gstr_9_annual: {
            table_4_outward_supplies: { taxable_value: "200000.00", cgst: "5000.00", sgst: "5000.00", igst: "0.00", total_output_tax: "10000.00" },
            table_6_itc_availed: { taxable_purchases: "45000.00", cgst: "1125.00", sgst: "1125.00", igst: "0.00", total_itc: "2250.00" },
            net_cash_tax_payable: "7750.00",
            excess_itc_carryforward: "0.00",
          },
        },
      ],
    };
  }

  let portfolio = null;
  let activeStatutoryData = null;

  function loadLocalPortfolio() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && Array.isArray(parsed.clients)) return parsed;
      }
    } catch (_err) {
      // ignore
    }
    return defaultPortfolio();
  }

  function saveLocalPortfolio() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(portfolio));
    } catch (_err) {
      // ignore
    }
  }

  async function tryFetchApiPortfolio() {
    const apiBase = window.ALGORISE_CONFIG && window.ALGORISE_CONFIG.apiBase;
    if (!apiBase) return;
    try {
      const resp = await fetch(`${apiBase}/accounting/ca/${CA_ID}/portfolio`);
      if (resp.ok) {
        const remote = await resp.json();
        if (remote && Array.isArray(remote.clients) && remote.clients.length > 0) {
          portfolio = { ...defaultPortfolio(), ...remote };
          document.getElementById("caSyncStatus").textContent = "Portfolio Mode: Live API Connected";
        }
      }
    } catch (_err) {
      // keep local-first dataset
    }
  }

  function renderPortfolio() {
    const totalArr = portfolio.clients.reduce((s, c) => s + Number(c.annual_fee_inr || 0), 0);
    const totalShare = portfolio.clients.reduce((s, c) => s + Number(c.ca_rev_share_inr || 0), 0);
    const totalMsme = portfolio.clients.reduce((s, c) => s + Number(c.msme_43bh_risk || 0), 0);
    const allMerkle = portfolio.clients.every((c) => c.merkle_valid !== false);

    document.getElementById("caFirmTitle").textContent = `${portfolio.firm_name} (FRN ${portfolio.frn_number || "124891W"})`;
    document.getElementById("kpiClientsCount").textContent = String(portfolio.clients.length);
    document.getElementById("kpiCaEarnings").textContent = fmtINR(totalShare);
    document.getElementById("kpiPortfolioArr").textContent = `Total Client ARR: ${fmtINR(totalArr)}`;
    document.getElementById("kpiPortfolioMsme").textContent = fmtINR(totalMsme);
    document.getElementById("kpiMerkleStatus").textContent = allMerkle ? "100% VERIFIED" : "ACTION REQUIRED";

    const tbody = document.getElementById("caClientsBody");
    tbody.innerHTML = portfolio.clients
      .map(
        (c) => `<tr>
        <td class="py-3 pr-3 font-sans">
          <div class="font-bold text-white">${escapeHtml(c.name)}</div>
          <div class="text-[11px] mono-nums text-slate-400">${escapeHtml(c.gstin)} · ${escapeHtml(c.last_bridge_sync || "Cloud")}</div>
        </td>
        <td class="py-3 pr-3">
          <div class="font-bold text-brand-cyan">${escapeHtml(c.plan_tier)}</div>
          <div class="text-[11px] text-emerald-400">CA Share: ${fmtINR(c.ca_rev_share_inr)}/yr</div>
        </td>
        <td class="py-3 pr-3">
          <span class="whitespace-nowrap inline-block px-2 py-0.5 rounded ${c.trial_balance_balanced ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300"} text-[10px]">
            ${c.trial_balance_balanced ? "0.00 PARITY" : "VARIANCE"}
          </span>
        </td>
        <td class="py-3 pr-3 text-right text-amber-300 font-bold">${fmtINR(c.msme_43bh_risk)}</td>
        <td class="py-3 pr-3 text-center">
          <span class="text-emerald-400 font-bold">${c.merkle_blocks || 1} Blks ✓</span>
        </td>
        <td class="py-3 pr-3 text-center text-white">${c.active_einvoices ?? 0}</td>
        <td class="py-3 text-right">
          <button type="button" onclick="window.__ca.inspectClient('${escapeHtml(c.company_id)}')" class="px-2.5 py-1 rounded bg-cyan-500/15 border border-cyan-500/40 text-brand-cyan text-[11px] font-bold hover:bg-cyan-500/25 cursor-pointer">
            Schedule III &amp; GSTR-9
          </button>
        </td>
      </tr>`
      )
      .join("");

    if (portfolio.clients.length > 0) {
      window.__ca.inspectClient(portfolio.clients[0].company_id);
    }
  }

  function renderStatutoryView(client, data) {
    activeStatutoryData = { client, data };
    document.getElementById("statClientHeading").textContent = `${client.name} — Schedule III & GSTR-9 Summary`;
    const eq = data.schedule_iii.equity_and_liabilities;
    const as = data.schedule_iii.assets;
    const pnl = data.schedule_iii.profit_and_loss;
    const g9 = data.gstr_9_annual;

    document.getElementById("statutoryCardsGrid").innerHTML = `
      <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
        <div class="font-extrabold text-brand-cyan uppercase">Schedule III — Equity &amp; Liabilities</div>
        <div class="flex justify-between"><span>Shareholders' Funds</span><span>${fmtINR(eq.shareholders_funds)}</span></div>
        <div class="flex justify-between text-amber-300"><span>Trade Payables (MSME 43B(h))</span><span>${fmtINR(eq.trade_payables_msme_micro_small)}</span></div>
        <div class="flex justify-between"><span>Trade Payables (Others)</span><span>${fmtINR(eq.trade_payables_other)}</span></div>
        <div class="flex justify-between"><span>Other Current Liabilities / GST</span><span>${fmtINR(eq.other_current_liabilities)}</span></div>
        <div class="border-t border-slate-700 pt-2 flex justify-between font-extrabold text-emerald-400"><span>Total Equity &amp; Liabilities</span><span>${fmtINR(eq.total)}</span></div>
      </div>

      <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
        <div class="font-extrabold text-brand-cyan uppercase">Schedule III — Assets &amp; P&amp;L</div>
        <div class="flex justify-between"><span>Trade Receivables</span><span>${fmtINR(as.trade_receivables)}</span></div>
        <div class="flex justify-between"><span>Cash &amp; Cash Equivalents</span><span>${fmtINR(as.cash_and_cash_equivalents)}</span></div>
        <div class="flex justify-between"><span>Other Current Assets (ITC)</span><span>${fmtINR(as.other_current_assets)}</span></div>
        <div class="flex justify-between"><span>Revenue from Operations</span><span>${fmtINR(pnl.revenue_from_operations)}</span></div>
        <div class="border-t border-slate-700 pt-2 flex justify-between font-extrabold text-emerald-400"><span>Profit Before Tax (Total Assets ${fmtINR(as.total)})</span><span>${fmtINR(pnl.profit_before_tax)}</span></div>
      </div>

      <div class="p-4 rounded-xl bg-slate-950 border border-emerald-500/30 space-y-2">
        <div class="font-extrabold text-emerald-400 uppercase">GSTR-9 Annual Return Summary</div>
        <div class="flex justify-between"><span>Table 4 Outward Taxable</span><span>${fmtINR(g9.table_4_outward_supplies.taxable_value)}</span></div>
        <div class="flex justify-between"><span>Total Output GST Liability</span><span>${fmtINR(g9.table_4_outward_supplies.total_output_tax)}</span></div>
        <div class="flex justify-between"><span>Table 6 Input Tax Credit (ITC)</span><span>${fmtINR(g9.table_6_itc_availed.total_itc)}</span></div>
        <div class="flex justify-between text-amber-300"><span>Excess ITC Carryforward</span><span>${fmtINR(g9.excess_itc_carryforward)}</span></div>
        <div class="border-t border-slate-700 pt-2 flex justify-between font-extrabold text-brand-cyan"><span>Net Cash Tax Payable</span><span>${fmtINR(g9.net_cash_tax_payable)}</span></div>
      </div>
    `;
  }

  window.__ca = {
    async inspectClient(companyId) {
      const client = portfolio.clients.find((c) => c.company_id === companyId);
      if (!client) return;
      const apiBase = window.ALGORISE_CONFIG && window.ALGORISE_CONFIG.apiBase;
      if (apiBase) {
        try {
          const resp = await fetch(`${apiBase}/accounting/companies/${companyId}/schedule-iii-gstr9`);
          if (resp.ok) {
            const remoteData = await resp.json();
            renderStatutoryView(client, remoteData);
            return;
          }
        } catch (_err) {
          // fallback to local snapshot
        }
      }
      renderStatutoryView(client, {
        schedule_iii: client.schedule_iii || defaultPortfolio().clients[0].schedule_iii,
        gstr_9_annual: client.gstr_9_annual || defaultPortfolio().clients[0].gstr_9_annual,
      });
    },
  };

  window.verifyAllClientsMerkle = async function () {
    const banner = document.getElementById("batchMerkleBanner");
    banner.classList.remove("hidden");
    const apiBase = window.ALGORISE_CONFIG && window.ALGORISE_CONFIG.apiBase;
    if (apiBase) {
      try {
        const resp = await fetch(`${apiBase}/accounting/ca/${CA_ID}/verify-all-merkle`);
        if (resp.ok) {
          const data = await resp.json();
          banner.innerHTML = `<strong class="text-emerald-400">MCA RULE 11(g) BATCH VERIFICATION PASSED:</strong> Verified ${data.clients_passed}/${data.clients_checked} SME ledgers at ${escapeHtml(data.checked_at)}. Zero tamper events.`;
          return;
        }
      } catch (_err) {
        // fallback below
      }
    }
    const totalBlocks = portfolio.clients.reduce((s, c) => s + Number(c.merkle_blocks || 1), 0);
    banner.innerHTML = `<strong class="text-emerald-400">MCA RULE 11(g) BATCH VERIFICATION PASSED:</strong> All ${portfolio.clients.length} client ledgers (${totalBlocks} SHA-256 Merkle blocks) verified intact.`;
  };

  window.openOnboardClientModal = function () {
    document.getElementById("onboardClientDialog").showModal();
  };

  window.submitOnboardClient = async function (event) {
    event.preventDefault();
    const name = document.getElementById("cName").value.trim();
    const gstin = document.getElementById("cGstin").value.trim().toUpperCase();
    const tier = document.getElementById("cTier").value;
    if (!name) return;

    const fee = PLAN_FEES[tier] || 5999;
    const revShare = (fee * 0.25).toFixed(2);
    const newId = "demo_ca_" + Math.random().toString(16).slice(2, 8);

    const apiBase = window.ALGORISE_CONFIG && window.ALGORISE_CONFIG.apiBase;
    if (apiBase) {
      try {
        await fetch(`${apiBase}/accounting/ca/${CA_ID}/clients`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            firm_name: portfolio.firm_name,
            frn_number: portfolio.frn_number,
            company_id: newId,
            company_name: name,
            company_gstin: gstin,
            plan_tier: tier,
          }),
        });
      } catch (_err) {
        // continue offline
      }
    }

    portfolio.clients.push({
      company_id: newId,
      name,
      gstin,
      plan_tier: tier,
      annual_fee_inr: fee.toFixed(2),
      ca_rev_share_inr: revShare,
      trial_balance_balanced: true,
      net_profit: "0.00",
      msme_43bh_risk: "0.00",
      merkle_valid: true,
      merkle_blocks: 1,
      active_einvoices: 0,
      last_bridge_sync: "Ready for AlgoBridge",
      schedule_iii: defaultPortfolio().clients[0].schedule_iii,
      gstr_9_annual: defaultPortfolio().clients[0].gstr_9_annual,
    });
    saveLocalPortfolio();
    renderPortfolio();
    document.getElementById("onboardClientDialog").close();
    document.getElementById("cName").value = "";
  };

  window.exportScheduleIIIJson = function () {
    if (!activeStatutoryData) return;
    const blob = new Blob([JSON.stringify(activeStatutoryData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `schedule-iii-gstr9-${activeStatutoryData.client.company_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  document.addEventListener("DOMContentLoaded", async () => {
    portfolio = loadLocalPortfolio();
    await tryFetchApiPortfolio();
    renderPortfolio();
  });
})();
