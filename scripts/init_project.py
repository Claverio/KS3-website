#!/usr/bin/env python3
"""
╔══════════════════════════════════════════╗
║        🧙 DB & S3 Wizard                ║
║  Automated project infrastructure init  ║
╚══════════════════════════════════════════╝

Reads configuration from backend/settings/.env and provisions:
  1. PostgreSQL database (CREATE DATABASE)
  2. S3 bucket with public-read ACL and CORS policy

Usage:
  python scripts/init_project.py            # Full run
  python scripts/init_project.py --dry-run   # Preview only, no changes
  python scripts/init_project.py --db-only   # Database only
  python scripts/init_project.py --s3-only   # S3 bucket only
"""

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI helpers (no dependencies)
# ---------------------------------------------------------------------------

BOLD = "\033[1m"
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"


def info(tag: str, msg: str) -> None:
    print(f"  {CYAN}[{tag}]{RESET} ℹ️  {msg}")


def success(tag: str, msg: str) -> None:
    print(f"  {GREEN}[{tag}]{RESET} ✅ {msg}")


def warn(tag: str, msg: str) -> None:
    print(f"  {YELLOW}[{tag}]{RESET} ⚠️  {msg}")


def error(tag: str, msg: str) -> None:
    print(f"  {RED}[{tag}]{RESET} ❌ {msg}")


def dry(tag: str, msg: str) -> None:
    print(f"  {DIM}[{tag}] 🔍 (dry-run) {msg}{RESET}")


def banner() -> None:
    print()
    print(f"  {BOLD}╔══════════════════════════════════════════╗{RESET}")
    print(f"  {BOLD}║        🧙 DB & S3 Wizard                ║{RESET}")
    print(f"  {BOLD}╠══════════════════════════════════════════╣{RESET}")
    print(f"  {BOLD}║  Reading .env from backend/settings/     ║{RESET}")
    print(f"  {BOLD}╚══════════════════════════════════════════╝{RESET}")
    print()


# ---------------------------------------------------------------------------
# .env loader
# ---------------------------------------------------------------------------

def load_env() -> dict:
    """Load and validate required environment variables from .env file."""
    from dotenv import dotenv_values

    # Resolve .env path relative to project root (one level up from scripts/)
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / "backend" / "settings" / ".env"

    if not env_path.exists():
        error("ENV", f"File not found: {env_path}")
        sys.exit(1)

    info("ENV", f"Loading {env_path}")

    values = dotenv_values(env_path)

    # Required keys
    required_db = ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"]
    required_s3 = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_STORAGE_BUCKET_NAME",
        "AWS_S3_ENDPOINT_URL",
    ]

    missing = [k for k in required_db + required_s3 if not values.get(k)]
    if missing:
        error("ENV", f"Missing required variables: {', '.join(missing)}")
        sys.exit(1)

    # Strip quotes that some .env files leave
    cleaned = {k: v.strip().strip('"').strip("'") for k, v in values.items() if v}

    # Print summary
    print()
    info("ENV", f"DB_HOST     = {cleaned['DB_HOST']}:{cleaned['DB_PORT']}")
    info("ENV", f"DB_NAME     = {cleaned['DB_NAME']}")
    info("ENV", f"DB_USER     = {cleaned['DB_USER']}")
    info("ENV", f"S3_ENDPOINT = {cleaned['AWS_S3_ENDPOINT_URL']}")
    info("ENV", f"BUCKET      = {cleaned['AWS_STORAGE_BUCKET_NAME']}")
    print()

    return cleaned


# ---------------------------------------------------------------------------
# PostgreSQL provisioning
# ---------------------------------------------------------------------------

def provision_database(env: dict, dry_run: bool = False) -> bool:
    """Create the PostgreSQL database if it doesn't exist."""
    import psycopg

    db_name = env["DB_NAME"]
    db_user = env["DB_USER"]
    db_password = env["DB_PASSWORD"]
    db_host = env["DB_HOST"]
    db_port = env["DB_PORT"]

    conninfo = (
        f"host={db_host} port={db_port} user={db_user} "
        f"password={db_password} dbname=postgres"
    )

    info("DB", f"Connecting to {db_host}:{db_port} as {db_user}...")

    try:
        # autocommit required for CREATE DATABASE (can't run inside transaction)
        with psycopg.connect(conninfo, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Check if database already exists
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (db_name,),
                )
                exists = cur.fetchone() is not None

                if exists:
                    info("DB", f"Database '{db_name}' already exists — skipping")
                    return True

                if dry_run:
                    dry("DB", f"Would CREATE DATABASE {db_name} OWNER {db_user}")
                    dry("DB", f"Would GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}")
                    return True

                # Create database
                # Using SQL composition to safely inject identifiers
                cur.execute(
                    psycopg.sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        psycopg.sql.Identifier(db_name),
                        psycopg.sql.Identifier(db_user),
                    )
                )
                success("DB", f"Database '{db_name}' created (owner: {db_user})")

                # Grant privileges
                cur.execute(
                    psycopg.sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                        psycopg.sql.Identifier(db_name),
                        psycopg.sql.Identifier(db_user),
                    )
                )
                success("DB", f"Granted ALL PRIVILEGES to {db_user}")

                return True

    except psycopg.OperationalError as e:
        error("DB", f"Connection failed: {e}")
        return False
    except psycopg.Error as e:
        error("DB", f"Database operation failed: {e}")
        return False


