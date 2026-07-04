# NOTE: config is not currently used by app code — values are read directly
# from environment variables in main.py / individual routers where needed.

import os

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
ENV = os.getenv("ENV", "development")
