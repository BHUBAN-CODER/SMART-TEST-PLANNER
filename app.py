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
    "• NO three consecutive classes can have the same exam on the same day\n"
    "• Class 11 (science/commerce/arts) MUST have same subject on same day\n"
    "• Class 12 (science/commerce/arts) MUST have same subject on same day\n"
    "• Class 11 and Class 12 will NEVER sync together\n"
)

# =========================================================
# DATE HELPERS
# =========================================================
def is_second_saturday(d):
    return d.weekday() == 5 and 8 <= d.day <= 14

def is_blocked_day(d, holidays):
    return d.weekday() == 6 or is_second_saturday(d) or d in holidays

# =========================================================
# CORE SCHEDULER (FIXED)
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

        row = {
            "Date": current_date.strftime("%d-%m-%Y"),
            "Day": current_date.strftime("%A")
        }

        subjects_today = []
        something_done = False
        used_subjects_today = set()

        for cls in classes:

            if cls in finished:
                row[cls] = "-"
                subjects_today.append("-")
                continue

            if not remaining[cls]:
                row[cls] = "-"
                finished.add(cls)
                subjects_today.append("-")
                continue

            recent = [s for s in subjects_today if s != "-"][-2:]

            assigned = False

            for candidate in list(remaining[cls]):

                if candidate in recent or candidate in used_subjects_today:
                    continue

                # HARD GROUP ENFORCEMENT
                if cls in group_of:
                    grp = group_of[cls]
                    members = class_groups[grp]

                    if all(candidate in remaining[m] for m in members):
                        for m in members:
                            row[m] = candidate
                            remaining[m].remove(candidate)
                            used_subjects_today.add(candidate)
                            if not remaining[m]:
                                finished.add(m)

                        something_done = True
                        assigned = True
                        break

                else:
                    row[cls] = candidate
                    remaining[cls].remove(candidate)
                    used_subjects_today.add(candidate)
                    something_done = True
                    assigned = True
                    if not remaining[cls]:
                        finished.add(cls)
                    break

            if not assigned:
                row[cls] = "-"
                subjects_today.append("-")

        if not something_done:
            break

        schedule.append(row)
        current_date += timedelta(days=1)
        used_days += 1

    return pd.DataFrame(schedule)

# =========================================================
# INPUT
# =========================================================
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
start_date = st.date_input("Exam start date", value=date.today())

holiday_dates = st.multiselect(
    "Holidays",
    options=[start_date + timedelta(days=i) for i in range(180)],
    format_func=lambda d: d.strftime("%d-%m-%Y")
)

# =========================================================
# RUN
# =========================================================
if st.button("📅 Generate Date Sheet") and uploaded_file is not None:

    df = pd.read_excel(uploaded_file)

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

    st.success("✅ Date Sheet Generated")
    st.dataframe(result, use_container_width=True)

    out = BytesIO()
    result.to_excel(out, index=False)
    out.seek(0)

    st.download_button(
        "⬇️ Download Final Date Sheet",
        data=out,
        file_name="final_datesheet.xlsx"
    )
