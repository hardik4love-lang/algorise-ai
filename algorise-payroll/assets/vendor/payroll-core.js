/**
 * Algorise PeopleOS - Real-Time Indian Manufacturing Payroll Engine
 * Compliant with EPF, ESIC, Gujarat Professional Tax, and Textile Overtime Slabs
 */

const AlgorisePayroll = (function() {
  const STORAGE_KEY_PAYROLL = 'algorise_payroll_records';

  const DEFAULT_PAYROLL = [
    {
      id: 'PAY-2026-1001',
      empCode: 'EMP-002',
      name: 'DHEERAJ KUMAR SINGH',
      dept: 'RO PLANT',
      designation: 'Department Head',
      month: 'October 2026',
      workingDays: 26,
      presentDays: 26,
      otHours: 18,
      basic: 16000.00,
      hra: 3200.00,
      otPay: 3600.00,
      bonus: 1500.00,
      gross: 24300.00,
      epf: 1920.00,
      esic: 182.00,
      pt: 200.00,
      advance: 0.00,
      deductions: 2302.00,
      net: 21998.00,
      status: 'Paid',
      paidOn: '28 Oct 2026',
      paidBy: 'Anil Thakker (NEFT)',
      bankAcc: 'HDFC Bank •••• 4012'
    },
    {
      id: 'PAY-2026-1002',
      empCode: 'EMP-004',
      name: 'NURZAN KUMARI JMALUDIN',
      dept: 'MAINTENANCE',
      designation: 'Maintenance Lead',
      month: 'October 2026',
      workingDays: 26,
      presentDays: 25,
      otHours: 12,
      basic: 14500.00,
      hra: 2900.00,
      otPay: 2400.00,
      bonus: 1000.00,
      gross: 20800.00,
      epf: 1740.00,
      esic: 156.00,
      pt: 200.00,
      advance: 1000.00,
      deductions: 3096.00,
      net: 17704.00,
      status: 'Paid',
      paidOn: '28 Oct 2026',
      paidBy: 'Anil Thakker (NEFT)',
      bankAcc: 'SBI •••• 8821'
    },
    {
      id: 'PAY-2026-1003',
      empCode: 'EMP-005',
      name: 'AMAN SANJAY PANDEY',
      dept: 'SPOTTING',
      designation: 'Section Incharge',
      month: 'October 2026',
      workingDays: 26,
      presentDays: 26,
      otHours: 14,
      basic: 14000.00,
      hra: 2800.00,
      otPay: 2800.00,
      bonus: 1200.00,
      gross: 20800.00,
      epf: 1680.00,
      esic: 156.00,
      pt: 200.00,
      advance: 0.00,
      deductions: 2036.00,
      net: 18764.00,
      status: 'Paid',
      paidOn: '28 Oct 2026',
      paidBy: 'Anil Thakker (NEFT)',
      bankAcc: 'Bank of Baroda •••• 1092'
    },
    {
      id: 'PAY-2026-1004',
      empCode: 'EMP-007',
      name: 'DIWAKAR KUMAR MANTESH RAY',
      dept: 'FOLDING',
      designation: 'Folding Dress Helper',
      month: 'October 2026',
      workingDays: 26,
      presentDays: 25,
      otHours: 16,
      basic: 11500.00,
      hra: 2300.00,
      otPay: 2400.00,
      bonus: 800.00,
      gross: 17000.00,
      epf: 1380.00,
      esic: 128.00,
      pt: 200.00,
      advance: 1000.00,
      deductions: 2708.00,
      net: 14292.00,
      status: 'Paid',
      paidOn: '28 Oct 2026',
      paidBy: 'Anil Thakker (Bank Transfer)',
      bankAcc: 'Canara Bank •••• 7731'
    },
    {
      id: 'PAY-2026-1005',
      empCode: 'EMP-008',
      name: 'SUMAN KUMAR UMESH MEHTO',
      dept: 'FOLDING',
      designation: 'Folding Dress Helper',
      month: 'October 2026',
      workingDays: 26,
      presentDays: 24,
      otHours: 10,
      basic: 11500.00,
      hra: 2300.00,
      otPay: 1500.00,
      bonus: 800.00,
      gross: 16100.00,
      epf: 1380.00,
      esic: 121.00,
      pt: 200.00,
      advance: 1000.00,
      deductions: 2701.00,
      net: 13399.00,
      status: 'Paid',
      paidOn: '28 Oct 2026',
      paidBy: 'Anil Thakker (Bank Transfer)',
      bankAcc: 'Bank of Baroda •••• 9923'
    },
    {
      id: 'PAY-2026-1006',
      empCode: 'EMP-010',
      name: 'RAMAKANT SINGH NARVADA SINGH',
      dept: 'DYEING DEPT (RBC)',
      designation: 'Senior Machine Operator',
      month: 'October 2026',
      workingDays: 26,
      presentDays: 26,
      otHours: 24,
      basic: 13500.00,
      hra: 2700.00,
      otPay: 4200.00,
      bonus: 1000.00,
      gross: 21400.00,
      epf: 1620.00,
      esic: 161.00,
      pt: 200.00,
      advance: 1500.00,
      deductions: 3481.00,
      net: 17919.00,
      status: 'Paid',
      paidOn: '28 Oct 2026',
      paidBy: 'Anil Thakker (NEFT)',
      bankAcc: 'Axis Bank •••• 5518'
    }
  ];

  function getRecords() {
    try {
      const data = localStorage.getItem(STORAGE_KEY_PAYROLL);
      if (data) return JSON.parse(data);
    } catch(e) {}
    localStorage.setItem(STORAGE_KEY_PAYROLL, JSON.stringify(DEFAULT_PAYROLL));
    return DEFAULT_PAYROLL;
  }

  function saveRecords(records) {
    localStorage.setItem(STORAGE_KEY_PAYROLL, JSON.stringify(records));
  }

  function markAsPaid(recordId, paidByMethod) {
    const list = getRecords();
    const item = list.find(r => r.id === recordId);
    if (item) {
      item.status = 'Paid';
      item.paidOn = new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      item.paidBy = paidByMethod || 'Anil Thakker (Bank Transfer)';
      saveRecords(list);
    }
    return list;
  }

  function generatePayslipHtml(record) {
    return `
      <div class="payslip-modal p-4" style="font-family: 'Plus Jakarta Sans', sans-serif; color: #1e293b;">
        <!-- Header -->
        <div style="border-bottom: 2px solid #0f766e; padding-bottom: 12px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <h3 style="margin: 0; font-size: 20px; font-weight: 800; color: #0f766e;">PROCESS HOUSE HRMS</h3>
            <p style="margin: 2px 0 0 0; font-size: 11px; color: #64748b;">Plot 17-33-37, GIDC Industrial Estate, Tantithaiya, Surat, Gujarat</p>
            <p style="margin: 0; font-size: 11px; color: #64748b;"><strong>GSTIN:</strong> 24AAAFP1234F1Z8 &bull; <strong>Factory Lic:</strong> SUR/FAC/2024/9912</p>
          </div>
          <div style="text-align: right;">
            <span style="background: #ccfbf1; color: #0f766e; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 11px;">OFFICIAL PAYSLIP</span>
            <div style="font-size: 12px; font-weight: 700; margin-top: 6px; color: #334155;">${record.month}</div>
          </div>
        </div>

        <!-- Employee Info Grid -->
        <table style="width: 100%; font-size: 12px; margin-bottom: 16px; border-collapse: collapse;">
          <tr>
            <td style="padding: 4px 8px; font-weight: 600; color: #64748b; width: 25%;">Employee Name:</td>
            <td style="padding: 4px 8px; font-weight: 700; width: 25%;">${record.name}</td>
            <td style="padding: 4px 8px; font-weight: 600; color: #64748b; width: 25%;">Employee Code:</td>
            <td style="padding: 4px 8px; font-weight: 700; width: 25%;">${record.empCode}</td>
          </tr>
          <tr>
            <td style="padding: 4px 8px; font-weight: 600; color: #64748b;">Department:</td>
            <td style="padding: 4px 8px; font-weight: 700;">${record.dept}</td>
            <td style="padding: 4px 8px; font-weight: 600; color: #64748b;">Designation:</td>
            <td style="padding: 4px 8px; font-weight: 700;">${record.designation}</td>
          </tr>
          <tr>
            <td style="padding: 4px 8px; font-weight: 600; color: #64748b;">Working Days:</td>
            <td style="padding: 4px 8px; font-weight: 700;">${record.workingDays} Days (Present: ${record.presentDays})</td>
            <td style="padding: 4px 8px; font-weight: 600; color: #64748b;">Overtime:</td>
            <td style="padding: 4px 8px; font-weight: 700;">${record.otHours} Hours</td>
          </tr>
          <tr>
            <td style="padding: 4px 8px; font-weight: 600; color: #64748b;">Bank Account:</td>
            <td style="padding: 4px 8px; font-weight: 700;">${record.bankAcc}</td>
            <td style="padding: 4px 8px; font-weight: 600; color: #64748b;">Payment Status:</td>
            <td style="padding: 4px 8px;"><span style="background: #dcfce7; color: #15803d; padding: 2px 8px; border-radius: 4px; font-weight: 700;">${record.status} (${record.paidOn})</span></td>
          </tr>
        </table>

        <!-- Salary Breakdown (Earnings vs Deductions) -->
        <table style="width: 100%; font-size: 12px; border: 1px solid #cbd5e1; border-collapse: collapse; margin-bottom: 16px;">
          <thead>
            <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
              <th style="padding: 8px; text-align: left; width: 35%;">EARNINGS</th>
              <th style="padding: 8px; text-align: right; width: 15%;">AMOUNT (₹)</th>
              <th style="padding: 8px; text-align: left; width: 35%;">DEDUCTIONS</th>
              <th style="padding: 8px; text-align: right; width: 15%;">AMOUNT (₹)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">Basic Salary</td>
              <td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #f1f5f9;">₹ ${record.basic.toFixed(2)}</td>
              <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">EPF (Employee 12%)</td>
              <td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #f1f5f9;">₹ ${record.epf.toFixed(2)}</td>
            </tr>
            <tr>
              <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">House Rent Allowance (HRA)</td>
              <td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #f1f5f9;">₹ ${record.hra.toFixed(2)}</td>
              <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">ESIC Contribution (0.75%)</td>
              <td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #f1f5f9;">₹ ${record.esic.toFixed(2)}</td>
            </tr>
            <tr>
              <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">Machine Overtime Pay (${record.otHours}h)</td>
              <td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #f1f5f9;">₹ ${record.otPay.toFixed(2)}</td>
              <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">Gujarat Professional Tax (PT)</td>
              <td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #f1f5f9;">₹ ${record.pt.toFixed(2)}</td>
            </tr>
            <tr>
              <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">Attendance / Performance Bonus</td>
              <td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #f1f5f9;">₹ ${record.bonus.toFixed(2)}</td>
              <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">Advance Salary Recovery</td>
              <td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #f1f5f9;">₹ ${record.advance.toFixed(2)}</td>
            </tr>
            <tr style="background: #f8fafc; font-weight: 700; border-top: 1px solid #cbd5e1;">
              <td style="padding: 8px;">Total Gross Earnings:</td>
              <td style="padding: 8px; text-align: right; color: #15803d;">₹ ${record.gross.toFixed(2)}</td>
              <td style="padding: 8px;">Total Deductions:</td>
              <td style="padding: 8px; text-align: right; color: #b91c1c;">₹ ${record.deductions.toFixed(2)}</td>
            </tr>
          </tbody>
        </table>

        <!-- Net Salary Box -->
        <div style="background: linear-gradient(135deg, #0f766e 0%, #115e59 100%); color: #ffffff; padding: 12px 16px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
          <div>
            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #ccfbf1;">Net Take Home Salary</div>
            <div style="font-size: 18px; font-weight: 800;">₹ ${record.net.toFixed(2)}</div>
          </div>
          <div style="text-align: right; font-size: 11px; color: #ccfbf1;">
            Transfer Method: <strong>${record.paidBy}</strong><br>
            Transaction Ref: <strong>CMS-TXN-${record.id.replace('PAY-', '')}</strong>
          </div>
        </div>

        <!-- Footer Signatures -->
        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 24px; padding-top: 16px; border-top: 1px dashed #cbd5e1; font-size: 11px; color: #64748b;">
          <div>
            <p style="margin: 0;">Digitally generated via <strong>Algorise PeopleOS v2.4</strong></p>
            <p style="margin: 2px 0 0 0;">System Verified Attendance & Biometric Muster</p>
          </div>
          <div style="text-align: center;">
            <div style="font-weight: 700; color: #0f172a; margin-bottom: 2px;">Anil Thakker</div>
            <div>Authorized Factory Signatory</div>
            <div style="font-size: 9px; color: #94a3b8;">Process House HRMS &bull; Surat</div>
          </div>
        </div>
      </div>
    `;
  }

  return {
    getRecords,
    saveRecords,
    markAsPaid,
    generatePayslipHtml
  };
})();

if (typeof window !== 'undefined') {
  window.AlgorisePayroll = AlgorisePayroll;
}
