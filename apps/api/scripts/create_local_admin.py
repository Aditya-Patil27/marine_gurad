#!/usr/bin/env python3
"""Create the first local administrator for offline SamudraSense login.

Run from ``apps/api``::

    python scripts/create_local_admin.py

The password is read with hidden input and is never accepted as a command-line
argument or written to logs. The script refuses to overwrite an existing user.
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session  # noqa: E402

from app.database import engine  # noqa: E402
from app.services.auth import (  # noqa: E402
    UserAlreadyExistsError,
    create_admin_user,
    get_user_by_username,
)


def prompt_username() -> str:
    while True:
        username = input("Admin username: ").strip()
        if not username:
            print("Username cannot be empty.")
            continue
        return username


def prompt_password() -> str:
    while True:
        password = getpass.getpass("Admin password (min 8 characters, hidden): ")
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            continue
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.")
            continue
        return password


def main() -> int:
    print("SamudraSense local administrator bootstrap")
    print("No default credentials exist; this creates the first administrator.")

    username = prompt_username()

    with Session(engine) as db:
        if get_user_by_username(db, username):
            print(f"Refusing to overwrite existing user '{username}'.", file=sys.stderr)
            return 1

    password = prompt_password()
    full_name = input("Full name (optional): ").strip() or None

    with Session(engine) as db:
        try:
            user = create_admin_user(db, username=username, password=password, full_name=full_name)
            created_username = user.username
        except UserAlreadyExistsError as exc:
            print(f"Refusing to overwrite existing user: {exc}", file=sys.stderr)
            return 1

    print(f"Administrator '{created_username}' created with role ADMINISTRATOR.")
    print("Store the password securely; it cannot be recovered from the database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())