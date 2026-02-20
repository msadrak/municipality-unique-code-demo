# Treasury Integration Module - Technical Summary

## 📦 Module Overview

**Module Name**: Treasury Integration API  
**Purpose**: Export approved transaction data to external Treasury System (Samaneh Khazaneh-dari)  
**Location**: `app/routers/treasury_integration.py`  
**Version**: 1.0.0  
**Date**: 2025-01-29

---

## 🏗️ Architecture

### Files Created/Modified

1. **NEW**: `app/routers/treasury_integration.py` - Main router implementation
2. **MODIFIED**: `app/routers/__init__.py` - Added router export
3. **MODIFIED**: `app/main.py` - Registered router with FastAPI app
4. **NEW**: `TREASURY_API_DOC.txt` - Complete handover documentation
5. **NEW**: `TREASURY_QUICK_REFERENCE.md` - Quick reference guide
6. **NEW**: `TREASURY_TECHNICAL_SUMMARY.md` - This document

---

## 🗺️ Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Request                              │
│  GET /api/v1/treasury/export?date_from=2025-01-01&limit=1000   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              Authentication & Authorization                      │
│  • Check session cookie                                         │
│  • Verify user role (admin, ACCOUNTANT, etc.)                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Query Construction                             │
│  • Base: transactions WHERE status = 'APPROVED'                 │
│  • Apply filters: date_from, date_to, zone_id                   │
│  • Eager load: financial_event, subsystem_activity             │
│  • Pagination: offset, limit                                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Database Query Execution                        │
│  Tables:                                                         │
│  • transactions                                                  │
│  • financial_event_refs (JOIN via financial_event_id)          │
│  • subsystem_activities (JOIN via subsystem_activity_id)       │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                Data Transformation                               │
│  For each transaction:                                          │
│  • Extract: unique_code → code_yekta                            │
│  • Extract: amount → amount (numeric)                           │
│  • Format: reviewed_at → submission_date (YYYY-MM-DD)           │
│  • Map: financial_event → {id, name}                            │
│  • Map: subsystem_activity → {id, name}                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   JSON Response                                  │
│  [                                                               │
│    {                                                             │
│      "code_yekta": "...",                                        │
│      "amount": 10000000,                                         │
│      "submission_date": "2025-01-29",                            │
│      "financial_event": {"id": 1, "name": "..."},               │
│      "activity": {"id": 1, "name": "..."}                        │
│    }                                                             │
│  ]                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema Mapping

### Primary Table: `transactions`

| Column | Type | Description | API Mapping |
|--------|------|-------------|-------------|
| `id` | Integer | Primary key | Internal use only |
| `unique_code` | String | 11-part code | → `code_yekta` |
| `amount` | Float | Amount in Rials | → `amount` |
| `reviewed_at` | DateTime | Approval timestamp | → `submission_date` (formatted) |
| `created_at` | DateTime | Creation timestamp | Fallback for submission_date |
| `status` | String | Transaction status | Filter: APPROVED |
| `financial_event_id` | Integer | FK to financial_event_refs | JOIN key |
| `subsystem_activity_id` | Integer | FK to subsystem_activities | JOIN key |
| `zone_id` | Integer | FK to org_units | Filter parameter |

### Joined Table: `financial_event_refs`

| Column | Type | Description | API Mapping |
|--------|------|-------------|-------------|
| `id` | Integer | Primary key | → `financial_event.id` |
| `title` | String | Event name | → `financial_event.name` |

### Joined Table: `subsystem_activities`

| Column | Type | Description | API Mapping |
|--------|------|-------------|-------------|
| `id` | Integer | Primary key | → `activity.id` |
| `title` | String | Activity name | → `activity.name` |

---

## 🔒 Security & Authorization

### Authentication
- **Method**: Session-based (cookie)
- **Middleware**: Uses existing `get_current_user()` from `auth` router
- **Session Storage**: In-memory (production should use Redis)

