import streamlit as st
import pandas as pd
import re
import base64
import xlsxwriter
import io

SCENARIO_A_HIGHLIGHT = [1592, 2923, 3082, 3500, 3940, 4705, 5053, 4430, 6580]
SCENARIO_B_HIGHLIGHT = [1032, 1980, 2661, 3250, 4332, 5560, 5845, 5945, 6487, 7850]
SCENARIO_C_HIGHLIGHT = [670, 1300, 2513, 3457, 4107, 4390, 5037, 5358, 6484]

def get_highlight_values(scenario):
    if scenario == "A":
        return SCENARIO_A_HIGHLIGHT
    elif scenario == "B":
        return SCENARIO_B_HIGHLIGHT
    elif scenario == "C":
        return SCENARIO_C_HIGHLIGHT
    else:
        return []

def save_df_as_excel(df):
    # Create a BytesIO buffer for the Excel file
    output = io.BytesIO()

    # Create a Pandas Excel writer with xlsxwriter as the engine
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name="Data", index=False)

        # Get the workbook and the worksheet
        workbook = writer.book
        worksheet = writer.sheets["Data"]

        # Define a format for the highlighted rows
        highlight_format = workbook.add_format({'bg_color': '#FFEB9C'})

        # Get the scenario from the dataframe
        scenario = df["Scenario"].iloc[0]
        highlight_values = get_highlight_values(scenario)

        # Update the 'Event' column for highlighted rows and apply the format
        event_count = 1
        for i, row in df.iterrows():
            if any(abs(val - row["Distm"]) < 1 for val in highlight_values):
                worksheet.set_row(i + 1, cell_format=highlight_format)  # +1 to account for header
                df.at[i, "Event"] = event_count
                event_count += 1

        # Save the updated dataframe to the Excel writer
        df.to_excel(writer, sheet_name="Data", index=False, startrow=1, header=False)

    # Seek to the beginning of the stream and return it
    output.seek(0)
    return output


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
                    skip_count -= 1
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
    
    # Determine the header file based on the content of the 5th line
    if "Scenario1\Scenario1 - Copy.txt" in fifth_line:
        return pd.read_csv("/mnt/data/TestA.csv")
    elif "Senario2\Scenario2.txt" in fifth_line:
        return pd.read_csv("/mnt/data/TestB.csv")
    elif "Scenario3\Scenario3.txt" in fifth_line:
        return pd.read_csv("/mnt/data/TestC.csv")
    else:
        raise ValueError("Unrecognized scenario in file.")


# Construct and populate the dataframe
def construct_dataframe_optimized(txt_file_path, structured_data):
    # Determine the appropriate header based on the 5th row of the txt file
    header_df = determine_header(txt_file_path)
    
    # Extract participant number and order from the file name
    file_name = txt_file_path.split('/')[-1]
    participant_number = int(file_name.split('_')[0])
    order = int(file_name.split('_')[1])
    
    # Determine the scenario based on the 5th row of the txt file
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
    
    # Prepare a list to collect row data
    rows = []
    
    # Populate the rows list
    for data_row in structured_data:
        # Split the data row into individual values
        values = data_row.split()
        
        # Construct the row data based on the provided instructions
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
            'IncXm': values[6],
            'IncXRm': values[7],
            'IncYm': values[8]
        }
        
        # Add the remaining values from the structured data to the row
        for i, col in enumerate(header_df.columns[13:], start=9):
            if i < len(values):
                row_data[col] = values[i]
            else:
                row_data[col] = None
        
        # Append the row data to the rows list
        rows.append(row_data)
    
    # Convert the rows list to a dataframe
    df = pd.DataFrame(rows, columns=header_df.columns)
    
    return df
