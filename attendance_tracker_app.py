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
st.caption("Optimized with OD, Makeup, Leave Simulator, and Recovery Calculator")

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

    df["Effective Present"] = (
        df["Present"] +
        df["OD"] +
        df["Makeup"]
    )

    df["Total Classes"] = (
        df["Present"] +
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

# ---------------- AGGREGATE PIE CHART ----------------
def plot_aggregate_pie(effective_present, total_absent):

    plt.figure(figsize=(5,5))

    plt.pie(
        [effective_present, total_absent],
        labels=["Aggregate Attendance", "Aggregate Absent"],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        startangle=90
    )

    plt.title("Aggregate Attendance vs Absent")

    st.pyplot(plt)
    plt.close()

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
text = st.text_area("Paste Attendance Report", height=300)

if text:

    df = parse_attendance(text)

    st.success("Attendance parsed successfully")

    st.subheader("Subject-wise Attendance")

    st.dataframe(df)

    # ---------------- SUMMARY ----------------
    total_present = df["Present"].sum()
    total_od = df["OD"].sum()
    total_makeup = df["Makeup"].sum()
    total_absent = df["Absent"].sum()

    effective_present = (
        total_present +
        total_od +
        total_makeup
    )

    total_classes = (
        total_present +
        total_absent
    )

    aggregate_attendance = (
        effective_present /
        total_classes * 100
    )

    st.subheader("Overall Summary")

    c1,c2,c3 = st.columns(3)
    c4,c5,c6 = st.columns(3)

    c1.metric("Present", total_present)
    c2.metric("Absent", total_absent)
    c3.metric("Total Classes", total_classes)

    c4.metric("OD", total_od)
    c5.metric("Makeup", total_makeup)
    c6.metric("Effective Present", effective_present)

    st.metric(
        "Aggregate Attendance %",
        f"{aggregate_attendance:.2f}%"
    )

    # UPDATED PIE CHART
    plot_aggregate_pie(
        effective_present,
        total_absent
    )

    # ---------------- TARGET OPTIMIZER ----------------
    st.subheader("🎯 Aggregate Target Optimizer")

    target = st.number_input(
        "Enter Target %",
        0,100,75
    )

    need = classes_needed(
        effective_present,
        total_classes,
        target
    )

    leave_safe = classes_can_leave(
        effective_present,
        total_classes,
        target
    )

    # SINGLE LINE OUTPUT
    if aggregate_attendance < target:
        st.warning(
            f"Attend {need} classes to reach {target}% attendance"
        )
    else:
        st.success(
            f"You can leave {leave_safe} classes safely"
        )

    # ---------------- LEAVE + RECOVERY SIMULATOR ----------------
    st.subheader("🎚️ Leave Simulator + Recovery Calculator")

    leave_x = st.slider(
        "Select number of classes to leave",
        0,
        total_classes + 50,
        0
    )

    new_total = total_classes + leave_x

    new_attendance = (
        effective_present /
        new_total * 100
    )

    st.metric(
        "Attendance after leaving",
        f"{new_attendance:.2f}%"
    )

    required_after_leave = classes_needed(
        effective_present,
        new_total,
        target
    )

    st.metric(
        "Classes required to recover target",
        required_after_leave
    )

    final_attendance = (
        (effective_present + required_after_leave) /
        (new_total + required_after_leave) * 100
    )

    st.metric(
        "Attendance after recovery",
        f"{final_attendance:.2f}%"
    )

    # ---------------- SUBJECT OPTIMIZER ----------------
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
