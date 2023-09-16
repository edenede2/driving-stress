import streamlit as st
import pandas as pd
import re
import base64
import numpy as np
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.styles import PatternFill

HIGHLIGHT_VALUES = {
    'A': [1592, 2923, 3082, 3500, 3940, 4705, 5053, 4430, 6580],
    'B': [1032, 1980, 2661, 3250, 4332, 5560, 5845, 5945, 6487, 7850],
    'C': [670, 1300, 2513, 3457, 4107, 4390, 5037, 5358, 6484]
}
def process_raw_file_for_streamlit(txt_file_path, original_file_name):
    structured_data = extract_structured_data_v6(txt_file_path)
    df_sorted = construct_dataframe_optimized_v2_refined(txt_file_path, structured_data, original_file_name)
    return df_sorted

def save_as_xlsx_with_highlight_refined(df, scenario):
    """
    Save the DataFrame as an XLSX file and highlight rows based on Distm values and scenario.
    Also, updates the Event column based on highlighted rows.
    """
    # Define the fill pattern for highlighting
    highlight_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    
    numeric_columns = ['Time', 'Velm', 'Distm', 'Xm', 'IncVm', 'IncRm', 'WheeleAng', 'ThrAcce', 'BrakAcce', 'TL', 'Crashes']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce', downcast='float')

    with pd.ExcelWriter("sorted_data.xlsx", engine='openpyxl') as writer:
        # Write the DataFrame to XLSX
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        # Get the workbook and sheet for further editing
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        # Iterate over the rows to highlight rows with an 'Event'
        for row_idx, row in enumerate(worksheet.iter_rows(min_row=2, max_row=worksheet.max_row), start=1):
            event_value = worksheet.cell(row=row_idx, column=4).value
            if event_value:  # If there's an event value, highlight the row
                for cell in row:
                    cell.fill = highlight_fill
                    
    return "sorted_data.xlsx"

# "save_as_xlsx_with_highlight_refined"



# Extract structured data from raw file
def extract_structured_data_v6(txt_file_path):
    structured_data = []
    start_reading = False
    skip_count = 2  # Number of lines to skip after the "Block #1: output_data," line
    short_line_count = 0  # Counter to track consecutive short lines
    
    # Open the txt file and read lines
    with open(txt_file_path, 'r', errors='ignore') as f:
        for line in f:
            # If the line contains "Block #1: output_data,", prepare to start reading the structured data
            if "Block #1:   output_data," in line:
                start_reading = True
                continue  # skip the current line
            
            # If we've started reading
            if start_reading:
                # Skip the next two lines after "Block #1: output_data,"
                if skip_count > 0:
                    skip_count -= 2
                    continue

                # If the line has a reasonable length (indicative of structured data)
                if len(line) > 100:
                    structured_data.append(line.strip())
                    short_line_count = 0  # Reset the short line counter
                else:
                    short_line_count += 1  # Increment the short line counter
                
                    # If we encounter two consecutive short lines, stop the extraction
                    if short_line_count >= 2:
                        break
    
    return structured_data

# Determine the header for the sorted data based on the 5th row of the txt file
def determine_header(txt_file_path):
    with open(txt_file_path, 'r', errors='ignore') as f:
        for _ in range(4):  # skip the first 4 lines
            next(f)
        fifth_line = f.readline().strip()

    if "Scenario1\Scenario1 - Copy.txt" in fifth_line:
        return pd.read_csv("TestA.csv")
    elif "Senario2\Scenario2.txt" in fifth_line:
        return pd.read_csv("TestB.csv")
    elif "Scenario3\Scenario3.txt" in fifth_line:
        return pd.read_csv("TestC.csv")

    else:
        raise ValueError("Unrecognized scenario in file.")

# Construct and populate the dataframe
def construct_dataframe_optimized_v2_refined(txt_file_path, structured_data, original_file_name):
    header_df = determine_header(txt_file_path)
    
    file_name = txt_file_path.split('/')[-1]
    if file_name != 'temp.txt':
        participant_number, order = file_name.replace(".txt", "").split('_')
    else:
        participant_number, order = original_file_name.replace(".txt", "").split('_')
    participant_number = int(participant_number)
    order = int(order)
    
    with open(txt_file_path, 'r', errors='ignore') as f:
        for _ in range(4):
            next(f)
        fifth_line = f.readline().strip()
    if "Scenario1\Scenario1 - Copy.txt" in fifth_line:
        scenario = "A"
    elif "Senario2\Scenario2.txt" in fifth_line:
        scenario = "B"
    elif "Scenario3\Scenario3.txt" in fifth_line:
        scenario = "C"
    else:
        scenario = None
    
    rows = []
    for data_row in structured_data:
        values = data_row.split()
        row_data = {
            'Participant': participant_number,
            'Scenario': scenario,
            'Order': order,
            'Event': None,
            'Time': values[0],
            'Velm': values[1],
            'Distm': float(values[2]),
            'Xm': values[3],
            'IncVm': values[4],
            'IncRm': values[5],
            'WheeleAng': values[6],
            'ThrAcce': values[7],
            'BrakAcce': values[8],
            'TL': values[9],
            'Crashes': values[10],
            'First RT': None,
            'First distance': None
        }
        for i, col in enumerate(header_df.columns[17:], start=11):
            if i < len(values):
                row_data[col] = values[i]
            else:
                row_data[col] = None
        rows.append(row_data)
    
    df = pd.DataFrame(rows, columns=header_df.columns)
    for highlight_value in HIGHLIGHT_VALUES.get(scenario, []):
        closest_row_idx = (df['Distm'] - highlight_value).abs().idxmin()
        df.at[closest_row_idx, 'Event'] = df.at[closest_row_idx, 'Distm']
    
    df['Event'] = df['Event'].rank(method='first').fillna(0).astype(int)
    df['Event'] = df['Event'].replace(0, np.nan)
    
    return df