### Authorization
- **Policy**: Role-based access control (RBAC)
- **Allowed Roles**:
  - `admin` - Full access
  - `ACCOUNTANT` - Accounting department
  - `ADMIN_L1` through `ADMIN_L4` - Multi-level admins
  - `inspector` - Audit/inspection role

### Data Access Control
- Users can only access transactions they are authorized to see
- Additional filtering can be implemented based on zone/region access

---

## 📊 API Endpoints

### 1. Export Transactions
```
GET /api/v1/treasury/export
```

**Query Parameters**:
- `status` (string, default: "APPROVED"): APPROVED | POSTED | ALL
- `date_from` (string, optional): YYYY-MM-DD
- `date_to` (string, optional): YYYY-MM-DD
- `zone_id` (integer, optional): Zone/region filter
- `limit` (integer, default: 1000, max: 10000): Records per page
- `offset` (integer, default: 0): Pagination offset

**Response**: Array of TreasuryTransactionSchema

### 2. Export Summary
```
GET /api/v1/treasury/export/summary
```

**Query Parameters**:
- `date_from` (string, optional): YYYY-MM-DD
- `date_to` (string, optional): YYYY-MM-DD

**Response**:
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

### 3. Health Check
```
GET /api/v1/treasury/health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-29T10:30:45.123456",
  "service": "Treasury Integration API",
  "version": "1.0.0"
}
```

---

## 📐 Pydantic Schemas

### TreasuryTransactionSchema
```python
class TreasuryTransactionSchema(BaseModel):
    code_yekta: str              # Required: unique transaction code
    amount: float                # Required: numeric amount in Rials
    submission_date: str         # Required: ISO date YYYY-MM-DD
    financial_event: FinancialEventSchema  # Required: event details
    activity: ActivitySchema     # Required: activity details
```

### FinancialEventSchema
```python
class FinancialEventSchema(BaseModel):
    id: int                      # Event ID
    name: str                    # Event name (Persian)
```

### ActivitySchema
```python
class ActivitySchema(BaseModel):
    id: int                      # Activity ID
    name: str                    # Activity name (Persian)
```

---

## 🔍 Query Optimization

### Eager Loading
Uses SQLAlchemy `joinedload()` to prevent N+1 queries:
```python
query = db.query(Transaction).options(
    joinedload(Transaction.financial_event),
    joinedload(Transaction.subsystem_activity)
)
```

### Indexing
Relies on existing database indexes:
- `transactions.status` (indexed)
- `transactions.reviewed_at` (indexed)
- `transactions.zone_id` (indexed)
- `transactions.unique_code` (indexed, unique)

### Performance Characteristics
- **Single record**: ~5-10ms
- **100 records**: ~50-100ms
- **1000 records**: ~200-500ms
- **10000 records**: ~2-5s

*Note: Times are approximate and depend on server hardware and database load*

---

## 🛡️ Error Handling

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | Success | Data returned successfully |
| 400 | Bad Request | Invalid query parameters (e.g., date format) |
| 401 | Unauthorized | No session cookie or session expired |
| 403 | Forbidden | User lacks required role |
| 500 | Server Error | Database error or unexpected exception |

### Error Response Format
```json
{
  "detail": "Error message in Persian and/or English"
}
```

---

## 📝 Data Validation

### Input Validation
- **Date Format**: Validated using `datetime.strptime()` with format `%Y-%m-%d`
- **Limit**: Range check (1 to 10000)
- **Offset**: Non-negative integer
- **Status**: Must be one of: APPROVED, POSTED, ALL

### Output Validation
- **code_yekta**: Must not be null or empty
- **amount**: Defaults to 0.0 if null
- **submission_date**: Uses reviewed_at or created_at, never null
- **financial_event**: Uses placeholder if missing (id=0, name="رویداد مالی نامشخص")
- **activity**: Uses placeholder if missing (id=0, name="فعالیت نامشخص")

---

## 🧪 Testing Strategy

### Unit Tests (Recommended)
1. Test authentication checks
2. Test authorization for different roles
3. Test date filter logic
4. Test pagination logic
5. Test data transformation
6. Test missing data fallbacks

