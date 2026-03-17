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
st.caption("Paste attendance from ERP (handles OD, Makeup, messy data)")

# ---------------- SETTINGS ----------------
st.sidebar.header("⚙️ Settings")

include_od = st.sidebar.toggle(
    "Include OD in attendance",
    value=True,
    help="Turn OFF if your ERP already includes OD in Present"
)

debug_mode = st.sidebar.toggle(
    "Debug Mode",
    value=False
)

# ---------------- COLORS ----------------
PRESENT_COLOR = "#1ABC9C"
ABSENT_COLOR = "#F39C12"

# ---------------- SAFE INT ----------------
def safe_int(x):
    try:
        return int(str(x).strip())
    except:
        return 0

# ---------------- CLEAN PDF ----------------
def clean_text(text):
    return text.encode("latin-1", "ignore").decode("latin-1")

# ---------------- PARSER ----------------
def parse_attendance(text):

    rows = []

    for line in text.splitlines():

        parts = re.split(r"\t+", line.strip())

        if debug_mode:
            st.write("RAW:", parts)

        if len(parts) < 8:
            continue

        if not parts[0].isdigit():
            continue

        subject = parts[2]

        present = safe_int(parts[4])
        od = safe_int(parts[5])
        makeup = safe_int(parts[6])
        absent = safe_int(parts[7])

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

    # ---------------- LOGIC ----------------
    if include_od:
        df["Effective Present"] = (
            df["Present"] +
            df["OD"] +
            df["Makeup"]
        )
    else:
        df["Effective Present"] = (
            df["Present"] +
            df["Makeup"]
        )

    # ✅ Correct Total Classes (ERP standard)
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

# ---------------- PIE CHART ----------------
def plot_attendance_percentage_pie(present, absent):

    total = present + absent

    if total == 0:
        st.warning("No data available")
        return

    attendance = present / total * 100

    plt.figure(figsize=(6,6))
    plt.pie(
        [attendance, 100 - attendance],
        labels=[
            f"Attendance {attendance:.2f}%",
            f"Remaining {100-attendance:.2f}%"
        ],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        startangle=90
    )

    st.pyplot(plt)
    plt.close()

# ---------------- MATH ----------------
def classes_needed(present, total, target):

    x = sp.symbols("x")

    sol = sp.solve(
        (present+x)/(total+x) - target/100,
        x
    )

    if sol:
        return max(0, math.ceil(sol[0]))

    return 0


def classes_can_leave(present, total, target):

    leave = 0

    while total + leave > 0 and present/(total+leave)*100 >= target:
        leave += 1

    return max(0, leave-1)

# ---------------- PDF ----------------
def generate_pdf(attendance, df):

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"Attendance Report",ln=True)

    pdf.set_font("Arial","",12)
    pdf.cell(0,10,f"Aggregate Attendance: {attendance:.2f}%",ln=True)

    pdf.ln(5)

    for _,r in df.iterrows():
        pdf.cell(
            0,8,
            clean_text(f"{r['Subject']} : {r['Attendance%']}%"),
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

    if debug_mode:
        st.subheader("🔍 Debug Data")
        st.write(df)

    st.subheader("Subject-wise Attendance")
    st.dataframe(df)

    # ---------------- SUMMARY ----------------
    total_present = df["Present"].sum()
    total_od = df["OD"].sum()
    total_makeup = df["Makeup"].sum()
    total_absent = df["Absent"].sum()

    if include_od:
        aggregate_present = total_present + total_od + total_makeup
    else:
        aggregate_present = total_present + total_makeup

    total_classes = total_present + total_absent

    aggregate_attendance = (
        aggregate_present / total_classes * 100
    )

    st.subheader("Overall Summary")

    c1,c2,c3 = st.columns(3)
    c4,c5,c6 = st.columns(3)

    c1.metric("Present", total_present)
    c2.metric("Absent", total_absent)
    c3.metric("Total Classes", total_classes)

    c4.metric("OD", total_od)
    c5.metric("Makeup", total_makeup)
    c6.metric("Aggregate Present", aggregate_present)

    st.metric(
        "Aggregate Attendance %",
        f"{aggregate_attendance:.2f}%"
    )

    # ---------------- PIE ----------------
    plot_attendance_percentage_pie(
        aggregate_present,
        total_classes - aggregate_present
    )

    # ---------------- TARGET ----------------
    st.subheader("🎯 Target Optimizer")

    target = st.number_input(
        "Enter Target %",
        min_value=0,
        max_value=100,
        value=75
    )

    need = classes_needed(
        aggregate_present,
        total_classes,
        target
    )

    leave = classes_can_leave(
        aggregate_present,
        total_classes,
        target
    )

    if aggregate_attendance < target:
        st.warning(f"Attend {need} classes")
    else:
        st.success(f"You can leave {leave} classes")

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
