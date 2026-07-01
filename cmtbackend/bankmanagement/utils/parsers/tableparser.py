from ..validationUtils import isDateValid
import pandas as pd, math
from decouple import config
import os
from decimal import Decimal
from datetime import datetime
from logging import getLogger
logger = getLogger(__name__)

FILE_PATH = config("BANK_FILES_PATH")


# PARSE TABLE FOR TYPE 1 OF XL SHEET
def parse_table_data1(workbook):
    try:
        txn_entries = []
        # Retrieve opening ledger to calculate available balance for each credit & debit operation
        # print(workbook.loc[1:])
        opening_balance = workbook.loc[0].at["Ledger Balance"]
        sheet_data = workbook.loc[1:]
        total_txn = 0
        total_credit = 0
        total_debit = 0
        for _, row_values in sheet_data.iterrows():
            date = row_values.at["1Entry Date"]
            transaction_date = isDateValid(date)
            # If no date is found, it means it's the end of the table
            if not transaction_date:
                # print(f"The table ended at row {_} with cell_value: {date or 'empty'}")
                break
            debit_amount = row_values.at["Payment Amount"]
            credit_amount = row_values.at["Receipt Amount"]

            if credit_amount is None or math.isnan(credit_amount):
                credit_amount = 0

            if debit_amount is None or math.isnan(debit_amount):
                debit_amount = 0

            if debit_amount > 0:
                total_debit += debit_amount
            if credit_amount > 0:
                total_credit += credit_amount
            total_txn += 1

            # Make debit_amount always negative using -abs()
            debit_amount = -abs(debit_amount)

            # Receivable amount is the sum of credit and debit (debit is now negative)
            Receivable_Amount = credit_amount + debit_amount
            print("Receivable_Amount:=====", Receivable_Amount)
            balance = row_values.at["Ledger Balance"]
            details = row_values.at["Transaction Details"]

            # Deduct the credit amount
            if not pd.isna(Receivable_Amount):
                opening_balance -= Receivable_Amount
            # Add the debit amount
            if not pd.isna(credit_amount):
                opening_balance += credit_amount
            # Create a dictionary for the transaction data
            txn_entries.append(
                {
                    "date_and_time": date,
                    "details": details,
                    "debit": debit_amount,
                    "Receivable_Amount": Receivable_Amount if not pd.isna(Receivable_Amount) else 0.00,
                    "credit_amount": (
                        credit_amount if not pd.isna(credit_amount) else 0.00
                    ),
                    "balance": balance if not pd.isna(balance) else opening_balance,
                }
            )
        return txn_entries, total_credit, total_debit
    except Exception as e:
        print(e, "THIS IS THE ERROR")
        return None, None, None


# PARSE TABLE FOR TYPE 2 OF XL SHEET
def parse_table_data2(workbook):
    txn_entries = []
    # Retrieve opening ledger to calculate available balance for each credit & debit operation
    sheet_data = workbook.loc[1:]
    for _, row_values in sheet_data.iterrows():
        date = row_values.at["Transaction Date"]
        debit_amount = row_values.at["Debit Amount"]
        credit_amount = row_values.at["Credit Amount"]
        balance = row_values.at["Balance"]
        details = row_values.at["Transaction Description"]
        transaction_date = isDateValid(date)
        # If no date is found, it means it's the end of the table
        if not transaction_date:
            print(f"The table ended at row {_} with cell_value: {date or 'empty'}")
            break
        # Append the data to our array
        txn_entries.append(
            {
                "date_and_time": date,
                "details": details,
                "debit_amount": debit_amount if not pd.isna(debit_amount) else 0.00,
                "credit_amount": credit_amount if not pd.isna(credit_amount) else 0.00,
                "balance": balance if not pd.isna(balance) else 0.00,
            }
        )
    return txn_entries


# PARSE TABLE FOR TYPE 3 OF XL SHEET
def parse_table_data3(workbook):
    txn_entries = []
    # Retrieve opening ledger to calculate available balance for each credit & debit operation
    sheet_data = workbook.loc[1:]
    for _, row_values in sheet_data.iterrows():
        date = row_values.at["Post date"]
        debit_amount = row_values.at["Debit amount"]
        credit_amount = row_values.at["Credit amount"]
        balance = row_values.at["Balance"]
        details = row_values.at["Narrative"]
        transaction_date = isDateValid(date)
        # If no date is found, it means it's the end of the table
        if not transaction_date:
            print(f"The table ended at row {_} with cell_value: {date or 'empty'}")
            break
        # Append the data to our array
        txn_entries.append(
            {
                "date_and_time": date,
                "details": details,
                "debit_amount": debit_amount if not pd.isna(debit_amount) else 0.00,
                "credit_amount": credit_amount if not pd.isna(credit_amount) else 0.00,
                "balance": balance if not pd.isna(balance) else 0.00,
            }
        )
    return txn_entries


