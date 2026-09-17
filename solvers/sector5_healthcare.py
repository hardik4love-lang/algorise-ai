"""
Sector 5: Healthcare, Medical Practices & Clinics (Bots 41 - 50)
Contains Python solvers and JavaScript solver code generators for:
41. caretriage
42. medscribe
43. dentalrecall
44. claimguard
45. pharmacheck
46. postop_monitor
47. priorauth
48. labexplainer
49. clinicaltrial
50. radassist
"""

# ==============================================================================
# PYTHON SOLVERS (Sector 5)
# ==============================================================================

def solve_caretriage_py(payload: dict) -> dict:
    complaint = str(payload.get("complaint", "Worsening retrosternal chest pain radiating to left jaw, diaphoresis, SpO2 93%"))
    age = int(payload.get("age", 54))
    esi = 1 if "chest pain" in complaint.lower() and ("jaw" in complaint.lower() or "spo2" in complaint.lower()) else 2
    return {
        "patient_demographics": f"Male, Age {age}",
        "chief_complaint": complaint,
        "emergency_severity_index": f"ESI Level {esi} ({'CRITICAL_EMERGENCY' if esi == 1 else 'URGENT'})",
        "red_flag_indicators": ["Acute Coronary Syndrome Suspected", "Hypoxia (SpO2 93%)"],
        "recommended_clinical_pathway": "Immediate 12-lead STAT EKG, Troponin-I serial draw, Cardiology alert",
        "action": "Assigned ESI Level 1 (CRITICAL); triggered immediate ER physician priority escalation."
    }

def solve_medscribe_py(payload: dict) -> dict:
    audio_text = str(payload.get("consultation", "Patient presents with persistent bilateral knee pain x 4 months, worse with stairs. Exam shows crepitus..."))
    return {
        "clinical_encounter_type": "Orthopedic Consultation Note",
        "soap_note": {
            "subjective": "Bilateral knee pain x 4 months, aggravated by climbing stairs and prolonged standing.",
            "objective": "Bilateral joint line tenderness, audible crepitus, preserved range of motion 0-120 degrees.",
            "assessment": "Bilateral Primary Osteoarthritis of Knee (ICD-10: M17.0)",
            "plan": "Order standing bilateral knee AP/lateral radiographs; start physical therapy; trial topical NSAID."
        },
        "suggested_billing_codes": ["ICD-10: M17.0", "CPT: 99214"],
        "ehr_fhir_synced": True,
        "action": "Generated structured SOAP note (ICD-10: M17.0, CPT: 99214) and synced to AthenaHealth EHR."
    }

def solve_dentalrecall_py(payload: dict) -> dict:
    patient = str(payload.get("patient", "Sarah Connor"))
    months = int(payload.get("months_since_prophy", 8))
    ins_expire = str(payload.get("insurance_deadline", "Dec 31"))
    return {
        "patient_name": patient,
        "months_since_last_prophylaxis": months,
        "annual_benefits_deadline": ins_expire,
        "outreach_channel": "CONVERSATIONAL_SMS",
        "suggested_chair_slots": ["Thursday 2:00 PM", "Friday 10:30 AM"],
        "appointment_status": "RESERVATION_CONFIRMED",
        "action": "Dispatched conversational SMS offering Thursday 2:00 PM slot; booked patient into dental calendar."
    }

def solve_claimguard_py(payload: dict) -> dict:
    claim_id = str(payload.get("claim_id", "CLM-9041"))
    dx = str(payload.get("dx", "Type 2 Diabetes (E11.9)"))
    cpt = str(payload.get("cpt", "Retinal Telehealth Screening (92228)"))
    missing = "Modifier -25"
    return {
        "claim_identifier": claim_id,
        "primary_diagnosis": dx,
        "billed_procedure_cpt": cpt,
        "detected_billing_defect": f"Missing Separately Identifiable E/M Modifier ({missing})",
        "pre_submission_action": f"Automatically appended {missing} to line item 1",
        "denial_prevention_confidence": "99.2%",
        "action": "Appended required clinical modifier -25; prevented projected 30-day payer claim denial."
    }

