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
            if dur < 0:
                raise ValueError("End time is before start time.")
            all_times.append(("infusion", drug, start_dt, end_dt, dur))
        except Exception as e:
            st.error(f"Error in infusion {i+1}: {e}")

if process:
    if not all_times:
        st.info("Please enter at least one valid infusion to process.")
    else:
        # Sort infusions chronologically by start time to make comparisons reliable
        all_times.sort(key=lambda x: x[2])

        total_durations = {}   # dict[str, float] (not strictly required but kept from your original structure)
        short_durations = {}   # dict[str, list[float]]
        drug_codes = {}        # dict[str, list[str]]
        skipped_infusions = []

        # Collect short and total durations first
        for _, drug, _, _, dur in all_times:
            if dur < 16:
                short_durations.setdefault(drug, []).append(dur)
            else:
                total_durations[drug] = total_durations.get(drug, 0) + dur

        previous_drug = None
        previous_end = None
        previous_start = None
        primary_done = False

        # Main coding loop
        for _, drug, start, end, dur in all_times:
            codes = []

            if dur < 16:
                # Handle these after the main loop (96374/96375/96376 logic)
                pass
            else:
                # --- Case 1: First primary infusion ---
                if not primary_done:
                    if 31 < dur <= 60:
                        codes.append("96365")
                    elif dur > 60:
                        codes.append("96365")
                        remaining = int(dur) - 60
                        full_blocks = remaining // 60
                        remainder = remaining % 60
                        # Add 96366 for each additional hour
                        codes.extend(["96366"] * full_blocks)
                        if remainder > 30:
                            codes.append("96366")
                    primary_done = True

                # --- Case 2: Same drug repeated within 30 minutes ---
                elif (
                    previous_drug == drug
                    and previous_start is not None
                    and previous_end is not None
                    and start >= previous_start
                    and (start - previous_end).total_seconds() / 60 < 30
                ):
                    if (end - previous_end).total_seconds() / 60 > 30 and dur > 30:
                        codes.append("96366")  # continuation if overlap > 30 min
                    else:
                        skipped_infusions.append(
                            f"No code for {drug} since repeated within 30 minutes "
                            f"({start.strftime('%Y-%m-%d %H:%M:%S')} → {end.strftime('%Y-%m-%d %H:%M:%S')})"
                        )
                        # update trackers and skip adding codes this round
                        previous_drug = drug
                        previous_end = end
                        previous_start = start
                        drug_codes.setdefault(drug, []).extend(codes)
                        continue

                # --- Case 3: New drug (one-time 96368 by your rule) ---
                elif drug != previous_drug and "96368" not in drug_codes.get(drug, []) and previous_start < start < previous_stop :
                    codes.append("96368")

                # --- Case 4: Subsequent infusions (different logic path) ---
                else:
                    codes.append("96367")
                    if dur > 60:
                        remaining = int(dur) - 60
                        full_blocks = remaining // 60
                        remainder = remaining % 60
                        units = full_blocks + (1 if remainder > 30 else 0)
                        if units > 0:
                            codes.append(f"96366*{units}")

            # Append codes for this infusion
            drug_codes.setdefault(drug, []).extend(codes)
            previous_drug = drug
            previous_end = end
            previous_start = start

        # Now handle short infusions (<16 min)
        for sdrug, durations in short_durations.items():
            for sdur in durations:
                # Ensure the key exists
                drug_codes.setdefault(sdrug, [])
                if "96365" in drug_codes.get(sdrug, []):
                    drug_codes[sdrug].append("96376")
                elif primary_done:
                    drug_codes[sdrug].append("96375")
                else:
                    drug_codes[sdrug].append("96374")

        # ---------- OUTPUT ----------
        st.markdown("## Results")

        st.markdown("### Infusion Summary")
        # Reset trackers for summary overlap calculation
        prev_drug = None
        prev_end = None
        for _, drug, start, end, dur in all_times:
            adjusted_dur = dur
            note = ""
            # If same drug and overlap exists → subtract overlap
            if prev_drug == drug and prev_end and start < prev_end:
                overlap = (prev_end - start).total_seconds() / 60
                adjusted_dur = max(0, dur - overlap)
                note = " (rest included in previous infusion)"
            st.write(
                f"{drug}: {start.strftime('%Y-%m-%d %H:%M:%S')} → "
                f"{end.strftime('%Y-%m-%d %H:%M:%S')} | {adjusted_dur:.2f} minutes{note}"
            )
            prev_drug = drug
            prev_end = end

        st.markdown("### Assigned Codes")
        if drug_codes:
            for d, codes in drug_codes.items():
                st.success(f"{d} - {', '.join(codes)}")
        else:
            st.info("No codes assigned.")

        for skipped in skipped_infusions:
            st.warning(skipped)
