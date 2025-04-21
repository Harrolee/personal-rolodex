import os
import json
import logging
from typing import List, Dict
from .models import KnowledgeGraph
from .config import KG_FILE, CHAT_HISTORY_FILE

# --- Knowledge Graph Persistence (JSON) ---
def load_kg() -> KnowledgeGraph:
    """Loads the knowledge graph from the JSON file."""
    try:
        if os.path.exists(KG_FILE):
            with open(KG_FILE, 'r') as f:
                data = json.load(f)
                # Handle potential empty file or invalid JSON
                if not data:
                    logging.warning(f"{KG_FILE} is empty, returning new graph.")
                    return KnowledgeGraph()
                return KnowledgeGraph(**data)
        else:
            logging.info(f"{KG_FILE} not found, creating a new empty graph.")
            return KnowledgeGraph() # Return empty graph if file doesn't exist
    except (json.JSONDecodeError, IOError, TypeError, ValueError) as e: # Added ValueError for Pydantic validation
        logging.error(f"Error loading knowledge graph from {KG_FILE}: {e}")
        # Don't use st.warning here as this module shouldn't depend on streamlit
        print(f"Warning: Could not load existing knowledge graph from {KG_FILE}, starting fresh. Error: {e}")
        return KnowledgeGraph() # Return empty graph on error

def save_kg(kg: KnowledgeGraph):
    """Saves the knowledge graph to the JSON file."""
    try:
        with open(KG_FILE, 'w') as f:
            json.dump(kg.model_dump(mode='json'), f, indent=2) # Use model_dump for Pydantic v2+
        logging.info(f"Knowledge graph saved to {KG_FILE}")
    except IOError as e:
        logging.error(f"Error saving knowledge graph to {KG_FILE}: {e}")
        # Don't use st.error here
        print(f"Error: Failed to save knowledge graph to {KG_FILE}: {e}")
    except Exception as e: # Catch potential Pydantic errors during dump
        logging.error(f"Error dumping knowledge graph model: {e}")
        print(f"Error: Failed to serialize knowledge graph: {e}")


# --- Chat History Persistence ---
def load_chat_history() -> List[Dict]:
    """Loads chat history from the JSON file."""
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, 'r') as f:
                history = json.load(f)
                # Basic validation
                if isinstance(history, list) and all(isinstance(item, dict) for item in history):
                    return history
                else:
                    logging.warning(f"{CHAT_HISTORY_FILE} has invalid format, returning empty list.")
                    return []
        else:
            return []
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error loading chat history from {CHAT_HISTORY_FILE}: {e}")
        return []

def save_chat_history(history: List[Dict]):
    """Saves chat history to the JSON file."""
    try:
        with open(CHAT_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except IOError as e:
        logging.error(f"Error saving chat history to {CHAT_HISTORY_FILE}: {e}")
    except TypeError as e: # Catch potential issues with non-serializable data in history
        logging.error(f"Error serializing chat history: {e}")