def parse_lloyds_table_data(file_name):
    error_message = ''
    try:
        count = 0
        data = []
        full_file_path = os.path.join(FILE_PATH, file_name)
        df = pd.read_excel(full_file_path, header=None)
        total_txn = 0
        debit_amount = 0
        credit_amount = 0
        # Iterate over all cells in the DataFrame
        for row in range(len(df.index)):
            for col in range(len(df.columns)):
                # Check if the cell contains the word "Transaction Information:" in column 1
                if col == 0 and isinstance(df.loc[row, col], str) and 'Transaction Information:' in df.loc[row, col]:
                    logger.info("Normal Lloyd parsing")
                    count += 1
                    # Check if "Beneficiary Details:" is coming in between "Transaction Information:" in column 1
                    beneficiary_details_value = '-'
                    beneficiary_details_flag = False
                    for r in range(row + 1, len(df)):  # Search in rows below the current row
                        if isinstance(df.loc[r, col], str) and df.loc[r, col] == 'Beneficiary Name:':
                            beneficiary_details_value = df.loc[r, col + 5] if col + 5 < len(df.columns) else None
                            beneficiary_details_flag = True
                        elif isinstance(df.loc[r, col], str) and 'Transaction Information:' in df.loc[r, col]:
                            break  # Stop searching if another "Transaction Information:" is encountered
                    # Extract relevant data
                    bankref = df.loc[row + 4, col + 3]
                    custref = df.loc[row + 5, col + 3]
                    account_name = df.loc[row + 2, col + 3]
                    if pd.isna(custref):
                        details = bankref
                    else:
                        details = str(bankref) + ' - ' + str(custref)
                    amt = '-' + df.loc[row + 1, col + 3] if df.loc[row + 4, col + 1] == 'DR' else df.loc[
                        row + 1, col + 3]
                    if beneficiary_details_value:
                        beneficiary_name = beneficiary_details_value
                    # Append data to the list
                    date_and_time_str = df.loc[row + 3, col + 1]
                    date_and_time = pd.to_datetime(date_and_time_str, format='%d-%b-%Y')
                    formatted_date = date_and_time.strftime('%Y-%m-%d')
                    amt = amt.replace(",", "")
                    amt = 0 if math.isnan(float(amt)) else Decimal(amt)

                    if df.loc[row + 4, col + 1] == 'DR':
                        amt = -abs(amt)
                        data.append(
                            {'date_and_time': formatted_date, 'Debit or Credit': df.loc[row + 4, col + 1],
                             'currency': df.loc[row + 5, col + 1], 'Receivable_Amount': amt,
                             'debit': amt,
                             'details': details if pd.notna(custref) else df.loc[row + 2, col + 1],
                             'account_name': account_name
                             })
                        debit_amount += amt
                    else:
                        data.append(
                            {'date_and_time': formatted_date, 'Debit or Credit': df.loc[row + 4, col + 1],
                             'currency': df.loc[row + 5, col + 1],
                             'Receivable_Amount': amt, 'debit': None,
                             'details': details if pd.notna(custref) else df.loc[row + 2, col + 1],
                             'account_name': account_name
                             })
                        credit_amount += amt

                elif col == 0 and isinstance(df.loc[row, col], str) and 'Reporting Period' in df.loc[row, col]:
                    logger.info("M&A Fees Lloyd parsing")
                    account_details = (df.loc[row + 2, col + 1]).split("/")
                    account_name = account_details[1].strip("")
                    currency = account_details[2].strip("")
                    closing_balance = df.loc[row + 3, col + 5]

                    for row_index in range(1, 11):
                        temp_row = row_index+row
                        if col == 0 and isinstance(df.loc[temp_row, col], str) and 'Posting Date' in df.loc[temp_row, col]:
                            debit_amount = credit_amount = 0
                            for rec in range(1, 1000):
                                actual_row = temp_row + rec
                                logger.info(f"actual_row: {actual_row}")
                                date_and_time_str = df.loc[actual_row, col]
                                if pd.notna(date_and_time_str) and str(date_and_time_str).strip().lower() not in ['nan', 'null']:
                                    date_and_time = pd.to_datetime(date_and_time_str, format='%d-%b-%Y')
                                    formatted_date = date_and_time.strftime('%Y-%m-%d')

                                    details = df.loc[actual_row, col + 2]

                                    bankref = details.split("  ")[0]
                                    custref = details.split("  ")[1]

                                    val = df.loc[actual_row, col + 3]
                                    if pd.notna(val) and str(val).strip().lower() not in ['nan', 'null']:
                                        val = -abs(val)
                                        data.append({
                                            'date_and_time': formatted_date, 
                                            'Debit or Credit': df.loc[actual_row, col + 3],
                                            'currency': currency, 
                                            'Receivable_Amount': val,
                                            'debit': val,
                                            'details': details,
                                            'account_name': account_name
                                        })
                                        debit_amount += val
                                    else:
                                        val = df.loc[actual_row, col + 4]
                                        data.append({
                                            'date_and_time': formatted_date, 
                                            'Debit or Credit': val,
                                            'currency': currency,
                                            'Receivable_Amount': val, 
                                            'debit': None,
                                            'details': details,
                                            'account_name': account_name
                                        })
                                        credit_amount += val

                                if df.loc[actual_row].astype(str).str.contains('End of Report Ledger Balance', na=False).any():
                                    logger.info(f"data: {data}")
                                    return data, debit_amount, credit_amount, error_message

                        # else:
                        #     raise Exception("Date not found.")

    except Exception as e:
        print(e, "Lloyd's ERROR")
        error_message = str(e)
        return None, None, None, error_message

    return data, debit_amount, credit_amount, error_message


