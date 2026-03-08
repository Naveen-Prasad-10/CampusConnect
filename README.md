# CampusConnect – AI‑Powered College Event Chatbot  
**Backend (FastAPI) · v2.0**  
_Scoring‑based multi‑intent NLP with per‑session memory & structured replies_

This README replaces the original development guide and reflects the
current `app.py`. The core behaviour is implemented entirely within that
file; many helper functions are annotated there.

---

## Features

* Natural‑language chat via `POST /chat` with session IDs.
* Multi‑intent scoring (e.g. “tech events with open registration”).
* Entity extraction for specific event names (fuzzy matching, noise
  stripping).
* Context‑aware follow‑ups (remember the last set of events).
* Rich replies with Markdown, randomised variants, time‑based greetings.
* Session history endpoints (`GET`/`DELETE /history/{id}`).
* Raw REST filter API for events (`GET /events` with query params).
* Health probe and frontend static file serving (`GET /health`, `/`).

---

## Architecture
Frontend (React + Vite) → FastAPI backend (app.py) → EVENTS list/data
## 1. Project Architecture

The system follows a three-layer architecture.


*Frontend*  
– Chat UI that sends user messages to `/chat` and renders returned
  `response` text and `events` array.

*Backend*  
– Normalises text, scores intents, extracts entities, builds responses.  
– Maintains in‑memory `EVENTS` list (mocked; Google Sheets integration
  can replace it later).  
– Stores per‑session history in `chat_sessions` for context.

*Data layer*  
– Currently hard‑coded; each event is a dict with fields such as
  `name`, `date`, `type`, `registration`, `volunteer`, plus optional
  metadata (`venue`, `description`, etc.).

---

## Setup

1. **Clone repository**

    ```powershell
    git clone <repo-url>
    cd CampusConnect
    ```

2. **Create & activate virtualenv**

    ```powershell
    python -m venv venv
    venv\Scripts\activate      # Windows
    # or: source venv/bin/activate
    ```

3. **Install dependencies**

    ```powershell
    pip install -r requirements.txt
    ```

4. **Run backend**

    ```powershell
    uvicorn app:app --reload
    ```

Server: `http://127.0.0.1:8000`  
Interactive docs: `http://127.0.0.1:8000/docs`

(Optional) install `python-dotenv` and add a `.env` file; `app.py` loads
it if available.

---

## Event schema

Events are plain dictionaries. Required keys used by filters:

``` json
{
  "name": "Hackathon 2026",
  "date": "2026-03-10",
  "type": "tech",
  "registration": "open",
  "volunteer": "yes"
}
```

Additional fields (time, venue, organizer, capacity, prize,
description) enrich detail responses.
_fmt_event() in app.py normalises missing fields for API output.

When migrating to Google Sheets, use columns matching these keys.

## 4. Intent Classification Module

Intent classification determines what the user wants to know about events.

The system currently supports the following intents:

Intent	Example Queries
upcoming_events	"What events are coming up?"
ongoing_events	"What events are happening today?"
open_registrations	"Which events are open for registration?"
volunteer_opportunities	"Where can I volunteer?"
Implementation Strategy

The initial implementation uses keyword scoring.

Example logic:

scores = {intent: 0 for intent in intents}

for intent, words in intents.items():
    for word in words:
        if word in query:
            scores[intent] += 1

The intent with the highest score is selected.

Future improvements may include:

TF-IDF similarity

Sentence embeddings

transformer-based intent detection

## 5. Event Retrieval Module

After detecting intent, the system retrieves relevant events.

Example filtering logic:

Registration queries
[e for e in events if e["registration"] == "open"]
Volunteer queries
[e for e in events if e["volunteer"] == "yes"]
Upcoming events

Return all future events sorted by date.

## 6. Google Sheets Integration

The backend should retrieve event data dynamically using the Google Sheets API.

Steps:

Create a Google Cloud project

Enable Google Sheets API

Create a service account

Download the credentials JSON

Share the Google Sheet with the service account email

## 7. Chat Response Generation

Responses should be clear and structured.

Example:

User query:

Which events are open for registration?

Response:

Open registrations:
• Hackathon (March 10)
• AI Workshop (March 15)
## 8. Frontend Chat Interface

The frontend should:

display chat messages

send requests to /chat

display responses from backend

Example API request:

fetch("/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({ message: userMessage })
})
## 9. Future Enhancements

Possible improvements include:

#### 1. Event category filtering

Example:

Any tech events?
#### 2. Date extraction

Example:

Events tomorrow
#### 3. Recommendation system

Suggest events based on:

user interests

past queries

#### 4. Advanced NLP

Possible upgrades:

Sentence Transformers

BERT intent classification

Named Entity Recognition (NER)

## 10. Contribution Guidelines

When adding new features:

Maintain modular code structure

Document new functions clearly

Ensure API endpoints remain consistent

Test queries using the /docs interface

## 11. Suggested Folder Structure
```CampusConnect/
│
├── backend/
│   ├── app.py
│   ├── intent_classifier.py
│   ├── event_service.py
│
├── frontend/
│   ├── src/
│   ├── components/
│
├── requirements.txt
├── README.md
└── .gitignore```
