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
    "The date sheet is generated STRICTLY based on the rule:\n"
    "NO three consecutive classes will have the same exam on the same day.\n\n"
    "If you want to change or relax this rule, please do it manually."
)

# =========================================================
# DATE HELPERS
# =========================================================
def is_second_saturday(d):
    return d.weekday() == 5 and 8 <= d.day <= 14

def is_blocked_day(d, holidays):
    return d.weekday() == 6 or is_second_saturday(d) or d in holidays

# =========================================================
# CORE SCHEDULER (UPDATED GROUPING – CORRECT)
# =========================================================
def generate_schedule(class_subjects, start_date, holidays):

    classes = list(class_subjects.keys())

    class_groups = {
        "11": ["11 science", "11 commerce", "11 arts"],
        "12": ["12 science", "12 commerce", "12 arts"]
    }

    group_of = {}
    for g, members in class_groups.items():
        for m in members:
            group_of[m] = g

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

        subjects_today = []
        i = 0

        while i < len(classes):
            cls = classes[i]

            if cls in finished or not remaining.get(cls):
                row[cls] = "-"
                subjects_today.append("-")
                finished.add(cls)
                i += 1
                continue

            recent = [s for s in subjects_today if s != "-"][-2:]

            assigned = False
            for sub in list(remaining[cls]):
                if sub in recent:
                    continue

                if cls in group_of:
                    grp = group_of[cls]
                    members = class_groups[grp]

                    if all(m in remaining and sub in remaining[m] for m in members):
                        for m in members:
                            row[m] = sub
                            remaining[m].remove(sub)
                            subjects_today.append(sub)
                            if not remaining[m]:
                                finished.add(m)
                        i += len(members)
                        assigned = True
                        break

                row[cls] = sub
                remaining[cls].remove(sub)
                subjects_today.append(sub)
                if not remaining[cls]:
                    finished.add(cls)
                i += 1
                assigned = True
                break

            if not assigned:
                row[cls] = "-"
                subjects_today.append("-")
                i += 1

        schedule.append(row)
        current_date += timedelta(days=1)

    return pd.DataFrame(schedule)

# =========================================================
# SESSION TABLE (EXACT EXAMPLE YOU GAVE)
# =========================================================
if "table" not in st.session_state:
    st.session_state.table = pd.DataFrame({
        "Class": [
            "6","7","8","9","10",
            "11 science","11 commerce","11 arts",
            "12 science","12 commerce","12 arts"
        ],
        "Subject 1": ["maths","maths","maths","maths","maths","maths","maths","eng","maths","maths","eng"],
        "Subject 2": ["eng","eng","eng","eng","eng","eng","eng","hindi/sanskrit","eng","eng","hindi/sanskrit"],
        "Subject 3": ["hindi","hindi","hindi","hindi/sanskrit","hindi/sanskrit","hindi/sanskrit","hindi/sanskrit","history","hindi/sanskrit","hindi/sanskrit","history"],
        "Subject 4": ["sanskrit","sanskrit","sanskrit","science","science","physics","business s","geography","physics","business s","geography"],
        "Subject 5": ["science","science","science","ai","ai","chem","economics","political sc","chem","economics","political sc"],
        "Subject 6": ["ai","ai","ai","sst","sst","bio/cs","accountancy","economics","bio/cs","accountancy","economics"]
    })

# =========================================================
# SUBJECT COLUMN CONTROL
# =========================================================
st.subheader("📋 Edit directly (Excel-like)")

subject_count = st.slider("Number of subject columns", 3, 12, 6)
cols = ["Class"] + [f"Subject {i}" for i in range(1, subject_count + 1)]
st.session_state.table = st.session_state.table.reindex(columns=cols, fill_value="")

edited = st.data_editor(
    st.session_state.table,
    num_rows="dynamic",
    use_container_width=True
)

st.session_state.table = edited

# =========================================================
# INPUTS
# =========================================================
start_date = st.date_input("📅 Exam start date", value=date.today())
holiday_dates = st.multiselect(
    "Holidays",
    options=[start_date + timedelta(days=i) for i in range(180)]
)

# =========================================================
# GENERATE
# =========================================================
if st.button("📅 Generate Date Sheet"):
    class_subjects = {}
    for _, r in edited.iterrows():
        cls = str(r["Class"]).strip().lower()
        subs = [str(s).strip() for s in r[1:] if str(s).strip()]
        if cls:
            class_subjects[cls] = subs

    result = generate_schedule(class_subjects, start_date, set(holiday_dates))
    st.dataframe(result, use_container_width=True)

    out = BytesIO()
    result.to_excel(out, index=False, engine="openpyxl")
    out.seek(0)

    st.download_button("⬇️ Download Final Date Sheet", out, "final_datesheet.xlsx")
