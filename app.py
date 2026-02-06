import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import BytesIO

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(page_title="Smart Test Planner", layout="wide")
st.title("📘 Smart Test Planner")

# =========================================================
# IMPORTANT RULE DISPLAY
# =========================================================
st.warning(
    "⚠️ IMPORTANT RULE\n\n"
    "The date sheet is generated STRICTLY based on the rule:\n"
    "NO three consecutive classes will have the same exam on the same day.\n\n"
    "If you want to change or relax this rule, please do it manually "
    "after downloading the final date sheet."
)

# =========================================================
# EXCEL-LIKE TEMPLATE (WITH EXAMPLE DATA)
# =========================================================
def example_template():
    return pd.DataFrame([
        ["6", "English", "Maths", "Science", "SST", "Hindi", "", ""],
        ["7", "English", "Maths", "Science", "SST", "Hindi", "", ""],
        ["8", "English", "Maths", "Science", "SST", "Hindi", "", ""],
        ["11 science", "English", "Maths", "Physics", "Chemistry", "CS", "", ""],
        ["11 commerce", "English", "Maths", "Economics", "BST", "Accounts", "", ""],
    ], columns=["Class"] + [f"Subject {i}" for i in range(1, 8)])

# =========================================================
# AUTO-SAVE SESSION STATE
# =========================================================
if "input_table" not in st.session_state:
    st.session_state.input_table = example_template()

# =========================================================
# TABLE CONTROLS
# =========================================================
st.subheader("📝 Enter Class & Subjects (Excel-like Editor)")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("➕ Add Row"):
        st.session_state.input_table.loc[len(st.session_state.input_table)] = [""] * len(
            st.session_state.input_table.columns
        )

with col2:
    if st.button("➖ Remove Last Row"):
        if len(st.session_state.input_table) > 1:
            st.session_state.input_table = st.session_state.input_table.iloc[:-1]

with col3:
    if st.button("🧹 Clear All"):
        st.session_state.input_table = example_template()

# =========================================================
# EDITABLE TABLE (AUTO-SAVED)
# =========================================================
edited_df = st.data_editor(
    st.session_state.input_table,
    num_rows="dynamic",
    use_container_width=True
)

st.session_state.input_table = edited_df

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

    class_groups = {
        "11": ["11 science", "11 commerce"],
        "12": ["12 science", "12 commerce"]
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

        row = {
            "Date": current_date.strftime("%d-%m-%Y"),
            "Day": current_date.strftime("%A")
        }

        subjects_today = []
        something_done = False
        i = 0

        while i < len(classes):
            cls = classes[i]

            if cls in finished:
                row[cls] = "-"
                subjects_today.append("-")
                i += 1
                continue

            if not remaining.get(cls):
                row[cls] = "-"
                finished.add(cls)
                subjects_today.append("-")
                i += 1
                continue

            recent = []
            for s in reversed(subjects_today):
                if s != "-":
                    recent.append(s)
                if len(recent) == 2:
                    break

            if cls in group_of and remaining[cls][0] in recent:
                row[cls] = "-"
                subjects_today.append("-")
                i += 1
                something_done = True
                continue

            assigned = False

            for candidate in list(remaining[cls]):
                if candidate in recent:
                    continue

                if cls in group_of:
                    grp = group_of[cls]
                    members = class_groups[grp]
                    if all(m in remaining and candidate in remaining[m] for m in members):
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
# EXAM SETTINGS
# =========================================================
st.subheader("📅 Exam Settings")

start_date = st.date_input("Exam start date", value=date.today())

holiday_dates = st.multiselect(
    "Holidays (optional)",
    options=[start_date + timedelta(days=i) for i in range(180)],
    format_func=lambda d: d.strftime("%d-%m-%Y")
)

# =========================================================
# RUN
# =========================================================
if st.button("📅 Generate Date Sheet"):

    df = st.session_state.input_table

    class_subjects = {}
    for _, r in df.iterrows():
        if pd.isna(r["Class"]):
            continue
        cls = str(r["Class"]).strip().lower()
        subs = [str(s).strip() for s in r[1:] if pd.notna(s)]
        if subs:
            class_subjects[cls] = subs

    if not class_subjects:
        st.error("Please enter valid class and subject data.")
        st.stop()

    result = generate_schedule(class_subjects, start_date, set(holiday_dates))

    st.success("✅ Date Sheet Generated")
    st.dataframe(result, use_container_width=True)

    out = BytesIO()
    result.to_excel(out, index=False, engine="openpyxl")
    out.seek(0)

    st.download_button(
        "⬇️ Download Final Date Sheet",
        data=out,
        file_name="final_datesheet.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

