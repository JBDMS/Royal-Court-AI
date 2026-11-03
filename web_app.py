import base64
import json
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from string import Template

import streamlit as st

from app.chatbot import ask_ai


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Personal AI Assistant",
    page_icon=":material/workspace_premium:",
    layout="centered",
)

PROGRESS_FILE = Path(__file__).with_name("german_progress.json")


# ---------------------------------------------------------------------------
# Configuration data
# ---------------------------------------------------------------------------
PERSONAS = {
    "Royal Advisor": {
        "avatar": ":material/workspace_premium:",
        "prompt": "You are a wise, loyal royal advisor: dignified, clear and practical.",
    },
    "Court Scholar": {
        "avatar": ":material/school:",
        "prompt": "You are a learned court scholar: precise, and you explain with structured reasoning.",
    },
    "Royal Scribe": {
        "avatar": ":material/edit_note:",
        "prompt": "You are a skilled royal scribe: excellent at writing, editing and drafting text.",
    },
    "Court Wizard": {
        "avatar": ":material/auto_awesome:",
        "prompt": "You are a friendly court wizard: imaginative and encouraging, but always accurate.",
    },
    "War Strategist": {
        "avatar": ":material/military_tech:",
        "prompt": "You are a calm strategist: break problems into clear plans and priorities.",
    },
}

GERMAN_AVATAR = ":material/translate:"

STYLE_PRESETS = {
    "Balanced": "Give clear, practical answers. Explain technical concepts step by step.",
    "Mentor (motivating)": (
        "Respond like an encouraging mentor. Be clear and practical, "
        "and close with one short motivating line."
    ),
    "Concise": "Keep answers short and direct. Use bullet points only when they help.",
    "Detailed": "Give thorough, well-structured answers with reasoning and examples.",
    "Beginner-friendly": "Explain as if to a beginner. Avoid jargon and use simple analogies.",
    "Formal": "Use a professional, formal tone suitable for academic or business writing.",
}

LENGTHS = {
    "Short": "Keep the answer under about 120 words.",
    "Medium": "Aim for a moderately sized answer of about 200 to 300 words.",
    "Detailed": "Give a comprehensive answer when the topic needs it.",
}

LANGUAGES = ["English", "Hindi", "Hinglish", "German"]
TITLES = ["Your Majesty", "My Lord", "My Lady", "Your Highness", "Scholar", "None"]
PREFIX_TITLES = {"My Lord", "My Lady", "Scholar"}  # used before the name

USER_AVATARS = {
    "Person": ":material/person:",
    "Shield": ":material/shield:",
    "Crown": ":material/workspace_premium:",
    "Star": ":material/star:",
    "Diamond": ":material/diamond:",
}

TEXT_SIZES = {"Small": 15, "Medium": 17, "Large": 19}

THEMES = {
    "Obsidian and Gold": dict(
        bg1="#0b0b0e", bg2="#14141a", bg3="#1c1913",
        accent="#c9a24a", soft="#e6cf91", rgb="201,162,74",
        ivory="#efe8d8", mist="#a8a293",
        panel="rgba(12,12,16,0.96)", glass="rgba(22,22,28,0.85)",
        field="rgba(255,255,255,0.05)", solid="#101015",
    ),
    "Burgundy and Brass": dict(
        bg1="#120709", bg2="#1e0b10", bg3="#2a1016",
        accent="#b8893b", soft="#dcbf86", rgb="184,137,59",
        ivory="#f0e6dc", mist="#b5a09a",
        panel="rgba(20,8,11,0.96)", glass="rgba(34,13,19,0.85)",
        field="rgba(255,255,255,0.05)", solid="#190a0e",
    ),
    "Forest and Champagne": dict(
        bg1="#07100c", bg2="#0d1d15", bg3="#12281d",
        accent="#cdb67a", soft="#e8dab0", rgb="205,182,122",
        ivory="#ece9dc", mist="#9fb3a6",
        panel="rgba(8,18,13,0.96)", glass="rgba(14,30,22,0.85)",
        field="rgba(255,255,255,0.05)", solid="#0c1a13",
    ),
    "Midnight and Silver": dict(
        bg1="#070b14", bg2="#0e1628", bg3="#141f38",
        accent="#b9c3d6", soft="#dde3ee", rgb="185,195,214",
        ivory="#e9edf5", mist="#9aa5ba",
        panel="rgba(8,12,22,0.96)", glass="rgba(15,24,42,0.85)",
        field="rgba(255,255,255,0.05)", solid="#0c1322",
    ),
}

