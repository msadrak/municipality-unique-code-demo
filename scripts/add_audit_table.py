import sys
import os

sys.path.append(os.getcwd())

from app.database import engine, Base
from app.models.attendance import AttendanceAuditLog

if __name__ == "__main__":
    print("Creating audit table...")
    Base.metadata.create_all(bind=engine)
    print("Done")
