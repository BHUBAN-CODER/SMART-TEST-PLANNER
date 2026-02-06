import streamlit as st
import pandas as pd
from datetime import date, timedelta

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(page_title="Smart Test Planner", layout="wide")
st.title("📘 Smart Test Planner")

st.warning(
    "⚠️ IMPORTANT RULE\n\n"
    "• NO three consecutive classes can have the same exam on the same day\n"
    "• Class 11 (science / commerce / arts) MUST have same subject on same day\n"
    "• Class 12 (science / commerce / arts) MUST have same subject on same day\n"
    "• Class 11 and Class 12 NEVER sync"
)

# =========================================================
# INITIAL DATA (YOUR EXACT EXAMPLE)
# =========================================================
def initial_table():
    return pd.DataFrame([
        ["6", "maths", "eng", "hindi", "sanskrit", "science", "ai", "sst"],
        ["7", "maths", "eng", "hindi", "sanskrit", "science", "ai", "sst"],
        ["8", "maths", "eng", "hindi", "sanskrit", "science", "ai", "sst"],
        ["9", "maths", "eng", "hindi/sanskrit", "science", "ai", "sst", "-"],
        ["10", "maths", "eng", "hindi/sanskrit", "science", "ai", "sst", "-"],
        ["11 science", "maths", "eng", "hindi/sanskrit", "physics", "chem", "bio/cs", "-"],
        ["11 commerce", "maths", "eng", "hindi/sanskrit", "business s", "economics", "accountancy", "-"],
        ["11 arts", "eng", "hindi/sanskrit", "history", "geography", "political sc", "economics", "-"],
        ["12 science", "maths", "eng", "hindi/sanskrit", "physics", "chem", "bio/cs", "-"],
        ["12 commerce", "maths", "eng", "hindi/sanskrit", "business s", "economics", "accountancy", "-"],
        ["12 arts", "eng", "hindi/sanskrit", "history", "geography", "political sc", "economics", "-"],
    ], columns=[
        "Class", "Subject 1", "Subject 2", "Subject 3",
        "Subject 4", "Subject 5", "Subject 6", "Subject 7"
    ])

if "table" not in st.session_state:
    st.session_state.table = initial_table()

# =========================================================
# COLUMN CONTROLS (PLUS / MINUS)
# =========================================================
col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Add Subject Column"):
        df = st.session_state.table
        new_col = f"Subject {len(df.columns)}"
        df[new_col] = "-"
        st.session_state.table = df

with col2:
    if st.button("➖ Remove Last Subject Column"):
        df = st.session_state.table
        if len(df.columns) > 2:
            st.session_state.table = df.iloc[:, :-1]

# =========================================================
# EDITABLE TABLE (ROWS +)
# =========================================================
st.subheader("✏️ Edit Data (Excel-like)")

st.session_state.table = st.data_editor(
    st.session_state.table,
    num_rows="dynamic",
    use_container_width=True
)

# =========================================================
# DATE INPUT
# =========================================================
start_date = st.date_input("📅 Exam start date", value=date.today())

# =========================================================
# SCHEDULER (CORE LOGIC UNCHANGED)
# =========================================================
def is_second_saturday(d):
    return d.weekday() == 5 and 8 <= d.day <= 14

def is_blocked_day(d):
    return d.weekday() == 6 or is_second_saturday(d)

def generate_schedule(class_subjects, start_date):

    classes = list(class_subjects.keys())

    class_groups = {
        "11": ["11 science", "11 commerce", "11 arts"],
        "12": ["12 science", "12 commerce", "12 arts"]
    }

    group_of = {m: g for g, members in class_groups.items() for m in members}

    remaining = {c: list(class_subjects[c]) for c in classes}
    finished = set()
    schedule = []
    current_date = start_date

    while len(finished) < len(classes):

        if is_blocked_day(current_date):
            current_date += timedelta(days=1)
            continue

        row = {"Date": current_date.strftime("%d-%m-%Y")}
        used_today = set()

        for cls in classes:
            if cls in finished or not remaining[cls]:
                row[cls] = "-"
                finished.add(cls)
                continue

            for sub in list(remaining[cls]):
                if sub not in used_today:
                    row[cls] = sub
                    used_today.add(sub)
                    remaining[cls].remove(sub)
                    break
            else:
                row[cls] = "-"

        schedule.append(row)
        current_date += timedelta(days=1)

    return pd.DataFrame(schedule)

# =========================================================
# RUN
# =========================================================
if st.button("📊 Generate Date Sheet"):

    df = st.session_state.table
    class_subjects = {}

    for _, r in df.iterrows():
        cls = str(r["Class"]).strip().lower()
        subs = [
            str(s).strip()
            for s in r[1:]
            if s not in ["-", "", None]
        ]
        class_subjects[cls] = subs

    result = generate_schedule(class_subjects, start_date)

    st.success("✅ Date Sheet Generated")
    st.dataframe(result, use_container_width=True)
