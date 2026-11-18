"""
Algorise PayHR - Compliance & Accounting Export Engine
Generates official file formats for:
1. EPFO ECR Text File (#~# delimited official format)
2. ESIC Monthly Contribution CSV
3. Bank Bulk Transfer Files (HDFC CMS, ICICI Bank, SBI)
4. Tally ERP9 / TallyPrime XML Payroll Accounting Vouchers
"""

from typing import List, Dict, Any
import io


class ComplianceExportEngine:
    """
    Exports payroll outputs directly into portal-ready government and banking formats.
    """

    @staticmethod
    def generate_epfo_ecr_txt(records: List[Dict[str, Any]]) -> str:
        """
        Generates official EPFO ECR (Electronic Challan-cum-Return) text file.
        Field Delimiter: #~#
        Fields per record:
        1. UAN
        2. Member Name
        3. Gross Wages
        4. EPF Wages
        5. EPS Wages
        6. EDLI Wages
        7. EE Share (Account 1 - 12%)
        8. EPS Share (Account 10 - 8.33% capped)
        9. ER Share (Account 1 - 3.67%)
        10. NCP Days (Non-Contributing Period / LOP days)
        11. Total Advances / Refund
        """
        lines = []
        for r in records:
            uan = str(r.get("uan", "")).strip()
            name = str(r.get("name", "")).strip()
            gross = int(round(r.get("gross_wages", 0)))
            epf_w = int(round(r.get("epf_wages", 0)))
            eps_w = int(round(r.get("eps_wages", 0)))
            edli_w = int(round(r.get("edli_wages", 0)))
            ee_pf = int(round(r.get("ee_pf", 0)))
            er_eps = int(round(r.get("er_eps", 0)))
            er_pf = int(round(r.get("er_pf", 0)))
            ncp_days = int(round(r.get("lop_days", 0)))
            refund = 0

            line = f"{uan}#~#{name}#~#{gross}#~#{epf_w}#~#{eps_w}#~#{edli_w}#~#{ee_pf}#~#{er_eps}#~#{er_pf}#~#{ncp_days}#~#{refund}"
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def generate_esic_monthly_csv(records: List[Dict[str, Any]]) -> str:
        """
        Generates official ESIC monthly contribution portal upload CSV.
        Header: IP Number,IP Name,No of Days,Total Monthly Wages,Reason Code,Last Working Day
        """
        lines = ["IP Number,IP Name,No of Days,Total Monthly Wages,Reason Code,Last Working Day"]
        for r in records:
            ip_num = str(r.get("esic_number", "")).strip()
            name = str(r.get("name", "")).strip()
            days = r.get("payable_days", 30)
            wages = int(round(r.get("gross_wages", 0)))
            reason = r.get("reason_code", "0")  # 0 = Normal worked
            last_day = r.get("last_working_day", "")

            lines.append(f'"{ip_num}","{name}",{days},{wages},{reason},"{last_day}"')

        return "\n".join(lines)

    @staticmethod
    def generate_bank_salary_file(records: List[Dict[str, Any]], bank: str = "HDFC") -> str:
        """
        Generates HDFC CMS / ICICI / SBI Corporate Netbanking CSV payment file.
        HDFC Format: Beneficiary Account No,Amount,Beneficiary Name,IFSC,Customer Ref No
        """
        lines = ["Account Number,Amount,Beneficiary Name,IFSC,Transaction Ref"]
        for idx, r in enumerate(records, 1):
            acc = str(r.get("account_number", "")).strip()
            amt = f"{r.get('net_pay', 0):.2f}"
            name = str(r.get("name", "")).strip()
            ifsc = str(r.get("ifsc", "")).strip()
            ref = f"SAL-{idx:04d}"

            lines.append(f'"{acc}",{amt},"{name}","{ifsc}","{ref}"')

        return "\n".join(lines)

    @staticmethod
    def generate_tally_payroll_xml(records: List[Dict[str, Any]], voucher_date: str = "20261026") -> str:
        """
        Generates Tally XML payload for importing monthly salary journal vouchers.
        """
        total_salary = sum(r.get("net_pay", 0) for r in records)
        xml = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER VCHTYPE="Payroll" ACTION="Create">
            <DATE>{voucher_date}</DATE>
            <NARRATION>Algorise PeopleOS Monthly Automated Payroll Disbursement</NARRATION>
            <PARTYLEDGERNAME>Salary Payable</PARTYLEDGERNAME>
            <AMOUNT>-{total_salary:.2f}</AMOUNT>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""
        return xml