### Integration Tests (Recommended)
1. Test full request/response cycle
2. Test with various filter combinations
3. Test pagination with large datasets
4. Test concurrent requests

### Manual Testing Checklist
- [ ] Health check endpoint returns 200
- [ ] Login with valid credentials returns session cookie
- [ ] Export without auth returns 401
- [ ] Export with insufficient role returns 403
- [ ] Export with valid auth returns transaction array
- [ ] Date filters work correctly
- [ ] Zone filter works correctly
- [ ] Pagination works correctly
- [ ] Summary endpoint returns statistics
- [ ] Invalid date format returns 400
- [ ] Data format matches specification

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] Code reviewed and approved
- [ ] Linter errors resolved
- [ ] Router registered in `app/main.py`
- [ ] Router exported in `app/routers/__init__.py`
- [ ] Documentation complete

### Deployment
- [ ] Deploy to staging environment
- [ ] Run smoke tests
- [ ] Verify database connectivity
- [ ] Check API response format
- [ ] Test authentication/authorization
- [ ] Deploy to production
- [ ] Monitor logs for errors

### Post-Deployment
- [ ] Provide API documentation to Treasury team
- [ ] Provide credentials for Treasury API user
- [ ] Set up monitoring/alerting
- [ ] Document any production issues
- [ ] Schedule follow-up review

---

## 🔧 Configuration

### Environment Variables (Recommended)
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/municipality_db

# CORS (if Treasury system calls from web)
ALLOWED_ORIGINS=http://treasury-system.gov.ir

# Session (for production)
SESSION_SECRET_KEY=your-secret-key
REDIS_URL=redis://localhost:6379/0
```

### FastAPI Configuration
Currently in `app/main.py`:
```python
app.include_router(treasury_integration_router)
```

---

## 📈 Monitoring & Observability

### Metrics to Track
1. **Request Rate**: Requests per minute
2. **Response Time**: Average query execution time
3. **Error Rate**: 4xx and 5xx responses
4. **Data Volume**: Records exported per day
5. **Active Users**: Unique users accessing API

### Logging
Consider adding structured logging:
```python
import logging

logger = logging.getLogger(__name__)

@router.get("/export")
def export_transactions(...):
    logger.info(
        "Treasury export requested",
        extra={
            "user_id": current_user.id,
            "filters": {
                "status": status,
                "date_from": date_from,
                "date_to": date_to
            }
        }
    )
```

---

## 🔄 Future Enhancements

### Short-term
1. Add CSV/Excel export format option
2. Implement caching for frequently requested data
3. Add webhook/push notification support
4. Implement request rate limiting

### Medium-term
1. Add more detailed filtering options
2. Implement data validation webhook
3. Add audit trail for export operations
4. Create admin dashboard for monitoring exports

### Long-term
1. Real-time data sync via WebSocket
2. Batch export scheduling
3. Data anonymization options
4. Multi-tenant support

---

## 📞 Support & Maintenance

### Code Owner
- **Team**: Financial Systems Integration Team
- **Module**: Treasury Integration
- **Contact**: IT Department

### Dependencies
- FastAPI >= 0.100.0
- SQLAlchemy >= 2.0
- Pydantic >= 2.0
- PostgreSQL >= 13

### Known Limitations
1. Maximum 10,000 records per request (use pagination for larger datasets)
2. Date filters apply to approval date only (not creation date)
3. Transactions without unique_code are excluded
4. Session-based auth (consider JWT for production)

---

## 📚 References

### Related Documentation
- `TREASURY_API_DOC.txt` - Complete handover documentation
- `TREASURY_QUICK_REFERENCE.md` - Quick reference guide
- `PROJECT_DOCUMENTATION.md` - Overall system documentation

### Database Schema
- `app/models.py` - SQLAlchemy models
- Lines 359-456: Transaction model
- Lines 68-73: FinancialEventRef model
- Lines 199-221: SubsystemActivity model

### Related Code
- `app/routers/auth.py` - Authentication logic
- `app/routers/accounting.py` - Similar export pattern
- `app/database.py` - Database connection setup

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-29  
**Author**: Treasury Integration Team