BACKDROPS = ["Dark Gradient", "Pinstripe", "Solid Dark", "Custom image"]

STARTER_PROMPTS = [
    ("Explain a concept", "Explain how REST APIs work, step by step."),
    ("Draft an email", "Help me write a polite email asking my professor for an extension."),
    ("Study plan", "Create a 7-day study plan for learning Python basics."),
    ("Project ideas", "Suggest 5 beginner-friendly project ideas using Streamlit."),
]

FOLLOW_UPS = {
    "Summarize": "Summarize your last answer in 3 short bullet points.",
    "Simplify": "Explain your last answer again in simpler words.",
    "Example": "Give me a practical example for your last answer.",
    "Continue": "Please continue and add anything important that is missing.",
}

DAILY_THOUGHTS = [
    "Small steps, taken every day, build kingdoms.",
    "Focus on the next right move, not the whole mountain.",
    "Discipline is the crown that every skill is built upon.",
    "Every expert once sat where you are sitting now.",
    "Begin before you feel ready; clarity follows action.",
    "Steady effort outlasts sudden inspiration.",
    "One finished task is worth a hundred perfect plans.",
]

GERMAN_LEVELS = ["A1", "A2", "B1", "B2"]

GERMAN_TOPICS = [
    "Greetings and introductions",
    "Ordering at a cafe",
    "Asking for directions",
    "Shopping for groceries",
    "At the university",
    "Talking about your family",
    "Your daily routine",
    "Making an appointment",
    "Using public transport",
    "Booking a hotel room",
    "At the doctor",
    "Talking about hobbies",
    "Weather and plans for the weekend",
    "Phone call to a friend",
]


# ---------------------------------------------------------------------------
# German progress (saved to a small JSON file)
# ---------------------------------------------------------------------------
def load_progress() -> list[str]:
    try:
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return sorted(set(str(d) for d in data.get("completed", [])))
    except (OSError, ValueError, AttributeError):
        return []


