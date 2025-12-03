import os

from dotenv import load_dotenv

if os.path.isfile("private.env"):
    load_dotenv("private.env")
if os.path.isfile(".env"):
    load_dotenv(".env")

PRODUCT_ID = os.environ.get("PRODUCT_ID", "dynafield")
DEFAULT_TENANT_ID = os.environ.get("DEFAULT_TENANT_ID", PRODUCT_ID)
DEFAULT_TENANT_DATABASE_ID = os.environ.get("DEFAULT_TENANT_DATABASE_ID", f"tenant-{PRODUCT_ID}-{DEFAULT_TENANT_ID}")

CLERK_SECRET_KEY = os.environ.get("CLERK_SECRET_KEY", "")
CLERK_JWKS_URL = os.environ.get("CLERK_JWKS_URL", "")
