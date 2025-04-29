"""
Novel-Forge Tracker v2.0
YA‑fantasy editing dashboard — Streamlit front‑end + TinyDB persistence.
"""

import json
import datetime as dt
from pathlib import Path

import streamlit as st
from tinydb import TinyDB

# ---------- CONFIG --------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_FILE = DATA_DIR / "tracker_db.json"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)
MAX_SNAPSHOTS = 5

STATUS_OPTS = ["Not Started", "Draft", "Line-Edits", "✅ Done"]
PRIORITY_EMOJIS = {"🟥": "High", "🟧": "Medium‑High", "🟨": "Medium", "🟩": "Low"}

st.set_page_config(
    page_title="Novel-Forge Tracker v2.0",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject CSS
st.markdown(
    (Path(__file__).parent / "assets" / "styles.css").read_text(),
    unsafe_allow_html=True,
)

# ---------- DB -----------------------------------------------------------
db = TinyDB(DB_FILE)
chapters_table = db.table("chapters")
todos_table = db.table("todos")
passes_table = db.table("edit_passes")

def load_demo_data():
    if len(chapters_table) == 0:
        demo = json.loads((Path(__file__).parent / "assets" / "test_data.json").read_text())
        chapters_table.insert_multiple(demo)

load_demo_data()

# ---------- SNAPSHOTS ----------------------------------------------------
def autosave():
    today = dt.date.today().isoformat()
    snap_file = SNAPSHOT_DIR / f"{today}.json"
    if not snap_file.exists():
        with open(snap_file, "w") as f:
            json.dump(db.all(), f, indent=2)
        snaps = sorted(SNAPSHOT_DIR.glob("*.json"))
        for old in snaps[:-MAX_SNAPSHOTS]:
            old.unlink()

autosave()

# ---------- HELPERS ------------------------------------------------------
def calc_countdown(deadline):
    if not deadline:
        return ""
    try:
        days = (dt.datetime.fromisoformat(deadline) - dt.datetime.now()).days
        return f"{days} d" if days >= 0 else "⚠️ overdue"
    except Exception:
        return "—"

def refresh_session():
    for key, table in [("chapters", chapters_table), ("todos", todos_table), ("passes", passes_table)]:
        if key not in st.session_state:
            st.session_state[key] = table.all()

refresh_session()

# ---------- SIDEBAR ------------------------------------------------------
with st.sidebar:
    st.header("📊 Word‑Count Dashboard")
    total_words = sum(ch.get("word_count", 0) for ch in st.session_state["chapters"])
    start_words = sum(ch.get("start_words", ch.get("word_count", 0)) for ch in st.session_state["chapters"])
    delta = total_words - start_words
    target_words = st.number_input("Target total words", 0, 500_000, value=90_000)
    st.metric("Current words", f"{total_words:,}")
    st.metric("Δ since project start", f"{delta:+,}")
    st.progress(min(total_words / target_words, 1.0))
    st.divider()
    st.toggle("🌙 Dark mode")

# ---------- TABS ---------------------------------------------------------
tabs = st.tabs(["📖 Chapters", "🪄 Editing Passes", "✅ To‑Dos", "📥 Import Wizard"])

# 1. Chapters
with tabs[0]:
    st.subheader("Chapter Progress")
    changed = st.data_editor(
        st.session_state["chapters"],
        num_rows="dynamic",
        column_config={
            "status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTS),
            "priority": st.column_config.SelectboxColumn("Priority", options=list(PRIORITY_EMOJIS)),
            "deadline": st.column_config.DateColumn("Deadline"),
        },
        use_container_width=True,
        key="chapters_editor",
    )
    if st.button("💾 Save chapters"):
        chapters_table.truncate()
        chapters_table.insert_multiple(changed)
        st.session_state["chapters"] = changed
        autosave()
        if any(row["status"] == "✅ Done" for row in changed):
            st.balloons()
            st.success("Kaela sneers: “About bloody time you wrapped one up.”")

# 2. Editing Passes
with tabs[1]:
    st.subheader("Focus‑Area Board")
    passes_changed = st.data_editor(
        st.session_state["passes"],
        num_rows="dynamic",
        column_config={
            "focus": st.column_config.SelectboxColumn(
                "Focus", options=["Pacing", "World‑building", "Prose Sparkle", "Character Arc", "Theme"]
            ),
            "status": st.column_config.CheckboxColumn("Done?"),
            "chapter": st.column_config.SelectboxColumn(
                "Chapter #", options=[""] + [c["#"] for c in st.session_state["chapters"]]
            ),
        },
        use_container_width=True,
        key="passes_editor",
    )
    if st.button("💾 Save passes"):
        passes_table.truncate()
        passes_table.insert_multiple(passes_changed)
        st.session_state["passes"] = passes_changed
        autosave()

# 3. To‑Dos
with tabs[2]:
    st.subheader("Master To‑Do")
    todos_changed = st.data_editor(
        st.session_state["todos"],
        num_rows="dynamic",
        column_config={"done": st.column_config.CheckboxColumn("✓")},
        use_container_width=True,
        key="todos_editor",
    )
    if st.button("💾 Save todos"):
        todos_table.truncate()
        todos_table.insert_multiple(todos_changed)
        st.session_state["todos"] = todos_changed
        autosave()

# 4. Import Wizard
with tabs[3]:
    st.subheader("Import Wizard")
    st.info("Upload a `.docx` or paste a Google Doc URL. Parser stubs live in `services/importers.py`.")
    st.file_uploader("Choose .docx", type=["docx"])
    st.text_input("…or Google Docs URL")
    st.warning("Importer not wired yet—go implement it!")

st.caption("© 2025 Novel‑Forge Tracker v2.0  |  Built with Streamlit 💜")