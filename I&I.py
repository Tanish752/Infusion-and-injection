import streamlit as st
from datetime import datetime as dt

def normalize_datetime(date_str: str, time_str: str) -> dt:
    try:
        time_obj = dt.strptime(time_str, "%H:%M:%S").time()
    except ValueError:
        if time_str.isdigit():
            if len(time_str) == 4:  # e.g. "0930"
                hours = int(time_str[:2])
                minutes = int(time_str[2:])
            elif len(time_str) == 3:  # e.g. "930"
                hours = int(time_str[:1])
                minutes = int(time_str[1:])
            else:
                raise ValueError("Invalid shorthand time format.")
            time_obj = dt.strptime(f"{hours:02d}:{minutes:02d}:00", "%H:%M:%S").time()
        else:
            raise ValueError("Invalid time format. Use HH:MM:SS or shorthand like 930/1000.")
    date_obj = dt.strptime(date_str, "%Y-%m-%d").date()
    return dt.combine(date_obj, time_obj)

def duration(start_dt: dt, end_dt: dt) -> float:
    return (end_dt - start_dt).total_seconds() / 60

st.set_page_config(page_title="Infusion Coding Tool", layout="wide")
st.title("Infusion Coding Tool")

process = st.button("Codes for Infusions")
infusion_number = st.number_input("Number of infusions", min_value=1, step=1)

all_times = []
st.markdown("### Enter Infusion Details")

for i in range(infusion_number):
    st.subheader(f"Infusion {i+1}")
    col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 2])
    with col1:
        drug = st.text_input("Drug name", key=f"drug{i}")
    with col2:
        start_date = st.date_input("Start Date", key=f"start_date{i}").strftime("%Y-%m-%d")
    with col3:
        start_time = st.text_input("Start time (HH:MM:SS or shorthand)", key=f"start{i}")
    with col4:
        end_date = st.date_input("End Date", key=f"end_date{i}").strftime("%Y-%m-%d")
    with col5:
        end_time = st.text_input("End time (HH:MM:SS or shorthand)", key=f"end{i}")

    if drug and start_time and end_time:
        try:
            start_dt = normalize_datetime(start_date, start_time)
            end_dt   = normalize_datetime(end_date, end_time)
            dur = duration(start_dt, end_dt)
            all_times.append(("infusion", drug, start_dt, end_dt, dur))
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
drug_codes = {}
skipped_infusions = []

previous_drug = None
previous_end = None
primary_done = False

for category, drug, start, end, dur in all_times:
    codes = []

    # --- Case 1: First primary infusion ---
    if not primary_done:
        if 31 < dur <= 60:
            codes.append("96365")
        elif dur > 60:
            codes.append("96365")
            remaining = int(dur) - 60
            full_blocks = remaining // 60
            remainder = remaining % 60
            for _ in range(full_blocks):
                codes.append("96366")
            if remainder > 30:
                codes.append("96366")
        primary_done = True

    # --- Case 2: Same drug repeated within 30 minutes ---
    elif previous_drug == drug and previous_end and (start - previous_end).total_seconds() / 60 < 30:
        if (end - previous_end).total_seconds() / 60 > 30:
            codes.append("96366")  # continuation if overlap >30 min
        else:
            skipped_infusions.append(
                f"No code for {drug} since repeated within 30 minutes "
                f"({start.strftime('%Y-%m-%d %H:%M:%S')} → {end.strftime('%Y-%m-%d %H:%M:%S')})"
            )
            previous_drug = drug
            previous_end = end
            continue

    # --- Case 3: Subsequent infusions ---
    else:
        codes.append("96367")
        if dur > 60:
            remaining = int(dur) - 60
            full_blocks = remaining // 60
            remainder = remaining % 60
             if not primary_done:
        if 31 < dur <= 60:
            codes.append("96365")
        elif dur > 60:
            codes.append("96365")
            remaining = int(dur) - 60
            full_blocks = remaining // 60
            remainder = remaining % 60
            units = full_blocks
			if remainder > 30:
			    units += 1
			if units > 0:
			    codes.append(f"96366*{units}")

        primary_done = True

    # ✅ Append codes instead of overwriting
    drug_codes.setdefault(drug, []).extend(codes)
    previous_drug = drug
    previous_end = end        
        

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
st.markdown("### Infusion Summary")
for category, drug, start, end, dur in all_times:
    adjusted_dur = dur
    note = ""

    # If same drug and overlap exists → subtract overlap
    if previous_drug == drug and previous_end and start < previous_end:
        overlap = (previous_end - start).total_seconds() / 60
        adjusted_dur = dur - overlap
        if adjusted_dur < 0:
            adjusted_dur = 0
        note = " (rest included in previous infusion)"

    st.write(
        f"{drug}: {start.strftime('%Y-%m-%d %H:%M:%S')} → "
        f"{end.strftime('%Y-%m-%d %H:%M:%S')} | {adjusted_dur:.2f} minutes{note}"
    )

    previous_drug = drug
    previous_end = end


st.markdown("### Assigned Codes")
for drug, codes in drug_codes.items():
    st.success(f"{drug} - {', '.join(codes)}")

for skipped in skipped_infusions:
    st.warning(skipped)


