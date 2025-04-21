import logging
import asyncio
from typing import Optional
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    SpeakOptions,
)
import instructor
from openai import OpenAI
from .config import DEEPGRAM_API_KEY, OPENAI_API_KEY
from .models import KnowledgeGraph

# --- Initialize Clients ---
try:
    # Configure Deepgram client
    dg_config: DeepgramClientOptions = DeepgramClientOptions(verbose=logging.WARNING) # Less verbose default
    deepgram_client = DeepgramClient(DEEPGRAM_API_KEY, dg_config)
    logging.info("Deepgram client initialized in services module.")

    # Initialize Instructor Client (using OpenAI)
    instructor_client = instructor.patch(OpenAI(api_key=OPENAI_API_KEY))
    logging.info("Instructor client initialized in services module.")

except Exception as e:
    logging.error(f"API client initialization failed in services module: {e}")
    # We might want to raise this or handle it more gracefully depending on app structure
    deepgram_client = None
    instructor_client = None


# --- Deepgram Functions ---

async def transcribe_audio(audio_data: bytes) -> Optional[str]:
    """Sends audio data to Deepgram for transcription."""
    if not deepgram_client or not audio_data:
        logging.error("Deepgram client not initialized or no audio data provided.")
        return None
    try:
        # Assuming WAV based on previous context, adjust mimetype if needed
        source = {'buffer': audio_data, 'mimetype': 'audio/wav'}
        options = {"punctuate": True, "model": "nova-2", "language": "en-US"}
        logging.info("Sending audio buffer to Deepgram for transcription...")
        # Corrected API method for SDK v3 buffer transcription
        response = deepgram_client.listen.prerecorded.v("1").transcribe_file(source, options)
        # Access transcript from PrerecordedResponse object
        # Based on SDK v3 structure
        if response and hasattr(response, 'results'):
            # Access transcript from the response object's properties
            transcript = response.results.channels[0].alternatives[0].transcript
            logging.info(f"Transcription received: {transcript[:50]}...")
            return transcript
        else:
            logging.error(f"Unexpected Deepgram transcription response format: {response}")
            return None
    except Exception as e:
        logging.error(f"Deepgram transcription error: {e}")
        # Optionally re-raise or return None
        return None

async def synthesize_speech(text: str) -> Optional[bytes]:
    """Sends text to Deepgram for speech synthesis."""
    if not deepgram_client or not text:
        logging.error("Deepgram client not initialized or no text provided.")
        return None
    try:
        SPEAK_OPTIONS = {"text": text}
        options = SpeakOptions(
            model="aura-asteria-en", # Example voice model
            encoding="linear16",    # Common encoding
            container="wav"         # Common container
        )
        logging.info(f"Sending text to Deepgram for synthesis: {text[:50]}...")
        
        # Use the synchronous version of the API instead of await
        response = deepgram_client.speak.v("1").stream(SPEAK_OPTIONS, options)
        
        # Check if stream is valid before reading
        if response and hasattr(response, 'stream') and response.stream:
             audio_bytes = response.stream.read() # Read all bytes from the stream
             logging.info("Speech synthesis received.")
             return audio_bytes
        else:
             logging.error("Invalid response or stream from Deepgram TTS.")
             return None
    except Exception as e:
        logging.error(f"Deepgram synthesis error: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return None


# --- Instructor Knowledge Extraction ---
async def extract_kg_data(text: str) -> Optional[KnowledgeGraph]:
    """Uses Instructor and OpenAI to extract KG data from text."""
    if not instructor_client or not text:
        logging.error("Instructor client not initialized or no text provided.")
        return None
    try:
        logging.info(f"Sending text to Instructor/OpenAI for extraction: {text[:50]}...")
        # Use instructor_client to call OpenAI and get structured output
        
        # More detailed system prompt with examples
        system_prompt = """
        You are an expert at extracting information about people, events, and their relationships from text narratives.
        
        Extract all people mentioned in the text, events they participated in, and relationships between people.
        
        For each person:
        - Create a unique ID (normalized name with underscores)
        - Include their full name
        
        For each event:
        - Create a unique ID
        - Include a brief description
        
        For relationships:
        - Identify connections between people (KNOWS, FRIENDS_WITH, etc.)
        - Identify connections between people and events (ATTENDED, ORGANIZED, etc.)
        - Include context about the relationship when available
        
        Even if the text is brief, extract as much information as possible.
        
        Here's an example:
        
        Input: "I went with Daniel Lomolino to State Street Pub this weekend. We met Sarah there who introduced us to her boyfriend Mike."
        
        Output:
        {
          "persons": [
            {"id": "daniel_lomolino", "name": "Daniel Lomolino"},
            {"id": "sarah", "name": "Sarah"},
            {"id": "mike", "name": "Mike"}
          ],
          "events": [
            {"id": "visit_to_state_street_pub", "description": "Visit to State Street Pub this weekend"}
          ],
          "relationships": [
            {"source": "daniel_lomolino", "target": "visit_to_state_street_pub", "type": "ATTENDED", "context": "Went to the pub"},
            {"source": "sarah", "target": "visit_to_state_street_pub", "type": "ATTENDED", "context": "Was at the pub"},
            {"source": "daniel_lomolino", "target": "sarah", "type": "KNOWS", "context": "Met at the pub"},
            {"source": "sarah", "target": "mike", "type": "DATING", "context": "Mike is Sarah's boyfriend"}
          ]
        }
        
        Always return a complete knowledge graph with all extracted information, even if the text is brief.
        """
        
        # More detailed user prompt
        user_prompt = f"""
        Please extract a knowledge graph from the following text, identifying all people, events, and relationships:
        
        {text}
        
        Return a structured knowledge graph with persons, events, and relationships following the exact format from the example.
        Make sure to include at least one person, event, and relationship if they exist in the text.
        """
        
        logging.info("Making OpenAI API call with Instructor...")
        
        # Set a longer timeout for the API call
        # Note: Instructor might not support await with response_model, so we'll use it without await
        extracted_graph = instructor_client.chat.completions.create(
            model="gpt-4o", # Or another suitable model like gpt-3.5-turbo
            response_model=KnowledgeGraph,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_retries=3, # Increased retries for robustness
            timeout=60.0,  # Longer timeout (60 seconds)
        )
        
        # Log the raw response for debugging
        logging.info(f"Raw extracted graph: {extracted_graph}")
        
        # More detailed success logging
        if extracted_graph and hasattr(extracted_graph, 'persons'):
            person_names = [p.name for p in extracted_graph.persons]
            event_descs = [e.description for e in extracted_graph.events]
            rel_types = [f"{r.source}-[{r.type}]->{r.target}" for r in extracted_graph.relationships]
            
            logging.info(f"Instructor extraction successful. Found {len(extracted_graph.persons)} persons: {person_names}")
            logging.info(f"Found {len(extracted_graph.events)} events: {event_descs}")
            logging.info(f"Found {len(extracted_graph.relationships)} relationships: {rel_types}")
            
            # Validate that we have at least some data
            if not extracted_graph.persons and not extracted_graph.events and not extracted_graph.relationships:
                logging.warning("Extraction returned empty knowledge graph. This might indicate a problem.")
            
            return extracted_graph
        else:
            logging.error(f"Extraction returned unexpected structure: {type(extracted_graph)}")
            return None
    except Exception as e:
        logging.error(f"Instructor/OpenAI extraction error: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        
        # Log the text that caused the error (truncated for log readability)
        logging.error(f"Text that caused the error (truncated): {text[:200]}...")
        
        return None
