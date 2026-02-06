import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import BytesIO

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="Smart Test Planner", layout="wide")
st.title("📘 Smart Test Planner")

st.warning(
    "⚠️ IMPORTANT RULE\n\n"
    "The date sheet is generated STRICTLY based on the rule:\n"
    "NO three consecutive classes will have the same exam on the same day.\n\n"
    "If you want to change or relax this rule, please do it manually "
    "after downloading the final date sheet."
)

# =========================================================
# SESSION INIT
# =========================================================
DEFAULT_SUBJECTS = 7

if "subject_count" not in st.session_state:
    st.session_state.subject_count = DEFAULT_SUBJECTS

if "data" not in st.session_state:
    rows = [
        ["6", "maths", "eng", "hindi", "sanskrit", "science", "ai", "sst"],
        ["7", "maths", "eng", "hindi", "sanskrit", "science", "ai", "sst"],
        ["8", "maths", "eng", "hindi", "sanskrit", "science", "ai", "sst"],
        ["9", "maths", "eng", "hindi/sanskrit", "science", "ai", "sst", ""],
        ["10", "maths", "eng", "hindi/sanskrit", "science", "ai", "sst", ""],
        ["11 science", "maths", "eng", "hindi/sanskrit", "physics", "chem", "bio/cs", ""],
        ["11 commerce", "maths", "eng", "hindi/sanskrit", "business s", "economics", "accountancy", ""],
        ["12 science", "maths", "eng", "hindi/sanskrit", "physics", "chem", "bio/cs", ""],
        ["12 commerce", "maths", "eng", "hindi/sanskrit", "business s", "economics", "accountancy", ""],
        ["11 arts", "eng", "hindi/sanskrit", "history", "geography", "political sc", "economics", ""],
        ["12 arts", "eng", "hindi/sanskrit", "history", "geography", "political sc", "economics", ""],
    ]

    columns = ["Class"] + [f"Subject {i}" for i in range(1, DEFAULT_SUBJECTS + 1)]
    st.session_state.data = pd.DataFrame(rows, columns=columns)

# =========================================================
# COLUMN CONTROLS
# =========================================================
c1, c2 = st.columns(2)

with c1:
    if st.button("➕ Add Subject Column"):
        st.session_state.subject_count += 1
        st.session_state.data[f"Subject {st.session_state.subject_count}"] = ""

with c2:
    if st.button("➖ Remove Subject Column") and st.session_state.subject_count > 1:
        st.session_state.data.drop(
            columns=[f"Subject {st.session_state.subject_count}"],
            inplace=True
        )
        st.session_state.subject_count -= 1

# =========================================================
# ROW CONTROLS
# =========================================================
r1, r2 = st.columns(2)

with r1:
    if st.button("➕ Add Class Row"):
        empty = {c: "" for c in st.session_state.data.columns}
        st.session_state.data = pd.concat(
            [st.session_state.data, pd.DataFrame([empty])],
            ignore_index=True
        )

with r2:
    if st.button("➖ Remove Last Row") and len(st.session_state.data) > 1:
        st.session_state.data = st.session_state.data.iloc[:-1]

# =========================================================
# EDITOR (MOBILE SAFE)
# =========================================================
st.subheader("✏️ Edit Directly (Excel-like)")

st.session_state.data = st.data_editor(
    st.session_state.data,
    use_container_width=True,
    num_rows="dynamic"
)

# =========================================================
# DATE HELPERS
# =========================================================
def is_second_saturday(d):
    return d.weekday() == 5 and 8 <= d.day <= 14

def is_blocked_day(d, holidays):
    return d.weekday() == 6 or is_second_saturday(d) or d in holidays

# =========================================================
# SCHEDULER
# =========================================================
def generate_schedule(class_subjects, start_date, holidays):
    classes = list(class_subjects.keys())
    remaining = {c: list(class_subjects[c]) for c in classes}
    finished = set()
    schedule = []
    cur = start_date

    while len(finished) < len(classes):
        if is_blocked_day(cur, holidays):
            cur += timedelta(days=1)
            continue

        row = {"Date": cur.strftime("%d-%m-%Y"), "Day": cur.strftime("%A")}
        recent = []

        for cls in classes:
            if cls in finished or not remaining[cls]:
                row[cls] = "-"
                continue

            for s in list(remaining[cls]):
                if s not in recent:
                    row[cls] = s
                    remaining[cls].remove(s)
                    recent.append(s)
                    break
            else:
                row[cls] = "-"

            if not remaining[cls]:
                finished.add(cls)

            if len(recent) > 2:
                recent.pop(0)

        schedule.append(row)
        cur += timedelta(days=1)

    return pd.DataFrame(schedule)

# =========================================================
# GENERATE
# =========================================================
st.subheader("📅 Generate Date Sheet")

start_date = st.date_input("Exam start date", value=date.today())
holidays = st.multiselect(
    "Holidays",
    [start_date + timedelta(days=i) for i in range(180)],
    format_func=lambda d: d.strftime("%d-%m-%Y")
)

if st.button("📅 Generate Date Sheet"):
    class_subjects = {}
    for _, r in st.session_state.data.iterrows():
        cls = str(r["Class"]).strip().lower()
        subs = [str(v).strip() for k, v in r.items() if k != "Class" and v]
        if cls:
            class_subjects[cls] = subs

    result = generate_schedule(class_subjects, start_date, set(holidays))

    st.dataframe(result, use_container_width=True)

    out = BytesIO()
    result.to_excel(out, index=False, engine="openpyxl")
    out.seek(0)

    st.download_button(
        "⬇️ Download Final Date Sheet",
        out,
        "final_datesheet.xlsx"
    )
