"""AWS Lambda entrypoint for FastAPI (Mangum)."""
from mangum import Mangum

from backend.api.main import app

handler = Mangum(app, lifespan="off")
