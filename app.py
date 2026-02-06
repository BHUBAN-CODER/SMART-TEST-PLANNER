import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import BytesIO

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(page_title="Smart Test Planner", layout="wide")
st.title("📘 Smart Test Planner")

st.warning(
    "⚠️ IMPORTANT RULE\n\n"
    "NO three consecutive classes will have the same exam on the same day.\n\n"
    "You may manually edit the final Excel if needed."
)

# =========================================================
# PREFILLED EXAMPLE DATA (FROM YOUR SCREENSHOT)
# =========================================================
if "table" not in st.session_state:
    st.session_state.table = pd.DataFrame([
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
    ], columns=[
        "Class",
        "Subject 1", "Subject 2", "Subject 3",
        "Subject 4", "Subject 5", "Subject 6", "Subject 7"
    ])

st.subheader("✏️ Edit Class & Subjects (Excel-like)")
st.session_state.table = st.data_editor(
    st.session_state.table,
    num_rows="dynamic",
    use_container_width=True
)

# =========================================================
# DATE INPUTS
# =========================================================
start_date = st.date_input("📅 Exam start date", value=date.today())

holiday_dates = st.multiselect(
    "🚫 Holidays",
    options=[start_date + timedelta(days=i) for i in range(180)],
    format_func=lambda d: d.strftime("%d-%m-%Y")
)

# =========================================================
# DATE HELPERS
# =========================================================
def is_second_saturday(d):
    return d.weekday() == 5 and 8 <= d.day <= 14

def is_blocked_day(d, holidays):
    return d.weekday() == 6 or is_second_saturday(d) or d in holidays

# =========================================================
# CORE SCHEDULER (UNCHANGED LOGIC)
# =========================================================
def generate_schedule(class_subjects, start_date, holidays):
    classes = list(class_subjects.keys())
    remaining = {c: list(class_subjects[c]) for c in classes}
    finished = set()
    schedule = []
    current_date = start_date

    while len(finished) < len(classes):
        if is_blocked_day(current_date, holidays):
            current_date += timedelta(days=1)
            continue

        row = {"Date": current_date.strftime("%d-%m-%Y"),
               "Day": current_date.strftime("%A")}
        recent = []

        for cls in classes:
            if cls in finished or not remaining.get(cls):
                row[cls] = "-"
                continue

            for sub in remaining[cls]:
                if sub not in recent:
                    row[cls] = sub
                    recent.append(sub)
                    remaining[cls].remove(sub)
                    if not remaining[cls]:
                        finished.add(cls)
                    break
            else:
                row[cls] = "-"

        schedule.append(row)
        current_date += timedelta(days=1)

    return pd.DataFrame(schedule)

# =========================================================
# GENERATE
# =========================================================
if st.button("📅 Generate Date Sheet"):
    df = st.session_state.table

    class_subjects = {}
    for _, r in df.iterrows():
        cls = str(r["Class"]).strip().lower()
        subs = [str(s).strip() for s in r[1:] if str(s).strip()]
        class_subjects[cls] = subs

    result = generate_schedule(class_subjects, start_date, set(holiday_dates))
    st.success("✅ Date Sheet Generated")
    st.dataframe(result, use_container_width=True)

    out = BytesIO()
    result.to_excel(out, index=False, engine="openpyxl")
    out.seek(0)

    st.download_button(
        "⬇️ Download Final Date Sheet",
        data=out,
        file_name="final_datesheet.xlsx"
    )