def parse_citibank_table_data(filename):
    error_message = ''
    # Load the first sheet of the Excel file into a DataFrame
    selected_columns = ['Value Date', 'Debit Amount', 'Credit Amount', 'CCY Code', 'Custodian Reference',
                        'Client Reference', 'Account Name']  # Columns required
    col1 = 'Custodian Reference'  # need to merge into details
    col2 = 'Client Reference'  # need to merge into details
    new_col_name = 'Details'  # merge values of bankref and custref column with a hyphin
    new_column_names = ['date_and_time', 'debit', 'Receivable_Amount', 'currency', 'account_name', 'details']
    column_to_ffill = 'account_name'

    full_file_path = os.path.join(FILE_PATH, filename)

    # Read the Excel file
    df = pd.read_excel(full_file_path, header=None)

    # Search for the header "Account ID" in column A (index 0)
    header_row = df[df.iloc[:, 0] == 'Account ID'].index[0]

    df = pd.read_excel(full_file_path, sheet_name=0, header=header_row)

    missing_columns = [col for col in selected_columns if col not in df.columns]
    if missing_columns:
        print(f"The following selected columns are missing in the DataFrame: {', '.join(missing_columns)}")
        return pd.DataFrame()

    # Filter the DataFrame to keep only the selected columns
    data = df[selected_columns].copy()  # Create a copy to avoid SettingWithCopyWarning

    # Define a function to merge bank refer and customer ref with the condition if it contains NONREF and '' then it shouldn't merge
    def merge_conditionally(row):
        # Extract and clean values
        col1_value = str(row[col1]).strip() if not pd.isnull(row[col1]) else ""
        col2_value = str(row[col2]).strip() if not pd.isnull(row[col2]) else ""
        
        # Check if values are valid (not empty, None, or 'NONREF')
        col1_valid = col1_value not in ['', 'NONREF']
        col2_valid = col2_value not in ['', 'NONREF']
        
        if col1_valid and col2_valid:
            # Only merge if both values are valid and not empty
            return f"{col1_value} - {col2_value}"
        elif col1_valid:
            return col1_value
        elif col2_valid:
            return col2_value
        return ""  # Return empty string if both values are invalid

    # Apply the function to create the new merged column
    data[new_col_name] = data.apply(merge_conditionally, axis=1)

    # Drop the original columns bank refer and customer ref
    data.drop(columns=[col1, col2], inplace=True)

    # Rename all columns in the DataFrame
    data.columns = new_column_names

    # Forward fill the specified column
    data[column_to_ffill] = data[column_to_ffill].ffill()

    # Drop rows where the first column is blank
    # data.dropna(subset=['date_and_time'], inplace=True)

    # Drop rows where all Value date, Client Reference and Custodian Reference are NaN, NaT, or blank
    data = data[~((data['date_and_time'].isnull()) & (data['details'] == ''))]

    # Reset index (optional, to clean up row numbering)
    data = data.reset_index(drop=True)

    # Making debit amount -ve if the amount is positive in the file.
    data['debit'] = data['debit'].apply(lambda x: -abs(x) if pd.notna(x) and not math.isnan(float(x)) and x > 0 else x)

    sum_debit_amount = data['debit'].sum()
    sum_credit_amount = data['Receivable_Amount'].sum()
    num_rows = data.shape[0]

    print(f"Sum of debit amount: {sum_debit_amount}")
    print(f"Sum of credit amount: {sum_credit_amount}")
    print(f"Number of entires: {num_rows}")

    excluded_fields = {"debit", "Receivable_Amount"}

    data = data.to_dict(orient='records')
    
    # Convert the data to a list of dictionaries (records)
    for row in data:
        blank_columns = [key for key, value in row.items() if 
                 key not in excluded_fields and 
                 (pd.isna(value) or str(value).strip() == '') and 
                 not isinstance(value, int)]

        if blank_columns:
            error_message = f"Columns {blank_columns} are blank"
            return None, None, None, error_message

    return data, sum_debit_amount, sum_credit_amount, error_message


