import streamlit as st
import pandas as pd
import re
import base64
import openpyxl
from openpyxl.styles import PatternFill

HIGHLIGHT_VALUES = {
    'A': [1592, 2923, 3082, 3500, 3940, 4705, 5053, 4430, 6580],
    'B': [1032, 1980, 2661, 3250, 4332, 5560, 5845, 5945, 6487, 7850],
    'C': [670, 1300, 2513, 3457, 4107, 4390, 5037, 5358, 6484]
}

def save_as_xlsx_with_highlight(df, scenario):
    """
    Save the DataFrame as an XLSX file and highlight rows based on Distm values and scenario.
    Also, updates the Event column based on highlighted rows.
    """
    # Define the fill pattern for highlighting
    highlight_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    numeric_columns = ['Time', 'Velm', 'Distm', 'Xm', 'IncVm', 'IncRm', 'WheeleAng', 'ThrAcce', 'BrakAcce', 'TL', 'Crashes']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce', downcast='float')
        # Create an Excel writer object
    with pd.ExcelWriter("sorted_data.xlsx", engine='openpyxl') as writer:
        # Write the DataFrame to XLSX
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        # Get the workbook and sheet for further editing
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        # Define an event counter
        event_counter = 1
        
        # Iterate over the rows to highlight and update the Event column
        for row_idx, row in enumerate(worksheet.iter_rows(min_row=2, max_row=worksheet.max_row, min_col=1, max_col=3), start=1):
            distm_value = row[2].value
            
            # Check if the distm value is close to any of the highlight values for the scenario
            for value in HIGHLIGHT_VALUES.get(scenario, []):
                if abs(distm_value - value) < 1.5:
                    for cell in row:
                        cell.fill = highlight_fill
                    # Update the Event column value
                    event_cell = worksheet.cell(row=row_idx + 1, column=4)
                    event_cell.value = event_counter
                    event_counter += 1
                    break
                    
    return "sorted_data.xlsx"


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
    # Open the txt file and read the 5th line
    with open(txt_file_path, 'r', errors='ignore') as f:
        for _ in range(4):  # skip the first 4 lines
            next(f)
        fifth_line = f.readline().strip()
    
    base_url = "https://raw.githubusercontent.com/edenede2/driving-stress/main/"
    
    # Determine the header file based on the content of the 5th line
    if "Scenario1\Scenario1 - Copy.txt" in fifth_line:
        return pd.read_csv(base_url + "TestA.csv")
    elif "Senario2\Scenario2.txt" in fifth_line:
        return pd.read_csv(base_url + "TestB.csv")
    elif "Scenario3\Scenario3.txt" in fifth_line:
        return pd.read_csv(base_url + "TestC.csv")
    else:
        raise ValueError("Unrecognized scenario in file.")

# Construct and populate the dataframe
def construct_dataframe_optimized_v2(txt_file_path, structured_data, original_file_name):
    # Determine the appropriate header based on the 5th row of the txt file
    header_df = determine_header(txt_file_path)
    
    # Extract participant number and order from the file name
    file_name = txt_file_path.split('/')[-1]
    if file_name != 'temp.txt':
        participant_number, order = file_name.replace(".txt", "").split('_')
    else:
        # Handle the temporary file case by reading the original file name from the uploaded file
        participant_number, order = original_file_name.replace(".txt", "").split('_')
    participant_number = int(participant_number)
    order = int(order)
    
    # Extract scenario from the file
    with open(txt_file_path, 'r', errors='ignore') as f:
        for _ in range(4):  # skip the first 4 lines
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
    
    # Construct the dataframe
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
            'Distm': values[2],
            'Xm': values[3],
            'IncVm': values[4],
            'IncRm': values[5],
            'WheeleAng': values[6],
            'ThrAcce': values [7],
            'BrakAcce': values[8],
            'TL': values[9],
            'Crashes': values[10],
            #'???':None,
            #'VelKPH':values[11],
            #'YawRate':values[12],
            #'WheeleOP':values[13],
            #'ThrOP':values[14],
            #'BrakOP':values[15],
            
            #'IncYm': values[8],
            #'Col1': values[9],
            #'Col2': values[10],
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
    return df


# Process the raw data file and return a sorted dataframe
def process_raw_file_for_streamlit(txt_file_path, original_file_name):
    # 1. Extract the structured data from the raw file
    structured_data = extract_structured_data_v6(txt_file_path)
    
    # 2 & 3. Determine the correct header and construct the dataframe
    df = construct_dataframe_optimized_v2(txt_file_path, structured_data, original_file_name)
    
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
                xlsx_path = save_as_xlsx_with_highlight(df_sorted, scenario)

                # Offer option to download the sorted data
                if st.button("Download Sorted Data as XLSX"):
                    with open(xlsx_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()  # Convert bytes to string
                        href = f'<a href="data:file/xlsx;base64,{b64}" download="sorted_data.xlsx">Download XLSX File</a>'
                        st.markdown(href, unsafe_allow_html=True)

            elif choice == "Event Analysis":
                show_event_analysis(df_sorted)

        except Exception as e:
            st.write("An error occurred:", str(e))

def calculate_changes(df, event_row_index, offset):
    """
    Calculate the changes in WheeleAng, ThrAcce, and BrakAcce for the selected row relative to the event row.
    """
    event_row = df.iloc[event_row_index]
    target_row = df.iloc[event_row_index + offset]
    
    changes = {
        'WheeleAng': target_row['WheeleAng'] - event_row['WheeleAng'],
        'ThrAcce': target_row['ThrAcce'] - event_row['ThrAcce'],
        'BrakAcce': target_row['BrakAcce'] - event_row['BrakAcce'],
        'TimeDifference': target_row['Time'] - event_row['Time'],
        'DistmDifference': target_row['Distm'] - event_row['Distm']
    }
    return changes

def show_event_analysis(df):
    """
    Display the analysis for selected event and row offset in the Streamlit app.
    """
    # Allow users to select an event
    event_options = df[df['Event'].notnull()]['Event'].unique().tolist()
    selected_event = st.sidebar.selectbox("Select an Event", event_options)
    
    # Allow users to select the row offset using a slider
    offset = st.sidebar.slider("Select Row Offset", -100, 100, 0)
    
    matching_rows = df[df['Event'] == selected_event]
    if matching_rows.empty:
        st.write(f"No data available for the selected event {selected_event}.")
        return
    event_row_index = matching_rows.index[0]
    changes = calculate_changes(df, event_row_index, offset)
    
    # Display the changes
    participant = df['Participant'].iloc[0]
    order = df['Order'].iloc[0]
    st.write(f"Participant {participant}_{order} changed the value of BrakAcce by {changes['BrakAcce']:.2f} points, ThrAcce by {changes['ThrAcce']:.2f} points, and WheeleAng by {changes['WheeleAng']:.2f} points.")
    st.write(f"The time difference is {changes['TimeDifference']} seconds and the distance difference is {changes['DistmDifference']} meters.")

if __name__ == "__main__":
    main()
