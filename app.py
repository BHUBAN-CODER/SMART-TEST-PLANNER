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
    "If you want to change or relax this rule, please do it manually "
    "after downloading the final date sheet."
)

# =========================================================
# SESSION STATE INITIALIZATION (PREFILLED EXAMPLE)
# =========================================================
if "subject_cols" not in st.session_state:
    st.session_state.subject_cols = 7

if "table" not in st.session_state:
    st.session_state.table = pd.DataFrame({
        "Class": [
            "6","7","8","9","10",
            "11 science","11 commerce","12 science","12 commerce",
            "11 arts","12 arts"
        ],
        "Subject 1": ["maths","maths","maths","maths","maths","maths","maths","maths","maths","eng","eng"],
        "Subject 2": ["eng","eng","eng","eng","eng","eng","eng","eng","eng","hindi/sanskrit","hindi/sanskrit"],
        "Subject 3": ["hindi","hindi","hindi","hindi/sanskrit","hindi/sanskrit","hindi/sanskrit","hindi/sanskrit","hindi/sanskrit","hindi/sanskrit","history","history"],
        "Subject 4": ["sanskrit","sanskrit","sanskrit","science","science","physics","business s","physics","business s","geography","geography"],
        "Subject 5": ["science","science","science","ai","ai","chem","economics","chem","economics","political sc","political sc"],
        "Subject 6": ["ai","ai","ai","sst","sst","bio/cs","accountancy","bio/cs","accountancy","economics","economics"],
        "Subject 7": ["sst","sst","sst","","","","","","","",""]
    })

# =========================================================
# TABLE CONTROLS
# =========================================================
c1, c2, c3, c4 = st.columns(4)

with c1:
    if st.button("➕ Add Row"):
        st.session_state.table.loc[len(st.session_state.table)] = [""] * len(st.session_state.table.columns)

with c2:
    if st.button("➖ Remove Last Row") and len(st.session_state.table) > 1:
        st.session_state.table = st.session_state.table.iloc[:-1]

with c3:
    if st.button("➕ Add Subject Column"):
        st.session_state.subject_cols += 1
        st.session_state.table[f"Subject {st.session_state.subject_cols}"] = ""

with c4:
    if st.button("➖ Remove Subject Column") and st.session_state.subject_cols > 1:
        col = f"Subject {st.session_state.subject_cols}"
        st.session_state.table.drop(columns=[col], inplace=True)
        st.session_state.subject_cols -= 1

# =========================================================
# EDITABLE TABLE
# =========================================================
st.subheader("✏️ Edit Data (Excel-like)")

edited_df = st.data_editor(
    st.session_state.table,
    use_container_width=True,
    num_rows="dynamic"
)

st.session_state.table = edited_df

# =========================================================
# DATE HELPERS
# =========================================================
def is_second_saturday(d):
    return d.weekday() == 5 and 8 <= d.day <= 14

def is_blocked_day(d, holidays):
    return d.weekday() == 6 or is_second_saturday(d) or d in holidays

# =========================================================
# CORE SCHEDULER (UNCHANGED)
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
    used_days = 0

    while len(finished) < len(classes) and used_days < 400:

        if is_blocked_day(current_date, holidays):
            current_date += timedelta(days=1)
            continue

        row = {"Date": current_date.strftime("%d-%m-%Y"), "Day": current_date.strftime("%A")}
        subjects_today = []
        something_done = False

        i = 0
        while i < len(classes):
            cls = classes[i]

            if cls in finished or not remaining.get(cls):
                row[cls] = "-"
                subjects_today.append("-")
                finished.add(cls)
                i += 1
                continue

            recent = [s for s in reversed(subjects_today) if s != "-"][:2]

            assigned = False
            for candidate in list(remaining[cls]):
                if candidate in recent:
                    continue

                if cls in group_of:
                    grp = group_of[cls]
                    members = class_groups[grp]

                    if all(candidate in remaining.get(m, []) for m in members):
                        for m in members:
                            row[m] = candidate
                            remaining[m].remove(candidate)
                            subjects_today.append(candidate)
                            if not remaining[m]:
                                finished.add(m)
                        i += len(members)
                        assigned = True
                        something_done = True
                        break

                row[cls] = candidate
                remaining[cls].remove(candidate)
                subjects_today.append(candidate)
                if not remaining[cls]:
                    finished.add(cls)
                i += 1
                assigned = True
                something_done = True
                break

            if not assigned:
                row[cls] = "-"
                subjects_today.append("-")
                i += 1

        if not something_done:
            break

        schedule.append(row)
        current_date += timedelta(days=1)
        used_days += 1

    return pd.DataFrame(schedule)

# =========================================================
# RUN
# =========================================================
st.subheader("📅 Generate Date Sheet")

start_date = st.date_input("Exam start date", value=date.today())

holiday_dates = st.multiselect(
    "Holidays",
    options=[start_date + timedelta(days=i) for i in range(180)],
    format_func=lambda d: d.strftime("%d-%m-%Y")
)

if st.button("🚀 Generate"):

    df = st.session_state.table.copy()
    class_subjects = {}

    for _, r in df.iterrows():
        cls = str(r["Class"]).strip().lower()
        subs = [str(v).strip() for k, v in r.items() if k.startswith("Subject") and v not in ("", None)]
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

