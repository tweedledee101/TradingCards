"""Legacy import path; container image uses lambda_entry.handler (see Dockerfile.api-lambda)."""
from lambda_entry import handler  # noqa: F401