# Streamlit app
def main():
    st.title("Driving Simulator Data Processor :car: :brain: :smile: \n by Eden Eldar")

    # Create a sidebar menu for navigation
    menu = ["Home", "Event Analysis"]
    choice = st.sidebar.selectbox("Menu", menu)

    # Common file upload for both Home and Event Analysis
    uploaded_file = st.file_uploader("Choose a file", type="txt")

    if uploaded_file is not None:
        # Capture the original file name
        original_file_name = uploaded_file.name

        # Save the uploaded file to a temporary location
        with open("temp.txt", "wb") as f:
            f.write(uploaded_file.getvalue())

        try:
            # Process the uploaded file
            df_sorted = process_raw_file_for_streamlit("temp.txt", original_file_name)

            if choice == "Home":
                # Display the processed data
                st.dataframe(df_sorted)

                # Determine the scenario
                scenario = df_sorted['Scenario'].iloc[0]

                # Save the processed data as an XLSX file with highlighting
                xlsx_path = save_as_xlsx_with_highlight_refined(df_sorted, scenario)

                # Offer option to download the sorted data
                if st.button("Download Sorted Data as XLSX"):
                    with open(xlsx_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()  # Convert bytes to string
                        href = f'<a href="data:file/xlsx;base64,{b64}" download="sorted_data.xlsx">Download XLSX File</a>'
                        st.markdown(href, unsafe_allow_html=True)

            elif choice == "Event Analysis":
                show_event_analysis_with_scatter(df_sorted)


        except Exception as e:
            st.write("An error occurred:", str(e))

def calculate_changes(df, event_row_index, offset):
    """
    Calculate the changes in WheeleAng, ThrAcce, and BrakAcce for the selected row relative to the event row.
    """
    event_row = df.iloc[event_row_index]
    target_row = df.iloc[event_row_index + offset]
    
    # Ensure the values are numeric before performing the subtraction
    def safe_subtract(val1, val2):
        try:
            return float(val1) - float(val2)
        except ValueError:
            return None  # or 0, or however you want to handle this case
    
    changes = {
        'WheeleAng': safe_subtract(target_row['WheeleAng'], event_row['WheeleAng']),
        'ThrAcce': safe_subtract(target_row['ThrAcce'], event_row['ThrAcce']),
        'BrakAcce': safe_subtract(target_row['BrakAcce'], event_row['BrakAcce']),
        'TimeDifference': safe_subtract(target_row['Time'], event_row['Time']),
        'DistmDifference': safe_subtract(target_row['Distm'], event_row['Distm'])
    }
    return changes

def plot_event_analysis_updated(df, selected_event, parameter, offset):
    """
    Plot the change in the selected parameter 100 rows before and after the event.
    Overlay a scatter plot to highlight the value at the selected offset.
    """
    # Find the index of the selected event
    event_index = df[df['Event'] == selected_event].index[0]

    # Extract a window of 200 rows centered around the event (100 rows before and after)
    window_start = max(0, event_index - 100)
    window_end = min(df.shape[0], event_index + 100)
    df_window = df.iloc[window_start:window_end]

    # Plot the parameter values
    plt.figure(figsize=(12, 6))
    plt.plot(df_window.index, df_window[parameter], label=parameter, color='blue')
    plt.axvline(x=event_index, color='r', linestyle='--', label='Event')
    
    # Overlay a scatter plot for the selected offset
    offset_index = event_index + offset
    value_at_offset = df_window.loc[offset_index, parameter]
    plt.scatter([offset_index], [df_window.loc[offset_index, parameter]], color='green', s=100, zorder=5, label='Selected Offset')
    
    plt.title(f'Change in {parameter} around Event {selected_event}')
    plt.xlabel('Row Index')
    plt.ylabel(parameter)
    plt.legend()
    plt.grid(True)

    # Display the plot in Streamlit
    st.pyplot(plt.gcf())
    plt.close()

# We also need to modify the show_event_analysis_updated function to pass the offset to the plot_event_analysis_updated function
def show_event_analysis_with_scatter(df):
    """
    Display the analysis for selected event and row offset in the Streamlit app.
    Also allows the user to select a parameter and view the change around the event.
    """
    # Check if there are any events
    event_options = df[df['Event'].notnull()]['Event'].unique().tolist()
    if not event_options:
        st.write("No events found in the data.")
        return

    # Allow users to select an event
    selected_event = st.sidebar.selectbox("Select an Event", event_options)
    
    # Allow users to select the row offset using a slider
    offset = st.sidebar.slider("Select Row Offset", -100, 100, 0)
    
    # Allow users to select a parameter to plot
    parameters = ['WheeleAng', 'ThrAcce', 'BrakAcce']
    selected_parameter = st.sidebar.selectbox("Select a Parameter to Analyze", parameters)

    # Plot the selected parameter around the event with the scatter overlay
    plot_event_analysis_updated(df, selected_event, selected_parameter, offset)
    
    matching_rows = df[df['Event'] == selected_event]
    event_row_index = matching_rows.index[0]
    changes = calculate_changes(df, event_row_index, offset)
    
    # Display the changes
    participant = df['Participant'].iloc[0]
    order = df['Order'].iloc[0]
    st.write(f"Participant {participant}_{order} changed the value of BrakAcce by {changes['BrakAcce']:.2f} points, ThrAcce by {changes['ThrAcce']:.2f} points, and WheeleAng by {changes['WheeleAng']:.2f} points.")
    st.write(f"The time difference is {changes['TimeDifference']} seconds and the distance difference is {changes['DistmDifference']} meters.")


if __name__ == "__main__":
    main()