# ---------------------------------------------------------------------------
# S3 provisioning
# ---------------------------------------------------------------------------

def provision_s3(env: dict, dry_run: bool = False) -> bool:
    """Create S3 bucket, set ACL and CORS policy."""
    import boto3
    from botocore.exceptions import ClientError

    bucket_name = env["AWS_STORAGE_BUCKET_NAME"]
    endpoint_url = env["AWS_S3_ENDPOINT_URL"]

    info("S3", f"Connecting to {endpoint_url}...")

    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=env["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=env["AWS_SECRET_ACCESS_KEY"],
        )

        # -- 1. Create Bucket -----------------------------------------------
        bucket_exists = False
        try:
            s3.head_bucket(Bucket=bucket_name)
            bucket_exists = True
            info("S3", f"Bucket '{bucket_name}' already exists — skipping creation")
        except ClientError as e:
            code = e.response["Error"].get("Code", "")
            if code in ("404", "NoSuchBucket"):
                bucket_exists = False
            elif code in ("403", "AccessDenied"):
                # Bucket exists but we don't have access — treat as exists
                warn("S3", f"Bucket '{bucket_name}' exists but access denied — skipping creation")
                bucket_exists = True
            else:
                raise

        if not bucket_exists:
            if dry_run:
                dry("S3", f"Would CreateBucket: {bucket_name}")
            else:
                s3.create_bucket(Bucket=bucket_name)
                success("S3", f"Bucket '{bucket_name}' created")

        # -- 2. Set ACL (public-read) ----------------------------------------
        if dry_run:
            dry("S3", f"Would set ACL to 'public-read' on {bucket_name}")
        else:
            try:
                s3.put_bucket_acl(Bucket=bucket_name, ACL="public-read")
                success("S3", "ACL set to public-read")
            except ClientError as e:
                # Some S3-compatible providers don't support bucket-level ACL
                warn("S3", f"Could not set bucket ACL (provider may not support it): {e}")

        # -- 3. Set CORS policy ----------------------------------------------
        cors_config = {
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["GET", "HEAD"],
                    "AllowedOrigins": ["*"],
                    "MaxAgeSeconds": 3600,
                }
            ]
        }

        if dry_run:
            dry("S3", f"Would set CORS policy: GET, HEAD from * (max-age: 3600s)")
        else:
            try:
                s3.put_bucket_cors(
                    Bucket=bucket_name, CORSConfiguration=cors_config
                )
                success("S3", "CORS policy applied (GET, HEAD from *)")
            except ClientError as e:
                warn("S3", f"Could not set CORS policy (provider may not support it): {e}")

        return True

    except ClientError as e:
        error("S3", f"S3 operation failed: {e}")
        return False
    except Exception as e:
        error("S3", f"Unexpected error: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="🧙 DB & S3 Wizard — Provision project infrastructure from .env",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without making any changes",
    )
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Only provision the PostgreSQL database",
    )
    parser.add_argument(
        "--s3-only",
        action="store_true",
        help="Only provision the S3 bucket",
    )
    args = parser.parse_args()

    # Validate mutually exclusive flags
    if args.db_only and args.s3_only:
        print("❌ Cannot use --db-only and --s3-only together")
        sys.exit(1)

    banner()

    if args.dry_run:
        print(f"  {YELLOW}{BOLD}⚡ DRY-RUN MODE — no changes will be made{RESET}")
        print()

    # Determine what to run
    run_db = not args.s3_only
    run_s3 = not args.db_only

    # Load config
    env = load_env()

    results = {}

    # Provision DB
    if run_db:
        print(f"  {BOLD}── PostgreSQL ──────────────────────────────{RESET}")
        results["db"] = provision_database(env, dry_run=args.dry_run)
        print()

    # Provision S3
    if run_s3:
        print(f"  {BOLD}── S3 Bucket ───────────────────────────────{RESET}")
        results["s3"] = provision_s3(env, dry_run=args.dry_run)
        print()

    # Summary
    print(f"  {BOLD}── Summary ─────────────────────────────────{RESET}")
    all_ok = all(results.values())

    if all_ok:
        if args.dry_run:
            print(f"  {GREEN}🔍 Dry-run complete. No changes made.{RESET}")
        else:
            print(f"  {GREEN}🎉 All done! Project infrastructure ready.{RESET}")
    else:
        failed = [k.upper() for k, v in results.items() if not v]
        print(f"  {RED}⚠️  Some steps failed: {', '.join(failed)}{RESET}")
        print(f"  {DIM}   Check errors above and fix your .env config.{RESET}")

    print()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