def save_progress(done: list[str]) -> None:
    try:
        PROGRESS_FILE.write_text(
            json.dumps({"completed": sorted(set(done))}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass  # progress still works for this session


def current_streak(done: list[str]) -> int:
    days = set()
    for d in done:
        try:
            days.add(date.fromisoformat(d))
        except ValueError:
            continue
    today = date.today()
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def german_tutor_prompt(level: str, pronunciation: bool, translations: bool) -> str:
    """Instructions that turn the assistant into a step-by-step German tutor."""
    pron = (
        " Add a simple English-style pronunciation hint in brackets after new words "
        "and key dialogue lines (for example: Guten Morgen [GOO-ten MOR-gen])."
        if pronunciation
        else ""
    )
    trans = (
        " Under each dialogue line, add the English translation in italics."
        if translations
        else (
            " Do not add translations under the dialogue lines so the learner can "
            "try to understand them; the vocabulary table must still give English meanings."
        )
    )
    return (
        f"You are a warm, patient German tutor for an English-speaking learner at "
        f"CEFR level {level}. Keep German sentences short and suitable for that level. "
        "Teach step by step, keep answers compact, and encourage the learner. "
        "These tutor rules take priority over any other style or length setting.\n\n"
        "When asked for a daily lesson, use exactly these markdown headings:\n"
        "### Step 1: Short dialogue\n"
        "A dialogue of 6 to 8 short lines between two named speakers, formatted as "
        "**Name:** German sentence." + trans + pron + "\n"
        "### Step 2: Vocabulary notes\n"
        "A markdown table with columns German, English, Note. Nouns must include the "
        "article (der/die/das) and the plural form.\n"
        "### Step 3: Grammar note\n"
        "One small grammar rule from the dialogue, explained simply with 2 examples.\n"
        "### Step 4: Usage tip\n"
        "One polite phrase or cultural note.\n"
        "### Step 5: Your turn\n"
        "Three short exercises (fill in the blank or translate). Do not show the answers. "
        "Ask the learner to reply with their answers.\n\n"
        "When the learner writes German, reply in this order: **Your sentence "
        "(corrected)**, **Notes** (short and clear, explaining each mistake), then "
        "continue the conversation with one short German question" 
        + (" followed by its English translation." if translations else ".")
        + " If the German is already correct, say so.\n"
        "When quizzing, ask one question at a time and wait for the learner's answer. "
        "When checking exercise answers, mark each one and explain briefly."
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def salutation(title: str, name: str) -> str:
    """How the assistant greets the user."""
    name = name.strip()
    if title == "None":
        return name or "friend"
    if not name:
        return title
    return f"{title} {name}" if title in PREFIX_TITLES else f"{name}, {title}"


def time_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def thought_of_the_day() -> str:
    return DAILY_THOUGHTS[date.today().toordinal() % len(DAILY_THOUGHTS)]


def build_preferences(persona, style, length, language, title, name, notes, german) -> str:
    """Combine every personalization choice into one instruction string."""
    if german["on"]:
        parts = [german_tutor_prompt(german["level"], german["pron"], german["trans"])]
    else:
        parts = [PERSONAS[persona]["prompt"], STYLE_PRESETS[style], LENGTHS[length]]
        if language == "German":
            parts.append(
                "Reply in simple German and add an English translation and short notes "
                "after each part."
            )
        elif language != "English":
            parts.append(f"Reply in {language}.")
    if title != "None":
        parts.append(
            f"Address the user respectfully as '{title}' now and then, "
            "but not in every sentence."
        )
    if name.strip():
        parts.append(f"The user's name is {name.strip()}.")
    if notes.strip():
        parts.append(f"Additional instructions: {notes.strip()}")
    return " ".join(parts)


def typewriter(text: str, delay: float = 0.003):
    """Yield text piece by piece for a gentle typing effect."""
    for piece in re.split(r"(\s+)", text):
        yield piece
        time.sleep(delay)


def transcript_markdown(messages: list[dict], assistant_name: str) -> str:
    stamp = datetime.now().strftime("%d %B %Y, %H:%M")
    lines = ["# Personal AI Assistant: Conversation", f"*Exported {stamp}*", ""]
    for msg in messages:
        speaker = "You" if msg["role"] == "user" else assistant_name
        lines += [f"**{speaker}:**", "", msg["content"], "", "---", ""]
    return "\n".join(lines)


def scrolls_markdown(scrolls: list[dict]) -> str:
    lines = ["# Royal Scrolls", ""]
    for i, scroll in enumerate(scrolls, 1):
        lines += [f"## {i}. {scroll['title']}", "", scroll["content"], "", "---", ""]
    return "\n".join(lines)


def queue_prompt(prompt: str) -> None:
    st.session_state.pending_prompt = prompt


def start_german(prompt: str) -> None:
    """Switch German tutor mode on and queue a lesson prompt."""
    st.session_state["german_mode"] = True
    st.session_state.pending_prompt = prompt


def mark_lesson_done() -> None:
    today = date.today().isoformat()
    if today not in st.session_state.german_done:
        st.session_state.german_done.append(today)
        save_progress(st.session_state.german_done)


def regenerate_last() -> None:
    msgs = st.session_state.messages
    if len(msgs) >= 2 and msgs[-1]["role"] == "assistant":
        msgs.pop()
        st.session_state.pending_prompt = msgs.pop()["content"]


def clear_conversation() -> None:
    st.session_state.messages = []
    st.session_state.pending_prompt = None


def save_scroll() -> None:
    """Save the latest answer to the Royal Scrolls."""
    msgs = st.session_state.messages
    if not msgs or msgs[-1]["role"] != "assistant":
        return
    answer = msgs[-1]["content"]
    question = msgs[-2]["content"] if len(msgs) >= 2 else "Saved answer"
    if any(s["content"] == answer for s in st.session_state.scrolls):
        return
    title = question.strip().replace("\n", " ")
    title = title[:60] + ("..." if len(title) > 60 else "")
    st.session_state.scrolls.append({"title": title, "content": answer})


def remove_scroll(index: int) -> None:
    if 0 <= index < len(st.session_state.scrolls):
        st.session_state.scrolls.pop(index)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
st.session_state.setdefault("messages", [])
st.session_state.setdefault("pending_prompt", None)
st.session_state.setdefault("scrolls", [])
st.session_state.setdefault("german_mode", False)
if "german_done" not in st.session_state:
    st.session_state.german_done = load_progress()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Royal Court")

    tab_court, tab_theme, tab_german, tab_scrolls = st.tabs(
        ["Court", "Theme", "German", "Scrolls"]
    )

    # ----- Court: who you are and how the assistant behaves -----
    with tab_court:
        user_name = st.text_input("Your name", key="user_name", placeholder="Optional")
        title = st.selectbox("Address me as", TITLES, index=0, key="title")
        emblem = st.selectbox("Your emblem", list(USER_AVATARS.keys()), key="emblem")

        persona = st.selectbox("Assistant persona", list(PERSONAS.keys()), key="persona")
        style = st.selectbox("Response style", list(STYLE_PRESETS.keys()), key="style")
        length = st.select_slider(
            "Answer length", options=list(LENGTHS.keys()), value="Medium", key="length"
        )
        language = st.selectbox("Reply language", LANGUAGES, key="language")
        notes = st.text_area(
            "Additional instructions (optional)",
            key="notes",
            placeholder="e.g. Use examples from computer science.",
            height=90,
        )

    # ----- Theme: look and feel -----
    with tab_theme:
        theme_name = st.selectbox("Colour palette", list(THEMES.keys()), key="theme")
        backdrop = st.selectbox("Backdrop", BACKDROPS, key="backdrop")

        bg_file = None
        if backdrop == "Custom image":
            bg_file = st.file_uploader(
                "Upload your backdrop",
                type=["png", "jpg", "jpeg", "webp"],
                key="bg_file",
                help="A dark overlay is added automatically so text stays readable.",
            )
            if bg_file is None:
                st.caption("Upload an image to use it as your backdrop.")

        text_size = st.select_slider(
            "Text size", options=list(TEXT_SIZES.keys()), value="Medium", key="text_size"
        )
        wide_layout = st.toggle("Wide layout", value=False, key="wide")
        ambient = st.toggle("Ambient light animation", value=True, key="ambient")
        typing_effect = st.toggle("Typing effect", value=True, key="typing_effect")

    # ----- German: daily lessons -----
    with tab_german:
        german_mode = st.toggle(
            "German tutor mode",
            key="german_mode",
            help="Replies become step-by-step German lessons with notes.",
        )
        german_level = st.select_slider(
            "Your level (CEFR)", options=GERMAN_LEVELS, value="A1", key="german_level"
        )

        done = st.session_state.german_done
        today_done = date.today().isoformat() in done
        lesson_no = max(1, len(done) + (0 if today_done else 1))
        suggested = GERMAN_TOPICS[(lesson_no - 1) % len(GERMAN_TOPICS)]

        topic_choice = st.selectbox(
            "Topic", ["Suggested for today"] + GERMAN_TOPICS, key="german_topic"
        )
        topic = suggested if topic_choice == "Suggested for today" else topic_choice
        st.caption(f"Today's suggestion: {suggested}")

        show_pron = st.toggle("Pronunciation hints", value=True, key="german_pron")
        show_trans = st.toggle("English translations", value=True, key="german_trans")

        m1, m2 = st.columns(2)
        m1.metric("Day streak", current_streak(done))
        m2.metric("Lessons done", len(done))

        lesson_prompt = (
            f"Start my German lesson for Day {lesson_no}: {topic} (level {german_level})."
        )
        practice_prompt = (
            f"Let's practise a short German conversation about: {topic}. "
            "You begin with one short line."
        )

        st.button(
            "Start today's lesson",
            key="g_lesson",
            use_container_width=True,
            on_click=start_german,
            args=(lesson_prompt,),
        )
        st.button(
            "Practise a conversation",
            key="g_practice",
            use_container_width=True,
            on_click=start_german,
            args=(practice_prompt,),
        )
        st.button(
            "Quiz me on today's lesson",
            key="g_quiz",
            use_container_width=True,
            on_click=start_german,
            args=("Quiz me on today's German lesson with 5 short questions, one at a time.",),
        )
        st.button(
            "Explain the grammar",
            key="g_grammar",
            use_container_width=True,
            on_click=start_german,
            args=("Explain the key grammar point from today's lesson with 3 more examples.",),
        )
        st.button(
            "Vocabulary flashcards",
            key="g_cards",
            use_container_width=True,
            on_click=start_german,
            args=("Give me 8 flashcard-style vocabulary pairs (German - English) from today's lesson.",),
        )
        st.button(
            "Lesson completed today" if today_done else "Mark today's lesson complete",
            key="g_done",
            use_container_width=True,
            disabled=today_done,
            on_click=mark_lesson_done,
        )
        st.caption("Tip: use Save under a lesson to keep your notes in Scrolls.")

    # ----- Scrolls: saved answers -----
    with tab_scrolls:
        scrolls = st.session_state.scrolls
        if not scrolls:
            st.caption("No scrolls yet. Use Save under an answer to keep it here.")
        else:
            for i, scroll in enumerate(scrolls):
                with st.expander(scroll["title"]):
                    st.markdown(scroll["content"])
                    st.button(
                        "Remove",
                        key=f"remove_scroll_{i}",
                        on_click=remove_scroll,
                        args=(i,),
                        use_container_width=True,
                    )
            st.download_button(
                "Download all scrolls",
                data=scrolls_markdown(scrolls),
                file_name="royal_scrolls.md",
                mime="text/markdown",
                use_container_width=True,
            )

    # ----- Conversation tools -----
    st.divider()

    has_answer = (
        len(st.session_state.messages) >= 2
        and st.session_state.messages[-1]["role"] == "assistant"
    )

    st.button(
        "Regenerate last answer",
        use_container_width=True,
        disabled=not has_answer,
        on_click=regenerate_last,
    )
    st.download_button(
        "Download conversation",
        data=transcript_markdown(
            st.session_state.messages,
            "German Tutor" if german_mode else persona,
        ),
        file_name="conversation.md",
        mime="text/markdown",
        use_container_width=True,
        disabled=not st.session_state.messages,
    )
    st.button("Clear conversation", use_container_width=True, on_click=clear_conversation)

    count = len(st.session_state.messages)
    words = sum(len(m["content"].split()) for m in st.session_state.messages)
    n_scrolls = len(st.session_state.scrolls)
    st.markdown(
        f'<p class="meta">{count} message{"s" if count != 1 else ""} &nbsp;|&nbsp; '
        f'{words} words &nbsp;|&nbsp; {n_scrolls} scroll{"s" if n_scrolls != 1 else ""}</p>',
        unsafe_allow_html=True,
    )

preferences = build_preferences(
    persona,
    style,
    length,
    language,
    title,
    user_name,
    notes,
    german=dict(
        on=german_mode, level=german_level, pron=show_pron, trans=show_trans
    ),
)
assistant_avatar = GERMAN_AVATAR if german_mode else PERSONAS[persona]["avatar"]
assistant_name = "German Tutor" if german_mode else persona
user_avatar = USER_AVATARS[emblem]


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
ROYAL_CSS = Template(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700&family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap');

:root {
    --gold: $accent;
    --gold-soft: $soft;
    --ivory: $ivory;
    --mist: $mist;
    --glass: $glass;
    --solid: $solid;
    --edge: rgba($rgb, 0.40);
}

html, body, .stApp { font-family: 'Lora', Georgia, serif; }

/* ---------- Background ---------- */
.stApp {
    color: var(--ivory);
    background:
        radial-gradient(ellipse at 15% 0%, rgba($rgb, 0.10), transparent 55%),
        radial-gradient(ellipse at 100% 100%, rgba($rgb, 0.07), transparent 50%),
        linear-gradient(160deg, $bg1, $bg2 55%, $bg3);
}
.stApp::before {
    content: ""; position: fixed; inset: -25%;
    background: radial-gradient(circle at 35% 35%, rgba($rgb, 0.11), transparent 38%);
    animation: drift 45s ease-in-out infinite alternate;
    pointer-events: none; z-index: 0;
}
@keyframes drift {
    from { transform: translate(-7%, -5%); }
    to   { transform: translate(9%, 7%); }
}
.stApp::after {
    content: ""; position: fixed; inset: 0;
    background: radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.50));
    pointer-events: none; z-index: 0;
}

[data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {
    position: relative; z-index: 1; background: transparent !important;
}
[data-testid="stHeader"] * { color: var(--ivory) !important; }
[data-testid="stAppDeployButton"] { display: none; }
.block-container { max-width: $max_width; padding-top: 3rem; }

/* ---------- Text ---------- */
.stApp p, .stApp li, .stApp label, .stApp span, [data-testid="stMarkdownContainer"] {
    color: var(--ivory);
}
h1, h2, h3, h4 {
    font-family: 'Cinzel', Georgia, serif;
    color: var(--gold-soft) !important;
    letter-spacing: 0.8px; font-weight: 700;
}
[data-testid="stWidgetLabel"] p {
    color: var(--gold-soft) !important; font-weight: 600; letter-spacing: 0.3px;
}
.meta, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
    color: var(--mist) !important; font-size: 13px;
}

/* ---------- Header ---------- */
.eyebrow {
    font-family: 'Cinzel', Georgia, serif; font-size: 0.74rem; font-weight: 600;
    letter-spacing: 0.38em; text-transform: uppercase;
    color: var(--gold); margin: 0 0 6px 2px;
}
.royal-title {
    font-family: 'Cinzel', Georgia, serif; font-weight: 700;
    font-size: 2.9rem; letter-spacing: 1.5px; line-height: 1.1; margin: 0;
    background: linear-gradient(90deg, $soft, $accent 50%, $soft);
    background-size: 200% auto;
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: goldShine 9s linear infinite;
}
@keyframes goldShine { to { background-position: 200% center; } }
.subtitle { color: var(--mist) !important; font-size: 1.05rem; font-style: italic; margin: 6px 0 0 2px; }

.rule { display: flex; align-items: center; gap: 14px; margin: 18px 0 28px 0; }
.rule::before, .rule::after { content: ""; flex: 1; height: 1px;
    background: linear-gradient(90deg, transparent, var(--gold)); }
.rule::after { background: linear-gradient(90deg, var(--gold), transparent); }
.rule i { width: 7px; height: 7px; background: var(--gold); transform: rotate(45deg); display: block; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: $panel; border-right: 1px solid var(--edge);
}
[data-testid="stSidebar"] hr { border-color: var(--edge); }

[data-baseweb="tab-list"] { gap: 2px; }
[data-baseweb="tab"] {
    color: var(--mist) !important; font-weight: 600; letter-spacing: 0.3px; font-size: 0.88rem;
}
[data-baseweb="tab"][aria-selected="true"] { color: var(--gold-soft) !important; }
[data-baseweb="tab-highlight"] { background-color: var(--gold) !important; }
[data-baseweb="tab-border"] { background-color: var(--edge) !important; }

/* Metrics */
[data-testid="stMetric"] {
    background: $field; border: 1px solid var(--edge); border-radius: 8px; padding: 10px 12px;
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { color: var(--mist) !important; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
    color: var(--gold-soft) !important; font-family: 'Cinzel', Georgia, serif;
}

/* ---------- Form fields ---------- */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"],
[data-baseweb="select"] > div {
    background-color: $field !important;
    border: 1px solid var(--edge) !important;
    border-radius: 6px !important;
}
input, textarea,
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    color: var(--ivory) !important;
    -webkit-text-fill-color: var(--ivory) !important;
    caret-color: var(--gold) !important;
    background: transparent !important;
}
input::placeholder, textarea::placeholder {
    color: var(--mist) !important;
    -webkit-text-fill-color: var(--mist) !important;
    opacity: 0.75 !important;
}
[data-baseweb="select"] div, [data-baseweb="select"] span { color: var(--ivory) !important; }
[data-baseweb="select"] svg { fill: var(--gold) !important; }

div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"] {
    background-color: var(--solid) !important;
    border: 1px solid var(--edge) !important;
}
div[data-baseweb="popover"] li, li[role="option"],
li[role="option"] div, li[role="option"] span {
    color: var(--ivory) !important; background-color: transparent !important;
}
li[role="option"]:hover, li[role="option"][aria-selected="true"] {
    background-color: rgba($rgb, 0.18) !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: $field !important; border: 1px dashed var(--edge) !important; border-radius: 6px;
}
[data-testid="stFileUploaderDropzone"] * { color: var(--mist) !important; }

[data-testid="stExpander"] details {
    background: $field; border: 1px solid var(--edge) !important; border-radius: 8px;
}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color: var(--ivory) !important; }

