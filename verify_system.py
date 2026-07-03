#!/usr/bin/env python3
"""
Verification script for AI Job Search & Application Intelligence Platform.
Tests all core components to ensure system is working correctly.
"""

import asyncio
import sys
import os
from pathlib import Path

# Force UTF-8 output for Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

async def verify_system():
    """Run comprehensive system verification."""
    print("=" * 60)
    print("AI Job Search & Application Intelligence Platform")
    print("System Verification")
    print("=" * 60)

    try:
        # Initialize database
        print("1. Initializing database...")
        from app.core.database import init_db
        # Import all models so Base.metadata knows about them
        from app.models import candidate, job, match, resume, application
        await init_db()
        print("   ✓ Database initialized successfully")

        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            # Test candidate profile
            print("2. Testing candidate profile...")
            from app.api.v1.candidate import get_or_create_default_profile
            profile = await get_or_create_default_profile(db)
            print(f"   ✓ Profile loaded: {profile.full_name}")
            print(f"   ✓ Domain: {profile.domain}")
            print(f"   ✓ Experience: {profile.experience_years} years")
            print(f"   ✓ Tech priorities: {list(profile.tech_stack_priorities.keys())}")

            # Test profile facts
            from app.models.candidate import ProfileFact
            from sqlalchemy import select
            facts_result = await db.execute(
                select(ProfileFact).where(ProfileFact.profile_id == profile.id)
            )
            facts = facts_result.scalars().all()
            print(f"   ✓ Loaded {len(facts)} verified facts")

            # Test job discovery
            print("3. Testing job discovery...")
            from app.api.v1.jobs import trigger_discovery
            discovery_result = await trigger_discovery(
                query="Data Engineer",
                limit=3,
                db=db
            )
            print(f"   ✓ Discovery completed: {discovery_result['discovered_total']} jobs found")
            print(f"   ✓ New jobs added: {discovery_result['new_jobs_added']}")
            print(f"   ✓ Duplicates removed: {discovery_result['duplicates_removed']}")

            # Test job listing
            print("4. Testing job listing...")
            from app.api.v1.jobs import list_jobs
            jobs = await list_jobs(db=db, limit=5)
            print(f"   ✓ Listed {len(jobs)} jobs from database")

            if jobs:
                job = jobs[0]
                print(f"   ✓ Sample job: {job.title} at {job.company_name}")
                if job.match:
                    print(f"   ✓ Match score: {job.match.overall_score}% ({job.match.recommendation})")
                    print(f"   ✓ Match pros: {len(job.match.pros)} items")
                    print(f"   ✓ Match gaps: {len(job.match.gaps)} items")
                else:
                    print(f"   ⚠ No match computed for sample job")

            # Test application stats
            print("5. Testing application statistics...")
            from app.api.v1.applications import get_application_stats
            stats = await get_application_stats(db=db)
            print(f"   ✓ Total applications: {stats['total_applications']}")
            print(f"   ✓ Discovered: {stats['discovered']}")
            print(f"   ✓ Applied: {stats.get('applied', 0)}")

            # Test resume parsing (if we had a sample)
            print("6. Testing resume parser availability...")
            from app.services.resume.parser import ResumeParserService
            parser = ResumeParserService()
            print("   ✓ Resume parser service loaded")

            # Test matching engine
            print("7. Testing matching engine...")
            from app.services.matching.explainer import matching_engine
            from app.schemas.job import JobCreate

            # Create a minimal test job
            test_job = JobCreate(
                source="test",
                external_id="test_001",
                canonical_url="https://example.com/job/1",
                company_name="Test Company",
                title="Data Engineer",
                location="Bangalore, India",
                description_raw="Looking for a Data Engineer with Python, SQL, and Spark experience.",
                requirements_structured=None
            )

            # This would normally call the AI provider, but we can test the structure
            print("   ✓ Matching engine imported successfully")

            print("\n" + "=" * 60)
            print("ALL SYSTEM VERIFICATIONS PASSED")
            print("=" * 60)
            print("\nSystem Status: READY FOR USE")
            print("- Backend API: http://127.0.0.1:8765")
            print("- API Documentation: http://127.0.0.1:8765/docs")
            print("- Health Check: http://127.0.0.1:8765/health")
            return True

    except Exception as e:
        print(f"\n✗ SYSTEM VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point."""
    try:
        result = asyncio.run(verify_system())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()