def parse_hsbc_table_data(filename):
    error_message = ''
    # Load the first sheet of the Excel file into a DataFrame
    selected_columns = ['Value date', 'Debit amount', 'Credit amount', 'Currency', 'Bank reference',
                        'Customer reference', 'Account name', 'Narrative']  # Columns required
    col1 = 'Bank reference'  # need to merge into details
    col2 = 'Customer reference'  # need to merge into details
    col3 = 'Narrative'
    new_col_name = 'Details'  # merge values of bankref and custref column with a hyphin
    new_column_names = ['date_and_time', 'debit', 'Receivable_Amount', 'currency', 'account_name', 'details']

    full_file_path = os.path.join(FILE_PATH, filename)
    df = pd.read_excel(full_file_path, sheet_name=0)

    # Search for the header "Account ID" in column A (index 0)
    if not df.columns[0] == "Account name":
        raise "Account Name header error. Please check the file."
    
    # header_row = df[df.iloc[:, 0] == 'Account name'].index[0]
    # df = pd.read_excel(full_file_path, sheet_name=0, header=header_row)

    missing_columns = [col for col in selected_columns if col not in df.columns]
    if missing_columns:
        print(f"The following selected columns are missing in the DataFrame: {', '.join(missing_columns)}")
        raise f"Missing columns {missing_columns}. Please check the file."
        # return pd.DataFrame()

    # Filter the DataFrame to keep only the selected columns
    data = df[selected_columns].copy()  # Create a copy to avoid SettingWithCopyWarning

    # Define a function to merge bank refer and customer ref with the condition if it contains NONREF and '' then it shouldn't merge
    def merge_conditionally(row):
        # Handle None and NaN values properly and Remove leading/trailing spaces
        col1_value = str(row[col1]).strip() if pd.notna(row[col1]) and row[col1] is not None else ''
        col2_value = str(row[col2]).strip() if pd.notna(row[col2]) and row[col2] is not None else ''
        col3_value = str(row[col3]).strip() if pd.notna(row[col3]) and row[col3] is not None else ''
        
        # Take Narrative value exists in the sheet then take it as a Payment ref
        if col3_value not in ['', 'NONREF']:
            return col3_value

        # If both col1_value and col2_value are valid, return the merged value
        if col1_value not in ['', 'NONREF'] and col2_value not in ['', 'NONREF']:
            return f"{col1_value} - {col2_value}"
        
        # If col1 is valid and col2 is not, return col1 value
        elif col1_value not in ['', 'NONREF']:
            return col1_value
        
        # If col2 is valid and col1 is not, return col2 value
        elif col2_value not in ['', 'NONREF']:
            return col2_value
        
        # If both are invalid, return an empty string
        return ''  

    # Apply the function to create the new merged column
    data[new_col_name] = data.apply(merge_conditionally, axis=1)

    # Drop the original columns bank refer and customer ref
    data.drop(columns=[col1, col2, col3], inplace=True)

    # Rename all columns in the DataFrame
    data.columns = new_column_names

    # Replace NaN values with 0 in the Series
    # data['debit'] = data['debit'].apply(lambda x: 0 if pd.isna(x) or math.isnan(float(x)) else x)
    data['debit'] = data['debit'].apply(lambda x: -abs(x) if pd.notna(x) and not math.isnan(float(x)) and x > 0 else 0 if pd.isna(x) else x)
    data['Receivable_Amount'] = data['Receivable_Amount'].apply(lambda x: 0 if pd.isna(x) or math.isnan(float(x)) else x)
    
    sum_debit_amount = float(data['debit'].sum())
    sum_credit_amount = float(data['Receivable_Amount'].sum())
    num_rows = data.shape[0]

    # Update 'Receivable_Amount' as 'Receivable_Amount - debit' to show it as the 
    data['Receivable_Amount'] = data['Receivable_Amount'] + data['debit']

    print(f"Total of debit amount: {sum_debit_amount}")
    print(f"Total of credit amount: {sum_credit_amount}")
    print(f"Total No. of entires: {num_rows}")

    excluded_fields = {"debit", "Receivable_Amount"}

    data = data.to_dict(orient='records')
    
    # Convert the data to a list of dictionaries (records)
    for row in data:
        blank_columns = [key for key, value in row.items() if 
                 key not in excluded_fields and 
                 (pd.isna(value) or str(value).strip() == '') and 
                 not isinstance(value, int)]

        if blank_columns:
            error_message = f"Columns {blank_columns} are blank"
            return None, None, None, error_message

    return data, sum_debit_amount, sum_credit_amount, error_message

