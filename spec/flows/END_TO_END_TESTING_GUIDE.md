# EmoScreen End-to-End Local Testing Guide

This guide tests the full local doctor -> patient -> payment/free form -> submission -> report -> audit workflow.

The current local test setup uses:

- Base URL: `http://127.0.0.1:8000`
- Test doctor code: `C488DF49`
- Local staff login: `local_doctor_C488DF49`
- Local staff password: `LocalPass123!`
- Payment mode: local dummy gateway only
- Languages to verify: `en`, `hi`, `ta`, `te`, `ml`, `mr`, `bn`, `kn`

Do not use real Razorpay keys for this test cycle.

## 1. Start Local Environment

### Terminal

Run these commands from the project root:

```bash
cd /Users/inditech-tech/Documents/PaidEmoscreen/EmoscreenPaid
export PATH="$HOME/.local/python-builds/3.11.15/python/bin:$PATH"
source .venv/bin/activate
./scripts/start_local_mysql.sh
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Expected result:

- Server starts at `http://127.0.0.1:8000/`
- `python manage.py check` reports no issues.
- MySQL is running locally on the configured local port.

## 2. Login Screen

### URL

`http://127.0.0.1:8000/admin/login/?next=/clinic/C488DF49/`

### What to do

1. Enter username: `local_doctor_C488DF49`
2. Enter password: `LocalPass123!`
3. Submit the login form.

### Expected result

- You are redirected to the doctor page.
- You should not see Google OAuth 401 errors.
- If you still see Google OAuth, go back to the admin login URL above and login again.

## 3. Home Screen

### URL

`http://127.0.0.1:8000/`

### What to verify

1. Navbar styling is applied.
2. Main landing page loads.
3. Buttons for registration, universal patient entry, and self screening are visible.
4. The page is responsive on desktop and mobile widths.

### Expected result

- Page loads with healthcare teal/blue styling.
- No 404s for CSS or JS in the server console.

## 4. Doctor Registration Screen

### URL

`http://127.0.0.1:8000/register/pediatrician/`

### What to do

1. Fill salutation, first name, last name, Gmail address, WhatsApp, IMC registration number, appointment booking number, clinic address, state, district, and receptionist WhatsApp.
2. Submit the form.

### Expected result

- A new doctor profile is created.
- A clinic sharing link is shown.
- Styling is applied to all form fields.

### Notes

Use this only when testing new doctor creation. For repeatable workflow testing, use existing doctor code `C488DF49`.

## 5. Doctor Workspace Screen

### URL

`http://127.0.0.1:8000/clinic/C488DF49/`

### What to do

1. Confirm the doctor/provider banner is visible.
2. Confirm the form contains:
   - Parent WhatsApp number
   - Language selector
   - Form selector
   - Patient name field for paid forms
   - Price selector for paid forms
3. Confirm available form choices include:
   - Behavioral free/red-flag form
   - Paid age-group forms

### Expected result

- The doctor can select either a free behavioral form or a paid form.
- Language selection is available for the free behavioral form.
- Paid forms are English-only.

## 6. Free Form Sharing Workflow

This tests doctor sharing a free behavioral screening form to a parent.

### Screen: Doctor Workspace

URL: `http://127.0.0.1:8000/clinic/C488DF49/`

### What to do

1. Enter parent WhatsApp number, for example `919123456780`.
2. Select a language, for example `English`.
3. Select `Behavioral: Behavioral and Emotional Red Flags`.
4. Submit.

### Expected result

- Browser redirects to a WhatsApp share URL.
- The WhatsApp message contains a local verification link like:
  `http://127.0.0.1:8000/verify/C488DF49/<token>/?lang=en`
- A workflow audit case is created with:
  - Form family: `LEGACY`
  - Status: `SENT`
  - Payment: `NOT_REQUIRED`

## 7. Free Form Parent Verification Screen

### URL

Use the verification link generated from the WhatsApp message.

Example pattern:

`http://127.0.0.1:8000/verify/C488DF49/<token>/?lang=en`

### What to do

1. Enter the same parent WhatsApp number used by the doctor.
2. Submit.

### Expected result

- Correct phone number redirects to language/form continuation.
- Incorrect phone number shows a mismatch error.
- Audit records:
  - `FORM_OPENED`
  - `PATIENT_VERIFIED`