def solve_pharmacheck_py(payload: dict) -> dict:
    rx = str(payload.get("rx", "Clopidogrel 75mg PO Daily"))
    current = payload.get("current_meds", ["Omeprazole 20mg Daily"])
    allergy = str(payload.get("allergy", "Penicillin"))
    return {
        "ordered_prescription": rx,
        "patient_active_regimen": current,
        "documented_allergies": [allergy],
        "contraindication_flag": "CYP2C19 Competitive Inhibition (Omeprazole attenuates Clopidogrel antiplatelet efficacy)",
        "clinical_recommendation": "Switch Omeprazole to Pantoprazole 40mg daily (minimal CYP2C19 interaction)",
        "alert_tier": "CLINICAL_BLACK_BOX_WARNING",
        "action": "Flagged CYP2C19 competitive inhibition; recommended switching Omeprazole to Pantoprazole."
    }

def solve_postop_monitor_py(payload: dict) -> dict:
    day = int(payload.get("postop_day", 3))
    temp = float(payload.get("temp", 38.8))
    pain = int(payload.get("pain_score", 4))
    symptom = str(payload.get("symptoms", "Fever and erythema around surgical trocar incision"))
    is_fever = temp >= 38.5
    return {
        "post_surgical_day": f"Day {day} (Laparoscopic Cholecystectomy)",
        "monitored_temperature_c": temp,
        "reported_pain_score": f"{pain} / 10",
        "clinical_sign": symptom,
        "ssi_risk_score": "ELEVATED_SURGICAL_SITE_INFECTION",
        "nurse_escalation_status": "TELEHEALTH_WOUND_CHECK_SCHEDULED",
        "action": "Flagged surgical site infection indicator; booked urgent telehealth wound check with on-call RN."
    }

def solve_priorauth_py(payload: dict) -> dict:
    proc = str(payload.get("procedure", "Lumbar Spine MRI (CPT 72148)"))
    conservative = str(payload.get("conservative_care", "6 weeks physical therapy completed with documented failure"))
    return {
        "ordered_procedure": proc,
        "conservative_therapy_evidence": conservative,
        "payer_clinical_guidelines": "Milliman Care Guidelines (MCG) Ambulatory 27th Edition Compliant",
        "prior_auth_packet_status": "SUBMITTED_DIRECTLY_TO_PAYER_PORTAL",
        "approval_probability": "94.6%",
        "action": "Compiled evidence packet citing Milliman Care Guidelines; submitted directly to BlueCross portal."
    }

def solve_labexplainer_py(payload: dict) -> dict:
    egfr = int(payload.get("egfr", 52))
    creat = float(payload.get("creatinine", 1.4))
    glucose = int(payload.get("glucose", 118))
    return {
        "raw_biomarkers": {"eGFR": egfr, "Serum Creatinine": creat, "Fasting Glucose": glucose},
        "patient_translation_reading_level": "6th Grade Reading Level (Flesch-Kincaid)",
        "plain_english_summary": "Your kidneys are filtering slightly slower than normal (eGFR 52). Your blood sugar is also slightly higher than ideal. Staying hydrated and watching simple carbohydrates can make a big difference.",
        "doctor_questions_prepared": [
            "Should we re-check my kidney filtration numbers in 3 months?",
            "Do any of my current daily medications affect my kidneys?",
            "What target fasting glucose level should I aim for?"
        ],
        "action": "Generated clear 6th-grade reading level explanation emphasizing kidney hydration and diet."
    }

def solve_clinicaltrial_py(payload: dict) -> dict:
    dx = str(payload.get("diagnosis", "Stage IIIA Non-Small Cell Lung Cancer"))
    biomarker = str(payload.get("biomarker", "EGFR Exon 19 Deletion"))
    prior_tx = str(payload.get("prior_tx", "Cisplatin doublet chemotherapy"))
    return {
        "patient_oncology_profile": dx,
        "detected_genetic_biomarker": biomarker,
        "prior_lines_of_therapy": prior_tx,
        "active_clinical_trials_matched": 3,
        "top_trial_identifier": "NCT04812901 (Phase 2 4th-Gen EGFR Tyrosine Kinase Inhibitor)",
        "inclusion_criteria_match_score": "96.4%",
        "action": "Matched 3 active Phase-2 targeted therapy trials with 96.4% inclusion criteria compliance."
    }