def safe_float(x, txn_type='cr'):
    try:
        # Convert the value to string, remove commas and whitespace, then convert to float
        new_val = str(x).replace(',', '').strip()
        val = float(new_val)
        if txn_type=='dr':
            return 0 if pd.isna(val) or math.isnan(val) else -abs(val)
        else:
            return 0 if pd.isna(val) or math.isnan(val) else val
    except Exception:
        return 0

def parse_jpmorgan_chase_bank_table_data(filename):
    try:
        error_message = ''
        # Define the selected columns (we removed Bank Reference and Customer Reference)
        selected_columns = ['Value Date', 'Debit Amount', 'Credit Amount', 'Currency', 'Account Name']
        # New column names for the final DataFrame
        new_column_names = ['date_and_time', 'debit', 'Receivable_Amount', 'currency', 'account_name', 'details']

        full_file_path = os.path.join(FILE_PATH, filename)
        df = pd.read_excel(full_file_path, sheet_name=0)

        # Verify that the required header "Account Name" exists
        if "Account Name" not in df.columns:
            raise Exception("Account Name header error. Please check the file.")

        missing_columns = [col for col in selected_columns if col not in df.columns]
        if missing_columns:
            print(f"The following selected columns are missing in the DataFrame: {', '.join(missing_columns)}")
            raise Exception(f"Missing columns {missing_columns}. Please check the file.")

        # Filter the DataFrame to keep only the selected columns
        data = df[selected_columns].copy()

        # Find all columns whose header contains "remarks" (case-insensitive)
        remarks_cols = [col for col in df.columns if "remarks" in col.lower()]
        if remarks_cols:
            # Concatenate values from all remarks columns, separated by "-", and remove NaN/empty values
            data['details'] = df[remarks_cols].astype(str).apply(
                lambda row: " ; ".join([val for val in row if pd.notna(val) and val.strip() != "" and val.lower() != "nan"]),
                axis=1
            )
        else:
            data['details'] = ""

        # Rename columns in the DataFrame to the desired names
        data.columns = new_column_names

        # Replace NaN values with 0 for debit and ensure debit is always negative
        data['debit'] = data['debit'].apply(lambda x: 0 if pd.isna(x) or math.isnan(float(x)) else -abs(x))
        data['Receivable_Amount'] = data['Receivable_Amount'].apply(lambda x: 0 if pd.isna(x) or math.isnan(float(x)) else x)

        sum_debit_amount = float(data['debit'].sum())
        sum_credit_amount = float(data['Receivable_Amount'].sum())
        num_rows = data.shape[0]

        # Update 'Receivable_Amount' by adding debit (which is negative) to show net values
        data['Receivable_Amount'] = data['Receivable_Amount'] + data['debit']

        print(f"Total of debit amount: {sum_debit_amount}")
        print(f"Total of credit amount: {sum_credit_amount}")
        print(f"Total No. of entries: {num_rows}")

        excluded_fields = {"debit", "Receivable_Amount"}

        data = data.to_dict(orient='records')
        
        # Convert the data to a list of dictionaries (records)
        for row in data:
            blank_columns = [key for key, value in row.items() if 
                 key not in excluded_fields and 
                 (pd.isna(value) or str(value).strip() == '') and 
                 not isinstance(value, int)]

            if blank_columns:
                error_message = f"Columns {blank_columns} are blank"
                return None, None, None, error_message

        return data, sum_debit_amount, sum_credit_amount, error_message
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)

