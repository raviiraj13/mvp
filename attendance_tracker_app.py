import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import sympy as sp
import math
import re

# ---------------- PAGE ----------------
st.set_page_config(page_title="Attendance Tracker", layout="wide")

st.title("📊 Attendance Tracker (OD & Makeup Optimized)")
st.caption("Fully optimized with OD and Makeup support")

# ---------------- COLORS ----------------
PRESENT_COLOR = "#1ABC9C"
ABSENT_COLOR = "#F39C12"

# ---------------- PDF SAFE ----------------
def clean_text(text):
    return text.encode("latin-1", "ignore").decode("latin-1")

# ---------------- RECALCULATE ----------------
def recalculate(df):

    df["Effective Present"] = (
        df["Present"] +
        df["OD"] +
        df["Makeup"] +
        df["Extra OD"] +
        df["Extra Makeup"]
    )

    df["Total Classes"] = (
        df["Present"] +
        df["Absent"] +
        df["OD"] +
        df["Makeup"] +
        df["Extra OD"] +
        df["Extra Makeup"]
    )

    df["Attendance%"] = (
        df["Effective Present"] /
        df["Total Classes"] * 100
    ).round(2)

    df["Status"] = df["Attendance%"].apply(
        lambda x: "🟢" if x >= 75 else "🔴"
    )

    return df

# ---------------- PARSER ----------------
def parse_skit(text):

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
            absent,
            0,
            0
        ])

    df = pd.DataFrame(rows, columns=[

        "Subject",
        "Present",
        "OD",
        "Makeup",
        "Absent",
        "Extra OD",
        "Extra Makeup"

    ])

    return recalculate(df)

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

# ---------------- CHART ----------------
def plot_pie(present, absent):

    plt.figure(figsize=(4,4))

    plt.pie(
        [present, absent],
        labels=["Present","Absent"],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR]
    )

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

    df = parse_skit(text)

    # -------- EXTRA OD / MAKEUP --------
    st.subheader("Optional: Add Extra OD / Makeup")

    for i in df.index:

        c1,c2 = st.columns(2)

        df.at[i,"Extra OD"] = c1.number_input(
            f"Extra OD - {df.at[i,'Subject']}",
            0, step=1,
            key=f"od{i}"
        )

        df.at[i,"Extra Makeup"] = c2.number_input(
            f"Extra Makeup - {df.at[i,'Subject']}",
            0, step=1,
            key=f"mk{i}"
        )

    df = recalculate(df)

    st.subheader("Attendance Table")

    st.dataframe(df)

    # -------- TOTAL SUMMARY --------
    total_present = df["Present"].sum()
    total_absent = df["Absent"].sum()
    total_od = df["OD"].sum()
    total_makeup = df["Makeup"].sum()

    extra_od = df["Extra OD"].sum()
    extra_makeup = df["Extra Makeup"].sum()

    effective_present = (
        total_present +
        total_od +
        total_makeup +
        extra_od +
        extra_makeup
    )

    total_classes = (
        total_present +
        total_absent +
        total_od +
        total_makeup +
        extra_od +
        extra_makeup
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
        "Enter Target %",
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
