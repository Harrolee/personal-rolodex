from pydantic import BaseModel, Field
from typing import List, Optional
import re

# --- Pydantic Models for Knowledge Graph (Simple Ontology) ---

# Make Person hashable for use in sets/dicts if needed later
class Person(BaseModel, frozen=True):
    id: str = Field(..., description="Unique identifier for the person, typically their name normalized (e.g., 'john_doe').")
    name: str = Field(..., description="The full name of the person.")

class Event(BaseModel):
    id: str = Field(..., description="Unique identifier for the event (e.g., 'meeting_at_cafe_2024').")
    description: str = Field(..., description="A brief description of the event.")
    attendees: Optional[List[str]] = Field(default_factory=list, description="List of person IDs who attended the event.")

class Relationship(BaseModel):
    source: str = Field(..., description="The ID of the source node (Person or Event).")
    target: str = Field(..., description="The ID of the target node (Person or Event).")
    type: str = Field(..., description="The type of relationship (e.g., 'KNOWS', 'ATTENDED').")
    context: Optional[str] = Field(None, description="Optional context about the relationship derived from the story.")

class KnowledgeGraph(BaseModel):
    persons: List[Person] = Field(default_factory=list)
    events: List[Event] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)

    def get_person_ids(self) -> set[str]:
        return {p.id for p in self.persons}

    def get_event_ids(self) -> set[str]:
        return {e.id for e in self.events}

    def get_relationship_tuples(self) -> set[tuple[str, str, str]]:
        return {(r.source, r.target, r.type) for r in self.relationships}

# --- Utility Functions ---

def normalize_id(name: str) -> str:
    """Normalizes a string to be used as an ID."""
    if not isinstance(name, str): # Handle potential non-string input
        name = str(name)
    name = name.lower()
    name = re.sub(r'\s+', '_', name) # Replace spaces with underscores
    name = re.sub(r'[^a-z0-9_]', '', name) # Remove non-alphanumeric characters except underscore
    return name.strip('_')
