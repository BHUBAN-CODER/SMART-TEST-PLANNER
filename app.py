import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import BytesIO
import io

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(
    page_title="Smart Test Planner",
    layout="wide"
)

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
# TEMPLATE DOWNLOAD
# =========================================================
def generate_template():
    return pd.DataFrame(
        columns=["Class"] + [f"Subject {i}" for i in range(1, 8)]
    )

template_buffer = BytesIO()
generate_template().to_excel(template_buffer, index=False, engine="openpyxl")
template_buffer.seek(0)

st.download_button(
    "⬇️ Download Excel Template",
    data=template_buffer,
    file_name="smart_test_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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

            # RULE: last 2 non-dash subjects
            recent = []
            for s in reversed(subjects_today):
                if s != "-":
                    recent.append(s)
                if len(recent) == 2:
                    break

            if cls in group_of:
                first_subject = remaining[cls][0]
                if first_subject in recent:
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

                    if all(
                        m in remaining and candidate in remaining[m]
                        for m in members
                    ):
                        for m in members:
                            row[m] = candidate
                            remaining[m].remove(candidate)
                            subjects_today.append(candidate)
                            if not remaining[m]:
                                finished.add(m)

                        i += len(members)
                        something_done = True
                        assigned = True
                        break

                row[cls] = candidate
                remaining[cls].remove(candidate)
                subjects_today.append(candidate)
                something_done = True

                if not remaining[cls]:
                    finished.add(cls)

                i += 1
                assigned = True
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
# INPUT (MOBILE SAFE)
# =========================================================
uploaded_file = st.file_uploader(
    "📤 Upload filled Excel template",
    type=["xlsx"],
    accept_multiple_files=False
)

start_date = st.date_input(
    "📅 Exam start date",
    value=date.today()
)

holiday_dates = st.multiselect(
    "📌 Holidays (optional)",
    options=[start_date + timedelta(days=i) for i in range(180)],
    format_func=lambda d: d.strftime("%d-%m-%Y")
)

# =========================================================
# RUN (MOBILE SAFE FILE HANDLING)
# =========================================================
if st.button("📅 Generate Date Sheet"):

    if uploaded_file is None:
        st.error("Please upload the filled Excel template first.")
    else:
        try:
            file_bytes = uploaded_file.read()
            df = pd.read_excel(io.BytesIO(file_bytes))
        except Exception as e:
            st.error("Failed to read the Excel file. Please re-upload.")
            st.stop()

        class_subjects = {}
        for _, r in df.iterrows():
            cls = str(r["Class"]).strip().lower()
            subs = [str(s).strip() for s in r[1:] if pd.notna(s)]
            class_subjects[cls] = subs

        result = generate_schedule(
            class_subjects,
            start_date,
            set(holiday_dates)
        )

        if result.empty:
            st.error("❌ No valid schedule possible with given rules.")
        else:
            st.success("✅ Date Sheet Generated Successfully")

            st.info(
                "ℹ️ The generated date sheet strictly follows the rule:\n"
                "NO three consecutive classes have the same exam on the same day."
            )

            st.dataframe(result, use_container_width=True)

            output = BytesIO()
            result.to_excel(output, index=False, engine="openpyxl")
            output.seek(0)

            st.download_button(
                "⬇️ Download Final Date Sheet",
                data=output,
                file_name="final_datesheet.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

