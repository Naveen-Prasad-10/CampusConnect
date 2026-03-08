"""
CampusConnect – AI-Powered College Event Chatbot  v2.0
Backend : FastAPI
NLP     : Scoring-based multi-intent classification with context-awareness
Data    : In-memory event store (Google Sheets integration deferred)
"""

import os
import re
import uuid
import random
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ── Optional: load .env file if python-dotenv is installed ───────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("campusconnect")

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="CampusConnect Chatbot API",
    description="AI-powered college event chatbot. Scoring-based NLP with session memory.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# EVENT DATA  (mock — Google Sheets integration deferred)
# =============================================================================

EVENTS: list[dict] = [
    {
        "name": "Hackathon 2026",
        "date": "2026-03-10",
        "type": "tech",
        "registration": "open",
        "volunteer": "yes",
        "venue": "Main Auditorium",
        "description": (
            "A 24-hour coding marathon open to all students. "
            "Build innovative solutions to real-world problems and compete for ₹50,000 in prizes."
        ),
    },
    {
        "name": "Music Night",
        "date": "2026-03-12",
        "type": "cultural",
        "registration": "closed",
        "volunteer": "no",
        "venue": "Open-Air Theatre",
        "description": "An evening of live performances by student bands and guest artists. Free entry for all.",
    },
    {
        "name": "AI & ML Workshop",
        "date": "2026-03-15",
        "type": "tech",
        "registration": "open",
        "volunteer": "yes",
        "venue": "Seminar Hall B",
        "description": (
            "Hands-on workshop covering machine learning fundamentals, model training, and deployment. "
            "Laptop required."
        ),
    },
    {
        "name": "Cultural Fest",
        "date": "2026-03-18",
        "type": "cultural",
        "registration": "open",
        "volunteer": "yes",
        "venue": "Campus Ground",
        "description": (
            "Annual inter-college cultural extravaganza featuring dance, drama, and art competitions. "
            "Cash prizes for winners."
        ),
    },
    {
        "name": "Career Fair 2026",
        "date": "2026-03-20",
        "type": "career",
        "registration": "open",
        "volunteer": "no",
        "venue": "Exhibition Hall",
        "description": "Top recruiters across sectors visiting campus for placements and internship opportunities.",
    },
    {
        "name": "Photography Exhibition",
        "date": "2026-03-08",
        "type": "art",
        "registration": "closed",
        "volunteer": "yes",
        "venue": "Gallery Room 1",
        "description": "Showcasing student photography work on the theme 'Urban Life'. Open all day.",
    },
    {
        "name": "Robotics Demo Day",
        "date": "2026-03-08",
        "type": "tech",
        "registration": "open",
        "volunteer": "yes",
        "venue": "Engineering Block C",
        "description": "Live demonstrations of student-built robots competing in an obstacle course.",
    },
    {
        "name": "Entrepreneurship Summit",
        "date": "2026-03-22",
        "type": "career",
        "registration": "open",
        "volunteer": "yes",
        "venue": "Conference Hall A",
        "description": "Pitch your startup ideas to investors. Workshops on funding, branding, and product design.",
    },
    {
        "name": "Classical Dance Showcase",
        "date": "2026-03-25",
        "type": "cultural",
        "registration": "open",
        "volunteer": "yes",
        "venue": "Mini Auditorium",
        "description": "Annual classical dance performances by students. Bharatanatyam, Kathak, and Mohiniyattam.",
    },
    {
        "name": "Cybersecurity Bootcamp",
        "date": "2026-03-28",
        "type": "tech",
        "registration": "open",
        "volunteer": "no",
        "venue": "Lab Complex 2",
        "description": (
            "Intensive two-day bootcamp on ethical hacking, CTF challenges, and network security fundamentals."
        ),
    },
]

TODAY_STR = datetime.now().strftime("%Y-%m-%d")

# =============================================================================
# SESSION STORE  (persistent chat history per session_id)
# =============================================================================
# Structure: { session_id: [ { "role": "user"|"bot", "text": ..., "timestamp": ... } ] }
chat_sessions: dict[str, list[dict]] = {}

