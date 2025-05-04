import streamlit as st
import asyncio
import logging
from typing import Optional

from src.models import KnowledgeGraph
from src.persistence import save_kg, save_chat_history
from src.services import transcribe_audio, synthesize_speech, extract_kg_data
from src.kg_utils import identify_new_persons, merge_confirmed_data

def process_audio_story():
    """
    Handles the core processing logic for audio input: transcription, extraction, and updating the knowledge graph.
    This function is intended to be called from app.py and relies on Streamlit's session_state.
    """
    if st.session_state.processing and not st.session_state.needs_confirmation and st.session_state.audio_bytes_to_process is not None and not st.session_state.current_file_processed:
        assistant_response = "Processing failed."  # Default response
        synthesized_audio = None
        processed_successfully = False
        audio_bytes = st.session_state.audio_bytes_to_process  # Use the stored bytes

        with st.spinner("Processing story... Transcribing..."):
            transcribed_text = asyncio.run(transcribe_audio(audio_bytes))
            st.session_state.current_file_processed = True  # Mark as processed inside this block

        if transcribed_text:
            # Add user message immediately after transcription
            st.session_state.chat_history.append({"role": "user", "content": transcribed_text})
            save_chat_history(st.session_state.chat_history)

            # Process the transcription directly without rerunning
            logging.info(f"Processing transcribed text directly: {transcribed_text[:100]}...")

            with st.spinner("Extracting information..."):
                logging.info(f"Starting knowledge graph extraction for text: {transcribed_text[:100]}...")
                try:
                    logging.info("Calling extract_kg_data function...")
                    extracted_data: Optional[KnowledgeGraph] = asyncio.run(extract_kg_data(transcribed_text))
                    if extracted_data is not None:
                        logging.info(f"Knowledge graph extraction completed successfully. Found {len(extracted_data.persons)} persons, {len(extracted_data.events)} events, {len(extracted_data.relationships)} relationships.")
                        if extracted_data.persons:
                            logging.info(f"Extracted persons: {[p.name for p in extracted_data.persons]}")
                        if extracted_data.events:
                            logging.info(f"Extracted events: {[e.description for e in extracted_data.events]}")
                        if extracted_data.relationships:
                            logging.info(f"Extracted relationships: {[(r.source, r.target, r.type) for r in extracted_data.relationships]}")
                    else:
                        logging.error("Knowledge graph extraction returned None.")
                except Exception as e:
                    logging.error(f"Exception during knowledge graph extraction: {str(e)}")
                    import traceback
                    logging.error(f"Traceback: {traceback.format_exc()}")
                    extracted_data = None

                logging.info(f"Extraction complete. extracted_data is None: {extracted_data is None}")

            if extracted_data:
                # Identify new persons BEFORE merging anything
                new_persons = identify_new_persons(st.session_state.knowledge_graph, extracted_data.persons)

                if new_persons:
                    # Need confirmation - store data and set flag
                    st.session_state.needs_confirmation = True
                    st.session_state.new_persons_buffer = new_persons
                    st.session_state.extracted_data_buffer = extracted_data  # Store all extracted data
                    logging.info("Extraction complete, pausing for user confirmation.")
                    st.rerun()  # Rerun to display the confirmation form

                else:
                    # No new persons, merge directly (only events and relationships)
                    logging.info("No new persons found, merging events and relationships directly.")
                    updated_kg = merge_confirmed_data(
                        current_kg=st.session_state.knowledge_graph,
                        confirmed_persons=[],  # No new persons to confirm
                        extracted_events=extracted_data.events,
                        extracted_relationships=extracted_data.relationships
                    )
                    if updated_kg != st.session_state.knowledge_graph:
                        st.session_state.knowledge_graph = updated_kg
                        save_kg(st.session_state.knowledge_graph)
                        logging.info("Knowledge graph updated with events/relationships.")
                        st.sidebar.json(st.session_state.knowledge_graph.model_dump(), expanded=False)  # Update sidebar
                        assistant_response = f"Okay, I processed the story and added {len(extracted_data.events)} event(s) and {len(extracted_data.relationships)} relationship(s) to the knowledge graph."
                    else:
                        assistant_response = "Okay, I processed the story. No new information was added to the knowledge graph."
                    processed_successfully = True

            elif extracted_data is not None:  # Extraction ran but found nothing
                assistant_response = "I understood the story, but didn't find any people, events, or relationships to add."
                processed_successfully = True
            else:  # Extraction failed
                assistant_response = "I understood the story, but encountered an error trying to extract structured information."
                processed_successfully = False  # Indicate failure

            # Generate TTS only if processing didn't pause for confirmation
            if not st.session_state.needs_confirmation:
                with st.spinner("Generating audio response..."):
                    synthesized_audio = asyncio.run(synthesize_speech(assistant_response))

                st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
                save_chat_history(st.session_state.chat_history)

                if synthesized_audio:
                    st.audio(synthesized_audio, format="audio/wav")

                # Reset processing state only if not paused for confirmation
                st.session_state.processing = False
                st.session_state.audio_bytes_to_process = None  # Clear processed bytes
                st.session_state.uploaded_file_key += 1  # Increment key to reset uploader/input
                st.rerun()

        # Handle transcription failure case (check processing flag to avoid double error)
        elif st.session_state.processing:
            st.error("Transcription failed. Please check the logs or try a different file/recording.")
            st.session_state.processing = False
            st.session_state.audio_bytes_to_process = None  # Clear bytes on failure too
            st.session_state.uploaded_file_key += 1  # Increment key to reset uploader/input
            st.rerun() 