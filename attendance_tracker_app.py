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
st.caption("Paste attendance from college ERP")

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

    # IMPORTANT RULE: Present = Present + Makeup
    df["Effective Present"] = df["Present"] + df["Makeup"]

    df["Total Classes"] = df["Effective Present"] + df["Absent"]

    df["Attendance%"] = (
        df["Effective Present"] /
        df["Total Classes"] * 100
    ).round(2)

    df["Status"] = df["Attendance%"].apply(
        lambda x: "🟢" if x >= 75 else "🔴"
    )

    return df.sort_values("Attendance%")


# ---------------- OVERALL DONUT ----------------
def plot_overall_donut(total_present, total_absent):

    st.subheader("📊 Overall Attendance Donut Chart")

    total = total_present + total_absent

    if total == 0:
        st.warning("No data")
        return

    present_percent = total_present / total * 100
    absent_percent = 100 - present_percent

    fig, ax = plt.subplots()

    ax.pie(
        [present_percent, absent_percent],
        labels=["Present", "Absent"],
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops={"width":0.4}
    )

    ax.set_title("Overall Attendance")

    st.pyplot(fig)

    plt.close(fig)


# ---------------- SUBJECT DONUT ----------------
def plot_subjectwise_donut(df):

    st.subheader("📘 Subject-wise Attendance Donut Charts")

    cols = st.columns(3)

    for i in range(len(df)):

        row = df.iloc[i]

        present = row["Effective Present"]
        absent = row["Absent"]

        total = present + absent

        if total == 0:
            continue

        present_percent = present / total * 100
        absent_percent = 100 - present_percent

        fig, ax = plt.subplots()

        ax.pie(
            [present_percent, absent_percent],
            labels=["Present", "Absent"],
            colors=[PRESENT_COLOR, ABSENT_COLOR],
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops={"width":0.4}
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

    st.subheader("📋 Attendance Table")

    st.dataframe(df)


    # ---------------- SUMMARY ----------------
    total_effective_present = df["Effective Present"].sum()
    total_absent = df["Absent"].sum()

    total_classes = total_effective_present + total_absent

    aggregate_attendance = (
        total_effective_present /
        total_classes * 100
    )

    st.subheader("📈 Overall Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric("Effective Present", total_effective_present)
    col2.metric("Absent", total_absent)
    col3.metric("Total Classes", total_classes)

    st.metric(
        "Aggregate Attendance %",
        f"{aggregate_attendance:.2f}%"
    )


    # ---------------- DONUT CHARTS ----------------
    plot_overall_donut(
        total_effective_present,
        total_absent
    )

    plot_subjectwise_donut(df)


    # ---------------- TARGET OPTIMIZER ----------------
    st.subheader("🎯 Target Optimizer")

    target = st.number_input(
        "Enter Target %",
        min_value=0,
        max_value=100,
        value=75
    )

    need = classes_needed(
        total_effective_present,
        total_classes,
        target
    )

    leave_safe = classes_can_leave(
        total_effective_present,
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
        "Classes to leave",
        min_value=0,
        max_value=500,
        value=0
    )

    new_total = total_classes + leave_x

    new_attendance = (
        total_effective_present /
        new_total * 100
    )

    st.metric(
        "New Attendance %",
        f"{new_attendance:.2f}%"
    )


    # ---------------- SUBJECT TARGET ----------------
    st.subheader("📘 Subject Target Optimizer")

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
        "Download PDF Report",
        pdf,
        "attendance_report.pdf"
    )
