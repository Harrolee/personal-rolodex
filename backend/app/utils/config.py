import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# API Keys
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# File paths for persistence (relative to project root)
KG_FILE = "knowledge_graph.json"
CHAT_HISTORY_FILE = "chat_history.json"

# --- API Key Validation ---
def validate_api_keys():
    """Checks if API keys are loaded correctly."""
    keys_valid = True
    if not DEEPGRAM_API_KEY or DEEPGRAM_API_KEY == "YOUR_DEEPGRAM_API_KEY":
        logging.error("Deepgram API key missing or placeholder in .env file.")
        keys_valid = False
    if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY":
        logging.error("OpenAI API key missing or placeholder in .env file.")
        keys_valid = False
    return keys_valid
