# 12 — AI Assistant and Multilingual Design

## 1. AI role
AI is an optional natural-language interface and explanation layer. It is not the route database, routing algorithm or source of transport truth.

## 2. Conversational planning
1. User asks: “How do I get from A to B with less walking?”
2. LLM extracts a structured intent: origin, destination, language, constraints.
3. Place resolver returns candidate canonical IDs.
4. If ambiguous, ask user to choose.
5. Call deterministic `plan_journey` tool.
6. Tool returns structured alternatives and evidence metadata.
7. LLM explains the options using only returned facts.
8. UI presents the same structured itinerary used by standard search.

## 3. Tool boundary
Expose narrowly scoped tools:
- `search_places(query, language, near?)`
- `search_stops(query, mode?)`
- `plan_journey(origin_id, destination_id, preferences)`
- `get_journey_step(journey_id, step_id)`
- `get_transport_help(topic, language)`

Do not expose arbitrary SQL or unrestricted database access to the LLM.

## 4. Hallucination controls
- Validate tool arguments with schemas.
- Require planner result IDs for every route claim.
- Do not allow LLM to create stop IDs, route IDs, fares, times or transfer links.
- If evidence is missing, say it is unknown.
- Keep citations/provenance in internal response metadata and show user-facing freshness notes.
- Test adversarial prompts that request invented shortcuts or unsupported routes.

## 5. RAG decision
RAG is not needed for route computation. Use relational/geospatial queries and graph search for structured transport facts.

RAG may later support:
- public transport terminology explanations;
- curated travel guidance and FAQs;
- app help and policy documents;
- source documentation for internal data operators.

A vector database is not required initially. Start with PostgreSQL full-text and trigram search for names/aliases. Add embeddings only if evaluation proves lexical search inadequate for a defined use case.

## 6. Languages
- Store canonical names separately from translated/alternate aliases.
- Use language tags (e.g. `en`, `si`, `ta`) and preserve original script.
- Keep transliteration as a search alias, not a replacement for native script.
- Have native speakers review transport instructions and critical terminology.
- Never machine-translate unverified destination-board wording and present it as official.
- UI language and transport display language can be independently configured.
