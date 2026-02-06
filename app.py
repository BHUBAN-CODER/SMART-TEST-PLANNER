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
    "• NO three consecutive classes will have the same exam on the same day.\n"
    "• Class 11 and Class 12 are treated as SEPARATE groups.\n"
    "• Subjects may sync partially within a group (e.g. Arts + Commerce).\n"
)

# =========================================================
# TEMPLATE
# =========================================================
def generate_template():
    return pd.DataFrame(columns=["Class"] + [f"Subject {i}" for i in range(1, 8)])

buf = BytesIO()
generate_template().to_excel(buf, index=False, engine="openpyxl")
buf.seek(0)

st.download_button(
    "⬇️ Download Excel Template",
    data=buf,
    file_name="smart_test_template.xlsx"
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

    # Separate academic groups
    groups = {
        "11": [c for c in classes if c.startswith("11")],
        "12": [c for c in classes if c.startswith("12")],
        "other": [c for c in classes if not c.startswith("11") and not c.startswith("12")]
    }

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

        for grp_classes in groups.values():

            # collect all subjects remaining in this group
            subject_pool = {}
            for cls in grp_classes:
                if cls in finished:
                    continue
                for sub in remaining.get(cls, []):
                    subject_pool.setdefault(sub, []).append(cls)

            # try each subject
            for subject, cls_list in subject_pool.items():

                # avoid 3 consecutive same subject
                recent = [s for s in subjects_today if s != "-"][-2:]
                if subject in recent:
                    continue

                # assign subject only to classes that have it
                for cls in grp_classes:
                    if cls in finished:
                        row[cls] = "-"
                    elif cls in cls_list:
                        row[cls] = subject
                        remaining[cls].remove(subject)
                        if not remaining[cls]:
                            finished.add(cls)
                    else:
                        row[cls] = "-"

                subjects_today.extend(
                    [subject if cls in cls_list else "-" for cls in grp_classes]
                )

                something_done = True
                break  # only one subject per group per day

            else:
                # nothing assigned in this group
                for cls in grp_classes:
                    row.setdefault(cls, "-")
                    subjects_today.append("-")

        if not something_done:
            break

        schedule.append(row)
        current_date += timedelta(days=1)
        used_days += 1

    return pd.DataFrame(schedule).fillna("-")

# =========================================================
# INPUT
# =========================================================
uploaded_file = st.file_uploader("Upload filled template", type=["xlsx"])
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

    if result.empty:
        st.error("❌ No valid schedule possible with given rules.")
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

