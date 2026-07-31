# Guideline Source References

This file records the official source URLs, license terms, and citation labels for all guideline PDFs in the Aegis-MD corpus.

**Policy:** PDFs are local-only and never committed to Git. This file is committed for reproducibility and auditability.

**Verification date:** URLs were live-tested in Jul 2026. Status notes reflect actual accessibility at time of testing.

**Corpus:** 18 documents — Tier 1 (4), Tier 2 (6), Tier 3 (8). Citation labels below are the exact labels emitted by `data/chroma/chunk.py` and shown in API responses.

---

## Tier 1 — Triage-Specific Frameworks

### 1. Australian Emergency Triage Education Kit (ETEK), 2nd Edition
- **Source URL:** https://www.safetyandquality.gov.au/resources/emergency-triage-education-kit-etek-second-edition
- **Publisher:** Australian Commission on Safety and Quality in Health Care (ACSQHC)
- **Published:** 2024 (2nd ed; original 2009)
- **Citation Label:** ETEK 2nd Ed
- **License:** CC BY 3.0 AU — open, non-commercial research compatible
- **Status:** Active, not superseded
- **Verified:** Page exists (timed out in automated test; PDF download available on page)
- **File:** `emergency_triage_education_kit_-_second_edition.pdf`

### 2. ACEP/ENA Joint Policy — Triage Scale Standardization
- **Source URL:** https://www.ena.org/sites/default/files/2025-08/Emergency%20Department%20Triage.pdf
- **Publisher:** American College of Emergency Physicians (ACEP) + Emergency Nurses Association (ENA)
- **Published:** Jan 2025 (revised Jun 2024, Jun 2023; original 2003)
- **Citation Label:** ACEP/ENA Triage Policy
- **License:** ACEP/ENA policy statement — internal and research use permitted
- **Status:** Active, current version
- **Verified:** PDF downloads directly (51 KB)
- **File:** `Emergency Department Triage.pdf`
- **Note:** Joint ACEP/ENA position statement supporting 5-level triage scales (ESI, ATS, CTAS, MTS). It endorses standardized triage but does not define the ATS levels themselves.

### 3. Triage in the Hospital
- **Source URL:** https://www.scribd.com/document/97517282/Triage-in-the-Hospital
- **Publisher:** Uploaded by user "Carie Manarondong" on Scribd (original publisher unknown)
- **Published:** Unknown
- **Citation Label:** Triage in the Hospital
- **License:** Scribd terms — restricted redistribution; research use only
- **Status:** Active (local corpus)
- **Verified:** Scribd page accessible; 15 pages, ATS triage content confirmed
- **File:** `97517282-Triage-in-the-Hospital.pdf`
- **Note:** Original publisher could not be identified. Content covers general ED triage principles and ATS categories.

### 4. Emergency Severity Index (ESI) Handbook, 5th Edition
- **Source URL:** https://media.emscimprovement.center/documents/Emergency_Severity_Index_Handbook.pdf
- **Publisher:** Emergency Nurses Association (ENA)
- **Published:** 2020 (5th ed)
- **Citation Label:** ESI Handbook
- **License:** ENA — check specific document terms
- **Status:** Active, current version
- **Verified:** PDF downloads directly
- **File:** `Emergency_Severity_Index_Handbook.pdf`
- **Note:** The definitive ESI algorithm reference — 5-level triage system widely used by US EDs. Covers decision points A-D, high-risk criteria, and resource utilization assessment.

---

## Tier 2 — Specialty Guidelines (ED-Relevant)

### 5. WHO Basic Emergency Care (BEC)
- **Source URL:** https://hlh.who.int/docs/librariesprovider4/clinical-care/who-icrc-basic-emergency-care.pdf
- **Publisher:** WHO + ICRC + IFEM
- **Published:** 2018
- **Citation Label:** WHO BEC
- **License:** CC BY-NC-SA 3.0 IGO — non-commercial research compatible
- **Status:** Active
- **Verified:** PDF downloads directly
- **File:** `WHO-ICRC-Basic-Emergency-Care.pdf`
- **Note:** Includes the ABCDE assessment framework, shock recognition, trauma triage principles, and emergency care algorithms. ISBN 978-92-4-151308-1.