## 8. Free Form Language Selection Screen

### URL

`http://127.0.0.1:8000/screen/C488DF49/`

### What to do

1. Select the intended language.
2. Continue to the screening form.

### Expected result

- User lands on:
  `http://127.0.0.1:8000/screen/C488DF49/<lang>/`
- The selected language is reflected in the form questions.

## 9. Free Screening Form Screen

### URL

Example:

`http://127.0.0.1:8000/screen/C488DF49/en/`

### What to do

1. Fill patient name.
2. Fill parent phone.
3. Fill patient email.
4. Fill date of birth.
5. Select gender.
6. Answer every question.
7. Submit.

### Expected result

- Missing required fields show validation errors.
- Completed form shows the result/report screen.
- Patient report email is simulated locally if SendGrid is not configured.
- Doctor report email is simulated locally when red flags are found.
- Audit status reaches `COMPLETED`.

## 10. Free Form Language Regression Test

Repeat the free screening form submission for every language:

| Language | URL Pattern |
| --- | --- |
| English | `/screen/C488DF49/en/` |
| Hindi | `/screen/C488DF49/hi/` |
| Tamil | `/screen/C488DF49/ta/` |
| Telugu | `/screen/C488DF49/te/` |
| Malayalam | `/screen/C488DF49/ml/` |
| Marathi | `/screen/C488DF49/mr/` |
| Bengali | `/screen/C488DF49/bn/` |
| Kannada | `/screen/C488DF49/kn/` |

### What to verify

1. Page loads for each language.
2. All questions render.
3. Form can be submitted.
4. Result screen appears.
5. No server errors occur.

### Expected result

- All 8 languages submit successfully.
- Audit cases are created and completed.

## 11. Paid Form Sharing Workflow

This tests doctor sharing a paid assessment with dummy local payment.

### Screen: Doctor Workspace

URL: `http://127.0.0.1:8000/clinic/C488DF49/`

### What to do

1. Enter parent WhatsApp number, for example `919876543211`.
2. Select any language. Paid forms remain English-only.
3. Select a paid form, for example:
   - `Paid: Emoscreen 0-2yrs 11 months`
   - `Paid: Emoscreen 3-5 years 11 months`
   - `Paid: Emoscreen 6-11yrs 11 months`
   - `Paid: Emoscreen 12-17yrs 11 months`
4. Enter patient name.
5. Select paid price, for example `Rs. 1`.
6. Submit.

### Expected result

- Browser redirects to WhatsApp.
- WhatsApp message includes paid link like:
  `http://127.0.0.1:8000/p/<order>/<doctor>/<form>/<amount>/<token>/`
- Audit case is created with:
  - Form family: `PAID`
  - Status: `SENT`
  - Payment status: `PENDING`

## 12. Paid Patient Entry Screen

### URL

Use the paid link generated from the WhatsApp message.

Example pattern:

`http://127.0.0.1:8000/p/<order_code>/C488DF49/<form_code>/<amount>/<token>/`

### What to do

1. Confirm form title and amount.
2. Enter patient email.
3. Click `Continue`.
4. Click `Proceed to Payment`.

### Expected result

- Patient email is saved.
- Audit records `FORM_OPENED` and `PATIENT_DETAILS_UPDATED`.
- User can proceed to dummy payment.

## 13. Dummy Payment Screen

### URL

Example pattern:

`http://127.0.0.1:8000/p/<order_code>/payment/`

### What to do: Success Path

1. Confirm the page says local dummy payment mode is enabled.
2. Click `Complete Dummy Payment`.

### Expected result

- No Razorpay popup opens.
- No real payment is charged.
- User redirects to the paid form.
- Order status becomes `PAID`.
- Audit payment status becomes `COMPLETED`.
- Payment gateway recorded as `dummy`.

### What to do: Failure Path

1. Click `Simulate Failure`.

### Expected result

- Payment failure message appears.
- Audit case records failure stage `PAYMENT`.
- User can retry by clicking `Complete Dummy Payment`.

## 14. Paid Assessment Form Screen

### URL

Example pattern:

`http://127.0.0.1:8000/p/<order_code>/form/`

### What to do

1. Fill child name.
2. Fill child date of birth.
3. Fill assessment date.
4. Select gender.
5. Fill completed by.
6. Check consent.
7. Answer every paid assessment question.
8. Submit.

