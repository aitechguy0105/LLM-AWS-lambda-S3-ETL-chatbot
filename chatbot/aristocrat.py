import pandas as pd

# Load the CSV file into a DataFrame
df = pd.read_csv('test.csv')

# Extract the desired properties
extracted_data = df[['Venue', 'Date', 'Time', 'EGM Turnover', 'EGM Wins']]  # Replace 'Column1' and 'Column2' with the actual column names
extracted_data = extracted_data.rename(columns={'Venue': 'Venue_Id'})
# Save the extracted data to a new CSV file
extracted_data.to_csv('output.csv', index=False)  # Set index=False to avoid writing row numbers to the file