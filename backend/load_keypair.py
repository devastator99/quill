from solathon.keypair import Keypair
from pathlib import Path
import json

# A) Load existing file
path = Path.home() / ".config/solana/id.json"
secret = json.loads(path.read_text())
wallet = Keypair.from_secret_key(bytes(secret))
print(wallet.public_key)