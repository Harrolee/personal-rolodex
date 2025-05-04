import logging
from typing import Optional
import instructor
from openai import OpenAI
from ..config import OPENAI_API_KEY
from ..models import KnowledgeGraph

class InstructorService:
    def __init__(self):
        try:
            self.instructor_client = instructor.patch(OpenAI(api_key=OPENAI_API_KEY))
            logging.info("Instructor client initialized in InstructorService.")
        except Exception as e:
            logging.error(f"Instructor client initialization failed: {e}")
            self.instructor_client = None

    async def extract_kg_data(self, text: str) -> Optional[KnowledgeGraph]:
        if not self.instructor_client or not text:
            logging.error("Instructor client not initialized or no text provided.")
            return None
        try:
            logging.info(f"Sending text to Instructor/OpenAI for extraction: {text[:50]}...")
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
            Input: \"I went with Daniel Lomolino to State Street Pub this weekend. We met Sarah there who introduced us to her boyfriend Mike.\"
            Output:
            {
              \"persons\": [
                {"id": "daniel_lomolino", "name": "Daniel Lomolino"},
                {"id": "sarah", "name": "Sarah"},
                {"id": "mike", "name": "Mike"}
              ],
              \"events\": [
                {"id": "visit_to_state_street_pub", "description": "Visit to State Street Pub this weekend"}
              ],
              \"relationships\": [
                {"source": "daniel_lomolino", "target": "visit_to_state_street_pub", "type": "ATTENDED", "context": "Went to the pub"},
                {"source": "sarah", "target": "visit_to_state_street_pub", "type": "ATTENDED", "context": "Was at the pub"},
                {"source": "daniel_lomolino", "target": "sarah", "type": "KNOWS", "context": "Met at the pub"},
                {"source": "sarah", "target": "mike", "type": "DATING", "context": "Mike is Sarah's boyfriend"}
              ]
            }
            Always return a complete knowledge graph with all extracted information, even if the text is brief.
            """
            user_prompt = f"""
            Please extract a knowledge graph from the following text, identifying all people, events, and relationships:
            {text}
            Return a structured knowledge graph with persons, events, and relationships following the exact format from the example.
            Make sure to include at least one person, event, and relationship if they exist in the text.
            """
            logging.info("Making OpenAI API call with Instructor...")
            extracted_graph = self.instructor_client.chat.completions.create(
                model="gpt-4o",
                response_model=KnowledgeGraph,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_retries=3,
                timeout=60.0,
            )
            logging.info(f"Raw extracted graph: {extracted_graph}")
            if extracted_graph and hasattr(extracted_graph, 'persons'):
                person_names = [p.name for p in extracted_graph.persons]
                event_descs = [e.description for e in extracted_graph.events]
                rel_types = [f"{r.source}-[{r.type}]->{r.target}" for r in extracted_graph.relationships]
                logging.info(f"Instructor extraction successful. Found {len(extracted_graph.persons)} persons: {person_names}")
                logging.info(f"Found {len(extracted_graph.events)} events: {event_descs}")
                logging.info(f"Found {len(extracted_graph.relationships)} relationships: {rel_types}")
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
            logging.error(f"Text that caused the error (truncated): {text[:200]}...")
            return None 