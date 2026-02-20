# Treasury Integration Module

## 📋 Overview

This module provides a REST API endpoint for exporting approved transaction data from the Municipality Financial System to the external Treasury System (Samaneh Khazaneh-dari).

**Version**: 1.0.0  
**Date**: 2025-01-29  
**Status**: Production Ready

---

## 🎯 Purpose

The Treasury System requires transaction data in a specific format with the following fields:
- `code_yekta` - Unique 11-part transaction code
- `amount` - Transaction amount in Rials
- `submission_date` - Transaction approval date
- `financial_event` - Financial event details (ID and name)
- `activity` - Activity details (ID and name)

This module automatically extracts and formats data from the municipality database to match this requirement.

---

## 📦 Files Included

### Core Implementation
- `app/routers/treasury_integration.py` - Main API router implementation
- `app/routers/__init__.py` - Router registration (modified)
- `app/main.py` - FastAPI app integration (modified)

### Documentation
- `TREASURY_API_DOC.txt` - Complete handover document for Treasury Manager
- `TREASURY_QUICK_REFERENCE.md` - Quick reference guide
- `TREASURY_TECHNICAL_SUMMARY.md` - Technical implementation details
- `TREASURY_README.md` - This file

### Testing
- `test_treasury_api.py` - Automated test suite

---

## 🚀 Quick Start

### 1. Installation

The module is already integrated into the main application. No additional installation needed.

### 2. Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test the API

#### Health Check
```bash
curl http://localhost:8000/api/v1/treasury/health
```

#### Login (get session cookie)
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  -c cookies.txt
```

#### Export Data
```bash
curl http://localhost:8000/api/v1/treasury/export?limit=10 \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

### 4. Run Automated Tests

```bash
python test_treasury_api.py
```

---

## 📖 API Documentation

### Endpoint URL
```
GET /api/v1/treasury/export
```

### Authentication
Required. User must have one of these roles:
- `admin`
- `ACCOUNTANT`
- `ADMIN_L1`, `ADMIN_L2`, `ADMIN_L3`, `ADMIN_L4`
- `inspector`

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | `APPROVED` | Filter by status (APPROVED, POSTED, ALL) |
| `date_from` | string | - | Start date (YYYY-MM-DD) |
| `date_to` | string | - | End date (YYYY-MM-DD) |
| `zone_id` | integer | - | Filter by zone/region |
| `limit` | integer | 1000 | Max records (1-10000) |
| `offset` | integer | 0 | Pagination offset |

### Response Example

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

### Additional Endpoints

#### Summary Statistics
```
GET /api/v1/treasury/export/summary
```

Returns:
```json
{
  "total_transactions": 1523,
  "total_amount": 45230000000,
  "date_range": {
    "from": "2025-01-01",
    "to": "2025-01-31"
  },
  "zones_count": 14,
  "status": "success"
}
```

#### Health Check
```
GET /api/v1/treasury/health
```

Returns:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-29T10:30:45.123456",
  "service": "Treasury Integration API",
  "version": "1.0.0"
}
```

---

## 🗺️ Data Mapping

| API Field | Database Source | Description |
|-----------|----------------|-------------|
| `code_yekta` | `transactions.unique_code` | 11-part unique identifier |
| `amount` | `transactions.amount` | Amount in Rials (numeric) |
| `submission_date` | `transactions.reviewed_at` | Approval date (YYYY-MM-DD) |
| `financial_event.id` | `financial_event_refs.id` | Event ID |
| `financial_event.name` | `financial_event_refs.title` | Event name |
| `activity.id` | `subsystem_activities.id` | Activity ID |
| `activity.name` | `subsystem_activities.title` | Activity name |

---

## 🔒 Security

### Authentication
- Session-based authentication (cookie)
- Must login via `/auth/login` first
- Session expires after inactivity

### Authorization
- Role-based access control (RBAC)
- Only specific roles can access the API
- Additional zone-based filtering possible

### Data Access
- Only approved transactions are exported
- Transactions without required fields are excluded
- No sensitive user data is exposed

---

## 🧪 Testing

### Manual Testing

1. **Health Check**
   ```bash
   curl http://localhost:8000/api/v1/treasury/health
   ```
   Expected: `{"status": "healthy"}`

2. **Login**
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin"}' \
     -c cookies.txt
   ```
   Expected: `{"status": "success"}`

