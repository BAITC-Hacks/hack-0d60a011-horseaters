"""Create the first local administrator after migrations.

Usage: python -m backend.infrastructure.bootstrap_admin --username admin@example.com
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from backend.domain.enums import UserRole
from backend.infrastructure.auth_security import hash_password
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.persistence.database import Database
from backend.infrastructure.persistence.models.catalog import UserCredentialModel, UserModel


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the first administrator")
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", default="Administrator")
    args = parser.parse_args()
    username = args.username.strip().lower()
    if len(username) < 3 or len(username) > 255:
        parser.error("username must be 3-255 characters")
    password = getpass.getpass("New admin password (12-256 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        print("Passwords do not match", file=sys.stderr)
        return 1
    try:
        password_hash = hash_password(password)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    database = Database(Settings().database_url)
    try:
        with database.session() as session:
            if session.scalar(select(UserModel.id).where(UserModel.external_id == username)) is not None:
                print("Username already exists", file=sys.stderr)
                return 1
            user = UserModel(external_id=username, display_name=args.display_name, role=UserRole.ADMIN)
            session.add(user)
            session.flush()
            session.add(UserCredentialModel(user_id=user.id, password_hash=password_hash))
        print(f"Admin created: {username}")
        return 0
    finally:
        database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