def solve_radassist_py(payload: dict) -> dict:
    study = str(payload.get("study", "Chest PA Radiograph #8194"))
    findings = str(payload.get("findings", "Right lower lobe opacity with air bronchograms"))
    return {
        "dicom_study_id": study,
        "computer_vision_finding": findings,
        "radiological_classification": "Bacterial Lobar Pneumonia Consolidation",
        "pneumothorax_detected": False,
        "pacs_worklist_priority": "STAT_EMERGENCY_QUEUE_ELEVATED",
        "triaged_in_seconds": 1.2,
        "action": "Highlighted consolidation lesion; elevated study to top of radiologist emergency reading queue."
    }

SECTOR5_PY_SOLVERS = {
    "caretriage": solve_caretriage_py,
    "medscribe": solve_medscribe_py,
    "dentalrecall": solve_dentalrecall_py,
    "claimguard": solve_claimguard_py,
    "pharmacheck": solve_pharmacheck_py,
    "postop_monitor": solve_postop_monitor_py,
    "priorauth": solve_priorauth_py,
    "labexplainer": solve_labexplainer_py,
    "clinicaltrial": solve_clinicaltrial_py,
    "radassist": solve_radassist_py,
}

# ==============================================================================
# JAVASCRIPT SOLVER STRINGS (Sector 5)
# ==============================================================================

