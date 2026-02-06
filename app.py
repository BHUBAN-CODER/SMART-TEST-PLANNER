import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import BytesIO

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(page_title="Smart Test Planner", layout="wide")
st.title("📘 Smart Test Planner")

# =========================================================
# IMPORTANT RULE
# =========================================================
st.warning(
    "⚠️ IMPORTANT RULE\n\n"
    "The date sheet is generated STRICTLY based on the rule:\n"
    "NO three consecutive classes will have the same exam on the same day.\n\n"
    "If you want to change or relax this rule, please do it manually "
    "after downloading the final date sheet."
)

# =========================================================
# SESSION STATE INIT
# =========================================================
if "subject_count" not in st.session_state:
    st.session_state.subject_count = 7

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame({
        "Class": [
            "6", "7", "8", "9", "10",
            "11 science", "11 commerce",
            "12 science", "12 commerce",
            "11 arts", "12 arts"
        ],
        "Subject 1": ["maths"] * 10 + ["eng", "eng"],
        "Subject 2": ["eng"] * 10 + ["hindi/sanskrit", "hindi/sanskrit"],
        "Subject 3": ["hindi"] * 3 + ["hindi/sanskrit"] * 2 + ["hindi/sanskrit"] * 2 + ["hindi/sanskrit"] * 2,
        "Subject 4": ["sanskrit"] * 3 + ["science"] * 2 + ["physics", "business s", "physics", "business s", "history", "history"],
        "Subject 5": ["science"] * 3 + ["ai"] * 2 + ["chem", "economics", "chem", "economics", "geography", "geography"],
        "Subject 6": ["ai"] * 3 + ["sst"] * 2 + ["bio/cs", "accountancy", "bio/cs", "accountancy", "political sc", "political sc"],
        "Subject 7": ["sst"] * 3 + [""] * 8
    })

# =========================================================
# COLUMN CONTROLS
# =========================================================
col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Add Subject Column"):
        st.session_state.subject_count += 1
        st.session_state.data[f"Subject {st.session_state.subject_count}"] = ""

with col2:
    if st.button("➖ Remove Last Subject Column") and st.session_state.subject_count > 1:
        st.session_state.data.drop(
            columns=[f"Subject {st.session_state.subject_count}"],
            inplace=True
        )
        st.session_state.subject_count -= 1

# =========================================================
# ROW CONTROLS
# =========================================================
col3, col4 = st.columns(2)

with col3:
    if st.button("➕ Add Class Row"):
        empty_row = {col: "" for col in st.session_state.data.columns}
        st.session_state.data = pd.concat(
            [st.session_state.data, pd.DataFrame([empty_row])],
            ignore_index=True
        )

with col4:
    if st.button("➖ Remove Last Row") and len(st.session_state.data) > 1:
        st.session_state.data = st.session_state.data.iloc[:-1]

# =========================================================
# EDITABLE TABLE (AUTO-SAVED)
# =========================================================
st.subheader("✏️ Edit Class & Subjects (Directly on Website)")

edited_df = st.data_editor(
    st.session_state.data,
    knowing=True,
    use_container_width=True,
    num_rows="dynamic"
)

st.session_state.data = edited_df

# =========================================================
# DATE HELPERS
# =========================================================
def is_second_saturday(d):
    return d.weekday() == 5 and 8 <= d.day <= 14

def is_blocked_day(d, holidays):
    return d.weekday() == 6 or is_second_saturday(d) or d in holidays

# =========================================================
# CORE SCHEDULER
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

        row = {"Date": current_date.strftime("%d-%m-%Y"), "Day": current_date.strftime("%A")}
        recent = []
        something_done = False

        for cls in classes:
            if cls in finished or not remaining.get(cls):
                row[cls] = "-"
                continue

            for sub in list(remaining[cls]):
                if sub not in recent:
                    row[cls] = sub
                    remaining[cls].remove(sub)
                    recent.append(sub)
                    something_done = True
                    break
            else:
                row[cls] = "-"

            if not remaining[cls]:
                finished.add(cls)

            if len(recent) > 2:
                recent.pop(0)

        if not something_done:
            break

        schedule.append(row)
        current_date += timedelta(days=1)

    return pd.DataFrame(schedule)

# =========================================================
# GENERATE DATE SHEET
# =========================================================
st.subheader("📅 Generate Date Sheet")

start_date = st.date_input("Exam start date", value=date.today())
holiday_dates = st.multiselect(
    "Holidays",
    options=[start_date + timedelta(days=i) for i in range(180)],
    format_func=lambda d: d.strftime("%d-%m-%Y")
)

if st.button("📅 Generate Date Sheet"):
    class_subjects = {}
    for _, r in st.session_state.data.iterrows():
        cls = str(r["Class"]).strip().lower()
        subs = [str(v).strip() for k, v in r.items() if k != "Class" and v]
        if cls:
            class_subjects[cls] = subs

    result = generate_schedule(class_subjects, start_date, set(holiday_dates))

    if result.empty:
        st.error("❌ No valid schedule possible.")
    else:
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

