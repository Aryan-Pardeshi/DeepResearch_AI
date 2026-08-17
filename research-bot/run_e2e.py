import sys
from pathlib import Path

root = Path(r"C:\Users\admin\Desktop\Aryan\PROJECTS\AI_Research_Assistant\research-bot")
sys.path.insert(0, str(root))

from dotenv import load_dotenv
load_dotenv(root / ".env")  # populate os.environ with real keys before any agent runs

# Delegate to the canonical E2E runner, preserving CLI args
sys.argv = [str(root / "test_research_mode.py")] + sys.argv[1:]
from test_research_mode import main
main()
