import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import sympy as sp
import math
import re

# ---------------- Page Config ----------------
st.set_page_config(page_title="Attendance Tracker", layout="wide")
st.title("📊 Attendance Tracker (Makeup + OD Supported)")
st.caption("Paste attendance data from your college portal")

# ---------------- COLORS ----------------
PRESENT_COLOR = "#1ABC9C"
ABSENT_COLOR  = "#F39C12"
BAR_COLORS    = ["#1ABC9C", "#16A085", "#2ECC71", "#F39C12", "#E67E22"]

# ---------------- PDF SAFE ----------------
def clean_text(text):
    return text.encode("latin-1", "ignore").decode("latin-1")

# ---------------- RECALCULATE ----------------
def recalculate_attendance(df):

    df["Effective Present"] = (
        df["Present"] +
        df["Makeup"] +
        df["OD"]
    )

    df["Total"] = (
        df["Present"] +
        df["Absent"] +
        df["Makeup"] +
        df["OD"]
    )

    df["Attendance%"] = df.apply(
        lambda r: (
            r["Effective Present"] /
            r["Total"] * 100
        ) if r["Total"] else 0,
        axis=1
    )

    df["Status"] = df["Attendance%"].apply(
        lambda x: "🟢" if x >= 75 else "🔴"
    )

    return df.sort_values("Attendance%")

# ---------------- PARSER ----------------
def smart_parse_pasted_data(text):

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rows = []

    for line in lines:

        parts = line.split("\t") if "\t" in line else re.split(r"\s{2,}", line)
        joined = " ".join(parts).lower()

        if "present" in joined and "absent" in joined:
            continue

        try:

            if len(parts) >= 9:

                subject = " ".join(parts[2:-6])
                present = int(parts[-5])
                absent = int(parts[-2])

            elif len(parts) == 3:

                subject, present, absent = parts
                present, absent = int(present), int(absent)

            else:
                continue

            rows.append([subject.strip(), present, absent, 0, 0])

        except:
            continue

    if not rows:
        raise ValueError("No valid attendance rows found")

    df = pd.DataFrame(
        rows,
        columns=["Subject", "Present", "Absent", "Makeup", "OD"]
    )

    return recalculate_attendance(df)

# ---------------- MATH ----------------
def classes_to_attend(present, total, target):

    x = sp.symbols("x")

    sol = sp.solve(
        (present + x) / (total + x) - target / 100,
        x
    )

    return max(0, math.ceil(sol[0])) if sol else 0


def classes_can_leave(present, total, target):

    if total == 0:
        return 0

    leave = 0

    while (present / (total + leave)) * 100 >= target:
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
        startangle=90,
        wedgeprops={"edgecolor": "white"}
    )

    plt.title("Aggregate Attendance")

    st.pyplot(plt)
    plt.close()


def plot_bar_chart(df):

    plt.figure(figsize=(9,4))

    colors = BAR_COLORS * (len(df)//len(BAR_COLORS) + 1)

    plt.bar(
        df["Subject"],
        df["Effective Present"],
        color=colors[:len(df)]
    )

    plt.xticks(rotation=60, ha="right")

    plt.ylabel("Effective Present Classes")
    plt.title("Attendance per Subject")

    st.pyplot(plt)
    plt.close()


def plot_subject_pie(subject, present, absent):

    plt.figure(figsize=(5,5))

    plt.pie(
        [present, absent],
        labels=["Present", "Absent"],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        startangle=90,
        wedgeprops={"edgecolor": "white"}
    )

    plt.title(subject)

    st.pyplot(plt)
    plt.close()


def plot_donut_charts(df):

    cols = 3
    rows = (len(df) + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(9, rows * 3.8))

    axes = axes.flatten()

    for i, ax in enumerate(axes):

        if i >= len(df):
            ax.axis("off")
            continue

        r = df.iloc[i]

        ax.pie(
            [r["Effective Present"], r["Absent"]],
            colors=[PRESENT_COLOR, ABSENT_COLOR],
            startangle=90,
            wedgeprops={"width": 0.35, "edgecolor": "white"}
        )

        ax.text(
            0, 0,
            f"{r['Attendance%']:.0f}%",
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold"
        )

        title = r["Subject"]

        if len(title) > 22:

            mid = len(title) // 2
            split_at = title.rfind(" ", 0, mid)

            if split_at != -1:
                title = title[:split_at] + "\n" + title[split_at+1:]

        ax.set_title(title, fontsize=9, pad=12)

    plt.tight_layout(pad=2.5)

    st.pyplot(fig)
    plt.close()

# ---------------- PDF ----------------
def generate_pdf(df, total_present, total_absent):

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 18)

    pdf.cell(
        0,
        10,
        clean_text("Attendance Report"),
        ln=True,
        align="C"
    )

    total = total_present + total_absent

    overall = (
        total_present / total
    ) * 100 if total else 0

    pdf.ln(6)

    pdf.set_font("Arial", "", 12)

    pdf.cell(
        0,
        7,
        clean_text(f"Overall Attendance: {overall:.1f}%"),
        ln=True
    )

    pdf.ln(6)

    pdf.set_font("Arial", "B", 14)

    pdf.cell(
        0,
        8,
        clean_text("Subject-wise Attendance"),
        ln=True
    )

    pdf.set_font("Arial", "", 11)

    for _, r in df.iterrows():

        pdf.cell(
            0,
            6,
            clean_text(
                f"{r['Subject']} - {r['Attendance%']:.1f}% "
                f"(Makeup: {r['Makeup']}, OD: {r['OD']})"
            ),
            ln=True
        )

    return pdf.output(dest="S").encode("latin-1")

