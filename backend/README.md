# MoTA Unified Scholarship Platform — Backend

Backend service for **SIH26238: Unified Scholarship Mobile Application for Tribal Students** (Ministry of Tribal Affairs).

---

## 1. Overview & Purpose

This backend provides a clean, secure, and asynchronous REST API for the MoTA Unified Scholarship Platform. It interfaces with an existing Supabase PostgreSQL database containing 11 pre-configured tables prefixed with `tribe_`.

### Implemented Scope:
- **Batch 1**:
  - Project setup with modular FastAPI & Pydantic architecture
  - Supabase integration with dual client model (Public Anonymous & Privileged Service Role)
  - Supabase Auth integration (Register, Login, `/auth/me`)
  - Student Profile APIs with strict token ownership verification
- **Batch 2**:
  - **Scholarship APIs**: 5 public read-only endpoints (all active schemes, scheme by ID, scheme by code, safe search, and summary)
  - **Application APIs**: 5 protected endpoints (create application, list own applications, get own application by ID, update draft, delete draft)
  - Strict ownership scoping (students cannot view, modify, or delete another student's applications)
  - Duplicate application prevention per student, scholarship, and academic year
  - Safe business ID generation (`TRB-APP-000001`) and draft-only mutation enforcement
- **Batch 3**:
  - **Document APIs**: 6 protected endpoints (register document, list own documents, get document by ID, update editable metadata, delete document, document verification status)
  - **Verification APIs**: 3 protected student lookup endpoints (list all verifications, get verification by ID, get verification by document)
  - Strict ownership isolation (cross-student resource lookup returns `404 Not Found`)
  - Document mutation protection (verified documents cannot be modified or deleted)
  - Prohibition of student self-verification (verifier mutation endpoints are restricted)
- **Batch 4 (Phase 4)**:
  - **Payment APIs**: 4 protected endpoints (list own payments, get payment by ID, get payments by application ID, student payment summary)
  - Strict ownership isolation via JWT resolution (`JWT -> auth_user_id -> tribe_students.id -> tribe_disbursements`)
  - Internal database UUID obfuscation (business IDs `TRB-PAY-XXXXXX`, `TRB-APP-XXXXXX` exposed in responses)
  - Read-only student security (no client-side payment mutation endpoints)

---

## 2. Directory Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, CORS, error handlers, and routers
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic Settings (.env loader)
│   │   ├── security.py          # JWT decode and security utilities
│   │   └── dependencies.py      # get_current_user token auth dependency
│   ├── db/
│   │   ├── __init__.py
│   │   └── supabase.py          # Supabase client singletons (Anon & Service)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── student.py           # Domain model mapping to `tribe_students`
│   │   ├── scholarship.py       # Domain model mapping to `tribe_scholarships`
│   │   ├── institution.py       # Domain model mapping to `tribe_institutions`
│   │   ├── application.py       # Domain model mapping to `tribe_applications`
│   │   ├── document.py          # Domain model mapping to `tribe_documents`
│   │   ├── verification.py      # Domain models mapping to verification tables
│   │   └── payment.py           # Domain model mapping to `tribe_disbursements`
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py              # Register, Login, AuthResponse schemas
│   │   ├── student.py           # StudentCreate, StudentUpdate, Status schemas
│   │   ├── scholarship.py       # ScholarshipResponse, List, Summary schemas
│   │   ├── application.py       # ApplicationCreate, Update, Response schemas
│   │   ├── document.py          # DocumentCreate, Update, Response schemas
│   │   ├── verification.py      # VerificationResponse, List, Detail schemas
│   │   └── payment.py           # PaymentResponse, List, Summary schemas
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api.py               # Base /api/v1 root route
│   │   ├── auth.py              # /api/v1/auth endpoints
│   │   ├── students.py          # /api/v1/students endpoints
│   │   ├── scholarships.py      # /api/v1/scholarships endpoints
│   │   ├── applications.py      # /api/v1/applications endpoints
│   │   ├── documents.py         # /api/v1/documents endpoints
│   │   ├── verifications.py     # /api/v1/verifications endpoints
│   │   └── payments.py          # /api/v1/payments endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Supabase Auth orchestration
│   │   ├── student_service.py   # tribe_students table operations
│   │   ├── scholarship_service.py # tribe_scholarships query operations
│   │   ├── application_service.py # tribe_applications workflow operations
│   │   ├── document_service.py    # tribe_documents workflow operations
│   │   ├── verification_service.py# verification lookup operations
│   │   └── payment_service.py     # tribe_disbursements lookup operations
│   └── utils/
│       ├── __init__.py
│       └── errors.py            # Structured exception classes & error handlers
├── tests/
│   ├── __init__.py
│   ├── test_health.py           # /health and /api/v1 tests
│   ├── test_auth.py             # Register, login, /auth/me tests
│   ├── test_students.py         # Student CRUD, status, and ownership tests
│   ├── test_scholarships.py     # Scholarship query, short code, search, summary tests
│   ├── test_applications.py     # Application CRUD, duplicate check, security tests
│   ├── test_documents.py        # Document CRUD, status guards, and ownership tests
│   ├── test_verifications.py    # Verification lookups and self-approval prevention tests
│   └── test_payments.py         # Payment lookups, summary, and cross-student isolation tests
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── bottle.txt                   # Primary development progress tracker
├── mouse.txt                    # Batch 2 progress tracker
└── chain.txt                    # Postman testing chain reference
```

---

## 3. Environment Variables Configuration

Create a `.env` file inside `backend/` based on `backend/.env.example`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
JWT_SECRET=your-supabase-jwt-secret
JWT_ALGORITHM=HS256
```

> [!CAUTION]
> Never commit `.env` or expose `SUPABASE_SERVICE_ROLE_KEY` or `JWT_SECRET` to the frontend.

---

## 4. Local Setup & Execution

### 1. Create and Activate Virtual Environment
```bash
cd backend
python3 -m venv .venv

# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run FastAPI Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

- **Base URL**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

---

## 5. API Endpoints Reference

### Health & Base Info
- `GET /health` — Service operational health check
- `GET /api/v1` — API metadata and version

---

### Authentication (`/api/v1/auth`)
- `POST /api/v1/auth/register` — Register a student account via Supabase Auth
- `POST /api/v1/auth/login` — Sign in with email and password, returns Bearer token
- `GET /api/v1/auth/me` — Retrieve current authenticated user profile *(Requires Bearer Token)*

---

### Student Management (`/api/v1/students`)
- `GET /api/v1/students/me` — Retrieve the authenticated student's profile from `tribe_students` *(Requires Bearer Token)*
- `POST /api/v1/students/me` — Create student profile linked to authenticated user UUID *(Requires Bearer Token)*
- `PUT /api/v1/students/me` — Update editable fields of authenticated student's profile *(Requires Bearer Token)*
- `GET /api/v1/students/me/status` — Check profile existence and completeness percentage *(Requires Bearer Token)*
- `GET /api/v1/students/{student_id}` — Protected profile lookup *(Requires Bearer Token; ownership verified)*

---

### Scholarship Schemes (`/api/v1/scholarships`)
*Read-only public endpoints for browsing MoTA schemes. No authentication required.*

- `GET /api/v1/scholarships` — Get all active scholarships
- `GET /api/v1/scholarships/summary` — Overview counts of total and active scholarship schemes
- `GET /api/v1/scholarships/search?q=<query>` — Safe keyword search across scheme titles, codes, types, and descriptions
- `GET /api/v1/scholarships/code/{short_name}` — Scheme lookup by short code (e.g. `PRE_MATRIC`, `POST_MATRIC`, `NFST`, `NOS`, `TOP_CLASS`)
- `GET /api/v1/scholarships/{scholarship_id}` — Scheme lookup by business identifier (e.g. `TRB-SCH-000001`)

---

### Student Applications (`/api/v1/applications`)
*Student workflow endpoints. Requires `Authorization: Bearer <token>` header.*

- `POST /api/v1/applications` — Create a new draft application
- `GET /api/v1/applications` — List all applications belonging to authenticated student
- `GET /api/v1/applications/{application_id}` — Retrieve specific application details *(Returns 404 if not owned)*
- `PUT /api/v1/applications/{application_id}` — Update allowable draft application fields *(Draft only)*
- `DELETE /api/v1/applications/{application_id}` — Delete a draft application *(Draft only)*

---

### Student Documents (`/api/v1/documents`)
*Student document management endpoints. Requires `Authorization: Bearer <token>` header.*

- `POST /api/v1/documents` — Register/upload a new student document
  - **Request Body**:
    ```json
    {
      "document_type": "CASTE_CERTIFICATE",
      "document_name": "Caste Certificate",
      "file_url": "https://storage.example.com/docs/caste.pdf",
      "storage_path": "documents/TRB-STU-000001/caste.pdf",
      "file_size": 102400,
      "file_type": "application/pdf",
      "document_number": "CC-2026-9876",
      "expiry_date": null
    }
    ```
- `GET /api/v1/documents` — List all active documents owned by the authenticated student
- `GET /api/v1/documents/{document_id}` — Get document details *(Returns 404 if not owned by student)*
- `PUT /api/v1/documents/{document_id}` — Update editable document metadata *(Verified documents cannot be updated)*
- `DELETE /api/v1/documents/{document_id}` — Delete a document *(Verified documents cannot be deleted)*
- `GET /api/v1/documents/{document_id}/verification` — Get verification status and remarks for a document

---

### Verifications (`/api/v1/verifications`)
*Student verification lookup endpoints. Requires `Authorization: Bearer <token>` header.*

- `GET /api/v1/verifications` — List all verification records across student documents and applications
- `GET /api/v1/verifications/{verification_id}` — Get verification record by ID *(Returns 404 if not owned)*
- `GET /api/v1/verifications/document/{document_id}` — Get verification details for a specific document

> [!NOTE]
> Verifier mutation workflow is restricted to authorized administrative personnel. Students cannot self-approve documents or alter verification levels.

---

### Payments & Disbursements (`/api/v1/payments`)
*Student disbursement lookup endpoints. Requires `Authorization: Bearer <token>` header.*

- `GET /api/v1/payments` — List all payment and disbursement records belonging strictly to the authenticated student
  - **Example Response**:
    ```json
    {
      "payments": [
        {
          "payment_id": "TRB-PAY-000001",
          "application_id": "TRB-APP-000001",
          "amount": 15000.0,
          "payment_status": "SUCCESS",
          "transaction_reference": "TXN-20261001-998811",
          "utr_number": "SBIN00019283746",
          "payment_date": "2026-10-01T14:30:00Z",
          "bank_name": "State Bank of India",
          "failure_reason": null,
          "academic_year": "2026-27",
          "scholarship": {
            "scholarship_id": "TRB-SCH-000001",
            "name": "Pre-Matric Scholarship for ST Students",
            "short_name": "PRE_MATRIC"
          },
          "created_at": "2026-10-01T14:00:00Z",
          "updated_at": "2026-10-01T14:30:00Z"
        }
      ],
      "count": 1
    }
    ```
- `GET /api/v1/payments/summary` — Student-level aggregated payment metrics (total, pending, processing, completed, failed, total amount, disbursed amount)
  - **Example Response**:
    ```json
    {
      "total_payments": 2,
      "pending_payments": 1,
      "processing_payments": 0,
      "completed_payments": 1,
      "failed_payments": 0,
      "total_amount": 30000.0,
      "disbursed_amount": 15000.0
    }
    ```
- `GET /api/v1/payments/application/{application_id}` — Get all disbursement records for a specific application *(Returns 404 if application not owned by student)*
- `GET /api/v1/payments/{payment_id}` — Get detailed disbursement record by payment ID *(Returns 404 if not owned by student)*

---

## 6. Security & Ownership Enforcement

1. **No Client-Supplied Identity Trust**: Student identity is derived exclusively from the validated JWT token (`auth_user_id`) mapped to `tribe_students.id`.
2. **Query & Payload Spoofing Protection**: Injected `student_id` or `auth_user_id` values in request bodies or query parameters are strictly ignored.
3. **Information Disclosure Prevention**: If Student A requests Student B's document, application, verification, or payment record, the API returns `404 Not Found` to prevent leaking that the record exists.
4. **Lifecycle & Mutation Guards**: Verified documents and non-draft applications are immutable and protected from student deletion.
5. **Self-Verification & Payment Mutation Prohibition**: No public endpoints exist for students to alter verification statuses or create/mutate payment records.
6. **Structured JSON Errors**: Errors follow a standard JSON schema:
   ```json
   {
     "error": {
       "code": "ERROR_CODE",
       "message": "Human readable message",
       "details": null
     }
   }
   ```

---

## 7. Running the Automated Test Suite

Run the full pytest suite:

```bash
cd backend
.venv/bin/pytest -v
```

### Test Coverage (92 Tests Total):
- **Health & API v1 Metadata**: 3 tests
- **Authentication**: 8 tests (Registration, validation, login, token extraction, invalid headers)
- **Student Profile Management**: 11 tests (Creation, updates, completeness status, ownership isolation)
- **Scholarship Schemes**: 10 tests (List active, ID lookup, short code lookup, keyword search, summary, validation)
- **Scholarship Applications**: 19 tests (Draft creation, listing, retrieval, update, deletion, invalid FKs, malformed academic year, duplicate protection, status guards, and UUID resolution)
- **Student Documents**: 15 tests (Registration, listing, detail lookup, editable update, deletion, verification info lookup, verified immutability guard, cross-student 404 isolation, spoofing prevention)
- **Verifications**: 8 tests (List student verifications, lookup by ID, document verification lookup, cross-student 404 isolation, student self-approval prevention)
- **Payments**: 18 tests (List payments, lookup by ID, application payment lookup, payment summary, cross-student isolation, spoofing prevention, mutation rejection, and service calculations)