/* ---------- Chat messages ---------- */
[data-testid="stChatMessage"] {
    background: var(--glass); backdrop-filter: blur(6px);
    border: 1px solid var(--edge); border-left: 3px solid var(--gold);
    border-radius: 10px; padding: 18px 20px;
    box-shadow: 0 8px 28px rgba(0,0,0,0.40);
    animation: riseIn 0.45s ease both;
}
@keyframes riseIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

[data-testid^="stChatMessageAvatar"] {
    background: linear-gradient(135deg, $soft, $accent) !important;
}
[data-testid^="stChatMessageAvatar"] * { color: #14110a !important; fill: #14110a !important; }

[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li {
    font-size: ${font_px}px; line-height: 1.65; color: var(--ivory);
}
[data-testid="stChatMessage"] h3 { font-size: 1.15rem; margin-top: 1.1rem; }
[data-testid="stChatMessage"] strong { color: var(--gold-soft); }
[data-testid="stChatMessage"] table { border-collapse: collapse; width: 100%; font-size: 15px; }
[data-testid="stChatMessage"] th { background: rgba($rgb, 0.16); color: var(--gold-soft); text-align: left; }
[data-testid="stChatMessage"] th, [data-testid="stChatMessage"] td { border: 1px solid var(--edge); padding: 9px 11px; }
[data-testid="stChatMessage"] pre { border-radius: 8px; border: 1px solid var(--edge); }
[data-testid="stChatMessage"] a { color: var(--gold-soft); }

/* ---------- Chat input ---------- */
[data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] { background: transparent !important; }

[data-testid="stChatInput"] {
    background-color: var(--solid) !important;
    border: 1px solid var(--edge) !important; border-radius: 10px !important;
    box-shadow: 0 0 24px rgba($rgb, 0.10);
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--gold) !important; box-shadow: 0 0 28px rgba($rgb, 0.28);
}
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] [data-baseweb],
[data-testid="stChatInput"] textarea {
    background: transparent !important; background-color: transparent !important;
    color: var(--ivory) !important; -webkit-text-fill-color: var(--ivory) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: var(--mist) !important; -webkit-text-fill-color: var(--mist) !important; opacity: 0.8;
}
[data-testid="stChatInputSubmitButton"] {
    background-color: var(--gold) !important; border-radius: 6px !important;
}
[data-testid="stChatInputSubmitButton"] svg { fill: #14110a !important; color: #14110a !important; }

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button {
    background: $field; color: var(--ivory);
    border: 1px solid var(--edge); border-radius: 6px;
    font-weight: 600; letter-spacing: 0.3px; transition: all 0.2s ease;
}
.stButton > button p, .stDownloadButton > button p { color: var(--ivory) !important; }
.stButton > button:hover, .stDownloadButton > button:hover {
    border-color: var(--gold); background: rgba($rgb, 0.14);
    box-shadow: 0 0 16px rgba($rgb, 0.25);
}
.stButton > button:hover p, .stDownloadButton > button:hover p { color: var(--gold-soft) !important; }
.stButton > button:disabled, .stDownloadButton > button:disabled { opacity: 0.35; }

/* ---------- Welcome card ---------- */
.welcome {
    background: var(--glass); backdrop-filter: blur(6px);
    border: 1px solid var(--edge); border-top: 2px solid var(--gold);
    border-radius: 10px; padding: 24px 26px; margin-bottom: 18px;
    box-shadow: 0 8px 28px rgba(0,0,0,0.40);
    animation: riseIn 0.6s ease both;
}
.welcome h3 { margin: 0 0 10px 0; font-size: 1.5rem; }
.welcome p { margin: 0; color: var(--mist) !important; line-height: 1.6; }
.welcome .thought {
    margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--edge);
    color: var(--gold-soft) !important; font-style: italic;
}
.welcome .thought b {
    font-family: 'Cinzel', Georgia, serif; font-style: normal;
    letter-spacing: 0.2em; font-size: 0.72rem; text-transform: uppercase; color: var(--gold);
}

