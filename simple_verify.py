#!/usr/bin/env python3
"""
Simple verification script for AI Job Search & Application Intelligence Platform.
"""

import asyncio
import sys
from pathlib import Path

# Force UTF-8 output for Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

async def verify_system():
    """Run basic system verification."""
    print("=" * 50)
    print("AI Job Search Platform - Verification")
    print("=" * 50)

    try:
        # Initialize database
        print("1. Initializing database...")
        from app.core.database import init_db
        await init_db()
        print("   OK: Database initialized")

        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            # Test candidate profile
            print("2. Testing candidate profile...")
            from app.api.v1.candidate import get_or_create_default_profile
            profile = await get_or_create_default_profile(db)
            print(f"   OK: Profile loaded: {profile.full_name}")
            print(f"   OK: Domain: {profile.domain}")

            # Test job discovery
            print("3. Testing job discovery...")
            from app.api.v1.jobs import trigger_discovery
            discovery_result = await trigger_discovery(
                query="Data Engineer",
                limit=2,
                db=db
            )
            print(f"   OK: Discovery completed: {discovery_result['discovered_total']} jobs found")
            print(f"   OK: New jobs added: {discovery_result['new_jobs_added']}")

            # Test job listing
            print("4. Testing job listing...")
            from app.api.v1.jobs import list_jobs
            jobs = await list_jobs(db=db, limit=3)
            print(f"   OK: Listed {len(jobs)} jobs from database")

            if jobs:
                job = jobs[0]
                print(f"   OK: Sample job: {job.title} at {job.company_name}")
                if job.match:
                    print(f"   OK: Match score: {job.match.overall_score}% ({job.match.recommendation})")
                else:
                    print(f"   WARNING: No match computed for sample job")

            # Test application stats
            print("5. Testing application statistics...")
            from app.api.v1.applications import get_application_stats
            stats = await get_application_stats(db=db)
            # stats is a dict, not an object
            print(f"   OK: Total applications: {stats['total_applications']}")

            print("\n" + "=" * 50)
            print("SYSTEM VERIFICATION PASSED")
            print("=" * 50)
            print("System Status: READY FOR USE")
            print("- Backend API: http://127.0.0.1:8765")
            print("- API Docs: http://127.0.0.1:8765/docs")
            return True

    except Exception as e:
        print(f"\nERROR: SYSTEM VERIFICATION FAILED: {e}")
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