3. **Export Data**
   ```bash
   curl http://localhost:8000/api/v1/treasury/export?limit=5 \
     -b cookies.txt
   ```
   Expected: Array of transaction objects

### Automated Testing

Run the test suite:
```bash
python test_treasury_api.py
```

This runs 8 tests:
1. Health check
2. Authentication
3. Unauthorized access prevention
4. Summary statistics
5. Basic export
6. Date filtering
7. Invalid date format handling
8. Pagination

---

## 📊 Performance

### Expected Performance
- **Single record**: ~5-10ms
- **100 records**: ~50-100ms
- **1000 records**: ~200-500ms
- **10000 records**: ~2-5s

### Optimization Tips
1. Use date filters to reduce dataset size
2. Use pagination for large datasets
3. Query during off-peak hours for best performance
4. Consider caching if querying same date range repeatedly

---

## 🛠️ Troubleshooting

### Common Issues

**Issue**: `401 Unauthorized`  
**Solution**: Login first to get session cookie

**Issue**: `403 Forbidden`  
**Solution**: Contact admin to grant appropriate role

**Issue**: Empty array `[]` returned  
**Solution**: Check date filters - there may be no data in that range

**Issue**: `400 Bad Request - Invalid date format`  
**Solution**: Use YYYY-MM-DD format (e.g., 2025-01-29, not 2025/01/29)

**Issue**: Slow response  
**Solution**: Reduce `limit` parameter or add date filters

---

## 📚 Documentation

### For Treasury Manager
- **`TREASURY_API_DOC.txt`** - Complete handover document with examples
- **`TREASURY_QUICK_REFERENCE.md`** - Quick reference guide

### For Developers
- **`TREASURY_TECHNICAL_SUMMARY.md`** - Technical implementation details
- **`app/routers/treasury_integration.py`** - Source code with inline documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔄 Integration Examples

### Python
```python
import requests

# Login
session = requests.Session()
session.post(
    "http://localhost:8000/auth/login",
    json={"username": "admin", "password": "admin"}
)

# Export data
response = session.get(
    "http://localhost:8000/api/v1/treasury/export",
    params={"date_from": "2025-01-01", "limit": 1000}
)

transactions = response.json()
for tx in transactions:
    print(f"Code: {tx['code_yekta']}, Amount: {tx['amount']}")
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

// Login
const session = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true
});

await session.post('/auth/login', {
  username: 'admin',
  password: 'admin'
});

// Export data
const response = await session.get('/api/v1/treasury/export', {
  params: {
    date_from: '2025-01-01',
    limit: 1000
  }
});

const transactions = response.data;
console.log(`Retrieved ${transactions.length} transactions`);
```

### cURL (Shell Script)
```bash
#!/bin/bash

# Login and save cookies
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  -c cookies.txt

# Export data
curl "http://localhost:8000/api/v1/treasury/export?limit=1000" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -o treasury_export.json

echo "Data exported to treasury_export.json"
```

---

## 🚦 Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | Success | Data retrieved successfully |
| 400 | Bad Request | Invalid parameters (e.g., date format) |
| 401 | Unauthorized | Not authenticated |
| 403 | Forbidden | Insufficient permissions |
| 500 | Server Error | Internal error |

---

## 📝 Change Log

### Version 1.0.0 (2025-01-29)
- Initial release
- Basic export functionality
- Authentication and authorization
- Date and zone filtering
- Pagination support
- Summary statistics endpoint
- Health check endpoint
- Complete documentation

---

## 🤝 Support

### For Questions
- **Technical Issues**: Contact IT Department
- **API Usage**: See `TREASURY_API_DOC.txt`
- **Integration Help**: See `TREASURY_TECHNICAL_SUMMARY.md`

### For Bugs or Feature Requests
- Document the issue with:
  - Request URL and parameters
  - Expected behavior
  - Actual behavior
  - Error message (if any)
- Contact development team

---

## 📄 License

This module is part of the Municipality Financial System.  
Developed for Isfahan Municipality - Financial Department.

---

**Last Updated**: 2025-01-29  
**Module Version**: 1.0.0  
**API Version**: 1.0.0
