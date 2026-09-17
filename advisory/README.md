# Advisory Knowledge Base

Rule-based advice records, one per disease class, shipped offline to the app as a signed pack.

| Path | Purpose |
|---|---|
| `records/` | One JSON/YAML record per `class_id`: names, symptoms, actions by severity, prevention, when to call an expert, sources |
| `audio/` | Hindi audio for each advice card |

## Rules
- Every record cites trusted sources (ICAR packages of practices, state agriculture department).
- Chemical advice must include dose, pre-harvest interval and safety gear.
- A named agronomist approves every pack before release.
- **No AI-generated agronomic advice.**
