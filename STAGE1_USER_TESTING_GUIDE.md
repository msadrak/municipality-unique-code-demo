# Stage 1 Credit Request Gate – User Testing Guide

## 🚀 How to Run Backend and Frontend

### Prerequisites

1. **Python 3.10+** with pip
2. **Node.js 18+** with npm
3. **PostgreSQL** running locally
4. **Database** `municipality_demo` exists

---

### Step 1: Start the Backend

Open a terminal and run:

```powershell
cd h:\Freelancing_Project\KalaniProject\municipality_demo
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Verify backend:**
- Open http://localhost:8000/docs – Swagger API docs
- Check `/credit-requests` endpoints are listed

---

### Step 2: Start the Frontend

Open a **second** terminal and run:

```powershell
cd h:\Freelancing_Project\KalaniProject\municipality_demo\frontend
npm install
npm run dev
```

**Expected output:**
```
VITE ready in ... ms
Local:   http://localhost:3000/
```

The frontend dev server proxies API calls to the backend on port 8000.

---

### Step 3: Ensure Users Exist

If you have not created users yet, run:

```powershell
cd h:\Freelancing_Project\KalaniProject\municipality_demo
python scripts\create_users.py
```

Or use the seed script if available. You need at least:

- **Regular user**: e.g. `user` / `user` or `test_user` / `user123`
- **Admin user**: e.g. `admin` / `admin` or `admin` / `admin123`

---

## ✅ What to Test as a User (Stage 1 Flow)

### A. Login

1. Open **http://localhost:3000** (or http://localhost:3000/login)
2. Log in as a **regular user** (e.g. `user` / `user`)
3. You should be redirected to the User Portal

---

### B. Credit Request Flow (تامین اعتبار)

1. In the User Portal, click the **"تامین اعتبار"** (Credit Provision) tab
2. **Create a credit request**
   - Click "ایجاد درخواست جدید" or similar
   - Fill in:
     - **منطقه (Zone)**: e.g. 20
     - **کد بودجه (Budget code)**: e.g. 11020401 (must exist in DB)
     - **مبلغ (Amount)**: e.g. 250000000
     - **شرح (Description)**: e.g. "تست درخواست تامین اعتبار"
   - Submit
3. **Verify**: New CR appears with status **پیش‌نویس (DRAFT)**

4. **Submit for approval**
   - Open the CR you created
   - Click **ارسال (Submit)**
   - Status changes to **ارسال شده (SUBMITTED)**

---

### C. Admin Approval

1. **Log out** and log in as **admin** (e.g. `admin` / `admin`)
2. Open **Admin Dashboard**
3. Go to **"تامین اعتبار"** tab
4. **Approve** the SUBMITTED credit request
   - Click on the CR
   - Click **تأیید (Approve)**
   - Optionally adjust approved amount
5. **Verify**: Status becomes **تأیید شده (APPROVED)**

---

### D. Create Transaction (Gate Enforcement)

1. **Log in again as the regular user**
2. In User Portal, start creating a **new transaction**
3. Go through the wizard:
   - Choose activity / organization
   - Select zone, department, section
   - Select budget code and amount
   - Add beneficiary

4. **On the last step (Preview / Submit)**:
   - You must **select a credit request**
   - If none available, you see a message like "درخواست تامین اعتبار موجود نیست"
   - Select your APPROVED credit request
   - Ensure amount ≤ approved amount
5. **Submit**
6. **Verify**: Transaction is created and appears in "تراکنش‌های من"

---

### E. Gate Enforcement Checks

| Test | Expected Result |
|------|-----------------|
| Submit transaction **without** selecting a CR | Error: "تامین اعتبار الزامی است" / submit button disabled |
| Use a DRAFT or SUBMITTED CR | Error: "وضعیت درخواست تامین اعتبار نامعتبر است" |
| Use an already-used CR | Error: "این درخواست تامین اعتبار قبلاً استفاده شده است" |
| Transaction amount > CR approved amount | Error: "مبلغ تراکنش از سقف تامین اعتبار تأیید شده بیشتر است" |

---

## 📋 Quick Checklist

- [ ] Backend runs on port 8000
- [ ] Frontend runs on port 3000
- [ ] Can log in as user and admin
- [ ] Can create DRAFT credit request
- [ ] Can submit CR (DRAFT → SUBMITTED)
- [ ] Admin can approve CR (SUBMITTED → APPROVED)
- [ ] Can select APPROVED CR in transaction wizard
- [ ] Cannot submit transaction without selecting CR
- [ ] Cannot use same CR twice
- [ ] Can view CR audit logs (سوابق)

---

## 🐛 Troubleshooting

### "Cannot connect to database"
- Start PostgreSQL
- Check `app/database.py` connection string

### "404 on /credit-requests"
- Ensure `credit_requests_router` is registered in `app/main.py`
- Ensure frontend vite proxy includes `/credit-requests` (see `vite.config.ts`)

### "No zones / budget codes in dropdown"
- Run seed scripts: `scripts/inject_test_budget.py`, org seed, etc.
- Check that `org_units` and `budget_items` have data

### "Login fails"
- Run `python scripts/create_users.py`
- Check `users` table has rows

### Frontend shows blank / wrong page
- Use **http://localhost:3000** when running `npm run dev`
- For production-style test: run `npm run build` in frontend, then access via backend at http://localhost:8000/portal

---

## 🔗 URLs Summary

| Purpose | URL |
|--------|-----|
| Frontend (dev) | http://localhost:3000 |
| Backend API docs | http://localhost:8000/docs |
| Login (via backend) | http://localhost:8000/login |
| User Portal (via backend) | http://localhost:8000/portal |
| Admin (via backend) | http://localhost:8000/admin |