### Expected result

- User redirects to review page.
- Draft answers are saved.
- Audit status becomes `IN_PROGRESS`.
- Completion percentage updates.

## 15. Paid Review Screen

### URL

Example pattern:

`http://127.0.0.1:8000/p/<order_code>/review/`

### What to do

1. Review all answers.
2. If incorrect, go back and edit.
3. If correct, submit final form.

### Expected result

- Final submit triggers scoring.
- Report generation starts.
- Audit records:
  - `FORM_SUBMITTED`
  - `REPORT_PROCESSING`
  - `REPORT_GENERATED`
  - `REPORT_SENT`
  - `WORKFLOW_COMPLETED`

## 16. Paid Thank You and Report Screen

### URL

Example pattern:

`http://127.0.0.1:8000/p/<order_code>/thank-you/`

### What to do

1. Confirm the report page loads.
2. Confirm patient and doctor report password hints are visible.
3. Download patient report.
4. Download doctor report.
5. Use `?refresh=1` to regenerate report if needed.

### Expected result

- Patient PDF and doctor PDF are available.
- Download attempts are audited as `REPORT_DOWNLOADED`.
- Existing report generation behavior remains unchanged.

## 17. Paid Orders Screen

### URL

`http://127.0.0.1:8000/clinic/C488DF49/paid/orders/`

### What to do

1. Confirm latest paid order appears.
2. Open the order detail screen.
3. Confirm order amount, patient details, payment state, and report/submission state.

### Expected result

- Paid orders are visible to the logged-in doctor.
- Order status updates after dummy payment and submission.

## 18. Self Screening Workflow

This tests a patient starting without a doctor-specific link.

### URL

`http://127.0.0.1:8000/start/self/`

### What to do

1. Enter patient/parent details as requested.
2. Submit/start.
3. Select language if prompted.
4. Fill the screening form.
5. Submit.

### Expected result

- Self screening uses the public doctor profile.
- Report is sent/simulated to the patient.
- Audit case is created with form family `SELF` or public screening context.
- No payment is required.

## 19. Universal Patient Entry Workflow

### URL

`http://127.0.0.1:8000/start/universal/`

### What to do

1. Enter the required patient/parent details.
2. Continue to language/form selection.
3. Fill and submit the free screening form.

### Expected result

- Universal flow reaches the same screening form.
- Submission and report work without a doctor-specific WhatsApp link.
- Audit captures source as universal entry.

## 20. Global Start Workflow

### URL

`http://127.0.0.1:8000/start/global/`

### What to do

1. Start from the global patient entry link.
2. Enter phone/details.
3. Continue through the screening form.
4. Submit.

### Expected result

- Patient can complete a screening from the global link.
- Audit captures source as global start.

## 21. Workflow Audit Dashboard

### URL

`http://127.0.0.1:8000/support/workflows/`

### What to do

1. Confirm the dashboard loads.
2. Review summary cards:
   - Total workflows
   - Completed
   - Payment pending
   - Submitted or later
   - Failed
   - Tracked paid revenue
3. Use filters:
   - Doctor
   - Patient/case/order
   - Date range
   - Form status
   - Payment status
   - Report status
   - Form family
4. Click a workflow case code.

### Expected result

- Dashboard lists latest workflow cases.
- Filters narrow results correctly.
- Each row shows doctor, patient, form, status, payment, progress, and last event.

## 22. Workflow Audit Detail Screen

### URL

Example:

`http://127.0.0.1:8000/support/workflows/<case_code>/`

### What to verify

1. Current status pill is visible.
2. Doctor section shows doctor name, code, and email.
3. Patient section shows patient name, WhatsApp, email, and completion.
4. Payment section shows required flag, amount, gateway, reference, paid time, and errors.
5. Report section shows generation and delivery state.
6. Event timeline shows immutable history.
7. Delivery attempts table shows WhatsApp/email attempts.
8. Retry links appear where applicable.

### Expected result

- Support can answer:
  - Which doctor sent the form?
  - Which patient received it?
  - Was it paid or free?
  - Was payment completed?
  - Did the patient open/start/submit?
  - Was report generated and delivered?
  - Where did a failure happen?

## 23. Admin Audit Screens

### URL

