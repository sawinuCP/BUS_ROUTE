# Sri Lanka Multimodal Journey Planner
## Final product, design and technical architecture package

**Version:** 1.0  
**Prepared:** 19 November 2026  
**Status:** Proposed baseline for review before implementation

This package defines a Sri Lankan multimodal journey-planning application focused on clear, actionable travel instructions across walking, bus and rail journeys.

### Package contents
| File | Purpose |
|---|---|
| `00_EXECUTIVE_SUMMARY_AND_DECISIONS.md` | Product definition and agreed design decisions |
| `01_PRODUCT_VISION_AND_USERS.md` | Vision, personas, principles and success measures |
| `02_TRAVELLER_PROBLEMS_AND_GAPS.md` | Problem analysis and product responses |
| `03_FEATURES_AND_SCOPE.md` | Detailed features, priorities and exclusions |
| `04_USER_STORIES.md` | Individual user stories with acceptance criteria |
| `05_USER_FLOWS_AND_UI_UX.md` | Main journeys and interaction design |
| `06_SYSTEM_ARCHITECTURE.md` | Logical architecture and component responsibilities |
| `07_TECH_STACK.md` | Recommended technologies and rationale |
| `08_DATA_MODEL.md` | Core relational and geospatial data model |
| `09_DATA_INGESTION_AND_REFRESH.md` | Source ingestion, update, validation and rollback |
| `10_ROUTING_ENGINE.md` | Multimodal graph, route search and instructions |
| `11_BACKEND_API_DESIGN.md` | API boundaries and example contracts |
| `12_AI_AND_LANGUAGE_DESIGN.md` | Grounded AI, multilingual search and RAG decision |
| `13_MOBILE_APP_DESIGN.md` | Mobile architecture, offline and active journey |
| `14_SECURITY_PRIVACY_ACCESSIBILITY.md` | Security, privacy and accessibility |
| `15_TESTING_DEPLOYMENT_OPERATIONS.md` | Quality, environments, observability and release |
| `16_ROADMAP_AND_ACCEPTANCE_GATES.md` | Phased implementation plan and completion gates |
| `17_OPEN_QUESTIONS_PRE_IMPLEMENTATION.md` | Clarifications and decisions required before build |

### How to use this package
1. Read `00` through `03` to confirm product scope.
2. Review every story in `04` with the intended users.
3. Review the architecture and data refresh approach in `06` through `12`.
4. Resolve the questions in `17`.
5. Approve the first pilot geography and data-source access before implementation.

### Important limitations
This is a technical/product design, not a claim that Sri Lanka has a complete public transport API or nationally complete digital route dataset. Data availability, accuracy, update frequency, licensing and permission must be verified source by source. The first release should only plan journeys within a declared, validated coverage area. Where current service operation is unknown, the app must say so rather than imply that a bus or train is operating now.
