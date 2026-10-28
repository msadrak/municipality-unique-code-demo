# Development Walkthrough & Fix Report

## 1. Frontend Migration: Dynamic Tailwind CSS v4
**Issue**: The [Login](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/frontend/src/components/Login.tsx#21-225) page UI suffered from horizontal stretching because arbitrary Tailwind utility classes like `max-w-[440px]` added from the Stitch designs were completely ignored by Vite.
**Actions Taken**:
- **Tailwind configuration**: Installed `@tailwindcss/vite` and updated [vite.config.ts](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/frontend/vite.config.ts), replacing the old static build system with the new dynamic v4 setup.
- **Index CSS cleanup**: Stripped out over 2000 lines of static Tailwind base code from [index.css](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/frontend/src/index.css) and replaced it with `@import "tailwindcss";`, while preserving your custom CSS rules (like `.glass-card` and `.dark` variables).
- **Result**: The Vite server dynamically catches arbitrary classes directly from [.tsx](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/frontend/src/App.tsx) files now, keeping the UI exact to design principles.

## 2. Infrastructure: Restoring PostgreSQL & Docker Services
**Issue**: The backend failed to start correctly due to multiple connection drops on the `postgresql://` string in [.env](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/.env).
**Actions Taken**:
- Forced Docker Desktop to start from the Windows Subsystem, enabling the pending [.yml](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/docker-compose.yml) hooks.
- Triggered `docker-compose up -d` to effectively spin up `municipality_postgres` and `municipality_redis`.
- Freshly reinstalled `psycopg2-binary` directly inside the `.venv` using proxy-bypass logic, resolving a critical Python Windows DLL load crash that was constantly killing Uvicorn on startup.
- Overrode Alembic migration bugs by directly injecting SQLAlchemy `Base.metadata.create_all()` into Postgres.
- Executed [seed_db.py](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/seed_db.py) to seamlessly populate the default accounts (including [admin](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/app/routers/auth.py#193-210)/[admin](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/app/routers/auth.py#193-210)).

## 3. The 500 Internal Server Error (Auth Route Debugging)
**Issue**: The frontend continuously displayed "نام کاربری یا رمز عبور اشتباه است" (Username or Password incorrect) — this was identified as a fake error caught by Redux/React. The backend was actually returning `500 Internal Server Error`.
**Actions Taken**:
- Isolated the Backend with `TestClient` to read the exact hidden Python traceback. 
- **Missing Dependency**: Reinstalled `slowapi` which had disappeared from `.venv` site-packages, preventing the `app.main` boot entirely.
- **Missing Columns in DB**: The database was missing the [failed_attempts](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/app/routers/auth.py#118-123) and `locked_until` columns. Since Alembic missed them, I executed native `ALTER TABLE` SQL commands to inject them dynamically into the [users](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/app/routers/auth.py#420-448) table. Added the missing columns to [app/models.py](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/app/models.py).
- **Timezone Conflicts**: The most intricate bug was deep within [app/routers/auth.py](file:///h:/Freelancing_Project/KalaniProject/municipality_demo/app/routers/auth.py). 
  ```python
  # OLD 
  if user.locked_until and user.locked_until > datetime.utcnow(): 
  ```
  Postgres `TIMESTAMP` was returning an offset-naive timestamp but Python logic clashed during comparisons. I refactored the logic to `user.locked_until.replace(tzinfo=None) > datetime.utcnow()` to ensure cross-database (SQLite and Postgres) backwards compatibility.

## Current State
Both `npm run dev` and `uvicorn` are structurally sound, running in isolation via the terminal. The admin logins resolve to `200 OK`. The workspace environment is fully synchronized with your design intent.