::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba($rgb, 0.35); border-radius: 6px; }
footer { visibility: hidden; }

@media (prefers-reduced-motion: reduce) {
    .stApp::before, .royal-title, [data-testid="stChatMessage"], .welcome {
        animation: none !important;
    }
}
</style>
"""
)

palette = THEMES[theme_name]
css = ROYAL_CSS.substitute(
    **palette,
    max_width="1100px" if wide_layout else "760px",
    font_px=TEXT_SIZES[text_size],
)
st.markdown(css, unsafe_allow_html=True)

# Backdrop variations
extra_css = ""
if backdrop == "Pinstripe":
    extra_css = f"""
    .stApp {{
        background:
            repeating-linear-gradient(90deg, rgba({palette['rgb']}, 0.05) 0 1px, transparent 1px 8px),
            linear-gradient(160deg, {palette['bg1']}, {palette['bg2']} 55%, {palette['bg3']});
    }}
    """
elif backdrop == "Solid Dark":
    extra_css = f"""
    .stApp {{ background: {palette['bg1']}; }}
    .stApp::before {{ display: none; }}
    """
elif backdrop == "Custom image" and bg_file is not None:
    encoded = base64.b64encode(bg_file.getvalue()).decode()
    extra_css = f"""
    .stApp {{
        background:
            linear-gradient(rgba(6,6,10,0.74), rgba(6,6,10,0.86)),
            url("data:{bg_file.type};base64,{encoded}") center / cover fixed;
    }}
    .stApp::before {{ display: none; }}
    """
if not ambient:
    extra_css += """
    .stApp::before, .royal-title { animation: none !important; }
    """
if extra_css:
    st.markdown(f"<style>{extra_css}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <p class="eyebrow">Your Private Court of Counsel</p>
    <h1 class="royal-title">Personal AI Assistant</h1>
    <p class="subtitle">A thoughtful assistant, built around your needs.</p>
    <div class="rule"><i></i></div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Work out the incoming prompt (typed, starter/quick action, or regenerate)
# ---------------------------------------------------------------------------
placeholder = (
    "Schreiben Sie hier auf Deutsch, oder fragen Sie auf Englisch..."
    if german_mode
    else "Write your question here..."
)
user_input = st.chat_input(placeholder)

if not user_input and st.session_state.pending_prompt:
    user_input = st.session_state.pending_prompt
    st.session_state.pending_prompt = None


# ---------------------------------------------------------------------------
# Welcome screen (empty conversation only)
# ---------------------------------------------------------------------------
if not st.session_state.messages and not user_input:
    if german_mode:
        intro = (
            f"Your German tutor is ready. Today is lesson {lesson_no}, "
            f"topic: {topic}, level {german_level}. Start the lesson below, or write "
            "a German sentence and I will correct it with notes."
        )
    else:
        intro = (
            f"Your {persona} is at your service. Ask a question, or begin with one of "
            "the suggestions below. The sidebar lets you change the persona, response "
            "style, the German tutor and the look of your court."
        )
    st.markdown(
        f"""
        <div class="welcome">
            <h3>{time_greeting()}, {salutation(title, user_name)}</h3>
            <p>{intro}</p>
            <p class="thought"><b>Thought of the day</b><br>{thought_of_the_day()}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.button(
        "Start today's German lesson",
        key="starter_german",
        use_container_width=True,
        on_click=start_german,
        args=(lesson_prompt,),
    )

    col1, col2 = st.columns(2)
    for i, (label, prompt_text) in enumerate(STARTER_PROMPTS):
        with (col1 if i % 2 == 0 else col2):
            st.button(
                label,
                key=f"starter_{i}",
                use_container_width=True,
                on_click=queue_prompt,
                args=(prompt_text,),
            )