def analyze_data_changes(df, event_row_index, row_offset):
    """
    Analyze changes in values for WheeleAng, ThrAcce, BrakAcce columns
    with respect to a highlighted (event) row.
    """
    # Ensure the selected row index is within dataframe bounds
    selected_row_index = event_row_index + row_offset
    if selected_row_index < 0 or selected_row_index >= len(df):
        return None

    # Extract relevant data
    event_row = df.iloc[event_row_index]
    selected_row = df.iloc[selected_row_index]

    # Calculate changes
    changes = {
        "WheeleAng": selected_row["WheeleAng"] - event_row["WheeleAng"],
        "ThrAcce": selected_row["ThrAcce"] - event_row["ThrAcce"],
        "BrakAcce": selected_row["BrakAcce"] - event_row["BrakAcce"],
        "Time": selected_row["Time"],
        "Distm": selected_row["Distm"],
        "dTime": selected_row["Time"] - event_row["Time"],
        "dDistm": selected_row["Distm"] - event_row["Distm"]
    }
    
    return changes

def analysis_page():
    """
    Streamlit page for analyzing changes in data values with respect to highlighted rows.
    """
    st.sidebar.title("Analysis Options")
    
    uploaded_excel = st.sidebar.file_uploader("Upload the Excel file", type="xlsx")
    
    if uploaded_excel:
        df = pd.read_excel(uploaded_excel)
        
        # Filter rows where Event is not null
        event_rows = df.dropna(subset=['Event'])
        
        # Choose an event to analyze
        event_choice = st.sidebar.selectbox("Choose an event to analyze", event_rows["Event"].tolist())
        
        # Choose the number of rows for offset
        row_offset = st.sidebar.slider("Select row offset", -100, 100, 0)
        
        if st.sidebar.button("Analyze"):
            event_row_index = df[df["Event"] == event_choice].index[0]
            analysis_results = analyze_data_changes(df, event_row_index, row_offset)
            
            if analysis_results:
                file_name = uploaded_excel.name.split('.')[0]
                st.write(f"In file {file_name}, with respect to Event {event_choice}:")
                st.write(f"- The value of `WheeleAng` changed by {analysis_results['WheeleAng']:.2f} points.")
                st.write(f"- The value of `ThrAcce` changed by {analysis_results['ThrAcce']:.2f} points.")
                st.write(f"- The value of `BrakAcce` changed by {analysis_results['BrakAcce']:.2f} points.")
                st.write(f"At a distance of {analysis_results['Distm']:.2f} meters (d = {analysis_results['dDistm']:.2f} meters) and a time of {analysis_results['Time']:.2f} seconds (d = {analysis_results['dTime']:.2f} seconds).")
            else:
                st.write("The selected row offset is out of the data range.")
        else:
            st.write("Select an event and row offset, then click 'Analyze' to view the results.")



# Process the raw data file and return a sorted dataframe
def process_raw_file_for_streamlit(txt_file_path):
    # 1. Extract the structured data from the raw file
    structured_data = extract_structured_data_v6(txt_file_path)
    
    # 2 & 3. Determine the correct header and construct the dataframe
    df = construct_dataframe_optimized(txt_file_path, structured_data)
    
    return df

