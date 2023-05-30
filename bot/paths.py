from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
INPUT_DIR = BASE_DIR / "input"
LOG_DIR = BASE_DIR / "log"

PRIVATE_KEYS_TXT = INPUT_DIR / "private_keys.txt"
TOKENS_TXT = INPUT_DIR / "tokens.txt"
