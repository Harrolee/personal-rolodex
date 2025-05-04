import streamlit as st
import asyncio
from src.models import KnowledgeGraph
from src.kg_utils import identify_new_persons, merge_confirmed_data
from src.services.instructor_service import InstructorService

st.set_page_config(layout="centered")
st.title("🧪 KG Text Tester")

st.markdown("Paste a story below and extract a knowledge graph from it:")

story = st.text_area(
    "Paste or type your story here:",
    height=150,
    key="story_text_input"
)

if st.button("Extract Knowledge Graph", disabled=not story):
    with st.spinner("Extracting knowledge graph..."):
        instructor_service = InstructorService()
        extracted_kg = asyncio.run(instructor_service.extract_kg_data(story))
        if not extracted_kg:
            st.error("No knowledge graph could be extracted.")
        else:
            # Simulate user confirming all new persons
            current_kg = KnowledgeGraph()
            new_persons = identify_new_persons(current_kg, extracted_kg.persons)
            merged_kg = merge_confirmed_data(
                current_kg=current_kg,
                confirmed_persons=new_persons,
                extracted_events=extracted_kg.events,
                extracted_relationships=extracted_kg.relationships
            )
            st.success("Knowledge graph extracted!")

            # Show as JSON
            st.subheader("Knowledge Graph (JSON)")
            st.json(merged_kg.model_dump(), expanded=False)

            # Pretty print
            st.subheader("Persons")
            for p in merged_kg.persons:
                st.write(f"- **{p.name}** (id: `{p.id}`)")
            st.subheader("Events")
            for e in merged_kg.events:
                st.write(f"- **{e.description}** (id: `{e.id}`) Attendees: {', '.join(e.attendees or [])}")
            st.subheader("Relationships")
            for r in merged_kg.relationships:
                st.write(f"- `{r.source}` -[{r.type}]-> `{r.target}` (Context: {r.context})")