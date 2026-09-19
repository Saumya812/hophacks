"""Copy Spacetime publisher token into backend/.env without printing secrets."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
toml_path = root / ".spacetime" / "config" / "cli.toml"
env_path = root / "backend" / ".env"

toml = toml_path.read_text(encoding="utf-8")
patterns = [
    r'spacetimedb_token\s*=\s*"([^"]+)"',
    r"spacetimedb_token\s*=\s*'([^']+)'",
    r'token\s*=\s*"([^"]+)"',
    r"token\s*=\s*'([^']+)'",
]
token = None
for pat in patterns:
    m = re.search(pat, toml)
    if m:
        token = m.group(1)
        break

if not token:
    print("TOKEN_NOT_FOUND")
    for line in toml.splitlines():
        if "=" in line and not line.strip().startswith("#"):
            print("KEY", line.split("=", 1)[0].strip())
    raise SystemExit(1)

text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
if "SPACETIMEDB_URI=" not in text:
    text = (
        "SPACETIMEDB_URI=http://127.0.0.1:3000\n"
        "SPACETIMEDB_DATABASE=findmypal\n"
        f"SPACETIMEDB_TOKEN={token}\n"
        + text
    )
elif "SPACETIMEDB_TOKEN=" in text:
    text = re.sub(
        r"^SPACETIMEDB_TOKEN=.*$",
        f"SPACETIMEDB_TOKEN={token}",
        text,
        flags=re.M,
    )
else:
    text = f"SPACETIMEDB_TOKEN={token}\n" + text

env_path.write_text(text, encoding="utf-8")
print("TOKEN_WRITTEN_TO_ENV")
print("TOKEN_LEN", len(token))
