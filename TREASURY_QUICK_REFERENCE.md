# Treasury Integration API - Quick Reference

## 🎯 Quick Start

### 1. Check API Health
```bash
GET http://localhost:8000/api/v1/treasury/health
```

### 2. Login
```bash
POST http://localhost:8000/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

### 3. Get Treasury Data
```bash
GET http://localhost:8000/api/v1/treasury/export
Cookie: [session cookie from login]
```

---

## 📊 Response Example

```json
[
  {
    "code_yekta": "20-02-015-11020401-001-01-000-A1B2C3-001-1403-001",
    "amount": 10000000,
    "submission_date": "2025-01-29",
    "financial_event": {
      "id": 1,
      "name": "تامین اعتبار"
    },
    "activity": {
      "id": 1,
      "name": "پرداخت حقوق"
    }
  }
]
```

---

## 🔧 Common Query Parameters

| Parameter | Example | Description |
|-----------|---------|-------------|
| `status` | `APPROVED` | Filter by status (APPROVED, POSTED, ALL) |
| `date_from` | `2025-01-01` | Start date (YYYY-MM-DD) |
| `date_to` | `2025-12-31` | End date (YYYY-MM-DD) |
| `zone_id` | `5` | Filter by region |
| `limit` | `1000` | Max records (1-10000) |
| `offset` | `0` | Pagination offset |

---

## 🔍 Example Queries

### Get January 2025 transactions
```
/api/v1/treasury/export?date_from=2025-01-01&date_to=2025-01-31
```

### Get Region 5 transactions
```
/api/v1/treasury/export?zone_id=5
```

### Get with pagination (first 500)
```
/api/v1/treasury/export?limit=500&offset=0
```

### Get summary statistics
```
/api/v1/treasury/export/summary?date_from=2025-01-01&date_to=2025-01-31
```

---

## 📋 Data Field Mapping

| API Field | Source Database | Description |
|-----------|----------------|-------------|
| `code_yekta` | `transactions.unique_code` | 11-part unique code |
| `amount` | `transactions.amount` | Amount in Rials |
| `submission_date` | `transactions.reviewed_at` | Approval date |
| `financial_event.id` | `financial_event_refs.id` | Event ID |
| `financial_event.name` | `financial_event_refs.title` | Event name |
| `activity.id` | `subsystem_activities.id` | Activity ID |
| `activity.name` | `subsystem_activities.title` | Activity name |

---

## ⚠️ Important Notes

- **Authentication Required**: Must login first to get session cookie
- **Required Roles**: admin, ACCOUNTANT, ADMIN_L1-L4, inspector
- **Amount Format**: Number (not string), in Rials
- **Date Format**: YYYY-MM-DD (ISO format)
- **Character Encoding**: UTF-8
- **Default Status**: APPROVED transactions only
- **Max Limit**: 10,000 records per request

---

## 🚨 Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | No session cookie | Login first |
| 403 Forbidden | Insufficient role | Contact admin |
| 400 Bad Request | Invalid date format | Use YYYY-MM-DD |
| Empty array `[]` | No matching data | Adjust filters |

---

## 📞 Support

- **Documentation**: See `TREASURY_API_DOC.txt` for full details
- **Interactive Docs**: http://localhost:8000/docs
- **Technical Support**: Contact IT Department

---

**Version**: 1.0  
**Last Updated**: 2025-01-29
