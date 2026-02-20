# Quick Start Guide - Running the Treasury Integration API

## 🚀 Server is Starting!

The FastAPI server is now running in the background.

---

## 📍 Access Points

### 1. API Health Check
```
http://localhost:8000/api/v1/treasury/health
```

### 2. Interactive API Documentation (Swagger UI)
```
http://localhost:8000/docs
```

### 3. Alternative API Documentation (ReDoc)
```
http://localhost:8000/redoc
```

### 4. Treasury Export Endpoint
```
http://localhost:8000/api/v1/treasury/export
```

---

## 🧪 Quick Test

### Test 1: Health Check
Open in browser or run:
```bash
curl http://localhost:8000/api/v1/treasury/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-29T...",
  "service": "Treasury Integration API",
  "version": "1.0.0"
}
```

### Test 2: Login (Required for Export)
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"admin\"}" \
  -c cookies.txt
```

### Test 3: Export Data (After Login)
```bash
curl http://localhost:8000/api/v1/treasury/export?limit=5 \
  -b cookies.txt
```

---

## 🔧 Manual Server Start

If you need to start the server manually:

```bash
cd h:\Freelancing_Project\KalaniProject\municipality_demo
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or with all interfaces:
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📋 Prerequisites

1. **Python 3.10+** ✅ (You have Python 3.14.2)
2. **PostgreSQL Database** - Must be running
   - Connection: `postgresql://postgres:15111380@localhost:5432/municipality_demo`
3. **Required Packages** - Install if needed:
   ```bash
   pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic
   ```

---

## 🐛 Troubleshooting

### Server Not Starting?
1. Check if port 8000 is already in use
2. Verify PostgreSQL is running
3. Check database connection string in `app/database.py`
4. Look for error messages in the terminal

### Database Connection Error?
- Ensure PostgreSQL is running
- Verify credentials in `app/database.py`
- Check if database `municipality_demo` exists

### Import Errors?
- Install missing packages: `pip install -r requirements.txt`
- Check Python path

---

## 📚 Next Steps

1. **Test the API** using the test script:
   ```bash
   python test_treasury_api.py
   ```

2. **View Documentation**:
   - Open http://localhost:8000/docs in your browser
   - Interactive API testing interface

3. **Read Full Documentation**:
   - `TREASURY_API_DOC.txt` - Complete guide
   - `TREASURY_QUICK_REFERENCE.md` - Quick reference

---

## ✅ Server Status

The server should now be running at:
- **URL**: http://localhost:8000
- **Health Check**: http://localhost:8000/api/v1/treasury/health
- **API Docs**: http://localhost:8000/docs

---

**Note**: The server is running with `--reload` flag, so it will automatically restart when you make code changes.
