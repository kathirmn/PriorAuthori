# Healthcare Prior Authorization Pipeline - Project Plan

## 1. Project Overview
This project is an automated Healthcare Prior Authorization pipeline that drastically reduces manual review times by seamlessly processing incoming faxes. The system sequentially pipelines requests through an Intake Engine for OCR/NLP extraction, an Administrative Validation Engine to check member eligibility, and a Rules Engine for clinical adjudication. Finally, all processed prior authorization requests are surfaced in a modern Streamlit UI for immediate Human-in-the-Loop review and override capabilities.

## 2. Architecture & Data Flow
The exact lifecycle of a document within this system follows a strict, folder-based microservice architecture:
- A prior authorization request begins as a mock PDF dropped into the `/mock_faxes` directory.
- The **Intake Engine** detects the PDF, applies `pdfplumber` (with `pytesseract` OCR fallback for scanned images) and `spaCy` NLP to extract critical fields, converting them into an EDI 278 string which is saved to `/edi_output`.
- The **Validation Engine** monitors `/edi_output`, parses the EDI file, and verifies member eligibility and dates against `member_database.json`. Invalid members are rejected immediately to `/processed_results`, while valid requests are moved to `/validated_requests`.
- The **Rules Engine** picks up EDI files from `/validated_requests`, adjudicates the clinical request (CPT codes, diagnosis, etc.) against the parameters defined in `policies.json`, and writes a final determination JSON (Approved/Rejected/Pending) to `/processed_results`.
- The **Dashboard** (Streamlit UI) continuously reads the JSON decisions from `/processed_results` to render the queue, providing reviewers visibility into the AI's data extractions and reasoning with manual override actions.

## 3. Directory Structure
```
e:\PriorAuth_Hackathon/
├── /mock_faxes/            # Drop location for incoming mock PDF faxes
├── /edi_output/            # Destination for generated EDI 278 files from the Intake Engine
├── /validated_requests/    # Destination for EDI files that passed administrative validation
├── /processed_results/     # Final JSON determinations (both administrative and clinical)
├── .streamlit/             # Streamlit configuration directory
├── __pycache__/            # Python bytecode cache
```

## 4. File Manifest
- **`intake_engine.py`**: Monitors `/mock_faxes`. Inputs: PDF files. Outputs: EDI 278 text files to `/edi_output`. Uses OCR and NLP for manual data extraction.
- **`validation_engine.py`**: Monitors `/edi_output`. Inputs: EDI 278 files. Outputs: Moves valid EDIs to `/validated_requests`, or generates REJECTED JSONs to `/processed_results` based on `member_database.json` checks.
- **`rules_engine.py`**: Monitors `/validated_requests`. Inputs: EDI 278 files. Outputs: Final JSON decision files to `/processed_results` after evaluating against `policies.json`.
- **`dashboard.py`**: The Streamlit user interface. Inputs: Reads JSON from `/processed_results` and PDFs from `/mock_faxes`. Outputs: A human-in-the-loop web UI for reviewing and overriding decisions.
- **`run_demo.py`**: Master orchestrator script. Automates directory creation, PDF generation, and sequentially launches the backend microservices and the Streamlit dashboard.
- **`generate_mock_faxes.py`**: Utility script to generate clean, text-based mock PDF faxes.
- **`generate_scanned_fax.py`**: Utility script to generate image-based mock PDF faxes for testing OCR fallback.
- **`member_database.json`**: Input mock database containing member eligibility statuses.
- **`policies.json`**: Input mock database containing clinical rules for adjudication.
- **`requirements.txt`**: Standard Python dependencies manifest.

## 5. Tech Stack & Dependencies
The core technologies driving this pipeline include:
- **Streamlit**: Web application framework for the UI dashboard.
- **spaCy**: Natural Language Processing library for entity extraction.
- **pytesseract** & **pdf2image**: Optical Character Recognition for scanned PDFs.
- **pdfplumber**: Direct text extraction from standard PDFs.

*Note:* After installing dependencies from `requirements.txt`, you must specifically download the spaCy English model by running:
`python -m spacy download en_core_web_sm`

## 6. AI Directives (Strict Rules for Claude)
- **Do not alter the microservice folder routing.**
- **Do not change the EDI 278 generation format.**
- **This is a hackathon prototype, prioritize working happy-path execution over edge-case error handling.**
