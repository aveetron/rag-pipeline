# RAG Pipeline Architecture

![My Image](/assets/pipeline.png)

## Components

- **Data Ingestion**: Collects data from various sources.
- **Data Processing**: Cleans and structures the data.
- **Vectorization**: Converts data into vectors.
- **Vector Store**: Stores the vectors.
- **Query Processing**: Processes user queries.
- **Response Generation**: Generates responses using the retrieved data

## Query API (streaming)

RAG answers are streamed over **Server-Sent Events** (SSE). Use this endpoint when you want token-by-token output (not a single JSON body at the end).

**URL:** `http://127.0.0.1:8000/query/ask/stream`  
**Method:** `POST`  
**Content-Type:** `application/json`

### Request body

| Field | Type | Description |
|--------|------|-------------|
| `question` | string | User question |
| `collection_name` | string | **Qdrant collection name / ID** — the UUID of the collection created when your document was ingested (same value as in Qdrant; after ingestion it appears in server logs, e.g. `qdrant indexed ... collection <uuid>`) |
| `top_k` | integer (optional) | How many chunks to retrieve (default `5`, max `20`) |

### Example payload

```json
{
  "question": "describe his experience in backend and devops in 5 sentences",
  "collection_name": "32e0894d-c466-449d-812f-f839589d5dbf",
  "top_k": 5
}
```

### Example (curl)

```bash
curl -N -X POST "http://127.0.0.1:8000/query/ask/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "describe his experience in backend and devops in 5 sentences",
    "collection_name": "32e0894d-c466-449d-812f-f839589d5dbf",
    "top_k": 5
  }'
```

The response is `text/event-stream`: lines like `data: {"delta":"..."}` for answer text, then `data: [DONE]` when finished. On errors before streaming starts, you may see `data: {"error":"..."}`.

### Non-streaming JSON (full answer in one response)

`POST http://127.0.0.1:8000/query/ask` with the same JSON body returns `{"answer":"...","sources":[...]}`.
