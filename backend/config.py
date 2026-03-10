"""환경 설정"""
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")
DART_API_KEY      = os.getenv("DART_API_KEY", "")
GITHUB_TOKEN      = os.getenv("GITHUB_TOKEN", "")
CRYPTOPANIC_KEY   = os.getenv("CRYPTOPANIC_KEY", "")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