`http://127.0.0.1:8000/admin/`

### What to do

Open these admin models:

- Workflow cases
- Workflow events
- Workflow delivery attempts
- Workflow payments
- Workflow reports

### Expected result

- Admin can inspect raw audit records.
- Workflow events are append-only records.
- Cases can be searched by case code, doctor, patient, phone, email, and order code.

## 24. Existing Legacy Reports Dashboard

### URL

`http://127.0.0.1:8000/admin/reports/`

### What to do

1. Open the legacy reports dashboard.
2. Apply date filters if available.
3. Export if required.

### Expected result

- Existing report dashboard still works.
- New workflow dashboard does not replace or break this report.

## 25. Negative Test Cases

| Test | Steps | Expected Result |
| --- | --- | --- |
| Wrong verification phone | Open free verification link and enter a different phone number | Error is shown, form is not opened |
| Unpaid paid form access | Open `/p/<order>/form/` before payment | Redirects to payment screen |
| Dummy payment failure | Click `Simulate Failure` | Failure is recorded and retry is available |
| Missing paid form fields | Submit paid assessment with unanswered required details | Validation prevents submission |
| Missing free form fields | Submit free screening with unanswered fields | Validation prevents submission |
| Report refresh | Open thank-you URL with `?refresh=1` | Report regenerates without changing existing report flow |
| Dashboard filters | Filter by payment pending or failed | Only matching cases appear |

## 26. Expected Audit Pipeline

### Free form

Expected status progression:

`CREATED -> SENT -> OPENED -> IN_PROGRESS -> SUBMITTED -> REPORT_GENERATED -> REPORT_SENT -> COMPLETED`

Payment status:

`NOT_REQUIRED`

### Paid form

Expected status progression:

`CREATED -> SENT -> OPENED -> PAYMENT_PENDING -> PAYMENT_COMPLETED -> IN_PROGRESS -> SUBMITTED -> REPORT_PROCESSING -> REPORT_GENERATED -> REPORT_SENT -> COMPLETED`

Payment status:

`PENDING -> COMPLETED`

### Failure

Expected status:

`FAILED`

Expected fields:

- Failure stage
- Failure timestamp
- Failure reason
- Retry action where applicable

## 27. Reference Screenshots

Existing reference screenshots are stored under:

- `spec/flows/Flow1-Doctor/`
- `spec/flows/Flow2-Parent/`

Useful files:

- `Flow1-Doctor/flow-01-step-01-DoctorFormSelection.png`
- `Flow1-Doctor/flow-01-step-02-DoctorSendsFormToPatient_WhatsappMessage.png`
- `Flow2-Parent/flow-02-step-01-1-PatientClicksLinkToPayment.png`
- `Flow2-Parent/flow-02-step-01-2-PatientPaymentInformationFormAndCompletesPayment.png`
- `Flow2-Parent/flow-02-step-03-1-ParentClicksLinktoForm.png`
- `Flow2-Parent/flow-02-step-04-1-ParentReviewsFormAnswers.png`
- `Flow2-Parent/flow-02-step-05-ParentSubmitsForm_ThankYouScreen.png`
- `Flow2-Parent/flow-02-step-06-ParentRecivesReportonMail.png`

## 28. Test Completion Checklist

Mark complete only when all items pass:

- [ ] Local server starts without errors.
- [ ] Doctor login works without Google OAuth 401.
- [ ] Doctor workspace loads.
- [ ] Doctor can share a free form.
- [ ] Parent can verify phone for free form.
- [ ] Parent can complete free form.
- [ ] Free report/result screen appears.
- [ ] All 8 languages load and submit.
- [ ] Doctor can share a paid form.
- [ ] Paid patient entry saves email.
- [ ] Dummy payment success works.
- [ ] Dummy payment failure works and is retryable.
- [ ] Paid assessment form saves answers.
- [ ] Paid review screen works.
- [ ] Paid final submit generates reports.
- [ ] Patient report download works.
- [ ] Doctor report download works.
- [ ] Paid orders screen reflects latest status.
- [ ] Self screening flow works.
- [ ] Universal/global flow works.
- [ ] Workflow audit dashboard loads.
- [ ] Workflow audit detail page shows full timeline.
- [ ] Legacy admin reports page still works.
- [ ] No server traceback occurs during testing.
