"""
Novel-Forge Tracker v2.0  —  Streamlit front-end + TinyDB persistence
Fully pandas-powered version (fixes st.data_editor() type-compat errors)
"""

import json
import datetime as dt
from pathlib import Path

import pandas as pd              # ← NEW
import streamlit as st
from tinydb import TinyDB

# ------------------------------------------------------------------
# 🔖 CONFIG
# ------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_FILE = DATA_DIR / "tracker_db.json"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)
MAX_SNAPSHOTS = 5

STATUS_OPTS = ["Not Started", "Draft", "Line-Edits", "✅ Done"]
PRIORITY_EMOJIS = {"🟥": "High", "🟧": "Medium-High", "🟨": "Medium", "🟩": "Low"}

st.set_page_config(
    page_title="Novel-Forge Tracker v2.0",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject CSS -------------------------------------------------------
st.markdown(
    (Path(__file__).parent / "assets" / "styles.css").read_text(),
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# 🗄️ DATABASE
# ------------------------------------------------------------------
db = TinyDB(DB_FILE)
chapters_table = db.table("chapters")
todos_table = db.table("todos")
passes_table = db.table("edit_passes")


def load_demo_data() -> None:
    """Populate DB with three-chapter demo set on first run."""
    if len(chapters_table) == 0:
        demo = json.loads(
            (Path(__file__).parent / "assets" / "test_data.json").read_text()
        )
        chapters_table.insert_multiple(demo)


load_demo_data()

# ------------------------------------------------------------------
# 🔄 SNAPSHOTS (autosave once per day)
# ------------------------------------------------------------------
def autosave() -> None:
    today = dt.date.today().isoformat()
    snap_file = SNAPSHOT_DIR / f"{today}.json"
    if not snap_file.exists():
        with open(snap_file, "w") as f:
            json.dump(db.all(), f, indent=2)
        snaps = sorted(SNAPSHOT_DIR.glob("*.json"))
        for old in snaps[:-MAX_SNAPSHOTS]:
            old.unlink()


autosave()

# ------------------------------------------------------------------
# 🧮 HELPERS
# ------------------------------------------------------------------
def refresh_session() -> None:
    """Load DB rows into session_state so edits persist live."""
    mapping = {
        "chapters": chapters_table,
        "todos": todos_table,
        "passes": passes_table,
    }
    for key, table in mapping.items():
        if key not in st.session_state:
            st.session_state[key] = table.all()


refresh_session()

# ------------------------------------------------------------------
# 🚀 SIDEBAR  –  Word-count dashboard
# ------------------------------------------------------------------
with st.sidebar:
    st.header("📊 Word-Count Dashboard")
    total_words = sum(ch.get("word_count", 0) for ch in st.session_state["chapters"])
    start_words = sum(
        ch.get("start_words", ch.get("word_count", 0)) for ch in st.session_state["chapters"]
    )
    delta = total_words - start_words
    target_words = st.number_input("Target total words", 0, 500_000, value=90_000)
    st.metric("Current words", f"{total_words:,}")
    st.metric("Δ since project start", f"{delta:+,}")
    st.progress(min(total_words / target_words, 1.0))
    st.divider()
    st.toggle("🌙 Dark mode")

# ------------------------------------------------------------------
# 🗂️ MAIN TABS
# ------------------------------------------------------------------
tabs = st.tabs(["📖 Chapters", "🪄 Editing Passes", "✅ To-Dos", "📥 Import Wizard"])

# ------------------------------------------------------------------
# 1️⃣ CHAPTERS TAB
# ------------------------------------------------------------------
# …[imports & config unchanged]…

# 1️⃣ CHAPTERS TAB
with tabs[0]:
    st.subheader("Chapter Progress")

    chapters_df = pd.DataFrame(st.session_state["chapters"])

    # 🔧 NEW: make sure date-ish columns are really datetime
    for col in ["deadline", "last_edited"]:
        if col in chapters_df.columns:
            chapters_df[col] = pd.to_datetime(chapters_df[col], errors="coerce")

    # 🚑 Streamlit grid can’t cope with pd.NaT → convert all NaT/NaN to None
    chapters_df = chapters_df.astype(object).where(~chapters_df.isna(), None)

    edited_chapters = st.data_editor(
        chapters_df,
        num_rows="dynamic",
        column_config={
            "status":   st.column_config.SelectboxColumn("Status",  options=STATUS_OPTS),
            "priority": st.column_config.SelectboxColumn("Priority", options=list(PRIORITY_EMOJIS)),
            "deadline": st.column_config.DateColumn("Deadline"),
        },
        use_container_width=True,
        key="chapters_editor",
    )

    if st.button("💾 Save chapters"):
        records = edited_chapters.to_dict("records")
        chapters_table.truncate()
        chapters_table.insert_multiple(records)
        st.session_state["chapters"] = records
        autosave()

        if any(r["status"] == "✅ Done" for r in records):
            st.balloons()
            st.success('Kaela sneers: “About bloody time you wrapped one up.”')


# ------------------------------------------------------------------
# 2️⃣ EDITING-PASSES TAB
# ------------------------------------------------------------------
with tabs[1]:
    st.subheader("Focus-Area Board")

    passes_df = pd.DataFrame(st.session_state["passes"])

    edited_passes = st.data_editor(
        passes_df,
        num_rows="dynamic",
        column_config={
            "focus": st.column_config.SelectboxColumn(
                "Focus",
                options=["Pacing", "World-building", "Prose Sparkle", "Character Arc", "Theme"],
            ),
            "status":  st.column_config.CheckboxColumn("Done?"),
            "chapter": st.column_config.SelectboxColumn(
                "Chapter #", options=[""] + [c["#"] for c in st.session_state["chapters"]]
            ),
        },
        use_container_width=True,
        key="passes_editor",
    )

    if st.button("💾 Save passes"):
        records = edited_passes.to_dict("records")
        passes_table.truncate()
        passes_table.insert_multiple(records)
        st.session_state["passes"] = records
        autosave()

# ------------------------------------------------------------------
# 3️⃣ TO-DO LIST TAB
# ------------------------------------------------------------------
with tabs[2]:
    st.subheader("Master To-Do")

    todos_df = pd.DataFrame(st.session_state["todos"])

    edited_todos = st.data_editor(
        todos_df,
        num_rows="dynamic",
        column_config={"done": st.column_config.CheckboxColumn("✓")},
        use_container_width=True,
        key="todos_editor",
    )

    if st.button("💾 Save todos"):
        records = edited_todos.to_dict("records")
        todos_table.truncate()
        todos_table.insert_multiple(records)
        st.session_state["todos"] = records
        autosave()

# ------------------------------------------------------------------
# 4️⃣ IMPORT WIZARD TAB  (stub)
# ------------------------------------------------------------------
with tabs[3]:
    st.subheader("Import Wizard")
    st.info("Upload a `.docx` or paste a Google Doc URL. Parser stubs live in `services/importers.py`.")
    st.file_uploader("Choose .docx", type=["docx"])
    st.text_input("…or Google Docs URL")
    st.warning("Importer not wired yet—go implement it!")

st.caption("© 2025 Novel-Forge Tracker v2.0  |  Built with Streamlit 💜")