def parse_mashreq_bank_table_data(filename):
    try:
        print("In frs function")
        error_message = ''
        # Define the columns that are required from the FRS data
        selected_columns = ['Value Dates', 'Transaction Reference', 'Customer Reference', 
                            'Debit Amount', 'Credit Amount', 'Transaction Remarks']
        
        col1 = 'Transaction Reference'  # Bank Reference equivalent
        col2 = 'Customer Reference'  # Customer Reference
        col3 = 'Transaction Remarks'  # Transaction Remarks
        
        new_column_names = ['date_and_time', 'transaction_reference', 'customer_reference', 
                            'debit', 'Receivable_Amount', 'account_name', 'currency', 'details']

        full_file_path = os.path.join(FILE_PATH, filename)

        # First load the first 5 rows to extract the account name from cell B2
        temp_df = pd.read_excel(full_file_path, sheet_name=0, header=None, nrows=5)
        account_name = temp_df.iloc[0, 1]  # Account name is in cell B2 (second row, second column)
        print(f"Account Name: {account_name}")

        # Load the Excel file, specifying header row 4 (which is row 5 in Excel, zero-indexed)
        df = pd.read_excel(full_file_path, sheet_name=0, header=4)

        # Search for 'Account Currency' in the first column and extract the currency value from the second column
        currency = None
        for index, row in df.iterrows():
            if 'Account Currency' in str(row[0]):
                currency = row[1]  # Get the currency from the second column
                break  # Exit the loop once currency is found

        # Filter rows until "Account Summary" is found in the first column (col A)
        summary_mask = df.iloc[:, 0].astype(str).str.contains("Account Summary", na=False)
        if summary_mask.any():
            summary_index = df.index[summary_mask][0]
            df = df.loc[:summary_index - 1]
        

        if currency is None:
            raise "Currency not found. Please check the file."

        # Checking if the essential columns exist in the dataframe
        missing_columns = [col for col in selected_columns if col not in df.columns]
        if missing_columns:
            print(f"The following selected columns are missing in the DataFrame: {', '.join(missing_columns)}")
            raise f"Missing columns {missing_columns}. Please check the file."

        # Filter the DataFrame to keep only the selected columns
        data = df[selected_columns].copy()  # Create a copy to avoid SettingWithCopyWarning

        # Define a function to merge transaction ref and customer ref conditionally
        def merge_conditionally(row):
            ref1 = row[col1]
            ref2 = row[col2]
            ref3 = row[col3]
            ref1_valid = not pd.isna(ref1) and str(ref1).strip() not in ['', 'NONREF']
            ref2_valid = not pd.isna(ref2) and str(ref2).strip() not in ['', 'NONREF']
            ref3_valid = not pd.isna(ref3) and str(ref3).strip() not in ['', 'NONREF']
            if ref3_valid:
                return ref3
            if ref1_valid and ref2_valid:
                return f"{ref1} - {ref2}"
            return ref1 if ref1_valid else (ref2 if ref2_valid else "")

        # Apply the function to create the new merged column
        data['details'] = data.apply(merge_conditionally, axis=1)

        # Instead of dropping the original columns, keep them to rename later
        # Rename columns:
        data.rename(columns={
            'Value Dates': 'date_and_time',
            'Transaction Reference': 'transaction_reference',
            'Customer Reference': 'customer_reference',
            'Debit Amount': 'debit',
            'Credit Amount': 'Receivable_Amount'
        }, inplace=True)

        # Add account_name and currency to all rows in the DataFrame
        data['account_name'] = account_name
        data['currency'] = currency

        # Rearrange the columns to match new_column_names order
        data = data[new_column_names]

        # Replace NaN values with 0 in the 'debit' and 'receivable_amount' columns
        data['debit'] = data['debit'].apply(safe_float, txn_type='dr')
        data['Receivable_Amount'] = data['Receivable_Amount'].apply(safe_float, txn_type='cr')

        # Calculate the total debit and credit amounts
        sum_debit_amount = float(data['debit'].sum())
        sum_credit_amount = float(data['Receivable_Amount'].sum())

        # Update 'receivable_amount' as 'receivable_amount + debit' to show the total
        data['Receivable_Amount'] = data['Receivable_Amount'] + data['debit']

        print(f"Total of debit amount: {sum_debit_amount}")
        print(f"Total of credit amount: {sum_credit_amount}")
        print(f"Total No. of entries: {data.shape[0]}")

        excluded_fields = {"debit", "Receivable_Amount", "customer_reference"}

        data = data.to_dict(orient='records')
        
        # Convert the data to a list of dictionaries (records)
        for row in data:
            blank_columns = [key for key, value in row.items() if 
                 key not in excluded_fields and 
                 (pd.isna(value) or str(value).strip() == '') and 
                 not isinstance(value, int)]

            if blank_columns:
                error_message = f"Columns {blank_columns} are blank"
                return None, None, None, error_message

        return data, sum_debit_amount, sum_credit_amount, error_message
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)

