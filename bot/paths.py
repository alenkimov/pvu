from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
INPUT_DIR = BASE_DIR / "input"
PRIVATE_KEYS_TXT = INPUT_DIR / "private_keys.txt"
TOKENS_TXT = INPUT_DIR / "tokens.txt"

INPUT_DIR.mkdir(exist_ok=True)
