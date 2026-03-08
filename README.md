Development Guide for Contributors

This document provides implementation guidelines for extending the CampusConnect AI Event Chatbot. The goal is to implement the utilities described in the project abstract, including intent classification, structured data retrieval, and a conversational interface for event discovery. 

NLP_abstract

1. Project Architecture

The system follows a three-layer architecture.

Frontend (React + Vite)
        ↓
Backend API (FastAPI)
        ↓
Intent Classification + Query Processing
        ↓
Event Database (Google Sheets)
Component Responsibilities

Frontend

Provides a chatbot-style interface

Sends user queries to backend API

Displays structured responses

Backend

Processes user queries

Performs intent classification

Retrieves event data

Generates response messages

Data Layer

Stores event information in Google Sheets

Provides dynamic updates without modifying backend code

2. Development Environment Setup
1. Clone the repository
git clone <repo-url>
cd CampusConnect
2. Create a virtual environment
python -m venv venv

Activate it:

Windows

venv\Scripts\activate

Linux / Mac

source venv/bin/activate
3. Install dependencies
pip install -r requirements.txt
4. Run the backend server
uvicorn app:app --reload

Server will start at:

http://127.0.0.1:8000

Interactive API documentation:

http://127.0.0.1:8000/docs
3. Event Data Schema

Event information should follow a consistent structure.

Example schema:

{
  "name": "AI Workshop",
  "date": "2026-03-15",
  "type": "tech",
  "registration": "open",
  "volunteer": "yes"
}

Recommended columns in Google Sheets:

Event Name	Date	Category	Registration	Volunteer
Hackathon	10 Mar	Tech	Open	Yes
Music Night	12 Mar	Cultural	Closed	No
4. Intent Classification Module

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

5. Event Retrieval Module

After detecting intent, the system retrieves relevant events.

Example filtering logic:

Registration queries
[e for e in events if e["registration"] == "open"]
Volunteer queries
[e for e in events if e["volunteer"] == "yes"]
Upcoming events

Return all future events sorted by date.

6. Google Sheets Integration

The backend should retrieve event data dynamically using the Google Sheets API.

Steps:

Create a Google Cloud project

Enable Google Sheets API

Create a service account

Download the credentials JSON

Share the Google Sheet with the service account email

7. Chat Response Generation

Responses should be clear and structured.

Example:

User query:

Which events are open for registration?

Response:

Open registrations:
• Hackathon (March 10)
• AI Workshop (March 15)
8. Frontend Chat Interface

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
9. Future Enhancements

Possible improvements include:

1. Event category filtering

Example:

Any tech events?
2. Date extraction

Example:

Events tomorrow
3. Recommendation system

Suggest events based on:

user interests

past queries

4. Advanced NLP

Possible upgrades:

Sentence Transformers

BERT intent classification

Named Entity Recognition (NER)

10. Contribution Guidelines

When adding new features:

Maintain modular code structure

Document new functions clearly

Ensure API endpoints remain consistent

Test queries using the /docs interface

11. Suggested Folder Structure
CampusConnect/
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
└── .gitignore