# =============================================================================
# NLP — TEXT NORMALISATION
# =============================================================================

CONTRACTIONS = {
    "what's": "what is", "where's": "where is", "when's": "when is",
    "who's": "who is", "how's": "how is", "i'm": "i am", "i've": "i have",
    "can't": "cannot", "won't": "will not", "don't": "do not",
    "isn't": "is not", "aren't": "are not", "haven't": "have not",
    "there's": "there is", "that's": "that is", "it's": "it is",
    "what're": "what are", "when're": "when are",
}


def normalize(text: str) -> str:
    """Lowercase, expand contractions, remove punctuation, collapse spaces."""
    text = text.lower().strip()
    for contraction, expansion in CONTRACTIONS.items():
        text = text.replace(contraction, expansion)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# =============================================================================
# NLP — MULTI-INTENT SCORING
# =============================================================================

# Each entry: (phrase_or_keyword, weight)
# Higher weights = stronger signal. Multi-word phrases score higher intentionally.
INTENT_KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "greeting": [
        ("hello", 3), ("hi", 3), ("hey", 3), ("good morning", 4),
        ("good afternoon", 4), ("good evening", 4), ("howdy", 2),
        ("greetings", 3), ("whats up", 3), ("sup", 2), ("yo", 2),
    ],
    "help": [
        ("help", 3), ("what can you do", 5), ("guide me", 4),
        ("how do i use", 4), ("commands", 3), ("options", 2),
        ("what do you know", 4), ("tell me about yourself", 5),
        ("features", 3), ("capabilities", 3), ("what can i ask", 4),
    ],
    "upcoming": [
        ("upcoming", 4), ("future events", 4), ("next events", 4),
        ("next", 2), ("soon", 3), ("scheduled", 3), ("coming up", 4),
        ("all events", 4), ("list events", 4), ("show events", 4),
        ("what events", 3), ("events are there", 4), ("events happening", 3),
        ("any events", 3), ("show me events", 4),
    ],
    "ongoing": [
        ("today", 4), ("right now", 5), ("happening now", 5),
        ("ongoing", 4), ("current events", 5), ("live", 3),
        ("currently", 4), ("this moment", 4), ("at the moment", 4),
        ("today events", 5), ("whats on today", 5),
    ],
    "registration": [
        ("register", 4), ("registration", 4), ("sign up", 4),
        ("enroll", 4), ("enrollment", 4), ("apply", 3),
        ("how to join", 4), ("open registration", 5),
        ("registrations open", 5), ("which events can i join", 5),
        ("can i register", 4), ("join an event", 4),
    ],
    "volunteer": [
        ("volunteer", 4), ("volunteering", 4), ("help out", 3),
        ("assist", 3), ("contribute", 3), ("support the event", 4),
        ("be a volunteer", 5), ("volunteer opportunities", 5),
        ("give back", 3), ("help with events", 4),
    ],
    "event_detail": [
        ("tell me about", 5), ("details", 4), ("info about", 5),
        ("information about", 5), ("describe", 3), ("more about", 4),
        ("what is the", 3), ("when is the", 3), ("where is the", 3),
        ("venue", 4), ("what time", 3), ("about the", 3),
    ],
    "category_filter": [
        ("tech events", 6), ("technology events", 6), ("cultural events", 6),
        ("art events", 6), ("career events", 6), ("coding events", 5),
        ("tech", 3), ("technology", 3), ("cultural", 3), ("culture", 3),
        ("art", 3), ("career", 3), ("sports", 3), ("robotics", 3),
        ("music events", 5), ("drama", 3), ("dance events", 5),
        ("engineering events", 5), ("science events", 5), ("startup", 3),
    ],
    "farewell": [
        ("bye", 4), ("goodbye", 4), ("see you", 4), ("cya", 4),
        ("take care", 3), ("later", 3), ("thanks bye", 5), ("thank you bye", 5),
        ("exit", 3), ("quit", 3),
    ],
    "thanks": [
        ("thanks", 4), ("thank you", 4), ("thx", 4), ("appreciate it", 4),
        ("appreciate that", 4), ("great", 2), ("awesome", 2), ("perfect", 2),
        ("helpful", 3), ("that helps", 4), ("nice", 2),
    ],
}


