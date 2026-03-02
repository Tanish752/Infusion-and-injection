from datetime import datetime as dt
import streamlit as st

def normalize_time(time_str: str) -> str:
    try:
        dt.strptime(time_str, "%H:%M:%S")
        return time_str
    except ValueError:
        if time_str.isdigit():
            if len(time_str) == 4:
                hours = int(time_str[:2])
                minutes = int(time_str[2:])
                return f"{hours:02d}:{minutes:02d}:00"
            elif len(time_str) == 3:
                hours = int(time_str[:1])
                minutes = int(time_str[1:])
                return f"{hours:02d}:{minutes:02d}:00"
        raise ValueError("Invalid time format. Use HH:MM:SS or shorthand like 930/1000.")

def duration(start_time: str, end_time: str) -> float:
    start_dt = dt.strptime(start_time, "%H:%M:%S")
    end_dt   = dt.strptime(end_time, "%H:%M:%S")
    return (end_dt - start_dt).total_seconds() / 60

st.set_page_config(page_title="Infusion Coding Tool", layout="wide")
st.title("Infusion Coding Tool")

process = st.button("Codes for Infusions")  # always at top

infusion_number = st.number_input("Number of infusions", min_value=1, step=1)

all_times = []
st.markdown("### Enter Infusion Details")
for i in range(infusion_number):
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        drug = st.text_input("Drug name", key=f"drug{i}")
    with col2:
        start_time = st.text_input("Start time (HH:MM:SS or shorthand)", key=f"start{i}")
    with col3:
        end_time = st.text_input("End time (HH:MM:SS or shorthand)", key=f"end{i}")

    if drug and start_time and end_time:
        try:
            dur = duration(normalize_time(start_time), normalize_time(end_time))
            all_times.append(("infusion", drug, start_time, end_time, dur))
        except Exception as e:
            st.error(f"Error in infusion {i+1}: {e}")

if process:
    total_durations = {}
    short_durations = {}
    drug_codes = {}

    for category, drug, start, end, dur in all_times:
        if dur < 16:
            short_durations.setdefault(drug, []).append(dur)
        else:
            total_durations[drug] = total_durations.get(drug, 0) + dur

    previous_drug = None
    primary_done = False

    for drug, total in total_durations.items():
        codes = []
        if not primary_done:
            if total > 31 and total <= 60:
                codes.append("96365")
            else:
                codes.append("96365")
                remaining = int(total) - 60
                full_blocks = remaining // 60
                remainder = remaining % 60
                for _ in range(full_blocks):
                    codes.append("96366")
                if remainder > 30:
                    codes.append("96366")
            primary_done = True
        else:
            codes.append("96367")
            if total > 60:
                remaining = int(total) - 60
                full_blocks = remaining // 60
                remainder = remaining % 60
                for _ in range(full_blocks):
                    codes.append("96366")
                if remainder > 30:
                    codes.append("96366")
        drug_codes[drug] = codes
        previous_drug = drug

    for drug, durations in short_durations.items():
        for dur in durations:
            if dur < 16:
                drug_codes.setdefault(drug, [])
                if "96365" in drug_codes.get(drug, []):
                    drug_codes[drug].append("96376")
                elif primary_done:
                    drug_codes[drug].append("96375")
                else:
                    drug_codes[drug].append("96374")

    st.markdown("## Results")
    st.markdown("### Total Durations (≥16 min)")
    for drug, total in total_durations.items():
        st.write(f"{drug}  -  {total} minutes")

    st.markdown("### Short Durations (<16 min)")
    for drug, durations in short_durations.items():
        for dur in durations:
            st.write(f"{drug}  -  {dur} minutes")

    st.markdown("### Assigned Codes")
    for drug, codes in drug_codes.items():
        st.success(f"{drug}  -  {', '.join(codes)}")