# ---------------------------------------------------------------------------
# Show previous messages
# ---------------------------------------------------------------------------
for message in st.session_state.messages:
    avatar = assistant_avatar if message["role"] == "assistant" else user_avatar
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])


# ---------------------------------------------------------------------------
# Quick actions under the latest answer
# ---------------------------------------------------------------------------
if has_answer and not user_input:
    cols = st.columns(5)
    with cols[0]:
        already_saved = any(
            s["content"] == st.session_state.messages[-1]["content"]
            for s in st.session_state.scrolls
        )
        st.button(
            "Saved" if already_saved else "Save",
            key="act_save",
            use_container_width=True,
            disabled=already_saved,
            on_click=save_scroll,
        )
    for col, (label, prompt_text) in zip(cols[1:], FOLLOW_UPS.items()):
        with col:
            st.button(
                label,
                key=f"act_{label}",
                use_container_width=True,
                on_click=queue_prompt,
                args=(prompt_text,),
            )


# ---------------------------------------------------------------------------
# Handle a new question
# ---------------------------------------------------------------------------
if user_input:
    history = list(st.session_state.messages)  # everything before this question

    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user", avatar=user_avatar):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar=assistant_avatar):
        try:
            with st.spinner(
                "Preparing your lesson..." if german_mode else "Preparing your answer..."
            ):
                answer = ask_ai(
                    chat_history=history,
                    user_message=user_input,
                    preferences=preferences,
                )

            if st.session_state.get("typing_effect", True):
                st.write_stream(typewriter(answer))
            else:
                st.markdown(answer)

            st.session_state.messages.append(
                {"role": "assistant", "content": answer}
            )

            # Refresh so sidebar buttons, counters and quick actions update.
            st.rerun()

        except Exception as error:
            st.error(
                "I couldn't generate a response. "
                "Please check your API key, model access, "
                "and internet connection."
            )
            st.caption(f"Technical details: {error}")

            # Remove the unanswered question so history stays clean.
            st.session_state.messages.pop()