def score_intents(text: str) -> dict[str, int]:
    scores = {intent: 0 for intent in INTENT_KEYWORDS}
    for intent, kw_list in INTENT_KEYWORDS.items():
        for phrase, weight in kw_list:
            if phrase in text:
                scores[intent] += weight
    return scores


def detect_intents(text: str, top_n: int = 2) -> list[tuple[str, int]]:
    """
    Return the top-N scoring intents above zero, sorted descending by score.
    This enables multi-intent handling (e.g. 'tech events with open registration').
    """
    normalised = normalize(text)
    scores = score_intents(normalised)
    ranked = sorted(
        [(intent, score) for intent, score in scores.items() if score > 0],
        key=lambda x: x[1],
        reverse=True,
    )
    return ranked[:top_n] if ranked else [("unknown", 0)]

# =============================================================================
# CONTEXT HELPERS  —  read previous turns to understand follow-ups
# =============================================================================

# Keywords that suggest the user is asking a follow-up rather than a new question
FOLLOWUP_SIGNALS = [
    "what about", "and", "those", "them", "these", "more about",
    "which of them", "of those", "from those", "any of them",
    "how about", "can i", "are any", "which ones",
]


def is_followup(text: str) -> bool:
    t = normalize(text)
    return any(sig in t for sig in FOLLOWUP_SIGNALS) and len(t.split()) < 12


def last_bot_events(history: list[dict]) -> list[str]:
    """Return the event names mentioned in the most recent bot turn (if any)."""
    for turn in reversed(history):
        if turn["role"] == "bot" and turn.get("event_names"):
            return turn["event_names"]
    return []


def get_context_scope(history: list[dict], all_events: list[dict]) -> list[dict]:
    """
    If the last bot reply narrowed results to a subset, return that subset
    so follow-up questions can be answered in-context.
    """
    names = last_bot_events(history)
    if not names:
        return all_events
    return [e for e in all_events if e["name"] in names] or all_events

# =============================================================================
# RESPONSE BUILDER  —  varied, rich, structured replies
# =============================================================================

def _fmt_event(e: dict) -> dict:
    return {
        "name": e.get("name", ""),
        "date": e.get("date", ""),
        "type": e.get("type", ""),
        "registration": e.get("registration", ""),
        "volunteer": e.get("volunteer", ""),
        "venue": e.get("venue", "TBD"),
        "description": e.get("description", ""),
    }


def _pick(*options: str) -> str:
    """Randomly choose one of several response variants for natural variety."""
    return random.choice(options)


def _time_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def _event_summary(e: dict) -> str:
    reg = "✅ Open" if e.get("registration") == "open" else "❌ Closed"
    vol = "🙋 Yes" if e.get("volunteer") == "yes" else "➖ No"
    return (
        f"**{e['name']}** | 📅 {e['date']} | 🏛 {e.get('venue','TBD')}\n"
        f"_{e.get('description','')}_\n"
        f"Registration: {reg} | Volunteer: {vol}"
    )


def _no_results_msg(filter_desc: str) -> str:
    return _pick(
        f"😕 No events matched **{filter_desc}** right now. Check back soon — the calendar updates regularly!",
        f"🔍 I couldn't find any **{filter_desc}** events at the moment. Stay tuned for new additions!",
        f"📭 Nothing under **{filter_desc}** currently. Try a different filter or type **help** to see what I can search.",
    )