# def parse_uob_table_data(workbook):
#     selected_columns = [
#         'Value Date', 'Our Reference', 'Your Reference', 'Deposit', 'Withdrawal',
#         'Description', 'Cheque Number', 'Reference5', 'Remarks', 'Reference7', 
#         'Reference8', 'Reference9', 'Reference10', 'Reference11', 'Reference12'
#     ]
#     try:
#         # If workbook is a DataFrame (as returned by open_sheet)
#         if isinstance(workbook, pd.DataFrame):
#             workbook.columns = workbook.columns.str.strip()

#             # Skip header row, then filter to only the selected columns
#             data = workbook[selected_columns].dropna(how='all').copy()
#         else:
#             # Get the first sheet from the workbook
#             sheet = workbook.sheet_by_index(0)
#             total_credit = 0
#             total_debit = 0
#             rows_list = []
#             # Retrieve header row and strip each header
#             headers = [str(h).strip() for h in sheet.row_values(0)]
            
#             # Iterate through the rows of the sheet
#             for row in range(0, sheet.nrows - 1):
#                 values = sheet.row_values(row)
#                 # Skip rows where all values are NaN
#                 if all(pd.isna(v) for v in values):
#                     continue
#                 # Create a dictionary using only the selected columns.
#                 row_dict = {}
#                 for col in selected_columns:
#                     for i, hdr in enumerate(headers):
#                         if hdr == col.strip():
#                             row_dict[col] = values[i]
#                             break
#                 rows_list.append(row_dict)
#             data = pd.DataFrame(rows_list)
#         return data.to_dict(orient='records')
#     except Exception as e:
#         print(e, "THIS IS THE ERROR")
#         return None

def parse_uob_table_data(workbook, row_limit):
    selected_columns = [
        "Value Date",
        "Description",
        "Deposit",
        "Withdrawal",
        "Balance"
    ]
    try:
        workbook.columns = workbook.columns.str.strip()
        data = workbook[selected_columns].iloc[:row_limit]
        data = data.dropna(how="all")
        return data.to_dict(orient="records")

    except Exception as e:
        print(e, "THIS IS THE ERROR")
        return None

