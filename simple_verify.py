#!/usr/bin/env python3
"""
Simple verification script for AI Job Search & Application Intelligence Platform.
Tests: DB init, register a user, get profile, discover jobs, list jobs, application stats.
"""

import asyncio
import secrets
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
    print("=" * 60)
    print("AI Job Search Platform - Verification (multi-user auth)")
    print("=" * 60)

    try:
        # Initialize database
        print("1. Initializing database...")
        from app.core.database import init_db
        from app.models import candidate, job, match, resume, application, user as user_model  # noqa
        await init_db()
        print("   OK: Database initialized")

        from app.core.database import AsyncSessionLocal
        from app.core.security import create_access_token, hash_password
        from app.api.v1.auth import _seed_profile_for_user, _seed_facts_from_yaml
        from app.models.user import User
        from sqlalchemy import select
        from app.core.config_loader import config_loader

        async with AsyncSessionLocal() as db:
            # Create a verification user (idempotent on rerun)
            print("2. Creating verification user...")
            username = "verify_simple"
            result = await db.execute(select(User).where(User.username == username))
            test_user = result.scalars().first()
            if not test_user:
                test_user = User(
                    username=username,
                    email=f"{username}@example.com",
                    hashed_password=hash_password("testpassword123"),
                    full_name="Verify Simple",
                    is_active=True,
                )
                db.add(test_user)
                await db.flush()
                profile = _seed_profile_for_user(test_user, config_loader.get_default_profile())
                db.add(profile)
                await db.flush()
                n_facts = await _seed_facts_from_yaml(db, profile)
                await db.commit()
                print(f"   OK: Created user '{username}' with profile '{profile.full_name}' and {n_facts} seed facts")
            else:
                print(f"   OK: Reusing existing user '{username}'")

            # Verify profile
            print("3. Verifying profile...")
            from app.api.v1.candidate import get_or_create_user_profile
            profile = await get_or_create_user_profile(db, test_user)
            print(f"   OK: Profile: {profile.full_name}, domain: {profile.domain}")

            # Job discovery
            print("4. Testing job discovery (user-scoped)...")
            from app.api.v1.jobs import trigger_discovery
            discovery = await trigger_discovery(
                query="Data Engineer", limit=2, db=db, current_user=test_user
            )
            print(f"   OK: Discovery completed: {discovery['discovered_total']} jobs found, {discovery['new_jobs_added']} new")

            # List jobs
            print("5. Testing job listing (user-scoped)...")
            from app.api.v1.jobs import list_jobs
            jobs = await list_jobs(db=db, current_user=test_user, limit=3)
            print(f"   OK: Listed {len(jobs)} jobs for user")
            if jobs:
                j = jobs[0]
                print(f"   OK: Sample: {j.title} @ {j.company_name}")
                if j.match:
                    print(f"   OK: Match score: {j.match.overall_score}% ({j.match.recommendation})")

            # Application stats (user-scoped)
            print("6. Testing application stats (user-scoped)...")
            from app.api.v1.applications import get_application_stats
            stats = await get_application_stats(db=db, current_user=test_user)
            print(f"   OK: Total applications: {stats['total_applications']}")

            # Auth round-trip
            print("7. Testing JWT auth round-trip...")
            from app.core.security import decode_access_token
            token = create_access_token(test_user.id, test_user.username)
            payload = decode_access_token(token)
            assert payload["sub"] == test_user.id
            assert payload["username"] == test_user.username
            print(f"   OK: Token round-trip succeeded (sub={payload['sub']})")

        print("\n" + "=" * 60)
        print("SYSTEM VERIFICATION PASSED")
        print("=" * 60)
        print("System Status: READY FOR USE")
        print("- Backend API: http://127.0.0.1:8765")
        print("- API Docs: http://127.0.0.1:8765/docs")
        print("- Login: see README 'Web UI' section")
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
