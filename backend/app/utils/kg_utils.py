import logging
from typing import List
from .models import KnowledgeGraph, Person, Event, Relationship, normalize_id

def identify_new_persons(current_kg: KnowledgeGraph, extracted_persons: List[Person]) -> List[Person]:
    """Identifies persons from the extracted list that are not in the current KG."""
    current_person_ids = current_kg.get_person_ids()
    new_persons = []
    seen_ids = set() # Track IDs encountered in this extraction to avoid duplicates within the extraction itself
    for person in extracted_persons:
        person_id = normalize_id(person.name) # Ensure ID is normalized before checking
        if person_id and person_id not in current_person_ids and person_id not in seen_ids:
            # Recreate person with normalized ID before adding
            new_persons.append(Person(id=person_id, name=person.name))
            seen_ids.add(person_id)
    if new_persons:
        logging.info(f"Identified {len(new_persons)} potential new persons: {[p.name for p in new_persons]}")
    return new_persons

def merge_confirmed_data(current_kg: KnowledgeGraph, confirmed_persons: List[Person], extracted_events: List[Event], extracted_relationships: List[Relationship]) -> KnowledgeGraph:
    """Merges confirmed persons, all extracted events, and related relationships into the current KG."""
    updated_kg = current_kg.model_copy(deep=True)

    current_person_ids = updated_kg.get_person_ids()
    current_event_ids = updated_kg.get_event_ids()
    current_relationships = updated_kg.get_relationship_tuples()

    # Add confirmed new persons
    confirmed_person_ids = set()
    for person in confirmed_persons:
        # ID should already be normalized from identify_new_persons
        if person.id and person.id not in current_person_ids:
            updated_kg.persons.append(person)
            current_person_ids.add(person.id)
            confirmed_person_ids.add(person.id) # Track added persons for relationship check
            logging.info(f"Adding confirmed new person: {person.name} (ID: {person.id})")

    # Add new events (no confirmation needed for events in this version)
    event_ids_added_this_run = set()
    for event in extracted_events:
        # Attempt to normalize ID from description if needed, or ensure it exists
        event_id = normalize_id(event.id if event.id else event.description[:30])

        if event_id and event_id not in current_event_ids and event_id not in event_ids_added_this_run:
            # Recreate event with normalized ID and attendees if present
            attendees = getattr(event, 'attendees', [])
            updated_kg.events.append(Event(id=event_id, description=event.description, attendees=attendees))
            current_event_ids.add(event_id)
            event_ids_added_this_run.add(event_id)
            logging.info(f"Adding new event: {event.description[:30]}... (ID: {event_id})")

    # Add new relationships (ensuring nodes exist and relationship is new)
    # Nodes can be existing ones OR newly confirmed persons OR newly added events
    all_person_ids = current_kg.get_person_ids().union(confirmed_person_ids)
    all_event_ids = current_kg.get_event_ids().union(event_ids_added_this_run) # Use updated event IDs

    rels_added_this_run = set()
    for rel in extracted_relationships:
        source_id = normalize_id(rel.source) # Normalize IDs just in case
        target_id = normalize_id(rel.target)
        rel_type = rel.type.upper() # Standardize relationship type case

        # Check if source and target nodes exist in the updated graph
        source_exists = source_id in all_person_ids or source_id in all_event_ids
        target_exists = target_id in all_person_ids or target_id in all_event_ids

        if not source_exists:
            logging.warning(f"Skipping relationship: Source node '{source_id}' not found in KG.")
            continue
        if not target_exists:
            logging.warning(f"Skipping relationship: Target node '{target_id}' not found in KG.")
            continue

        rel_tuple = (source_id, target_id, rel_type)
        if rel_tuple not in current_relationships and rel_tuple not in rels_added_this_run:
             # Recreate relationship with normalized IDs and type
            updated_kg.relationships.append(Relationship(source=source_id, target=target_id, type=rel_type, context=rel.context))
            current_relationships.add(rel_tuple)
            rels_added_this_run.add(rel_tuple)
            logging.info(f"Adding new relationship: {source_id} -[{rel_type}]-> {target_id}")

    return updated_kg