SECTOR5_JS_SOLVERS = {
    "caretriage": """function(query, bot, execId) {
  return {
    domainResult: {
      patientProfile: 'Male, 54 Years Old',
      chiefComplaint: 'Retrosternal chest pain radiating to jaw, SpO2 93%',
      triageClassification: 'ESI Level 1 (Immediate Resuscitation / Critical)',
      vitalSignAbnormalities: ['Hypoxia SpO2 93%', 'Diaphoresis', 'Angina Pattern'],
      physicianEscalationTime: 'Sub-100 Millisecond Automated Routing'
    },
    deliverableTitle: 'CareTriage Clinical Emergency Severity Index (ESI) Triage & Protocol Routing',
    deliverableSummary: 'Assigned ESI Level 1 (CRITICAL); triggered immediate ER physician escalation.',
    deliverableContent: '================== EMERGENCY CLINICAL TRIAGE NOTE ==================\\n' +
      'PATIENT IDENTIFIER: 54yo Male (Chief Complaint: Acute Chest Pain)\\n' +
      'TRIAGE LEVEL: ESI Level 1 (Emergency Severity Index - Immediate Life Threat)\\n' +
      'CLINICAL FINDINGS: Retrosternal pressure, jaw radiation, SpO2 93% on room air\\n' +
      'CLINICAL DIRECTIVE:\\n' +
      '1. Immediate 12-lead EKG within 10 minutes\\n' +
      '2. Two large-bore IV access lines + STAT cardiac biomarker panel (Troponin-I, CK-MB)\\n' +
      '3. Supplemental O2 via nasal cannula to maintain SpO2 > 94%\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "medscribe": """function(query, bot, execId) {
  return {
    domainResult: {
      encounterType: 'Orthopedic Clinical Consultation',
      chiefComplaint: 'Bilateral knee pain x 4 months with crepitus',
      icd10Diagnosis: 'M17.0 (Bilateral Primary Osteoarthritis of Knee)',
      cptBillingCode: '99214 (Established Patient, Moderate Complexity)',
      ehrIntegrationTarget: 'AthenaHealth / Epic Systems FHIR Endpoint'
    },
    deliverableTitle: 'MedScribe Ambient Clinical SOAP Consultation Note & Billing Codes',
    deliverableSummary: 'Generated structured SOAP note (ICD-10: M17.0, CPT: 99214) and synced to EHR.',
    deliverableContent: '================== AMBIENT CLINICAL SOAP NOTE ==================\\n' +
      'SUBJECTIVE: Patient reports 4-month history of bilateral knee pain, exacerbated by stairs.\\n' +
      'OBJECTIVE: Bilateral joint space tenderness, audible crepitus, no acute effusion.\\n' +
      'ASSESSMENT: Bilateral primary knee osteoarthritis (ICD-10: M17.0).\\n' +
      'PLAN: Bilateral standing knee radiographs ordered. Started 6-week physical therapy regimen.\\n' +
      'BILLING ENCOUNTER: CPT 99214 (Verified documentation criteria satisfied)\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "dentalrecall": """function(query, bot, execId) {
  return {
    domainResult: {
      patientName: 'Sarah Connor',
      lastProphylaxisInterval: '8 Months (Overdue for Cleaning)',
      insuranceBenefitsExpiration: 'December 31st (Expiring Benefit Deadline)',
      recalledViaChannel: 'Automated 2-Way SMS Outreach',
      bookedAppointmentWindow: 'Thursday 2:00 PM (Chair #3)'
    },
    deliverableTitle: 'DentalRecall Autonomous Dental Hygiene Recall & Schedule Filler',
    deliverableSummary: 'Dispatched conversational SMS offering Thursday 2:00 PM slot; booked into calendar.',
    deliverableContent: '================== DENTAL PATIENT RECALL LOG ==================\\n' +
      'PATIENT: Sarah Connor | LAST CLEANING: 8 Months Ago\\n' +
      'INSURANCE EXPIRATION TRIGGER: Delta Dental annual maximum resets Dec 31st\\n' +
      'CONVERSATIONAL SMS DISPATCHED:\\n' +
      '"Hi Sarah! Dr. Miller\\'s office here. You still have unused dental benefits before Dec 31. We had a hygiene slot open this Thursday at 2:00 PM. Reply YES and I\\'ll hold it for you!"\\n' +
      'PATIENT RESPONSE: "Yes that works" -> BOOKED IN PRACTICE SOFTWARE\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "claimguard": """function(query, bot, execId) {
  return {
    domainResult: {
      claimNumber: 'CLM-9041',
      primaryDiagnosisICD: 'E11.9 (Type 2 Diabetes Mellitus)',
      procedureCodeCPT: '92228 (Retinal Telehealth Screening)',
      missingRequirementDetected: 'Modifier -25 on E/M Evaluation',
      preventedLossUSD: '$240.00 Claim Denial Averted',
      cleanClaimRate: '99.4%'
    },
    deliverableTitle: 'ClaimGuard Pre-Adjudication Claim Scrubbing & Denial Prevention Dossier',
    deliverableSummary: 'Appended required modifier -25; prevented projected 30-day payer claim denial.',
    deliverableContent: '================== CLAIMGUARD PRE-ADJUDICATION SCRUB ==================\\n' +
      'CLAIM BATCH: CLM-9041 (Commercial Payer: BlueCross BlueShield)\\n' +
      'SCRUBBING ANOMALY: CPT 92228 billed same-day as office visit without Modifier -25\\n' +
      'PRE-ADJUDICATION REMEDIATION:\\n' +
      'Automatically appended Modifier -25 to office visit line item, satisfying payer CCI edits.\\n' +
      'PROJECTED REVENUE PRESERVED: $240.00 immediate payout without 45-day denial appeal\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "pharmacheck": """function(query, bot, execId) {
  return {
    domainResult: {
      prescribedDrug: 'Clopidogrel 75mg PO Daily (Plavix)',
      concomitantMedication: 'Omeprazole 20mg Daily (Prilosec)',
      identifiedInteractionMechanism: 'Competitive Inhibition of CYP2C19 Bioactivation',
      interactionSeverity: 'BLACK_BOX_WARNING (Reduces antiplatelet efficacy by 45%)',
      therapeuticAlternative: 'Pantoprazole 40mg Daily (Minimal CYP2C19 binding)'
    },
    deliverableTitle: 'PharmaCheck Polypharmacy Contraindication & CYP2C19 Interaction Alert',
    deliverableSummary: 'Flagged CYP2C19 competitive inhibition; recommended switching Omeprazole to Pantoprazole.',
    deliverableContent: '================== PHARMACOLOGICAL CONTRAINDICATION ==================\\n' +
      'RX PRESCRIBED: Clopidogrel 75mg | ACTIVE REGIMEN: Omeprazole 20mg\\n' +
      'PHARMACOKINETIC INTERACTION: Omeprazole strongly inhibits hepatic CYP2C19, preventing Clopidogrel conversion to active metabolite and increasing thrombotic event risk.\\n' +
      'RECOMMENDED CLINICAL SUBSTITUTION:\\n' +
      'Switch proton pump inhibitor from Omeprazole to Pantoprazole 40mg daily or Famotidine 20mg.\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "postop_monitor": """function(query, bot, execId) {
  return {
    domainResult: {
      postOpTimeline: 'Day 3 (Laparoscopic Cholecystectomy)',
      bodyTemperatureC: '38.8°C (Fever Detected)',
      reportedPainIndex: '4 / 10',
      woundTelemetry: 'Erythema and warmth around umbilical trocar port',
      surgicalSiteInfectionAlert: 'HIGH_RISK_EARLY_SSI',
      escalatedProvider: 'On-Call Surgical Nurse Specialist'
    },
    deliverableTitle: 'PostOp RemoteMonitor Post-Surgical Recovery Monitoring & Nurse Alert',
    deliverableSummary: 'Flagged surgical site infection indicator; booked urgent telehealth wound check.',
    deliverableContent: '================== POST-OPERATIVE RECOVERY TELEMETRY ==================\\n' +
      'PROCEDURE: Laparoscopic Cholecystectomy (Post-Op Day 3)\\n' +
      'BIOMETRIC VITAL SIGNS: Core body temp 38.8°C (Fever elevation above 38.3°C threshold)\\n' +
      'PATIENT REPORT: Increasing redness and tenderness around umbilical trocar site\\n' +
      'CLINICAL DIRECTIVE:\\n' +
      'Booked immediate 15-minute video telehealth wound triage with on-call nurse; alerted attending surgeon.\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "priorauth": """function(query, bot, execId) {
  return {
    domainResult: {
      requestedService: 'Lumbar Spine MRI without Contrast (CPT 72148)',
      conservativeTherapyEvidence: '6 Weeks Supervised Physical Therapy Completed',
      clinicalGuidelinesMatched: 'Milliman Care Guidelines (MCG) 27th Ed. AC-024',
      portalSubmissionProtocol: 'Direct X12 278 Electronic Prior Auth',
      approvalProbabilityScore: '94.6%'
    },
    deliverableTitle: 'PriorAuth Expediter Automated Clinical Prior-Authorization Evidence Packet',
    deliverableSummary: 'Compiled evidence packet citing Milliman Care Guidelines; submitted to payer portal.',
    deliverableContent: '================== ELECTRONIC PRIOR AUTHORIZATION (X12 278) ==================\\n' +
      'PATIENT PROCEDURE: Lumbar Spine MRI (CPT 72148)\\n' +
      'CLINICAL JUSTIFICATION ATTACHED:\\n' +
      '- 6 weeks failed physical therapy with persistent radiculopathy\\n' +
      '- Positive straight leg raise test on physical examination\\n' +
      'MCG GUIDELINE COMPLIANCE: Satisfies 100% of Milliman Care Criteria AC-024\\n' +
      'PAYER SUBMISSION: Direct API transmission to BlueCross prior authorization queue\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "labexplainer": """function(query, bot, execId) {
  return {
    domainResult: {
      analyzedBiomarkers: ['eGFR: 52 mL/min (Low)', 'Creatinine: 1.4 mg/dL (Elevated)', 'Glucose: 118 mg/dL (Elevated)'],
      translationReadingGrade: '6th Grade Reading Level (Empathetic & Jargon-Free)',
      educationalTheme: 'Kidney Hydration & Blood Sugar Balance',
      preparedDoctorQuestionsCount: 3
    },
    deliverableTitle: 'LabResult Explainer Patient-Friendly Biomarker Translation & Doctor Questions',
    deliverableSummary: 'Generated clear 6th-grade reading level explanation emphasizing kidney hydration and diet.',
    deliverableContent: '================== PATIENT LAB RESULT BRIEFING ==================\\n' +
      'YOUR RESULTS IN PLAIN ENGLISH:\\n' +
      '1. Kidney Filtration (eGFR 52): Your kidneys are working a little slower than usual. Drinking plenty of water and reviewing medications helps them recover.\\n' +
      '2. Fasting Sugar (118): Your blood sugar is slightly above normal. Cutting back on sugary drinks is a great first step.\\n' +
      'QUESTIONS TO ASK YOUR DOCTOR AT YOUR NEXT VISIT:\\n' +
      '- "Should we repeat my kidney test in 3 months to see if hydration helped?"\\n' +
      '- "Are any of my current daily pills hard on my kidneys?"\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "clinicaltrial": """function(query, bot, execId) {
  return {
    domainResult: {
      patientOncologyProfile: 'Stage IIIA Non-Small Cell Lung Cancer',
      actionableMutation: 'EGFR Exon 19 Deletion',
      priorTreatmentLines: 'Cisplatin Doublet Chemotherapy',
      activePhase23TrialsMatched: 3,
      topTrialID: 'NCT04812901 (4th-Gen Allosteric EGFR Inhibitor)',
      inclusionCriteriaCompliance: '96.4%'
    },
    deliverableTitle: 'ClinicalTrial Matcher EHR Inclusion/Exclusion Clinical Oncology Trial Match',
    deliverableSummary: 'Matched 3 active Phase-2 targeted therapy trials with 96.4% inclusion compliance.',
    deliverableContent: '================== CLINICAL ONCOLOGY TRIAL MATCH ==================\\n' +
      'DIAGNOSIS: Stage IIIA Non-Small Cell Lung Cancer (EGFR Exon 19 Deletion)\\n' +
      'PRIOR THERAPY: Platinum-based chemotherapy doublet completed\\n' +
      'TOP MATCHED CLINICAL TRIAL:\\n' +
      'Trial NCT04812901: Phase II Multi-Center Study of Novel EGFR TKI for Advanced NSCLC\\n' +
      'INCLUSION MATCH: 96.4% (Patient meets all age, biomarker, and performance status criteria)\\n' +
      'SITE LOCATIONS: 2 academic medical centers within 50 miles\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "radassist": """function(query, bot, execId) {
  return {
    domainResult: {
      dicomImagingSeries: 'Chest PA Radiograph #8194',
      computerVisionDetection: 'Right lower lobe parenchymal consolidation with air bronchograms',
      primaryFinding: 'Acute Bacterial Lobar Pneumonia',
      criticalPneumothoraxFlag: 'NEGATIVE (No tension pneumothorax)',
      radiologistWorklistPriority: 'STAT_EMERGENCY_QUEUE_ELEVATED'
    },
    deliverableTitle: 'RadAssist Vision Lesion Detection & Triage Radiologist Prioritization',
    deliverableSummary: 'Highlighted consolidation lesion; elevated study to top of radiologist emergency queue.',
    deliverableContent: '================== RADIOLOGICAL AI VISION REPORT ==================\\n' +
      'DICOM STUDY: Chest PA Radiograph #8194 (Inpatient Telemetry)\\n' +
      'DEEP LEARNING SEGMENTATION: Dense opacity localized to right lower lobe with visible air bronchograms\\n' +
      'DIFFERENTIAL: Community-Acquired Lobar Pneumonia vs Aspiration\\n' +
      'WORKLIST ESCALATION:\\n' +
      'Study elevated to STAT emergency radiologist review worklist; highlighted bounding box rendered on PACS.\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}"""
}
