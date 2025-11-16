import streamlit as st
import pandas as pd
import json
import io
from openpyxl import Workbook
from openpyxl.styles import PatternFill
import os

# Streamlit page configuration
st.set_page_config(layout="wide")
st.title("A-PAG QC LOG Prayagraj")

with st.expander("🛠️ Standard Operating Procedure (SOP) for Quality Check Tool", expanded=False):
    st.markdown("""
    If you face issues while using the tool, follow these steps:  

    ✅ **1. Disable Firewall & Antivirus**  
    - Turn off your system’s firewall and temporarily disable Windows Defender/Antivirus.  

    ✅ **2. Check Network Settings**  
    - Switch to a *public network* if using a private one.  

    ✅ **3. Ensure Stable Internet**  
    - Verify your *internet speed* is stable.  

    ✅ **4. Check Server Status**  
    - Ensure the *dashboard server is operational*.  

    ✅ **5. Prevent Data Loss**  
    - **Enable "Save My Responses"** to avoid data loss.  
    - **Download responses** regularly, especially before breaks or shutting down your device.  

    For further assistance, contact **Rishabh Chaturvedi** at **rishabh.c@a-pag.org** or **9873695374**.
    """)

# File uploader
uploaded_file = st.file_uploader(
    "Upload your CSV or Excel file (the report Excel with metadata header rows)",
    type=["csv", "xlsx", "xls"]
)

# Feedback file
FEEDBACK_FILE = "feedback_data_prayagraj.json"

if not os.path.exists(FEEDBACK_FILE):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump({}, f)

if "feedback" not in st.session_state:
    try:
        with open(FEEDBACK_FILE, "r") as f:
            st.session_state.feedback = json.load(f)
    except:
        st.session_state.feedback = {}

ROWS_PER_PAGE = 10
if "page" not in st.session_state:
    st.session_state.page = 0

disapproval_reasons = [
    "After Photo-Missing",
    "After Photo-Wrong/Blurry",
    "Incomplete Work/Work Not Started",
    "Image taken from wrong angle"
]


# ---------- HEADER DETECTION ----------
def detect_header_row_excel(path_or_buffer, max_scan_rows=20):
    try:
        temp = pd.read_excel(path_or_buffer, header=None, nrows=max_scan_rows)
    except:
        try:
            path_or_buffer.seek(0)
            temp = pd.read_excel(path_or_buffer, header=None, nrows=max_scan_rows)
        except:
            return 5
    for i in range(min(max_scan_rows, len(temp))):
        row_vals = temp.iloc[i].astype(str).str.strip().tolist()
        if any(v.lower() == "complaint number" for v in row_vals if v):
            return i
    return 5


def read_input_file(uploaded):
    try: uploaded.seek(0)
    except: pass

    if uploaded.name.lower().endswith((".xlsx", ".xls")):
        row = detect_header_row_excel(uploaded)
        try: uploaded.seek(0)
        except: pass
        df = pd.read_excel(uploaded, header=row)

    else:  # CSV
        try: uploaded.seek(0)
        except: pass
        preview = pd.read_csv(uploaded, nrows=10)
        if any(str(c).lower().startswith("unnamed") for c in preview.columns):
            try: uploaded.seek(0)
            except: pass
            df = pd.read_csv(uploaded, header=5)
        else:
            uploaded.seek(0)
            df = pd.read_csv(uploaded)

    df.columns = df.columns.astype(str).str.strip()
    return df


# ---------- REQUIRED COLUMNS ----------
REQUIRED_COLS = {
    "Complaint Number",
    "Zone",
    "Ward",
    "Complaint Sub type",
    "Address",
    "Surveyor Name",
    "Complaint Description",
    "Upload Documents",
    "Resolved Documents",
    "Registration Location"
}


