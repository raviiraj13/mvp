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
st.caption("Optimized with automatic OD and Makeup detection")

# ---------------- COLORS ----------------
PRESENT_COLOR = "#1ABC9C"
ABSENT_COLOR = "#F39C12"

# ---------------- CLEAN PDF ----------------
def clean_text(text):
    return text.encode("latin-1", "ignore").decode("latin-1")

# ---------------- PARSE DATA ----------------
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

    if not rows:
        raise ValueError("Invalid format")

    df = pd.DataFrame(rows, columns=[

        "Subject",
        "Present",
        "OD",
        "Makeup",
        "Absent"

    ])

    # Effective present
    df["Effective Present"] = (
        df["Present"] +
        df["OD"] +
        df["Makeup"]
    )

    # Total classes
    df["Total Classes"] = (
        df["Present"] +
        df["OD"] +
        df["Makeup"] +
        df["Absent"]
    )

    # Attendance %
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

    while total+leave > 0 and (
        present/(total+leave)*100 >= target
    ):
        leave += 1

    return max(0, leave-1)

# ---------------- PIE CHART ----------------
def plot_pie(present, absent):

    plt.figure(figsize=(5,5))

    plt.pie(
        [present, absent],
        labels=["Present","Absent"],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        startangle=90
    )

    plt.title("Overall Attendance")

    st.pyplot(plt)
    plt.close()

# ---------------- PDF ----------------
def generate_pdf(summary, df):

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"Attendance Report", ln=True)

    pdf.set_font("Arial","",12)

    pdf.cell(0,8,f"Total Classes: {summary['total']}", ln=True)
    pdf.cell(0,8,f"Present: {summary['present']}", ln=True)
    pdf.cell(0,8,f"Absent: {summary['absent']}", ln=True)
    pdf.cell(0,8,f"OD: {summary['od']}", ln=True)
    pdf.cell(0,8,f"Makeup: {summary['makeup']}", ln=True)
    pdf.cell(0,8,f"Attendance: {summary['attendance']:.2f}%", ln=True)

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

    try:

        df = parse_attendance(text)

        st.success("Attendance parsed successfully")

        st.subheader("Subject-wise Attendance")

        st.dataframe(df)

        # -------- SUMMARY --------
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
            effective_present +
            total_absent
        )

        attendance = (
            effective_present /
            total_classes * 100
        )

        st.subheader("Overall Summary")

        c1,c2,c3 = st.columns(3)
        c4,c5,c6 = st.columns(3)

        c1.metric("Total Present", total_present)
        c2.metric("Total Absent", total_absent)
        c3.metric("Total Classes", total_classes)

        c4.metric("Total OD", total_od)
        c5.metric("Total Makeup", total_makeup)
        c6.metric("Effective Present", effective_present)

        st.metric(
            "Overall Attendance %",
            f"{attendance:.2f}%"
        )

        plot_pie(
            effective_present,
            total_absent
        )

        # -------- TARGET --------
        st.subheader("Target Optimizer")

        target = st.number_input(
            "Enter target %",
            0,100,75
        )

        need = classes_needed(
            effective_present,
            total_classes,
            target
        )

        leave = classes_can_leave(
            effective_present,
            total_classes,
            target
        )

        st.info(f"Attend {need} more classes")
        st.info(f"Can leave {leave} classes safely")

        # -------- PDF --------
        summary = {

            "present": total_present,
            "absent": total_absent,
            "od": total_od,
            "makeup": total_makeup,
            "total": total_classes,
            "attendance": attendance

        }

        pdf = generate_pdf(summary, df)

        st.download_button(
            "Download PDF",
            pdf,
            "attendance_report.pdf"
        )

    except Exception as e:

        st.error("Parsing failed")
        st.code(str(e))