def download_link_excel(buffer, filename, text):
    """
    Generate a link to download the excel file
    """
    b64 = base64.b64encode(buffer.getvalue()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{text}</a>'
    return href

# Modify the Streamlit app function to integrate the above changes

def streamlit_app_with_excel():
    st.title("Driving Simulator Data Processor :car: :brain: :smile: \n by Eden Eldar")

    # Upload file
    uploaded_file = st.file_uploader("Choose a file", type="txt")
    
    if uploaded_file is not None:
        # Save the uploaded file to a temporary location
        with open("temp.txt", "wb") as f:
            f.write(uploaded_file.getvalue())
        
        try:
            # Process the uploaded file
            df_sorted = process_raw_file_for_streamlit("temp.txt")
            
            # Display the processed data
            st.dataframe(df_sorted)
            
            # Offer option to download the sorted data as Excel
            if st.button("Download Sorted Data as Excel"):
                excel_buffer = save_df_as_excel(df_sorted)
                dl_link = download_link_excel(excel_buffer, "sorted_data.xlsx", "Download Excel File")
                st.markdown(dl_link, unsafe_allow_html=True)
                
        except Exception as e:
            st.write("An error occurred:", str(e))

#def main():
#    st.title("Driving Simulator Data Processor :car: :brain: :smile: \n by Eden Eldar")

#    # Upload file
#    uploaded_file = st.file_uploader("Choose a file", type="txt")
    
#    if uploaded_file is not None:
 #       # Save the uploaded file to a temporary location
  #      with open("temp.txt", "wb") as f:
   #         f.write(uploaded_file.getvalue())
        
    #    try:
     #       # Process the uploaded file
      #      df_sorted = process_raw_file_for_streamlit("temp.txt")
            
       #     # Display the processed data
        #    st.dataframe(df_sorted)
            
         #   # Offer option to download the sorted data
          #  if st.button("Download Sorted Data as Excel"):
           #     excel_buffer = save_df_as_excel(df_sorted)
            #    dl_link = download_link_excel(excel_buffer, "sorted_data.xlsx", "Download Excel File")
             #   st.markdown(dl_link, unsafe_allow_html=True)

                
        #except Exception as e:
         #   st.write("An error occurred:", str(e))

def analyze_data_changes(df, event_row_index, row_offset):
    """
    Analyze changes in values for WheeleAng, ThrAcce, BrakAcce columns
    with respect to a highlighted (event) row.
    """
    # Ensure the selected row index is within dataframe bounds
    selected_row_index = event_row_index + row_offset
    if selected_row_index < 0 or selected_row_index >= len(df):
        return None

    # Extract relevant data
    event_row = df.iloc[event_row_index]
    selected_row = df.iloc[selected_row_index]

    # Calculate changes
    changes = {
        "WheeleAng": selected_row["WheeleAng"] - event_row["WheeleAng"],
        "ThrAcce": selected_row["ThrAcce"] - event_row["ThrAcce"],
        "BrakAcce": selected_row["BrakAcce"] - event_row["BrakAcce"],
        "Time": selected_row["Time"],
        "Distm": selected_row["Distm"],
        "dTime": selected_row["Time"] - event_row["Time"],
        "dDistm": selected_row["Distm"] - event_row["Distm"]
    }
    
    return changes

def analysis_page():
    """
    Streamlit page for analyzing changes in data values with respect to highlighted rows.
    """
    st.sidebar.title("Analysis Options")
    
    uploaded_excel = st.sidebar.file_uploader("Upload the Excel file", type="xlsx")
    
    if uploaded_excel:
        df = pd.read_excel(uploaded_excel)
        
        # Filter rows where Event is not null
        event_rows = df.dropna(subset=['Event'])
        
        # Choose an event to analyze
        event_choice = st.sidebar.selectbox("Choose an event to analyze", event_rows["Event"].tolist())
        
        # Choose the number of rows for offset
        row_offset = st.sidebar.slider("Select row offset", -100, 100, 0)
        
        if st.sidebar.button("Analyze"):
            event_row_index = df[df["Event"] == event_choice].index[0]
            analysis_results = analyze_data_changes(df, event_row_index, row_offset)
            
            if analysis_results:
                file_name = uploaded_excel.name.split('.')[0]
                st.write(f"In file {file_name}, with respect to Event {event_choice}:")
                st.write(f"- The value of `WheeleAng` changed by {analysis_results['WheeleAng']:.2f} points.")
                st.write(f"- The value of `ThrAcce` changed by {analysis_results['ThrAcce']:.2f} points.")
                st.write(f"- The value of `BrakAcce` changed by {analysis_results['BrakAcce']:.2f} points.")
                st.write(f"At a distance of {analysis_results['Distm']:.2f} meters (d = {analysis_results['dDistm']:.2f} meters) and a time of {analysis_results['Time']:.2f} seconds (d = {analysis_results['dTime']:.2f} seconds).")
            else:
                st.write("The selected row offset is out of the data range.")
        else:
            st.write("Select an event and row offset, then click 'Analyze' to view the results.")

def integrated_streamlit_app():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Choose a Page", ["Data Processing", "Data Analysis"])
    
    if page == "Data Processing":
        streamlit_app_with_excel()
    elif page == "Data Analysis":
        analysis_page()

if __name__ == "__main__":
    integrated_streamlit_app()