# ---------- MAIN ----------
if uploaded_file:
    df = read_input_file(uploaded_file)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        st.error(f"Your file is missing required columns: {missing}")
        st.stop()

    # Filters
    zone = st.selectbox("Filter by Zone", ["All"] + df["Zone"].dropna().unique().tolist())
    ward = st.selectbox("Filter by Ward", ["All"] + df["Ward"].dropna().unique().tolist())
    subtype = st.selectbox("Filter by Complaint Sub type", ["All"] + df["Complaint Sub type"].dropna().unique().tolist())

    filtered = df.copy()
    if zone != "All": filtered = filtered[filtered["Zone"] == zone]
    if ward != "All": filtered = filtered[filtered["Ward"] == ward]
    if subtype != "All": filtered = filtered[filtered["Complaint Sub type"] == subtype]

    total_pages = (len(filtered) + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE
    if st.session_state.page >= total_pages:
        st.session_state.page = 0

    start = st.session_state.page * ROWS_PER_PAGE
    end = start + ROWS_PER_PAGE
    df_page = filtered.iloc[start:end]

    # ----------- LIVE SUMMARY -----------
    status_counts = {s: 0 for s in [
        "Status Yet to be Updated",
        "Not Reviewed(Incorrect Before/Poor Identification)",
        "Correct",
        "Incorrect"
    ]}

    for pid in filtered["Complaint Number"].astype(str):
        status = st.session_state.feedback.get(pid, {}).get("Quality", "Status Yet to be Updated")
        status_counts[status] += 1

    with st.sidebar:
        st.subheader("Review Summary 📊")
        for k, v in status_counts.items():
            st.write(f"**{k}:** {v}")

        correct = status_counts["Correct"]
        incorrect = status_counts["Incorrect"]
        reviewed = correct + incorrect
        total = reviewed + status_counts["Not Reviewed(Incorrect Before/Poor Identification)"] + status_counts["Status Yet to be Updated"]

        if reviewed > 0:
            st.write(f"**Current QC Status %:** {correct * 100 / reviewed:.2f}%")
        else:
            st.write("**Current QC Status %:** 0.00%")

        if total > 0:
            st.write(f"**Current Sample Size %:** {reviewed * 100 / total:.2f}%")
        else:
            st.write("**Current Sample Size %:** 0.00%")

        st.write(f"**QC Done:** {reviewed}")

    # ----------- DISPLAY ROWS -----------
    for _, row in df_page.iterrows():
        pid = str(row["Complaint Number"])
        subtype = row["Complaint Sub type"]
        zone = row["Zone"]
        ward = row["Ward"]
        address = row["Address"]
        surveyor = row["Surveyor Name"]
        description = row["Complaint Description"]
        regloc = row["Registration Location"]
        pre_img = row["Upload Documents"]
        post_img = row["Resolved Documents"]

        st.subheader(f"Complaint Number: {pid} | Sub type: {subtype}")
        st.text(f"Zone: {zone} | Ward: {ward} | Surveyor: {surveyor} | Address: {address}")
        st.write(f"**Complaint Description:** {description}")
        st.write(f"**Registration Location:** {regloc}")

        c1, c2 = st.columns(2)
        with c1:
            if str(pre_img).strip():
                st.markdown(
                    f'<img src="{pre_img}" style="width:500px;height:400px;object-fit:cover;border:1px solid #ccc;">',
                    unsafe_allow_html=True
                )
            else:
                st.warning("No Pre Image Provided")

        with c2:
            if str(post_img).strip():
                st.markdown(
                    f'<img src="{post_img}" style="width:500px;height:400px;object-fit:cover;border:1px solid #ccc;">',
                    unsafe_allow_html=True
                )
            else:
                st.warning("No Post Image Provided")

        saved = st.session_state.feedback.get(pid, {}).get("Quality", "Status Yet to be Updated")

        status = st.radio(
            f"Status for Complaint Number {pid}",
            ["Status Yet to be Updated", "Not Reviewed(Incorrect Before/Poor Identification)", "Correct", "Incorrect"],
            index=["Status Yet to be Updated",
                   "Not Reviewed(Incorrect Before/Poor Identification)",
                   "Correct",
                   "Incorrect"].index(saved)
        )

        saved_reason = st.session_state.feedback.get(pid, {}).get("comment", "")
        reason = ""
        if status == "Incorrect":
            reason = st.selectbox(
                f"Reason for Disapproval (ID {pid})",
                disapproval_reasons,
                index=disapproval_reasons.index(saved_reason) if saved_reason in disapproval_reasons else 0
            )

        st.session_state.feedback[pid] = {
            "Quality": status,
            "comment": reason if status == "Incorrect" else ""
        }

    # ----------- PAGINATION -----------
    st.markdown(f"**Page {st.session_state.page + 1} of {total_pages}**")

    p1, p2, p3 = st.columns([1, 6, 1])
    with p1:
        if st.session_state.page > 0:
            if st.button("⬅️ Previous Page"):
                st.session_state.page -= 1
                st.rerun()

    with p2:
        pass

    with p3:
        if st.session_state.page < total_pages - 1:
            if st.button("Next Page ➡️"):
                st.session_state.page += 1
                st.rerun()

    # ----------- SAVE RESPONSES -----------
    if st.button("Save My Responses"):
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(st.session_state.feedback, f)
        st.success("Responses Saved!")

    # ----------- EXPORT EXCEL -----------
    def create_excel_download(df_in):
        wb = Workbook()
        ws = wb.active
        headers = df_in.columns.tolist()
        ws.append(headers + ["Review Status", "Comments"])

        total_cols = len(headers) + 2

        for i, (_, r) in enumerate(df_in.iterrows(), start=1):
            pid = str(r["Complaint Number"])
            fb = st.session_state.feedback.get(pid, {})
            status = fb.get("Quality", "Status Yet to be Updated")
            comment = fb.get("comment", "")

            ws.append(r.tolist() + [status, comment])

            fill = {
                "Correct": "00FF00",
                "Incorrect": "FF0000",
                "Not Reviewed(Incorrect Before/Poor Identification)": "FFFF00",
            }.get(status, "FFFFFF")

            for c in range(1, total_cols + 1):
                ws.cell(row=i + 1, column=c).fill = PatternFill(start_color=fill, end_color=fill, fill_type="solid")

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    if st.button("Download Excel"):
        excel_buf = create_excel_download(filtered)
        st.download_button(
            "Download the Excel file",
            excel_buf,
            "qc_log_prayagraj.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