# ── Category synonym map ──────────────────────────────────────────────────────
CATEGORY_ALIASES: dict[str, list[str]] = {
    "tech": ["tech", "technology", "coding", "engineering", "robotics", "science",
             "ai", "machine learning", "cybersecurity", "computer", "software"],
    "cultural": ["cultural", "culture", "music", "dance", "drama", "art", "fest",
                 "performance", "showcase", "classical"],
    "career": ["career", "job", "placement", "internship", "recruitment",
               "startup", "entrepreneur", "business"],
    "art": ["art", "photography", "painting", "exhibition", "gallery"],
}


def _resolve_category(text: str) -> Optional[str]:
    for cat, aliases in CATEGORY_ALIASES.items():
        if any(alias in text for alias in aliases):
            return cat
    return None


def build_response(
    intents_ranked: list[tuple[str, int]],
    message: str,
    history: list[dict],
) -> dict:
    """
    Build a structured chatbot response.
    Supports multi-intent (e.g. category_filter + registration).
    Returns: { "response", "events", "event_names" }
    """
    all_events = EVENTS
    norm_msg = normalize(message)

    # Resolve primary (and optional secondary) intents
    primary_intent, primary_score = intents_ranked[0]
    secondary_intent = intents_ranked[1][0] if len(intents_ranked) > 1 else None
    secondary_score  = intents_ranked[1][1] if len(intents_ranked) > 1 else 0

    # Effective event pool — narrows automatically for follow-ups
    followup = is_followup(message)
    event_pool = get_context_scope(history, all_events) if followup else all_events

    matched_events: list[dict] = []
    response_text = ""

    # ── Greeting ──────────────────────────────────────────────────────────────
    if primary_intent == "greeting":
        greeting = _time_greeting()
        response_text = _pick(
            f"{greeting}! 👋 I'm **CampusConnect**, your campus event assistant. "
            "Ask me about upcoming events, registrations, volunteering, or any specific event!",
            f"Hey there! 😊 Welcome to **CampusConnect**! "
            f"{greeting}! I can help you explore campus events, find open registrations, and lots more.",
            f"Hi! 👋 {greeting}! I'm here to keep you in the loop about everything happening on campus. "
            "What would you like to know?",
        )

    # ── Thanks ────────────────────────────────────────────────────────────────
    elif primary_intent == "thanks":
        response_text = _pick(
            "You're welcome! 😊 Is there anything else I can help you with?",
            "Happy to help! 🎉 Let me know if you have more questions.",
            "Glad that was useful! Feel free to ask anything else about campus events.",
            "No problem at all! 👌 Anything else you'd like to know?",
        )

    # ── Farewell ──────────────────────────────────────────────────────────────
    elif primary_intent == "farewell":
        response_text = _pick(
            "Goodbye! 👋 Hope to see you at an event soon!",
            "Take care! 😊 Feel free to come back whenever you need event info.",
            "See you around! 🎓 Have a great time on campus!",
        )

    # ── Help ──────────────────────────────────────────────────────────────────
    elif primary_intent == "help":
        response_text = (
            "💡 **Here's everything I can help with:**\n\n"
            "| What you want | What to ask |\n"
            "|---|---|\n"
            "| All events | *\"Show me all upcoming events\"* |\n"
            "| Today's events | *\"What's happening today?\"* |\n"
            "| Open registrations | *\"Which events can I register for?\"* |\n"
            "| Volunteering | *\"Where can I volunteer?\"* |\n"
            "| By category | *\"Show me tech events\"* / *\"Any cultural events?\"* |\n"
            "| Event details | *\"Tell me about the Hackathon\"* |\n"
            "| Combined filters | *\"Tech events with open registration\"* |\n\n"
            "_I also remember what we talked about, so you can ask follow-up questions like "
            "\"Do any of those have open registration?\"_"
        )

    # ── Upcoming events ───────────────────────────────────────────────────────
    elif primary_intent == "upcoming":
        pool = event_pool
        matched_events = pool
        count = len(matched_events)
        response_text = _pick(
            f"📅 Here are all **{count} upcoming event(s)** I know about:",
            f"🗓️ Found **{count} event(s)** on the calendar. Take a look:",
            f"Here's a full rundown of the **{count} scheduled event(s)**:",
        ) if count else _no_results_msg("upcoming")

    # ── Ongoing today ─────────────────────────────────────────────────────────
    elif primary_intent == "ongoing":
        matched_events = [e for e in event_pool if e.get("date", "") == TODAY_STR]
        count = len(matched_events)
        response_text = _pick(
            f"🔴 **{count} event(s) happening today** ({TODAY_STR}):",
            f"📍 Today's live events ({TODAY_STR}) — there are **{count}**:",
        ) if count else (
            f"😕 Nothing is scheduled for today ({TODAY_STR}). "
            "Try asking about *upcoming events* to plan ahead!"
        )

    # ── Open registrations ◀ possibly combined with category ─────────────────
    elif primary_intent == "registration":
        pool = event_pool
        if secondary_intent == "category_filter" and secondary_score >= 3:
            cat = _resolve_category(norm_msg)
            if cat:
                pool = [e for e in pool if e.get("type", "").lower() == cat]
        matched_events = [e for e in pool if e.get("registration", "").lower() == "open"]
        count = len(matched_events)
        response_text = _pick(
            f"📝 **{count} event(s)** currently have open registrations. Don't miss out:",
            f"✅ You can register for **{count} event(s)** right now:",
            f"🎟️ Here are **{count} event(s)** that are still accepting registrations:",
        ) if count else _no_results_msg("open registration")

    # ── Volunteer ◀ possibly combined with category ───────────────────────────
    elif primary_intent == "volunteer":
        pool = event_pool
        if secondary_intent == "category_filter" and secondary_score >= 3:
            cat = _resolve_category(norm_msg)
            if cat:
                pool = [e for e in pool if e.get("type", "").lower() == cat]
        matched_events = [e for e in pool if e.get("volunteer", "").lower() == "yes"]
        count = len(matched_events)
        response_text = _pick(
            f"🙋 **{count} event(s)** are looking for volunteers — great way to get involved:",
            f"🤝 You can volunteer at **{count} event(s)**. Here they are:",
            f"💪 Found **{count}** volunteering opportunit{'y' if count == 1 else 'ies'}:",
        ) if count else _no_results_msg("volunteer")

    # ── Category filter ◀ possibly combined with registration/volunteer ───────
    elif primary_intent == "category_filter":
        cat = _resolve_category(norm_msg)
        if cat:
            pool = [e for e in event_pool if e.get("type", "").lower() == cat]
            # Combine with secondary intent if strong enough
            if secondary_intent == "registration" and secondary_score >= 3:
                pool = [e for e in pool if e.get("registration", "").lower() == "open"]
                tag = f"{cat} events with open registration"
            elif secondary_intent == "volunteer" and secondary_score >= 3:
                pool = [e for e in pool if e.get("volunteer", "").lower() == "yes"]
                tag = f"{cat} events with volunteering"
            else:
                tag = f"{cat}"
            matched_events = pool
            count = len(matched_events)
            response_text = _pick(
                f"🏷️ Found **{count} {tag}** event(s):",
                f"📌 Here are the **{count} {tag}** event(s) on the calendar:",
            ) if count else _no_results_msg(tag)
        else:
            # Couldn't detect a specific category — show all with explanation
            matched_events = list(event_pool)
            categories = sorted({e.get("type", "") for e in EVENTS})
            response_text = (
                f"🏷️ I can filter by category! Available types: **{', '.join(categories)}**.\n"
                "For now, here's everything — just tell me which category you're interested in:"
            )

    # ── Event detail ──────────────────────────────────────────────────────────
    elif primary_intent == "event_detail":
        # Match events whose name overlaps meaningfully with the user's message
        words_in_msg = set(w for w in norm_msg.split() if len(w) > 3)
        scored_events = []
        for e in event_pool:
            event_words = set(normalize(e["name"]).split())
            overlap = len(words_in_msg & event_words)
            if overlap:
                scored_events.append((overlap, e))
        scored_events.sort(key=lambda x: x[0], reverse=True)
        matched_events = [e for _, e in scored_events]

        if matched_events:
            names = " & ".join(e["name"] for e in matched_events[:2])
            response_text = _pick(
                f"🔍 Here's what I found about **{names}**:",
                f"📋 Details for **{names}**:",
                f"ℹ️ Sure! Here's the info on **{names}**:",
            )
        else:
            # Graceful fallback — show everything
            matched_events = list(event_pool)
            response_text = (
                "🔍 I couldn't pin down a specific event from that. "
                "Here's everything on the calendar — try asking by name, like "
                "*\"Tell me about the Hackathon\"*:"
            )

    # ── Unknown / no match ────────────────────────────────────────────────────
    else:
        # Check if user is asking a follow-up in context
        if followup and last_bot_events(history):
            matched_events = get_context_scope(history, all_events)
            response_text = (
                "🤔 I'm not 100% sure what you're asking, but here's what we were looking at:"
            )
        else:
            response_text = _pick(
                "🤔 I didn't quite catch that. You can ask me about:\n"
                "- *Upcoming events* or *what's happening today*\n"
                "- *Open registrations* or *volunteering opportunities*\n"
                "- *Tech events*, *cultural events*, or other categories\n"
                "- *Tell me about [event name]* for details\n"
                "Type **help** to see a full guide!",
                "😅 I'm not sure how to answer that one. Try rephrasing, or type **help** "
                "to see everything I can assist with!",
            )

    return {
        "response": response_text,
        "events": [_fmt_event(e) for e in matched_events],
        "event_names": [e["name"] for e in matched_events],  # stored in history for context
    }

# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    intent: str
    confidence: int
    response: str
    events: list[dict]

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Main chatbot endpoint. Maintains per-session conversation history."""
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = req.session_id or str(uuid.uuid4())
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    history = chat_sessions[session_id]
    ts = datetime.now().isoformat()
    history.append({"role": "user", "text": message, "timestamp": ts})

    intents_ranked = detect_intents(message)
    primary_intent, primary_score = intents_ranked[0]
    logger.info(
        f"[{session_id}] '{message}' → "
        + ", ".join(f"{i}({s})" for i, s in intents_ranked)
    )

    result = build_response(intents_ranked, message, history)

    # Persist bot turn (includes event_names for context-awareness)
    history.append({
        "role": "bot",
        "text": result["response"],
        "event_names": result["event_names"],
        "timestamp": datetime.now().isoformat(),
    })

    return ChatResponse(
        session_id=session_id,
        intent=primary_intent,
        confidence=primary_score,
        response=result["response"],
        events=result["events"],
    )


@app.get("/history/{session_id}")
def get_history(session_id: str):
    """Return full conversation history for a session."""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {
        "session_id": session_id,
        "message_count": len(chat_sessions[session_id]),
        "history": [
            {k: v for k, v in turn.items() if k != "event_names"}
            for turn in chat_sessions[session_id]
        ],
    }


@app.delete("/history/{session_id}")
def clear_history(session_id: str):
    """Clear conversation history for a session."""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    del chat_sessions[session_id]
    return {"detail": f"Session '{session_id}' cleared."}


@app.get("/events")
def list_events(
    category: Optional[str] = None,
    registration: Optional[str] = None,
    volunteer: Optional[str] = None,
):
    """Raw event list with optional query-param filters."""
    results = list(EVENTS)
    if category:
        results = [e for e in results if e.get("type", "").lower() == category.lower()]
    if registration:
        results = [e for e in results if e.get("registration", "").lower() == registration.lower()]
    if volunteer:
        results = [e for e in results if e.get("volunteer", "").lower() == volunteer.lower()]
    return {"count": len(results), "events": [_fmt_event(e) for e in results]}


@app.get("/health")
def health():
    """Liveness probe."""
    return {
        "status": "ok",
        "version": "2.0.0",
        "events_loaded": len(EVENTS),
        "active_sessions": len(chat_sessions),
    }


@app.get("/")
def serve_frontend():
    return FileResponse("index.html")