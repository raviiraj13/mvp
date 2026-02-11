import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import sympy as sp
import math
import re

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Smart Attendance Optimizer",
    layout="wide"
)

# ---------------- THEME ----------------
st.markdown("""
<style>

.stApp {
    background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
    color: white;
}

[data-testid="stMetric"] {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 15px;
}

.stDataFrame {
    background: rgba(255,255,255,0.03);
}

</style>
""", unsafe_allow_html=True)

st.title("🎯 Smart Attendance Optimizer")
st.caption("Supports OD, Makeup, Optimization, and PDF export")

# ---------------- COLORS ----------------
PRESENT_COLOR = "#00FFA3"
ABSENT_COLOR = "#FF4B4B"
OD_COLOR = "#00C8FF"

# ---------------- PARSER ----------------
def smart_parse_pasted_data(text):

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rows = []

    for line in lines:

        if "subject code" in line.lower():
            continue

        parts = line.split("\t")

        if len(parts) < 9:
            continue

        try:

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

        except:
            continue

    if not rows:
        return None

    df = pd.DataFrame(
        rows,
        columns=[
            "Subject",
            "Present",
            "OD",
            "Makeup",
            "Absent"
        ]
    )

    return df


# ---------------- COMPUTE ----------------
def compute_attendance(df):

    df["Effective Present"] = (
        df["Present"] +
        df["OD"] +
        df["Makeup"]
    )

    df["Total"] = (
        df["Present"] +
        df["OD"] +
        df["Makeup"] +
        df["Absent"]
    )

    df["Attendance%"] = (
        df["Effective Present"] /
        df["Total"] * 100
    ).round(2)

    df["Status"] = df["Attendance%"].apply(
        lambda x: "🟢 Safe" if x >= 75 else "🔴 Risk"
    )

    return df.sort_values("Attendance%")


# ---------------- MATH ----------------
def classes_to_attend(present, total, target):

    x = sp.symbols("x")

    sol = sp.solve(
        (present + x)/(total + x) - target/100,
        x
    )

    if sol:
        return max(0, math.ceil(sol[0]))

    return 0


def classes_can_leave(present, total, target):

    leave = 0

    while total + leave > 0 and (present/(total+leave))*100 >= target:

        leave += 1

    return max(0, leave-1)


# ---------------- CHART ----------------
def plot_overall(present, absent, od):

    fig, ax = plt.subplots()

    ax.pie(
        [present, absent, od],
        labels=["Present","Absent","OD"],
        colors=[PRESENT_COLOR, ABSENT_COLOR, OD_COLOR],
        autopct="%1.1f%%"
    )

    ax.set_title("Overall Attendance Distribution")

    st.pyplot(fig)


def plot_subject_chart(df):

    fig, ax = plt.subplots(figsize=(10,4))

    ax.bar(
        df["Subject"],
        df["Attendance%"],
        color=PRESENT_COLOR
    )

    plt.xticks(rotation=60)

    ax.set_ylabel("Attendance %")

    st.pyplot(fig)


# ---------------- PDF ----------------
def generate_pdf(df):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial","B",16)

    pdf.cell(0,10,"Attendance Report",ln=True)

    pdf.set_font("Arial","",12)

    for _,row in df.iterrows():

        pdf.cell(
            0,8,
            f"{row['Subject']} : {row['Attendance%']}%",
            ln=True
        )

    return pdf.output(dest="S").encode("latin-1")


# ---------------- INPUT ----------------
st.subheader("Paste Attendance Report")

pasted = st.text_area("", height=300)

if pasted:

    df = smart_parse_pasted_data(pasted)

    if df is None:

        st.error("Invalid format")

    else:

        df = compute_attendance(df)

        st.subheader("Attendance Table")

        st.dataframe(df, use_container_width=True)

        # ---------------- AGGREGATE ----------------

        total_present = df["Effective Present"].sum()
        total_absent = df["Absent"].sum()
        total_od = df["OD"].sum()

        total = total_present + total_absent

        overall = total_present / total * 100

        st.subheader("Overall Metrics")

        c1,c2,c3 = st.columns(3)

        c1.metric("Attendance %", f"{overall:.2f}")
        c2.metric("Present", total_present)
        c3.metric("Absent", total_absent)

        plot_overall(total_present, total_absent, total_od)

        # ---------------- AGGREGATE OPTIMIZATION ----------------

        st.subheader("Aggregate Optimization")

        target = st.number_input(
            "Target %",
            min_value=0,
            max_value=100,
            value=75
        )

        need = classes_to_attend(
            total_present,
            total,
            target
        )

        leave = classes_can_leave(
            total_present,
            total,
            target
        )

        c1,c2 = st.columns(2)

        c1.success(f"Attend {need} classes")

        c2.warning(f"Can leave {leave} classes")


        # ---------------- SUBJECT OPTIMIZATION ----------------

        st.subheader("Subject Optimization")

        subject = st.selectbox(
            "Select Subject",
            df["Subject"]
        )

        row = df[df["Subject"]==subject].iloc[0]

        need_sub = classes_to_attend(
            row["Effective Present"],
            row["Total"],
            target
        )

        leave_sub = classes_can_leave(
            row["Effective Present"],
            row["Total"],
            target
        )

        c1,c2 = st.columns(2)

        c1.success(f"Attend {need_sub} classes in {subject}")

        c2.warning(f"Can leave {leave_sub} classes in {subject}")


        # ---------------- CHART ----------------

        st.subheader("Subject Chart")

        plot_subject_chart(df)


        # ---------------- PDF ----------------

        st.subheader("Download Report")

        pdf = generate_pdf(df)

        st.download_button(
            "Download PDF",
            pdf,
            "attendance_report.pdf"
        )
