import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import sympy as sp
import math
import re

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Attendance Tracker",
    layout="wide"
)

st.title("📊 Attendance Tracker")
st.caption("Auto-detects Present, OD, Makeup, Absent from portal data")

# ---------------- COLORS ----------------
PRESENT_COLOR = "#1ABC9C"
ABSENT_COLOR = "#F39C12"
BAR_COLORS = ["#1ABC9C", "#16A085", "#2ECC71", "#F39C12", "#E67E22"]

# ---------------- PDF SAFE ----------------
def clean_text(text):
    return text.encode("latin-1", "ignore").decode("latin-1")

# ---------------- RECALCULATE ----------------
def recalculate_attendance(df):

    df["Effective Present"] = (
        df["Present"]
        + df["OD"]
        + df["Makeup"]
        + df["Extra OD"]
        + df["Extra Makeup"]
    )

    df["Total"] = (
        df["Present"]
        + df["Absent"]
        + df["OD"]
        + df["Makeup"]
        + df["Extra OD"]
        + df["Extra Makeup"]
    )

    df["Attendance%"] = df.apply(
        lambda r:
        (r["Effective Present"] / r["Total"] * 100)
        if r["Total"] > 0 else 0,
        axis=1
    )

    df["Attendance%"] = df["Attendance%"].round(2)

    df["Status"] = df["Attendance%"].apply(
        lambda x: "🟢" if x >= 75 else "🔴"
    )

    return df.sort_values("Attendance%")

# ---------------- PARSER ----------------
def parse_portal_data(text):

    rows = []

    for line in text.splitlines():

        parts = re.split(r"\t+", line.strip())

        if len(parts) >= 9 and parts[0].isdigit():

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
                0,   # Extra OD
                0    # Extra Makeup
            ])

    if not rows:
        raise ValueError("No valid attendance rows found")

    df = pd.DataFrame(rows, columns=[
        "Subject",
        "Present",
        "OD",
        "Makeup",
        "Absent",
        "Extra OD",
        "Extra Makeup"
    ])

    return recalculate_attendance(df)

# ---------------- MATH ----------------
def classes_to_attend(present, total, target):

    x = sp.symbols("x")

    solution = sp.solve(
        (present + x)/(total + x) - target/100,
        x
    )

    if solution:
        return max(0, math.ceil(solution[0]))

    return 0


def classes_can_leave(present, total, target):

    leave = 0

    while total + leave > 0 and (
        present / (total + leave) * 100 >= target
    ):
        leave += 1

    return max(0, leave - 1)

# ---------------- CHARTS ----------------
def plot_aggregate_pie(present, absent):

    plt.figure(figsize=(5,5))

    plt.pie(
        [present, absent],
        labels=["Present", "Absent"],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        startangle=90
    )

    plt.title("Aggregate Attendance")

    st.pyplot(plt)
    plt.close()


def plot_bar_chart(df):

    plt.figure(figsize=(10,4))

    colors = BAR_COLORS * (len(df)//len(BAR_COLORS) + 1)

    plt.bar(
        df["Subject"],
        df["Effective Present"],
        color=colors[:len(df)]
    )

    plt.xticks(rotation=60, ha="right")

    plt.title("Effective Present Classes")

    st.pyplot(plt)
    plt.close()


def plot_subject_pie(subject, present, absent):

    plt.figure(figsize=(5,5))

    plt.pie(
        [present, absent],
        labels=["Present", "Absent"],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR]
    )

    plt.title(subject)

    st.pyplot(plt)
    plt.close()

# ---------------- PDF ----------------
def generate_pdf(df, total_present, total_absent):

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0,10,"Attendance Report", ln=True)

    total = total_present + total_absent

    overall = (
        total_present / total * 100
        if total else 0
    )

    pdf.set_font("Arial","",12)

    pdf.cell(
        0,10,
        clean_text(
            f"Overall Attendance: {overall:.2f}%"
        ),
        ln=True
    )

    pdf.ln(5)

    for _, row in df.iterrows():

        pdf.cell(
            0,8,
            clean_text(
                f"{row['Subject']} : "
                f"{row['Attendance%']}% "
                f"(OD:{row['OD']} Makeup:{row['Makeup']})"
            ),
            ln=True
        )

    return pdf.output(dest="S").encode("latin-1")

# ---------------- INPUT ----------------
pasted = st.text_area(
    "📋 Paste Attendance Report",
    height=300
)

df = None

if pasted:

    try:

        df = parse_portal_data(pasted)

        st.success("✅ Attendance detected successfully")

    except Exception as e:

        st.error("❌ Failed to parse attendance")
        st.code(str(e))

# ---------------- OUTPUT ----------------
if df is not None:

    st.subheader("📋 Attendance Overview")

    st.dataframe(df)

    # -------- EXTRA OD / MAKEUP --------
    st.subheader("➕ Add Extra OD / Makeup (Optional)")

    for i in df.index:

        col1, col2 = st.columns(2)

        df.at[i, "Extra OD"] = col1.number_input(
            f"Extra OD for {df.at[i,'Subject']}",
            min_value=0,
            step=1,
            key=f"extra_od_{i}"
        )

        df.at[i, "Extra Makeup"] = col2.number_input(
            f"Extra Makeup for {df.at[i,'Subject']}",
            min_value=0,
            step=1,
            key=f"extra_makeup_{i}"
        )

    df = recalculate_attendance(df)

    st.subheader("📋 Updated Attendance")

    st.dataframe(df)

    # -------- AGGREGATE --------
    total_present = df["Effective Present"].sum()
    total_absent = df["Absent"].sum()

    total_classes = total_present + total_absent

    overall = (
        total_present / total_classes * 100
        if total_classes else 0
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("Present", total_present)
    c2.metric("Absent", total_absent)
    c3.metric("Overall %", f"{overall:.2f}")

    plot_aggregate_pie(
        total_present,
        total_absent
    )

    # -------- TARGET --------
    st.subheader("🎯 Target Attendance")

    target = st.number_input(
        "Enter target %",
        0,
        100,
        75
    )

    if overall < target:

        need = classes_to_attend(
            total_present,
            total_classes,
            target
        )

        st.warning(
            f"Attend {need} more classes"
        )

    else:

        leave = classes_can_leave(
            total_present,
            total_classes,
            target
        )

        st.success(
            f"You can leave {leave} classes"
        )

    # -------- SUBJECT --------
    st.subheader("🎯 Subject Analysis")

    subject = st.selectbox(
        "Select Subject",
        df["Subject"]
    )

    row = df[df["Subject"] == subject].iloc[0]

    plot_subject_pie(
        subject,
        row["Effective Present"],
        row["Absent"]
    )

    plot_bar_chart(df)

    # -------- PDF --------
    st.subheader("📄 Download Report")

    pdf = generate_pdf(
        df,
        total_present,
        total_absent
    )

    st.download_button(
        "Download PDF",
        pdf,
        "attendance_report.pdf",
        mime="application/pdf"
    )