def format_date(date_val):
    try:
        if isinstance(date_val, str):
            # Try parsing with multiple formats
            for fmt in ("%d/%m/%Y", "%b %d, %Y"):  # Add more formats as needed
                try:
                    return datetime.strptime(date_val.strip(), fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
            # If no format worked, return the original value (or handle error)
            return date_val
        elif isinstance(date_val, datetime):
            return date_val.strftime("%Y-%m-%d")
        else:
            return date_val 
    except:
        return None

def parse_cibc_bank_table_data(filename):
    try:
        error_message = ""
        full_file_path = os.path.join(FILE_PATH, filename)
        
        # 1) Read the entire sheet with no header, so we can access specific cells by index
        df_raw = pd.read_excel(full_file_path, sheet_name=0, header=None)

        # 2) Iterate through the first column to find the row containing "date" (case-insensitive)
        header_row = None
        for row_idx in range(df_raw.shape[0]):
            cell_value = str(df_raw.iloc[row_idx, 0]).lower()
            if "date" in cell_value:
                header_row = row_idx
                break
        
        if header_row is None:
            raise Exception("Header row containing 'date' not found.")
        
        # 3) Read the table using the header row as the header row
        df_table = pd.read_excel(full_file_path, sheet_name=0, header=header_row)

        # 4) Extract the needed cells based on the header row
        account_name = df_raw.iloc[header_row-3, 0]
        account_number = df_raw.iloc[header_row-2, 0]  # if you need it for reference
        
        # Check columns D through M for currency (indices 3 to 12)
        currency = None
        for col_idx in range(3, 13):  # D, E, F, G, H, I, J, K, L, M columns
            cell_value = df_raw.iloc[header_row-2, col_idx]
            if pd.notna(cell_value) and str(cell_value).strip() != '':
                currency = cell_value
                break

        if currency is None:
            raise Exception("Currency not found in columns D through M")
        
        # 5) Rename columns to your desired schema
        df_table.rename(
            columns={
                "Date": "date_and_time",
                "Description": "details",
                "Debit amount": "debit",
                "Credit amount": "Receivable_Amount",
                "Balance": "balance"
            },
            inplace=True
        )

        # Format the 'date_and_time' column
        df_table['date_and_time'] = df_table['date_and_time'].apply(format_date)
        df_table['details'] = df_table['details'].apply(lambda val: "" if pd.isna(val) else val)

        # 6) Replace NaN in 'debit' and 'Receivable_Amount' columns with 0
        df_table["debit"] = df_table["debit"].fillna(0)
        df_table["debit"] = -abs(df_table["debit"])
        df_table["Receivable_Amount"] = df_table["Receivable_Amount"].fillna(0)
        df_table["balance"] = df_table["balance"].fillna(0)

        # 7) Insert the same account_name and currency for each row
        df_table["account_name"] = account_name
        df_table["currency"] = currency

        # 8) Reorder columns to match the exact order you want
        df_table = df_table[
            ["date_and_time", "debit", "Receivable_Amount",
             "account_name", "currency", "details", "balance"]
        ]
        df_table_copy = df_table.copy()

        # Normalize 'details' to lowercase (ignoring NaNs)
        df_table["details"] = df_table["details"].str.lower()

        # Find the index of the first occurrence of "opening balance" and "closing balance"
        opening_idx = df_table.index[df_table["details"] == "opening balance"]
        closing_idx = df_table.index[df_table["details"] == "closing balance"]
   
        df_table.loc[~df_table.index.isin([opening_idx[0], closing_idx[0]]), 'details'] = df_table_copy.loc[~df_table_copy.index.isin([opening_idx[0], closing_idx[0]]), 'details']

        if not opening_idx.empty and not closing_idx.empty:
            start = opening_idx[0]
            end = closing_idx[0]
            # Slice the DataFrame only if the opening balance comes before the closing balance
            if start <= end:
                df_table = df_table.loc[start:end]

        # Update data from the modified df_table
        data = df_table.to_dict(orient="records")
        
        # 9) Calculate sums for debit and credit
        sum_debit_amount = df_table["debit"].sum()
        sum_credit_amount = df_table["Receivable_Amount"].sum()

        # Update 'receivable_amount' as 'receivable_amount + debit' to show the total
        for record in data:
            record['Receivable_Amount'] += record['debit']
        
        excluded_fields = {"debit", "Receivable_Amount", "details"}
        opening_balance = data[0]
        closing_balance = data[-1]
        # Convert the data to a list of dictionaries (records)
        for row in data:
            blank_columns = [key for key, value in row.items() if 
                 key not in excluded_fields and 
                 (pd.isna(value) or str(value).strip() == '') and 
                 not isinstance(value, int)]

            if blank_columns:
                error_message = f"Columns {blank_columns} are blank"
                return None, None, None, error_message

        # 10) Balance validation check
        balance_check = False
        if opening_balance and closing_balance:
            initial_balance = opening_balance["balance"]
            final_balance = closing_balance["balance"]

            expected_final_balance = initial_balance + sum_debit_amount + sum_credit_amount
            balance_check = round(final_balance, 2) == round(expected_final_balance, 2)
        
        # Finally, return the table data, sum of debits, sum of credits
        if balance_check:
            return data[1:-1], sum_debit_amount, sum_credit_amount, error_message
        error_message = "Closing balance is not matching with the actual records balance total."
        return None, None, None, error_message
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)
