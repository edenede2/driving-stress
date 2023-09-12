import streamlit as st
import pandas as pd
import re
import base64

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
    
    base_url = "https://raw.githubusercontent.com/edenede2/driving-stress/headers/"
    
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
def construct_dataframe_optimized_v2(txt_file_path, structured_data, header_df):
    # Extract participant number and order from the file name
    file_name = txt_file_path.split('/')[-1]
    if file_name != 'temp.txt':
        participant_number, order = file_name.replace(".txt", "").split('_')
        participant_number = int(participant_number)
        order = int(order)
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
            'IncXm': values[6],
            'IncXRm': values[7],
            'IncYm': values[8],
            'Col1': values[9],
            'Col2': values[10],
            'First RT': None,
            'First distance': None
        }
        for i, col in enumerate(header_df.columns[17:], start=12):
            if i < len(values):
                row_data[col] = values[i]
            else:
                row_data[col] = None
        rows.append(row_data)
    
    df = pd.DataFrame(rows, columns=header_df.columns)
    return df


# Process the raw data file and return a sorted dataframe
def process_raw_file_for_streamlit(txt_file_path):
    # 1. Extract the structured data from the raw file
    structured_data = extract_structured_data_v6(txt_file_path)
    
    # 2 & 3. Determine the correct header and construct the dataframe
    df = construct_dataframe_optimized(txt_file_path, structured_data)
    
    return df

# Streamlit app
def main():
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
            
            # Offer option to download the sorted data
            if st.button("Download Sorted Data as CSV"):
                csv = df_sorted.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()  # Ensure this line is correct
                href = f'<a href="data:file/csv;base64,{b64}" download="sorted_data.csv">Download CSV File</a>'
                st.markdown(href, unsafe_allow_html=True)
                
        except Exception as e:
            st.write("An error occurred:", str(e))

if __name__ == "__main__":
    main()
