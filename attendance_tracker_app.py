import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import sympy as sp
import math
import re

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Attendance Tracker", layout="wide")

st.title("📊 Attendance Tracker")
st.caption("Paste the Attendance from college ERP")

# ---------------- COLORS ----------------
PRESENT_COLOR = "#1ABC9C"
ABSENT_COLOR = "#F39C12"

# ---------------- CLEAN PDF ----------------
def clean_text(text):
    return text.encode("latin-1", "ignore").decode("latin-1")


# ---------------- PARSER ----------------
def parse_attendance(text):

    rows = []

    for line in text.splitlines():

        parts = re.split(r"\t+", line.strip())

        if len(parts) < 9:
            continue

        if not parts[0].isdigit():
            continue

        subject = parts[2]
        present = int(parts[4])
        od = int(parts[5])
        makeup = int(parts[6])
        absent = int(parts[7])

        rows.append([
            subject,
            present,
            od,
            makeup,
            absent
        ])

    df = pd.DataFrame(rows, columns=[
        "Subject",
        "Present",
        "OD",
        "Makeup",
        "Absent"
    ])

    # IMPORTANT FORMULA: Present = Present + Makeup
    df["Effective Present"] = (
        df["Present"] +
        df["Makeup"]
    )

    df["Total Classes"] = (
        df["Effective Present"] +
        df["Absent"]
    )

    df["Attendance%"] = (
        df["Effective Present"] /
        df["Total Classes"] * 100
    ).round(2)

    df["Status"] = df["Attendance%"].apply(
        lambda x: "🟢" if x >= 75 else "🔴"
    )

    return df.sort_values("Attendance%")


# ---------------- OVERALL DONUT ----------------
def plot_all_subjects_donut(aggregate_present, total_absent):

    st.subheader("📊 Overall Attendance Donut Chart")

    total = aggregate_present + total_absent

    attendance_percent = aggregate_present / total * 100
    remaining_percent = 100 - attendance_percent

    fig, ax = plt.subplots(figsize=(6,6))

    ax.pie(
        [attendance_percent, remaining_percent],
        labels=["Present", "Absent"],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        startangle=90,
        wedgeprops=dict(width=0.4)
    )

    ax.set_title("Overall Attendance")

    st.pyplot(fig)

    plt.close(fig)


# ---------------- SUBJECT DONUT ----------------
def plot_subject_donut(df):

    st.subheader("📘 Subject-wise Attendance Donut Charts")

    cols = st.columns(3)

    for i, (_, row) in enumerate(df.iterrows()):

        present = row["Effective Present"]
        absent = row["Absent"]

        total = present + absent

        if total == 0:
            continue

        attendance_percent = present / total * 100
        remaining_percent = 100 - attendance_percent

        fig, ax = plt.subplots(figsize=(4,4))

        ax.pie(
            [attendance_percent, remaining_percent],
            labels=["Present", "Absent"],
            autopct="%1.1f%%",
            colors=[PRESENT_COLOR, ABSENT_COLOR],
            startangle=90,
            wedgeprops=dict(width=0.4)
        )

        ax.set_title(row["Subject"])

        cols[i % 3].pyplot(fig)

        plt.close(fig)


# ---------------- MATH ----------------
def classes_needed(present, total, target):

    x = sp.symbols("x")

    sol = sp.solve(
        (present+x)/(total+x)-target/100,
        x
    )

    if sol:
        return max(0, math.ceil(sol[0]))

    return 0


def classes_can_leave(present, total, target):

    leave = 0

    while present/(total+leave)*100 >= target:
        leave += 1

    return max(0, leave-1)


# ---------------- PDF ----------------
def generate_pdf(attendance, df):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial","B",16)

    pdf.cell(0,10,"Attendance Report", ln=True)

    pdf.set_font("Arial","",12)

    pdf.cell(
        0,10,
        f"Aggregate Attendance: {attendance:.2f}%",
        ln=True
    )

    pdf.ln(5)

    for _,r in df.iterrows():

        pdf.cell(
            0,8,
            clean_text(
                f"{r['Subject']} : {r['Attendance%']}%"
            ),
            ln=True
        )

    return pdf.output(dest="S").encode("latin-1")


# ---------------- INPUT ----------------
text = st.text_area(
    "Paste Attendance Report",
    height=300
)

if text:

    df = parse_attendance(text)

    st.success("Attendance uploaded successfully 🥳")

    st.subheader("Subject-wise Attendance Table")

    st.dataframe(df)


    # ---------------- SUMMARY ----------------
    total_present = df["Effective Present"].sum()
    total_absent = df["Absent"].sum()

    total_classes = total_present + total_absent

    aggregate_attendance = (
        total_present /
        total_classes * 100
    )

    st.subheader("Overall Summary")

    c1,c2,c3 = st.columns(3)

    c1.metric("Effective Present", total_present)
    c2.metric("Absent", total_absent)
    c3.metric("Total Classes", total_classes)

    st.metric(
        "Aggregate Attendance %",
        f"{aggregate_attendance:.2f}%"
    )


    # ---------------- DONUT CHARTS ----------------
    plot_all_subjects_donut(
        total_present,
        total_absent
    )

    plot_subject_donut(df)


    # ---------------- TARGET OPTIMIZER ----------------
    st.subheader("🎯 Aggregate Target Optimizer")

    target = st.number_input(
        "Enter Target %",
        min_value=0,
        max_value=100,
        value=75,
        step=1
    )

    need = classes_needed(
        total_present,
        total_classes,
        target
    )

    leave_safe = classes_can_leave(
        total_present,
        total_classes,
        target
    )

    if aggregate_attendance < target:

        st.warning(
            f"Attend {need} classes to reach {target}%"
        )

    else:

        st.success(
            f"You can leave {leave_safe} classes safely"
        )


    # ---------------- LEAVE SIMULATOR ----------------
    st.subheader("🎚️ Leave Simulator")

    leave_x = st.number_input(
        "Enter classes to leave",
        min_value=0,
        max_value=total_classes + 500,
        value=0
    )

    new_total = total_classes + leave_x

    new_attendance = (
        total_present /
        new_total * 100
    )

    st.metric(
        "Attendance after leaving",
        f"{new_attendance:.2f}%"
    )


    # ---------------- SUBJECT TARGET ----------------
    st.subheader("🎯 Subject-wise Target Optimizer")

    subject = st.selectbox(
        "Select Subject",
        df["Subject"]
    )

    row = df[df["Subject"] == subject].iloc[0]

    sub_need = classes_needed(
        row["Effective Present"],
        row["Total Classes"],
        target
    )

    sub_leave = classes_can_leave(
        row["Effective Present"],
        row["Total Classes"],
        target
    )

    if row["Attendance%"] < target:

        st.warning(
            f"{subject}: Attend {sub_need} classes"
        )

    else:

        st.success(
            f"{subject}: Can leave {sub_leave} classes"
        )


    # ---------------- PDF ----------------
    pdf = generate_pdf(
        aggregate_attendance,
        df
    )

    st.download_button(
        "Download PDF",
        pdf,
        "attendance_report.pdf"
    )
