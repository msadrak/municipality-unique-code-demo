# User Testing Guide - Municipality Demo System

## 🌐 Accessing the Application

The backend server is running at **http://localhost:8000**

### Available Pages:

1. **Public Dashboard (No Login Required)**
   - URL: http://localhost:8000/
   - Shows general statistics and public information

2. **Login Page**
   - URL: http://localhost:8000/login
   - Login to access user/admin portals

3. **User Portal** (After Login)
   - URL: http://localhost:8000/portal
   - For regular users to create transactions

4. **Admin Dashboard** (After Login)
   - URL: http://localhost:8000/admin
   - For administrators to manage transactions

5. **API Documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

---

## 🔐 Login Credentials

Based on the codebase, try these credentials:

### Option 1: Default Credentials (from login.html)
- **Regular User**: `user` / `user`
- **Admin**: `admin` / `admin`

### Option 2: Seeded Users (if database is seeded)
- **Regular User**: `test_user` / `user123`
- **Admin**: `admin` / `admin123`

**Note**: If login fails, you may need to create users first. See "Creating Users" section below.

---

## ✅ What to Test as a User

### 1. **Public Dashboard** (No Login Required)
   - ✅ Visit http://localhost:8000/
   - ✅ Check if statistics cards display (Total Transactions, Active Budgets, Unique Codes, Total Amounts)
   - ✅ Check if "Recent Activity" table loads
   - ✅ Test tab switching (General Stats, Budget Status, Unique Codes)
   - ✅ Verify "Login" button redirects to login page

### 2. **Login Functionality**
   - ✅ Visit http://localhost:8000/login
   - ✅ Try logging in with credentials
   - ✅ Check error messages for wrong credentials
   - ✅ Verify redirect after successful login:
     - Admin users → `/admin`
     - Regular users → `/portal`
   - ✅ Test "View Public Dashboard" link (no login required)

### 3. **User Portal** (Regular User)
   After logging in as a regular user, test:

   - ✅ **Transaction Creation Wizard**
     - Navigate through wizard steps
     - Fill organization details (Zone, Department, Section)
     - Select budget items
     - Choose financial events
     - Add beneficiary information
     - Upload attachments (if available)
     - Preview transaction
     - Submit transaction

   - ✅ **My Transactions List**
     - View list of your submitted transactions
     - Check transaction status (Pending, Approved, Rejected)
     - View transaction details
     - Filter/search transactions

   - ✅ **Dashboard**
     - View activity cards
     - Check statistics
     - Navigate to different sections

### 4. **Admin Dashboard** (Admin User)
   After logging in as admin, test:

   - ✅ **Transaction Management**
     - View all transactions (pending, approved, rejected)
     - Filter transactions by status, user, date
     - Review transaction details
     - Approve/reject transactions
     - Check 4-level approval workflow

   - ✅ **User Management**
     - View user list
     - Create/edit users
     - Assign roles and permissions
     - Manage user access

   - ✅ **Budget Management**
     - View budget items
     - Check budget allocations
     - Monitor budget usage

   - ✅ **Reports & Analytics**
     - View transaction reports
     - Check financial summaries
     - Export data

### 5. **API Endpoints** (Optional - for technical testing)
   Visit http://localhost:8000/docs to test API endpoints:
   - ✅ Health check: `/api/v1/treasury/health`
   - ✅ Authentication: `/auth/login`, `/auth/me`
   - ✅ Transactions: `/portal/transactions`
   - ✅ Budget: `/budget-items`
   - ✅ Treasury Export: `/api/v1/treasury/export`

---

## 🛠️ Creating Users (If Login Fails)

If you get login errors, you may need to create users first. Run this script:

```bash
cd h:\Freelancing_Project\KalaniProject\municipality_demo
python scripts\create_users.py
```

Or use the seed script:
```bash
python scripts\seed_users.py
```

This will create:
- **admin** / **admin123** (Admin user)
- **test_user** / **user123** (Regular user)

---

## 🐛 Common Issues & Solutions

### Issue: "Cannot connect to database"
**Solution**: Make sure PostgreSQL is running
- Check: `Get-Service -Name postgresql*` (Windows)
- Start PostgreSQL service if needed

### Issue: "Login fails with correct credentials"
**Solution**: 
1. Users may not exist - run `python scripts\create_users.py`
2. Password hash may be outdated - run `python scripts\seed_users.py`

### Issue: "No data showing in dashboard"
**Solution**: 
- Database may be empty
- Run seed scripts to populate test data:
  ```bash
  python scripts\seed_budget.py
  python scripts\seed_org.py
  ```

### Issue: "Frontend not loading"
**Solution**: 
- The backend serves HTML files directly
- Make sure backend is running on port 8000
- Try accessing http://localhost:8000/login directly

---

## 📋 Testing Checklist

### Basic Functionality
- [ ] Can access public dashboard without login
- [ ] Can access login page
- [ ] Can login as regular user
- [ ] Can login as admin
- [ ] Can logout
- [ ] Can navigate between pages

### User Portal Features
- [ ] Can create new transaction
- [ ] Can view my transactions
- [ ] Can see transaction status
- [ ] Can view transaction details
- [ ] Dashboard shows correct statistics

### Admin Features
- [ ] Can view all transactions
- [ ] Can filter transactions
- [ ] Can approve/reject transactions
- [ ] Can view user list
- [ ] Can manage users
- [ ] Can view reports

### Data Validation
- [ ] Required fields are validated
- [ ] Error messages are clear
- [ ] Form submissions work correctly
- [ ] Data persists after submission

---

## 🎯 Key Features to Test

1. **Transaction Workflow**
   - Create transaction → Submit → Admin Review → Approval/Rejection

2. **Budget Integration**
   - Select budget items
   - Check budget availability
   - Verify budget constraints

3. **Multi-level Approval**
   - Test 4-level approval workflow
   - Check status at each level

4. **User Permissions**
   - Regular users can only see their transactions
   - Admins can see all transactions
   - Role-based access control

5. **Treasury Integration**
   - Export data to treasury system
   - Check treasury API endpoints

---

## 📞 Need Help?

- Check API documentation: http://localhost:8000/docs
- Review backend logs in terminal
- Check database connection in `app/database.py`
- Verify PostgreSQL is running

---

**Happy Testing! 🚀**
