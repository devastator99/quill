import os
from dotenv import load_dotenv
from solders.pubkey import Pubkey

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
DATABASE_URL = os.getenv("DATABASE_URL")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")

# Solana setup
PROGRAM_ID = Pubkey.from_string("5AhcUJj8WtAqR6yfff76HyZFX7LWovRZ1bcgN9n3Rwa7")

MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
TX_CONFIRMATION_TIMEOUT = 60  # seconds
