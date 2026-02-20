# Setup Instructions - Treasury Integration API

## ⚠️ Required Packages Not Installed

The server cannot start because required Python packages are missing. Follow these steps to install them:

---

## 📦 Step 1: Install Required Packages

Open PowerShell or Command Prompt in the project directory and run:

```bash
cd h:\Freelancing_Project\KalaniProject\municipality_demo
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic
```

**OR** if you have a virtual environment:

```bash
# Activate virtual environment first
# Then install packages
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic
```

---

## 🗄️ Step 2: Ensure PostgreSQL is Running

The application requires PostgreSQL database. Verify:

1. **PostgreSQL is installed and running**
2. **Database exists**: `municipality_demo`
3. **Connection details** (in `app/database.py`):
   - Host: `localhost`
   - Port: `5432`
   - Database: `municipality_demo`
   - Username: `postgres`
   - Password: `15111380`

**To check PostgreSQL:**
```bash
# Check if PostgreSQL service is running (Windows)
Get-Service -Name postgresql*

# Or check if port 5432 is listening
netstat -an | findstr 5432
```

---

## 🚀 Step 3: Start the Server

Once packages are installed and PostgreSQL is running:

```bash
cd h:\Freelancing_Project\KalaniProject\municipality_demo
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## ✅ Step 4: Verify Server is Running

### Test Health Endpoint:
Open in browser or run:
```bash
curl http://localhost:8000/api/v1/treasury/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-29T...",
  "service": "Treasury Integration API",
  "version": "1.0.0"
}
```

### Or open in browser:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/treasury/health

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'fastapi'"
**Solution**: Install packages as shown in Step 1

### Issue: "Connection refused" or database errors
**Solution**: 
1. Ensure PostgreSQL is running
2. Check database credentials in `app/database.py`
3. Verify database `municipality_demo` exists

### Issue: "Address already in use" (port 8000)
**Solution**: 
- Use a different port: `--port 8001`
- Or stop the process using port 8000

### Issue: Python 3.14 compatibility
**Note**: Python 3.14.2 is very new. If packages fail to install:
- Try using Python 3.11 or 3.12
- Or wait for package updates

---

## 📋 Complete Package List

If you want to install all packages at once:

```bash
pip install fastapi uvicorn[standard] sqlalchemy psycopg2-binary pydantic python-multipart
```

**Package purposes:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - ORM for database
- `psycopg2-binary` - PostgreSQL driver
- `pydantic` - Data validation
- `python-multipart` - Form data handling

---

## 🧪 Step 5: Run Tests

After server is running, test the API:

```bash
python test_treasury_api.py
```

This will run 8 automated tests to verify everything works.

---

## 📚 Next Steps

Once the server is running:

1. **View API Documentation**: http://localhost:8000/docs
2. **Read Treasury API Guide**: `TREASURY_API_DOC.txt`
3. **Test the endpoints** using the interactive docs
4. **Run automated tests**: `python test_treasury_api.py`

---

## 💡 Quick Commands Reference

```bash
# Install packages
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic

# Start server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Test health
curl http://localhost:8000/api/v1/treasury/health

# Run tests
python test_treasury_api.py
```

---

**Need Help?** Check the documentation files:
- `TREASURY_README.md` - Module documentation
- `TREASURY_API_DOC.txt` - Complete API guide
- `QUICK_START.md` - Quick start guide
