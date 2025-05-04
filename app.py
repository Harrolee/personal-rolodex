import streamlit as st
import asyncio
import logging
from typing import Optional

# Import refactored components
from src.config import validate_api_keys
from src.models import KnowledgeGraph, Person # Import Person for type hinting
from src.persistence import load_kg, save_kg, load_chat_history, save_chat_history
from src.services import synthesize_speech
from src.kg_utils import merge_confirmed_data
from streamlit_components.core_processing import process_audio_story

# --- Initial Setup & Validation ---

# Configure logging (already done in config, but good practice)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Validate API Keys early
if not validate_api_keys():
    st.error("API Key validation failed. Please check your .env file and logs.")
    st.stop()

# --- Streamlit App UI ---

st.set_page_config(layout="wide")
st.title("🎙️ Personal Rolodex via Stories")

# --- Session State Management ---
# Initialize session state variables if they don't exist
default_values = {
    'chat_history': load_chat_history,
    'knowledge_graph': load_kg,
    'processing': False,
    'needs_confirmation': False,
    'extracted_data_buffer': None,
    'new_persons_buffer': list,
    'uploaded_file_key': 0, # To help reset file uploader
    'current_file_processed': False, # Flag to prevent reprocessing the same file
    'audio_bytes_to_process': None # To store bytes from either source
}
for key, default_value_or_factory in default_values.items():
    if key not in st.session_state:
        # Check if the value is callable (a factory function/type) or a direct value
        if callable(default_value_or_factory):
            st.session_state[key] = default_value_or_factory() # Call the factory
        else:
            st.session_state[key] = default_value_or_factory # Assign the direct value

# --- Sidebar ---
st.sidebar.header("Knowledge Graph")
# Use a placeholder if KG is empty or None for display
kg_display_data = st.session_state.knowledge_graph.model_dump() if st.session_state.knowledge_graph else {}
st.sidebar.json(kg_display_data, expanded=False)

# Add a button to clear the knowledge graph and chat history
if st.sidebar.button("Clear All Data"):
    # Reset knowledge graph
    st.session_state.knowledge_graph = KnowledgeGraph()
    save_kg(st.session_state.knowledge_graph)
    # Reset chat history
    st.session_state.chat_history = []
    save_chat_history(st.session_state.chat_history)
    # Reset other state
    st.session_state.needs_confirmation = False
    st.session_state.extracted_data_buffer = None
    st.session_state.new_persons_buffer = []
    st.session_state.processing = False
    st.session_state.uploaded_file_key += 1
    logging.info("All data cleared by user.")
    st.sidebar.success("All data cleared successfully!")
    st.rerun()

# --- Main Conversation Area ---
st.header("Conversation")
# Display chat history
for message in st.session_state.chat_history:
    role = message.get("role", "assistant") # Default role if missing
    content = message.get("content", "")
    with st.chat_message(role):
        st.markdown(content)

# --- Confirmation Form (Conditional Display) ---
if st.session_state.needs_confirmation and st.session_state.new_persons_buffer:
    st.warning("Please confirm new people found in the story:")
    with st.form("confirmation_form"):
        confirmed_persons_list = []
        for person in st.session_state.new_persons_buffer:
            # Use checkbox for each person, default to True (add)
            add_person = st.checkbox(f"Add '{person.name}' (ID: {person.id}) to Rolodex?", value=True, key=f"confirm_{person.id}")
            if add_person:
                confirmed_persons_list.append(person)

        submitted = st.form_submit_button("Confirm Selections")
        if submitted:
            logging.info(f"User confirmed adding {len(confirmed_persons_list)} out of {len(st.session_state.new_persons_buffer)} new persons.")
            # Merge confirmed data
            if st.session_state.extracted_data_buffer:
                updated_kg = merge_confirmed_data(
                    current_kg=st.session_state.knowledge_graph,
                    confirmed_persons=confirmed_persons_list,
                    extracted_events=st.session_state.extracted_data_buffer.events,
                    extracted_relationships=st.session_state.extracted_data_buffer.relationships
                )

                if updated_kg != st.session_state.knowledge_graph:
                    st.session_state.knowledge_graph = updated_kg
                    save_kg(st.session_state.knowledge_graph)
                    logging.info("Knowledge graph updated and saved after confirmation.")
                    st.sidebar.json(st.session_state.knowledge_graph.model_dump(), expanded=False) # Update sidebar
                    assistant_response = f"Okay, I've added the confirmed people and related information to the knowledge graph."
                else:
                     assistant_response = "Okay, no new information was added based on your confirmation."

                # Generate TTS for the final response
                with st.spinner("Generating audio response..."):
                    synthesized_audio = asyncio.run(synthesize_speech(assistant_response))

                st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
                save_chat_history(st.session_state.chat_history)

                if synthesized_audio:
                    st.audio(synthesized_audio, format="audio/wav")

            # Reset confirmation state
            st.session_state.needs_confirmation = False
            st.session_state.extracted_data_buffer = None
            st.session_state.new_persons_buffer = []
            st.session_state.processing = False # Ensure processing is false
            st.session_state.uploaded_file_key += 1 # Increment key to reset uploader
            st.rerun()


