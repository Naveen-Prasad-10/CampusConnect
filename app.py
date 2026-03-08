from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# Allow requests from any origin (needed for browser-based frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------
# Dummy event database
# ------------------------------------------------

events = [
    {"name": "Hackathon", "date": "March 10", "type": "tech", "registration": "open", "volunteer": "yes"},
    {"name": "Music Night", "date": "March 12", "type": "cultural", "registration": "closed", "volunteer": "no"},
    {"name": "AI Workshop", "date": "March 15", "type": "tech", "registration": "open", "volunteer": "yes"}
]

# ------------------------------------------------
# Request format
# ------------------------------------------------

class Query(BaseModel):
    message: str

# ------------------------------------------------
# Intent Classification
# ------------------------------------------------

intents = {
    "registration": ["register", "registration", "sign up"],
    "volunteer": ["volunteer", "help", "assist"],
    "upcoming": ["upcoming", "next", "future", "events"],
    "ongoing": ["today", "happening", "now"]
}

def detect_intent(text):
    text = text.lower()

    scores = {intent: 0 for intent in intents}

    for intent, words in intents.items():
        for word in words:
            if word in text:
                scores[intent] += 1

    return max(scores, key=scores.get)

# ------------------------------------------------
# Chatbot Endpoint
# ------------------------------------------------

@app.post("/chat")
def chat(query: Query):

    intent = detect_intent(query.message)

    if intent == "registration":

        open_events = [e["name"] for e in events if e["registration"] == "open"]

        return {"response": f"Open registrations: {', '.join(open_events)}"}

    elif intent == "volunteer":

        volunteer_events = [e["name"] for e in events if e["volunteer"] == "yes"]

        return {"response": f"Volunteer opportunities: {', '.join(volunteer_events)}"}

    elif intent == "upcoming":

        event_list = [e["name"] for e in events]

        return {"response": f"Upcoming events: {', '.join(event_list)}"}

    else:

        return {"response": "Sorry, I couldn't understand your request."}

# ------------------------------------------------
# Serve the chatbot frontend
# ------------------------------------------------

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")