### 6. WHO Interagency Integrated Triage Tool (IITT) — Adult
- **Source URL:** https://cdn.who.int/media/docs/default-source/integrated-health-services-(ihs)/csy/iitt/iitt_adult.pdf
- **Publisher:** WHO + ICRC + Médecins Sans Frontières (MSF)
- **Published:** 2020
- **Citation Label:** WHO IITT
- **License:** WHO open access — non-commercial research compatible
- **Status:** Active, supersedes ETAT for facility-based triage
- **Verified:** PDF downloads directly
- **File:** `iitt_adult.pdf`
- **Note:** Three-colour triage system (red/yellow/green) for adults. Includes high-risk vital signs, ABCDE assessment, and referral algorithms.

### 7. NICE Head Injury — CG176 (updated to NG232)
- **Source URL:** https://www.nice.org.uk/guidance/ng232
- **Publisher:** UK National Institute for Health and Care Excellence (original CG176, Jan 2014; updated as NG232, May 2023)
- **Published:** 2023
- **Citation Label:** NICE Head Injury NG232
- **License:** Crown Copyright — Open Government Licence (OGL) v3.0 permitted for research
- **Status:** NG232 is the current version; core triage criteria unchanged from CG176
- **Verified:** nice.org.uk returns HTTP 403 to automated fetchers; PDF downloadable via browser from the guidance page
- **File:** `NICE-head-injury.pdf`
- **Note:** CT scan criteria for head injury triage. Key for head injury + anticoagulant presentations.

### 8. Six to Help — Fixing Acute Medicine
- **Source URL:** https://gettingitrightfirsttime.co.uk/wp-content/uploads/2023/07/Six-to-Help-Fix-Acute-Medicine-Guidance-for-improving-in-hospital-flow-FINAL-V1-July-2023.pdf
- **Publisher:** Getting It Right First Time (GIRFT) + Society for Acute Medicine (SAM), NHS England
- **Published:** July 2023
- **Citation Label:** Six to Help Acute Medicine
- **License:** NHS/GIRFT — open for research use
- **Status:** Active, current version
- **Verified:** PDF downloads directly from GIRFT and SAM mirrors
- **File:** `Six-to-Help-Fix-Acute-Medicine-Guidance-for-improving-in-hospital-flow-FINAL-V1-July-2023.pdf`
- **Note:** Six-step guidance for improving acute hospital flow. Also mirrored at acutemedicine.org.uk.

### 9. RCEM Best Practice — Acute Pain in Adults
- **Source URL:** https://www.rcem.ac.uk/Publications/
- **Publisher:** Royal College of Emergency Medicine (RCEM)
- **Published:** 2024
- **Citation Label:** RCEM Acute Pain
- **License:** RCEM — check specific document terms
- **Status:** Active
- **Verified:** RCEM site requires account for some publications
- **File:** `Management_of_Acute_Pain_in_Adults_2024_v1.pdf`
- **Note:** Pain assessment and management in ED. Relevant for pain-score-based triage escalation.

