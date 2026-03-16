# Prior Authorization Processing System

## The Goal
Automate the extraction of medical data from unstructured faxes (PDFs) and adjudicate them against medical policies.

## Architecture

Our system is built using a modular, end-to-end microservice architecture composed of the following services:

### Microservice 1 (Intake) → `intake_engine.py`
- **Description**: A Python script that acts as the extraction engine.
- **Functionality**: Monitors `/mock_faxes` for incoming PDF faxes. Uses `pdfplumber` and `spaCy` to extract Patient Name, Member ID, Diagnosis Code, CPT Code, and Days of Physiotherapy.
- **Output**: Translates extracted data into an EDI 278 formatted `.txt` file in `/edi_output`.

### Microservice 1.5 (Administrative Validation) → `validation_engine.py`
- **Description**: A Python script that performs eligibility gating before clinical review.
- **Functionality**: Monitors `/edi_output` for EDI 278 files. Parses the Member ID from the `NM1*IL` segment and validates it against `member_database.json` (member exists, status is Active, coverage dates are valid).
- **Routing Logic**:
  - ✅ **VALID** → EDI file moved to `/validated_requests` for clinical adjudication.
  - ❌ **INVALID** → Administrative Denial JSON written to `/processed_results`. EDI file deleted.

### Microservice 2 (Adjudication) → `rules_engine.py`
- **Description**: A Python script that handles the clinical decision-making logic.
- **Functionality**: Reads EDI 278 files from `/validated_requests`. Parses CPT code (from `SV1`) and physiotherapy days (from custom `MSG` segment). Compares them against a local `policies.json` database.
- **Output**: Structured APPROVED/REJECTED JSON decision payload in `/processed_results`.

### Microservice 3 (UI) → `dashboard.py` *(planned)*
- **Description**: A Streamlit dashboard for stakeholders.
- **Functionality**: Visualizes the processing queue, extracted data, and final adjudication decisions in real time.

## Pipeline Flow

```
/mock_faxes (PDF)
      │
      ▼  MS-1: intake_engine.py
/edi_output (EDI 278)
      │
      ▼  MS-1.5: validation_engine.py
      ├──► /validated_requests  (Member VALID)
      └──► /processed_results   (Member INVALID → Admin Denial)
                  │
                  ▼  MS-2: rules_engine.py
            /processed_results   (APPROVED / REJECTED clinical decision)
```

## Directory Structure
- `/mock_faxes`: Incoming unstructured PDF faxes (monitored by Intake).
- `/edi_output`: EDI 278 files from Intake (monitored by Validation).
- `/validated_requests`: Eligibility-cleared EDI files ready for clinical adjudication.
- `/processed_results`: Final decision JSON payloads (admin denials + clinical decisions).

## Support Files
- `policies.json`: CPT-level clinical policy rules database.
- `member_database.json`: Mock member eligibility database.
