import pytest
from unittest.mock import AsyncMock, patch
from src.models import KnowledgeGraph, Person, Event, Relationship
from src.kg_utils import identify_new_persons, merge_confirmed_data
from src.services.instructor_service import InstructorService

@pytest.mark.asyncio
async def test_kg_creation_with_canned_transcription():
    # Canned transcription (story)
    canned_story = "Alice and Bob met at the Blue Bottle Cafe on Sunday. They were joined by Carol."

    # What we expect the extraction to return
    extracted_kg = KnowledgeGraph(
        persons=[
            Person(id="alice", name="Alice"),
            Person(id="bob", name="Bob"),
            Person(id="carol", name="Carol"),
        ],
        events=[
            Event(id="blue_bottle_cafe_meeting", description="Meeting at Blue Bottle Cafe on Sunday", attendees=["alice", "bob", "carol"]),
        ],
        relationships=[
            Relationship(source="alice", target="blue_bottle_cafe_meeting", type="ATTENDED", context="Alice attended the meeting"),
            Relationship(source="bob", target="blue_bottle_cafe_meeting", type="ATTENDED", context="Bob attended the meeting"),
            Relationship(source="carol", target="blue_bottle_cafe_meeting", type="ATTENDED", context="Carol attended the meeting"),
            Relationship(source="alice", target="bob", type="KNOWS", context="Met at the cafe"),
            Relationship(source="alice", target="carol", type="KNOWS", context="Met at the cafe"),
            Relationship(source="bob", target="carol", type="KNOWS", context="Met at the cafe"),
        ]
    )

    # Start with an empty KG
    current_kg = KnowledgeGraph()

    # Patch InstructorService.extract_kg_data to return our canned KG
    with patch.object(InstructorService, 'extract_kg_data', new=AsyncMock(return_value=extracted_kg)):
        instructor_service = InstructorService()
        # Simulate extraction
        result_kg = await instructor_service.extract_kg_data(canned_story)
        assert result_kg is not None
        # Identify new persons
        new_persons = identify_new_persons(current_kg, result_kg.persons)
        # Merge confirmed data (simulate user confirming all new persons)
        merged_kg = merge_confirmed_data(
            current_kg=current_kg,
            confirmed_persons=new_persons,
            extracted_events=result_kg.events,
            extracted_relationships=result_kg.relationships
        )
        # Assertions: all persons, events, and relationships should be present
        person_ids = {p.id for p in merged_kg.persons}
        assert person_ids == {"alice", "bob", "carol"}
        event_ids = {e.id for e in merged_kg.events}
        assert "blue_bottle_cafe_meeting" in event_ids
        rel_types = {(r.source, r.target, r.type) for r in merged_kg.relationships}
        assert ("alice", "bob", "KNOWS") in rel_types
        assert ("alice", "blue_bottle_cafe_meeting", "ATTENDED") in rel_types
        assert ("carol", "blue_bottle_cafe_meeting", "ATTENDED") in rel_types 