# ---------------- INPUT ----------------
pasted = st.text_area(
    "📋 Paste attendance data",
    height=300
)

df = None

if pasted.strip():

    try:

        df = smart_parse_pasted_data(pasted)

        st.success("✅ Attendance uploaded successfully")

    except Exception as e:

        st.error("❌ Upload failed")
        st.code(str(e))

# ---------------- OUTPUT ----------------
if df is not None:

    st.subheader("📋 Add Makeup / OD Classes")

    for i in df.index:

        col1, col2 = st.columns(2)

        with col1:

            df.at[i, "Makeup"] = st.number_input(
                f"Makeup for {df.at[i,'Subject']}",
                min_value=0,
                step=1,
                key=f"makeup{i}"
            )

        with col2:

            df.at[i, "OD"] = st.number_input(
                f"OD for {df.at[i,'Subject']}",
                min_value=0,
                step=1,
                key=f"od{i}"
            )

    df = recalculate_attendance(df)

    st.subheader("📋 Attendance Overview")

    st.dataframe(df)

    total_present = df["Effective Present"].sum()
    total_absent = df["Absent"].sum()

    total_classes = total_present + total_absent

    overall = (
        total_present / total_classes
    ) * 100 if total_classes else 0

    c1, c2, c3 = st.columns(3)

    c1.metric("Present", total_present)
    c2.metric("Absent", total_absent)
    c3.metric("Overall %", f"{overall:.1f}")

    plot_aggregate_pie(total_present, total_absent)

    # ---------------- TARGET ----------------
    st.markdown("## 🎯 Target Aggregate Attendance")

    target = st.number_input(
        "Target %",
        0,
        100,
        75
    )

    if target > overall:

        need = classes_to_attend(
            total_present,
            total_classes,
            target
        )

        st.warning(
            f"Attend {need} more classes "
            f"(Makeup or Regular)"
        )

    else:

        leave = classes_can_leave(
            total_present,
            total_classes,
            target
        )

        st.success(
            f"You can leave {leave} classes safely"
        )

    # ---------------- SUBJECT ----------------
    st.markdown("## 🎯 Subject Target")

    subject = st.selectbox(
        "Select subject",
        df["Subject"]
    )

    row = df[df["Subject"] == subject].iloc[0]

    need = classes_to_attend(
        row["Effective Present"],
        row["Total"],
        target
    )

    leave = classes_can_leave(
        row["Effective Present"],
        row["Total"],
        target
    )

    st.info(
        f"{subject}: Attend {need} more | Can leave {leave}"
    )

    # ---------------- CHARTS ----------------
    st.markdown("## 📈 Visual Insights")

    plot_subject_pie(
        subject,
        row["Effective Present"],
        row["Absent"]
    )

    plot_bar_chart(df)

    plot_donut_charts(df)

    # ---------------- PDF ----------------
    st.markdown("## 📄 Download Report")

    pdf = generate_pdf(
        df,
        total_present,
        total_absent
    )

    st.download_button(
        "Download PDF",
        pdf,
        file_name="attendance_report.pdf",
        mime="application/pdf"
    )