### 10. Haemophilia Emergency Management
- **Source URL:** https://www.bleeding.org/healthcare-professionals/guidelines-on-care/masac-documents/masac-document-257-guidelines-for-emergency-department-management-of-individuals-with-hemophilia-and-other-bleeding-disorders
- **Publisher:** National Hemophilia Foundation (NF), Medical and Scientific Advisory Council — MASAC Document 257, 2019
- **Published:** 2019
- **Citation Label:** Haemophilia Emergency Management
- **License:** NF — open access for research use
- **Status:** Active; superseded by WFH Guidelines 3rd ed (2020) but ED-specific content remains relevant
- **Verified:** NF page accessible; PDF available from haemophilia.org.uk mirror
- **File:** `Management-of-patients-with-Haemophilia-in-Emergency-Departments.pdf`
- **Note:** ED management guidelines for hemophilia patients. WFH 3rd ed (https://haemophilia.org.uk/wp-content/uploads/pdf/WFH-Guidelines-for-the-Management-of-Hemophilia-3rd-edition.pdf) is the broader reference.

---

## Tier 3 — Supplementary Guidelines

### 11. WHO Pocket Book of Hospital Care for Children
- **Source URL:** https://www.who.int/publications/i/item/9789241549902
- **Publisher:** WHO
- **Published:** 2nd Edition, 2013
- **Citation Label:** WHO Hospital Care Children
- **License:** CC BY-NC-SA 3.0 IGO — non-commercial research compatible
- **Status:** Active
- **Verified:** who.int publication page may return 404 (ISBN-based URLs have moved); PDF available via WHO IRIS
- **File:** `pocket_booklet_hospital_care_0.pdf`
- **Note:** Pediatric triage context, emergency signs, and referral criteria.

### 12. WHO IMAI — District Clinician Manual: Hospital Care for Adolescents and Adults
- **Source URL:** https://iris.who.int/bitstream/handle/10665/350623/9789290228882-eng.pdf
- **Publisher:** WHO South-East Asia Regional Office
- **Published:** 2021
- **Citation Label:** WHO IMAI Hospital Care
- **License:** WHO open access — non-commercial research compatible
- **Status:** Active
- **Verified:** PDF available via WHO IRIS
- **File:** `9789241548373_eng.pdf`
- **Note:** Covers emergency triage (Quick Check), ABCDE assessment, and management of severe illness at district hospital level.

### 13. RCEM Best Practice — Invasive Procedures in the ED
- **Source URL:** https://www.rcem.ac.uk/Publications/
- **Publisher:** Royal College of Emergency Medicine (RCEM)
- **Published:** 2024
- **Citation Label:** RCEM Invasive Procedures
- **License:** RCEM — check specific document terms
- **Status:** Active
- **Verified:** RCEM site requires account for some publications
- **File:** `RCEM_Best_Practice_Invasive_Procedures_in_the_Emergency_Department.pdf`
- **Note:** Reference for procedural guidance in ED settings.

### 14. Singapore MOH Clinical Practice Guidelines
- **Source URL:** https://www.moh.gov.sg/hpp/doctors/guidelines/cpg_medical
- **Publisher:** Ministry of Health, Singapore
- **Published:** 2017
- **Citation Label:** MOH CPG General
- **License:** Singapore government publication — research use permitted
- **Status:** Active (archive page; individual guidelines may have newer editions)
- **Verified:** MOH guidelines portal accessible; PDF available from SMJ and diabetes.org.sg mirrors
- **File:** `5506cpg1.pdf`
- **Note:** General CPG framework document. Specific guideline scope should be verified from PDF title page.

### 15. Singapore MOH Hypertension Guidelines
- **Source URL:** http://www.smj.org.sg/sites/default/files/07_CPG-298122017_Hypertension.pdf
- **Publisher:** Ministry of Health, Singapore (published in Singapore Med J, 2018)
- **Published:** 2017 (executive summary published SMJ 2018;59(1):17-27)
- **Citation Label:** MOH Hypertension
- **License:** Singapore government publication — research use permitted
- **Status:** Active; superseded by ACE Clinical Guideline on Hypertension (Dec 2023) but CPG remains valid reference
- **Verified:** PDF downloads directly from SMJ and diabetes.org.sg mirrors
- **File:** `MOH-Clinical-Practice-Guidelines-Hypertension.pdf`
- **Note:** Second edition of MOH hypertension CPG. Newer ACE guideline available at ace-hta.gov.sg.

### 16. STI Guidelines 2021
- **Source URL:** https://www.cdc.gov/std/treatment-guidelines/STI-Guidelines-2021.pdf
- **Publisher:** U.S. Centers for Disease Control and Prevention (CDC)
- **Published:** July 23, 2021
- **Citation Label:** STI Guidelines 2021
- **License:** U.S. Government work — public domain
- **Status:** Active; updates the 2015 STD Treatment Guidelines
- **Verified:** PDF downloads directly from CDC
- **File:** `STI-Guidelines-2021.pdf`
- **Note:** Comprehensive STI treatment guidelines covering gonorrhea, chlamydia, syphilis, trichomoniasis, and more. MMWR Recomm Rep 2021;70(4):1-187.

### 17. NHLBI Asthma EPR-3 Guidelines
- **Source URL:** https://www.nhlbi.nih.gov/guidelines/asthma
- **Publisher:** U.S. National Institutes of Health (NHLBI)
- **Published:** 2007
- **Citation Label:** NHLBI Asthma EPR-3
- **License:** U.S. Government work — public domain
- **Status:** Active
- **Verified:** NCI/NHLBI pages accessible
- **File:** `EPR-3_Asthma_Full_Report_2007.pdf`
- **Note:** Respiratory triage context.

### 18. Pediatrics Guidelines (ACEP Clinical Policy — Fever in Children)
- **Source URL:** https://www.acep.org/siteassets/uploads/uploaded-files/acep/clinical-and-practice-management/clinical-policies/pediatrics.pdf
- **Publisher:** American College of Emergency Physicians (ACEP), published in Annals of Emergency Medicine
- **Published:** 2003 (Ann Emerg Med. 2003;42:530-545; doi:10.1067/mem.2003.377)
- **Citation Label:** ACEP Pediatric Fever
- **License:** ACEP clinical policy — ACEP copyright; research use permitted
- **Status:** Active; revised edition "Fever - Infants and Children Younger than 2 Years" in review
- **Verified:** PDF downloads directly from ACEP
- **File:** `pediatrics.pdf`
- **Note:** Clinical Policy for Children Younger Than Three Years Presenting to the ED With Fever.

---

## Superseded / Historical Notes

| Document | Superseded By | Notes |
|----------|--------------|-------|
| NICE Head Injury CG176 | NICE NG232 (May 2023) | NG232 is current; core triage criteria unchanged. Corpus PDF reflects the current guidance. |
| WHO ETAT | WHO IITT (2020) | ETAT removed from corpus. IITT retained as the current facility-based triage tool. |

---

## URL Verification Summary

| Source | Automated Fetch | Browser Download | Notes |
|--------|----------------|-----------------|-------|
| WHO documents | Most direct PDF links work | Yes | hlh.who.int and WHO IRIS reliable |
| ENA/ACEP policy | Direct PDF works | Yes | |
| ACSQHC (ETEK) | Timed out | Yes | Page exists, PDF on page |
| NICE | HTTP 403 | Yes | Bot protection on nice.org.uk; download via browser |
| RCEM | Partial | Partial | Some publications require an account |
| GIRFT/SAM | Direct PDF works | Yes | Six to Help downloads from both mirrors |
| CDC (STI) | Direct PDF works | Yes | Public domain, no restrictions |
| Singapore MOH | Direct PDF works | Yes | SMJ and diabetes.org.sg mirrors available |
| Scribd (Triage in Hospital) | Requires login | Partial | User-uploaded content; restricted redistribution |
| NF MASAC (Haemophilia) | Page accessible | Yes | Open access guidelines |
| ACEP (Pediatrics) | Direct PDF works | Yes | ACEP clinical policy |

---

## License Summary

| License Type | Documents | Research Use |
|-------------|-----------|--------------|
| CC BY 3.0 AU | ETEK 2nd Ed | Yes |
| CC BY-NC-SA 3.0 IGO | WHO BEC, WHO IITT, WHO Hospital Care Children, WHO IMAI Hospital Care | Yes (non-commercial) |
| OGL v3.0 | NICE Head Injury NG232 | Yes |
| ACEP/ENA policy | ACEP/ENA Triage Policy, ESI Handbook, ACEP Pediatric Fever | Internal/research |
| Public Domain | NHLBI Asthma EPR-3, STI Guidelines 2021 (CDC) | Yes |
| NHS/GIRFT open | Six to Help Acute Medicine | Yes |
| NF open access | Haemophilia Emergency Management | Yes |
| Singapore govt pub. | MOH CPG General, MOH Hypertension | Yes |
| Scribd terms | Triage in the Hospital | Restricted — research only |
| Unknown / Check terms | RCEM Acute Pain, RCEM Invasive Procedures | Verify before use |

---

## Download Priority

Documents that are **verified downloadable** (can be fetched programmatically):

1. WHO BEC — `https://hlh.who.int/docs/librariesprovider4/clinical-care/who-icrc-basic-emergency-care.pdf`
2. WHO IITT Adult — `https://cdn.who.int/media/docs/default-source/integrated-health-services-(ihs)/csy/iitt/iitt_adult.pdf`
3. ACEP/ENA Triage Policy — `https://www.ena.org/sites/default/files/2025-08/Emergency%20Department%20Triage.pdf`
4. ESI Handbook — `https://media.emscimprovement.center/documents/Emergency_Severity_Index_Handbook.pdf`
5. Six to Help Acute Medicine — `https://gettingitrightfirsttime.co.uk/wp-content/uploads/2023/07/Six-to-Help-Fix-Acute-Medicine-Guidance-for-improving-in-hospital-flow-FINAL-V1-July-2023.pdf`
6. STI Guidelines 2021 — `https://www.cdc.gov/std/treatment-guidelines/STI-Guidelines-2021.pdf`
7. MOH Hypertension — `http://www.smj.org.sg/sites/default/files/07_CPG-298122017_Hypertension.pdf`
8. Pediatrics (ACEP Pediatric Fever) — `https://www.acep.org/siteassets/uploads/uploaded-files/acep/clinical-and-practice-management/clinical-policies/pediatrics.pdf`

Documents that require **manual browser download** (nice.org.uk blocks automated access):

1. NICE Head Injury — download via browser at nice.org.uk/guidance/ng232

Documents that require **institutional access or account**:

1. RCEM publications — some require an account (Acute Pain, Invasive Procedures)
2. Scribd (Triage in the Hospital) — requires login for full access

