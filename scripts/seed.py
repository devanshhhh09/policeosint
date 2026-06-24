#!/usr/bin/env python3
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.core.security import hash_password
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.case import Case, CaseType, CaseStatus, CasePriority
from app.core.database import Base

async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        users = [
            User(badge_number="GGN/CYB/ADMIN/001", email="admin@policeosint.gov.in",
                 full_name="System Administrator", hashed_password=hash_password("Admin@1234"),
                 role=UserRole.SUPER_ADMIN, status=UserStatus.ACTIVE, is_verified=True,
                 station_name="Gurugram Cyber Cell", district="Gurugram", designation="System Admin"),
            User(badge_number="GGN/CYB/2024/001", email="sharma@policeosint.gov.in",
                 full_name="Insp. Rajesh Sharma", hashed_password=hash_password("Inspector@1234"),
                 role=UserRole.INSPECTOR, status=UserStatus.ACTIVE, is_verified=True,
                 station_name="Gurugram Cyber Cell", district="Gurugram", designation="Inspector (Cyber)"),
            User(badge_number="GGN/CYB/2024/002", email="verma@policeosint.gov.in",
                 full_name="Analyst Priya Verma", hashed_password=hash_password("Analyst@1234"),
                 role=UserRole.ANALYST, status=UserStatus.ACTIVE, is_verified=True,
                 station_name="Gurugram Cyber Cell", district="Gurugram", designation="OSINT Analyst"),
            User(badge_number="GPCSSI/2025/001", email="intern@gpcssi.in",
                 full_name="Intern Aryan Kumar", hashed_password=hash_password("Intern@1234"),
                 role=UserRole.TRAINEE, status=UserStatus.ACTIVE, is_verified=True,
                 station_name="GPCSSI Training Centre", district="Gurugram", designation="Security Intern"),
        ]
        db.add_all(users)
        await db.flush()
        cases = [
            Case(case_number="CYB/2025/1847", title="Investment scam — ₹4.2L UPI fraud",
                 case_type=CaseType.INVESTMENT_FRAUD, status=CaseStatus.ACTIVE,
                 priority=CasePriority.HIGH, created_by_id=users[1].id,
                 amount_lost="420000", victim_name="Rohit Mehta",
                 ipc_sections=["419","420","66D"], incident_location="Sector 14, Gurugram"),
            Case(case_number="CYB/2025/1832", title="Phishing portal — fake HDFC site",
                 case_type=CaseType.PHISHING, status=CaseStatus.ACTIVE,
                 priority=CasePriority.HIGH, created_by_id=users[1].id,
                 ipc_sections=["66C","66D","419"]),
            Case(case_number="CYB/2025/1820", title="Ransomware — SME Gurugram",
                 case_type=CaseType.RANSOMWARE, status=CaseStatus.CLOSED,
                 priority=CasePriority.CRITICAL, created_by_id=users[1].id,
                 ipc_sections=["66F","43A"]),
        ]
        db.add_all(cases)
        await db.commit()

    print("\n✅ Database seeded!\n")
    print("=" * 50)
    print("  DEMO CREDENTIALS")
    print("=" * 50)
    print("  Super Admin  : GGN/CYB/ADMIN/001 / Admin@1234")
    print("  Inspector    : GGN/CYB/2024/001  / Inspector@1234")
    print("  Analyst      : GGN/CYB/2024/002  / Analyst@1234")
    print("  GPCSSI Intern: GPCSSI/2025/001   / Intern@1234")
    print("=" * 50)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
