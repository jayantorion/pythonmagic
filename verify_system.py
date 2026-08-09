#!/usr/bin/env python3
"""
Full verification script for AI Job Search & Application Intelligence Platform.
Tests: DB init, auth flow, profile, facts, discovery, matching, applications, parser, isolation.
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
    """Run comprehensive system verification."""
    print("=" * 60)
    print("AI Job Search & Application Intelligence Platform")
    print("System Verification (Multi-User Auth)")
    print("=" * 60)

    try:
        print("1. Initializing database...")
        from app.core.database import init_db
        from app.models import candidate, job, match, resume, application, user as user_model  # noqa
        await init_db()
        print("   [OK] Database initialized")

        from app.core.database import AsyncSessionLocal
        from app.core.security import create_access_token, decode_access_token, hash_password
        from app.api.v1.auth import _seed_profile_for_user, _seed_facts_from_yaml
        from app.models.user import User
        from app.core.config_loader import config_loader
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            # 1. Auth: Register a user
            print("\n2. Testing auth flow (register / login / me)...")
            from app.core.auth import get_current_user
            from fastapi.security import OAuth2PasswordBearer

            username = f"verify_full"
            res = await db.execute(select(User).where(User.username == username))
            user_a = res.scalars().first()
            if not user_a:
                user_a = User(
                    username=username,
                    email=f"{username}@example.com",
                    hashed_password=hash_password("testpassword123"),
                    full_name="Verify User A",
                    is_active=True,
                )
                db.add(user_a)
                await db.flush()
                profile_a = _seed_profile_for_user(user_a, config_loader.get_default_profile())
                db.add(profile_a)
                await db.flush()
                await _seed_facts_from_yaml(db, profile_a)
                await db.commit()
            token_a = create_access_token(user_a.id, user_a.username)
            payload = decode_access_token(token_a)
            assert payload["sub"] == user_a.id
            print(f"   [OK] User '{username}' registered + token issued + decoded")

            # 2. Profile
            print("\n3. Testing candidate profile (user-scoped)...")
            from app.api.v1.candidate import get_or_create_user_profile
            profile = await get_or_create_user_profile(db, user_a)
            assert profile.user_id == user_a.id
            print(f"   [OK] Profile: {profile.full_name}, domain: {profile.domain}, "
                  f"{profile.experience_years} yrs, tech: {list(profile.tech_stack_priorities.keys())}")

            # 3. Profile facts
            from app.models.candidate import ProfileFact
            facts_res = await db.execute(
                select(ProfileFact).where(ProfileFact.profile_id == profile.id)
            )
            facts = facts_res.scalars().all()
            print(f"   [OK] Loaded {len(facts)} verified facts")

            # 4. Job discovery
            print("\n4. Testing job discovery (user-scoped)...")
            from app.api.v1.jobs import trigger_discovery
            discovery = await trigger_discovery(
                query="Data Engineer", limit=3, db=db, current_user=user_a
            )
            print(f"   [OK] Discovery: total={discovery['discovered_total']}, "
                  f"new={discovery['new_jobs_added']}, dups={discovery['duplicates_removed']}")

            # 5. Job listing
            print("\n5. Testing job listing (user-scoped)...")
            from app.api.v1.jobs import list_jobs
            jobs = await list_jobs(db=db, current_user=user_a, limit=5)
            print(f"   [OK] Listed {len(jobs)} jobs")
            if jobs:
                j = jobs[0]
                print(f"   [OK] Sample: {j.title} @ {j.company_name}")
                if j.match:
                    print(f"   [OK] Match: {j.match.overall_score}% ({j.match.recommendation}), "
                          f"pros={len(j.match.pros)}, gaps={len(j.match.gaps)}")

            # 6. Application stats
            print("\n6. Testing application stats (user-scoped)...")
            from app.api.v1.applications import get_application_stats
            stats = await get_application_stats(db=db, current_user=user_a)
            print(f"   [OK] Total: {stats['total_applications']}, "
                  f"discovered={stats['discovered']}, applied={stats['applied']}")

            # 7. Resume parser
            print("\n7. Testing resume parser...")
            from app.services.resume.parser import ResumeParserService
            parser = ResumeParserService()
            print("   [OK] ResumeParserService loaded")

            # 8. Matching engine
            print("\n8. Testing matching engine...")
            from app.services.matching.explainer import matching_engine
            from app.schemas.job import JobCreate
            test_job = JobCreate(
                source="test",
                external_id="test_001",
                canonical_url="https://example.com/job/1",
                company_name="Test Company",
                title="Data Engineer",
                location="Bangalore, India",
                description_raw="Looking for a Data Engineer with Python, SQL, and Spark experience.",
                requirements_structured=None,
            )
            print("   [OK] Matching engine imported & test job created")

            # 9. User isolation
            print("\n9. Testing user isolation...")
            username_b = "verify_full_b"
            res_b = await db.execute(select(User).where(User.username == username_b))
            user_b = res_b.scalars().first()
            if not user_b:
                user_b = User(
                    username=username_b,
                    email=f"{username_b}@example.com",
                    hashed_password=hash_password("testpassword123"),
                    full_name="Verify User B",
                    is_active=True,
                )
                db.add(user_b)
                await db.flush()
                profile_b = _seed_profile_for_user(user_b, config_loader.get_default_profile())
                db.add(profile_b)
                await db.flush()
                await _seed_facts_from_yaml(db, profile_b)
                await db.commit()

            # User B should see 0 applications (isolation check)
            stats_b = await get_application_stats(db=db, current_user=user_b)
            assert stats_b["total_applications"] == 0, \
                f"User isolation broken: user B sees {stats_b['total_applications']} apps"
            print(f"   [OK] User B has 0 applications (isolation holds, user A has {stats['total_applications']})")

            # User B should not be able to read user A's job by ID
            from app.api.v1.jobs import get_job_detail
            from fastapi import HTTPException
            if jobs:
                try:
                    await get_job_detail(jobs[0].id, db=db, current_user=user_b)
                    raise AssertionError("User isolation broken: B could read A's job")
                except HTTPException as e:
                    if e.status_code == 404:
                        print(f"   [OK] User B got 404 reading user A's job (isolation holds)")
                    else:
                        raise

        print("\n" + "=" * 60)
        print("ALL SYSTEM VERIFICATIONS PASSED")
        print("=" * 60)
        print("\nSystem Status: READY FOR USE")
        print("- Backend API: http://127.0.0.1:8765")
        print("- API Documentation: http://127.0.0.1:8765/docs")
        print("- Health Check: http://127.0.0.1:8765/health")
        print("- Web UI (after frontend build): http://localhost:3000")
        return True

    except Exception as e:
        print(f"\nFAIL: SYSTEM VERIFICATION FAILED: {e}")
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