# --- Audio Input & Processing Trigger ---
st.header("Tell a Story")

# Option 1: Upload File
# Use the key to allow resetting the uploader
uploaded_file = st.file_uploader(
    "Upload an audio file (WAV recommended):",
    type=['wav', 'mp3', 'ogg', 'm4a'],
    disabled=st.session_state.processing or st.session_state.needs_confirmation, # Disable if processing or confirming
    key=f"file_uploader_{st.session_state.uploaded_file_key}"
)
process_upload_button = st.button(
    "Process Uploaded Story",
    disabled=st.session_state.processing or st.session_state.needs_confirmation or not uploaded_file,
    key="process_upload_btn"
)

st.markdown("--- OR ---")

# Option 2: Record Audio
recorded_audio_bytes = st.audio_input(
    "Record a voice message:",
    disabled=st.session_state.processing or st.session_state.needs_confirmation,
    key=f"audio_input_{st.session_state.uploaded_file_key}" # Use same key logic to reset
)
process_recording_button = st.button(
    "Process Recording",
    disabled=st.session_state.processing or st.session_state.needs_confirmation or not recorded_audio_bytes,
    key="process_recording_btn"
)


# Trigger processing if either button is pressed
if (process_upload_button and uploaded_file is not None) or \
   (process_recording_button and recorded_audio_bytes is not None):

    # Determine the source of audio bytes
    if process_upload_button and uploaded_file is not None:
        st.session_state.audio_bytes_to_process = uploaded_file.getvalue()
        logging.info("Processing triggered by uploaded file.")
    elif process_recording_button and recorded_audio_bytes is not None:
        st.session_state.audio_bytes_to_process = recorded_audio_bytes
        logging.info("Processing triggered by recorded audio.")
    else:
         # This case should ideally not be reached due to button logic, but good to handle
        st.session_state.audio_bytes_to_process = None
        logging.warning("Processing trigger condition met but no audio source found.")


    if st.session_state.audio_bytes_to_process:
        st.session_state.processing = True
        # Clear previous confirmation state if starting new processing
        st.session_state.needs_confirmation = False
        st.session_state.extracted_data_buffer = None
        st.session_state.new_persons_buffer = []
        st.session_state.current_file_processed = False # Reset processing flag for new input
        logging.info("Setting processing state to True and resetting confirmation/buffers.")
        st.rerun() # Rerun to show spinner and start processing block
    else:
        # If for some reason we triggered but have no bytes, reset and log
        st.session_state.processing = False
        st.warning("Could not get audio bytes to process.")


# --- Core Processing Logic ---
process_audio_story()


# --- Placeholder for Text Input Querying ---
st.header("Ask about your Rolodex")
query_text = st.text_input(
    "Enter your question:",
    key="query_input",
    disabled=st.session_state.processing or st.session_state.needs_confirmation # Disable during processing/confirmation
)
if query_text:
    st.info(f"Querying about: {query_text} (Functionality TBD)")
    # --- TODO: Add logic to parse query, query KG, generate response ---
    # 1. Parse user query (maybe use Instructor again?)
    # 2. Query st.session_state.knowledge_graph (or Neo4j later)
    # 3. Generate natural language response
    # 4. Update chat history
    # 5. Optionally generate TTS

# --- Footer ---
st.markdown("---")
st.caption("Rolodex App v0.1 - Refactored")
