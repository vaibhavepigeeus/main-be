from ..generalUtils import open_sheet, find_header_row
from .headerparser import parse_headers
from .tableparser import parse_table_data1, parse_table_data2, parse_table_data3, parse_lloyds_table_data, \
    parse_citibank_table_data, parse_hsbc_table_data, parse_jpmorgan_chase_bank_table_data, parse_mashreq_bank_table_data, parse_uob_table_data, parse_cibc_bank_table_data
import math
import pandas as pd
from datetime import datetime
from decimal import Decimal
from logging import getLogger
logger = getLogger(__name__)


# TYPE 1 OF BANK SHEET
def parse_barclay_data(file_name):
    # Initialize headers according to the excel sheet
    headers = [
        ["Bank Name", "C"],
        ["Account Number", "C"],
        ["Account Name", "C"],
        ["Currency", "C"],
        ["Total Payment Amount / Payment Count", "C"],
        ["Total Receipt Amount / Receipt Count", "C"],
        ["Transaction Count", "C"],
    ]
    # Get reference to the sheet
    sheet_for_header = open_sheet(file_name, None)
    # get all the headers value
    headersdata = parse_headers(sheet_for_header, headers)
    dataheaders = {
        "account_number": headersdata[0],
        "account_name": headersdata[1],
        "currency": headersdata[2],
        "bank_name": headersdata[3],

        "payment_amount": headersdata[4],
        "receipt_amount": headersdata[5],
        "transaction_count": headersdata[6],
    }
    header_row = find_header_row(sheet_for_header, "Ledger Balance")
    sheet_for_table = open_sheet(file_name, header_row)
    table_data, total_credit, debit_amount = parse_table_data1(sheet_for_table)

    headersdata[4] = headersdata[4].split('/')[0]
    headersdata[5] = headersdata[5].split('/')[0]

    headersdata[4] = headersdata[4].replace(",", "")
    headersdata[5] = headersdata[5].replace(",", "")

    try:
        headersdata[4] = 0 if math.isnan(float(headersdata[4])) else Decimal(headersdata[4])
    except Exception as e:
        print("Exception e:", str(e))
        headersdata[4] = 0
    try:
        headersdata[5] = 0 if math.isnan(float(headersdata[5])) else Decimal(headersdata[5])
    except Exception as e:
        print("Exception e:", str(e))
        headersdata[5] = 0
    headersdata[4] = -abs(headersdata[4])
    dataheaders.update({"payment_amount": -abs(headersdata[4])})
    dataheaders.update({"receipt_amount": headersdata[5]})

    error_message = ""
    excluded_fields = {"debit", "Receivable_Amount", "payment_amount", "receipt_amount", "transaction_count"}
    if dataheaders:
        blank_columns = []
        blank_columns += [
            key for key, value in dataheaders.items() 
            if key not in excluded_fields and 
            (pd.isna(value) or (isinstance(value, str) and value.strip() == "")) and 
            not isinstance(value, (int, Decimal))  
        ]
        
    for row in table_data:
        blank_columns += [key for key, value in row.items() if key not in excluded_fields and not value and not isinstance(value, (int, float))]

        if blank_columns:
            error_message = f"Columns {blank_columns} are blank"
            return None, None, None, error_message

    for obj in table_data:
        obj.update(dataheaders)
        obj.update({"error_message": error_message})
        import time
    return table_data, headersdata[4], headersdata[5], None


def parse_lloyds_data(file_name):
    table_data, debit_amount, credit_amount, error_message = parse_lloyds_table_data(file_name)
    return table_data, debit_amount, credit_amount, error_message


def parse_citibank_data(file_name):
    table_data, debit_amount, credit_amount, error_message = parse_citibank_table_data(file_name)
    return table_data, debit_amount, credit_amount, error_message 


def parse_hsbc_data(file_name):
    table_data, credit_amount, debit_amount, error_message = parse_hsbc_table_data(file_name)
    return table_data, credit_amount, debit_amount, error_message

def parse_jpmorgan_chase_bank_data(file_name):
    logger.info(f"In the parse_jpmorgan_chase_bank_data function")
    table_data, credit_amount, debit_amount, error_message = parse_jpmorgan_chase_bank_table_data(file_name)
    return table_data, credit_amount, debit_amount, error_message

def parse_mashreq_bank_data(file_name):
    logger.info(f"In the parse_mashreq_bank_data function")
    table_data, debit_amount, credit_amount, error_message = parse_mashreq_bank_table_data(file_name)
    return table_data, debit_amount, credit_amount, error_message

# def parse_uob_bank_data(file_name):
#     logger.info("=== Starting parse_uob_bank_data ===")
#     logger.info(f"Input file_name: {file_name}")
    
#     # Initialize headers according to the excel sheet
#     logger.info("--- Initializing headers ---")
#     headers1 = [
#         ["Value Date", "C"],
#         ["Our Reference", "C"],
#         ["Your Reference", "C"],
#         ["Deposit", "C"], #credit_amount
#         ["Withdrawal", "C"], #debit_amount
#     ]
#     logger.info(f"headers1: {headers1}")

#     headers2 = [
#         ["Account Name", "C"],
#         ["Account Currency", "C"],
#         ["Account Number", "C"],
#     ]
#     logger.info(f"headers2: {headers2}")

#     headers3 = [["Total in Account Currency", "L"]]
#     logger.info(f"headers3: {headers3}")

#     # Get reference to the sheet
#     logger.info("--- Opening sheet for headers ---")
#     sheet_for_header = open_sheet(file_name, None)
#     logger.info(f"sheet_for_header opened")
    
#     # get all the headers value
#     logger.info("--- Parsing headers data ---")
#     headersdata1 = parse_headers(sheet_for_header, headers1)
#     logger.info(f"headersdata1: {headersdata1}")
    
#     headersdata2 = parse_headers(sheet_for_header, headers2)
#     logger.info(f"headersdata2: {headersdata2}")
    
#     headersdata3 = parse_headers(sheet_for_header, headers3)
#     logger.info(f"headersdata3: {headersdata3}")

#     logger.info("--- Finding header rows ---")
#     header_row1 = find_header_row(sheet_for_header, "H1")
#     logger.info(f"header_row1 (H1): {header_row1}")
    
#     header_row2 = find_header_row(sheet_for_header, "D1")
#     logger.info(f"header_row2 (D1): {header_row2}")
    
#     logger.info("--- Opening sheets for tables ---")
#     sheet_for_table1 = open_sheet(file_name, header_row1)
#     logger.info(f"sheet_for_table1 opened with header_row1: {header_row1}")
    
#     sheet_for_table2 = open_sheet(file_name, header_row2)
#     logger.info(f"sheet_for_table2 opened with header_row2: {header_row2}")
    
#     logger.info("--- Parsing UOB table data ---")
#     table_data = parse_uob_table_data(sheet_for_table2)
#     logger.info(f"Original table_data length: {len(table_data)}")
#     logger.info(f"First few rows of table_data: {table_data[:3] if len(table_data) > 0 else 'No data'}")

#     logger.info("--- Processing header amounts ---")
#     headersdata1[4] = str(headersdata1[4]).replace(",", "")
#     logger.info(f"headersdata1[4] (Withdrawal) after comma removal: {headersdata1[4]}")
    
#     headersdata1[3] = str(headersdata1[3]).replace(",", "")
#     logger.info(f"headersdata1[3] (Deposit) after comma removal: {headersdata1[3]}")

#     logger.info("--- Converting header amounts to Decimal ---")
#     try:
#         headersdata1[4] = 0 if math.isnan(float(headersdata1[4])) else Decimal(headersdata1[4])
#         logger.info(f"headersdata1[4] (Withdrawal) as Decimal: {headersdata1[4]}")
#     except Exception as e:
#         logger.error(f"Exception e: {str(e)}")
#         headersdata1[4] = 0
#         logger.info(f"headersdata1[4] set to 0 due to exception")
    
#     try:
#         headersdata1[3] = 0 if math.isnan(float(headersdata1[3])) else Decimal(headersdata1[3])
#         logger.info(f"headersdata1[3] (Deposit) as Decimal: {headersdata1[3]}")
#     except Exception as e:
#         logger.error(f"Exception e: {str(e)}")
#         headersdata1[3] = 0
#         logger.info(f"headersdata1[3] set to 0 due to exception")

#     logger.info("--- Initializing totals and error handling ---")
#     error_message = ""
#     total_credit = 0
#     total_debit = 0
#     logger.info(f"Initial totals - total_credit: {total_credit}, total_debit: {total_debit}")
    
#     logger.info("--- Processing file totals from headers3 ---")
#     file_debit = float(headersdata3[0].split('|')[1])
#     file_credit = float(headersdata3[0].split('|')[0])
#     logger.info(f"File totals - file_debit: {file_debit}, file_credit: {file_credit}")
    
#     # Update each transaction object: if debit is positive, make it negative.
#     logger.info("--- Processing table rows ---")
#     new_table_data = []
#     for i, row in enumerate(table_data[:-1]):
#         logger.info(f"--- Processing row {i+1}/{len(table_data)-1} ---")
#         logger.info(f"Original row: {row}")
        
#         # Normalize keys by stripping spaces
#         row = {key.strip(): value for key, value in row.items()}
#         logger.info(f"Row after key normalization: {row}")
        
#         # Get the value date
#         value_date = row.get("Value Date", "")
#         logger.info(f"Value Date: {value_date}")

#         logger.info("--- Checking for blank columns ---")
#         excluded_fields = {"Deposit", "Withdrawal", "Cheque Number", "Remarks", "Description"}  # Fields to ignore

#         blank_columns = [
#             key for key, value in row.items() 
#             if key not in excluded_fields and not 'reference' in key.lower() and (not value or (isinstance(value, float) and math.isnan(value)) or pd.isna(value))
#         ]
#         logger.info(f"Blank columns found: {blank_columns}")

#         if not headersdata2[2] or (isinstance(headersdata2[2], float) and math.isnan(headersdata2[2])) or pd.isna(headersdata2[2]):   
#             blank_columns.append('account_name')
#             logger.info("Added 'account_name' to blank_columns due to missing headersdata2[2]")
#         elif not headersdata2[1] or (isinstance(headersdata2[1], float) and math.isnan(headersdata2[1])) or pd.isna(headersdata2[1]):
#             blank_columns.append('currency')
#             logger.info("Added 'currency' to blank_columns due to missing headersdata2[1]")

#         if blank_columns:
#             error_message = f"Columns {blank_columns} are blank"
#             logger.error(f"ERROR: {error_message}")
#             return None, None, None, error_message

#         logger.info("--- Extracting row data ---")
#         date_val = row.get("Value Date", "")
#         trans_ref = row.get("Our Reference", "")
#         cust_ref = row.get("Your Reference", "")
#         deposit = row.get("Deposit", 0)
#         withdrawal = row.get("Withdrawal", 0)
#         logger.info(f"Extracted - date_val: {date_val}, trans_ref: {trans_ref}, cust_ref: {cust_ref}")
#         logger.info(f"Amounts - deposit: {deposit}, withdrawal: {withdrawal}")
        
#         # Make sure withdrawal (debit) is negative if positive.
#         if isinstance(withdrawal, (int, float)) and withdrawal > 0:
#             withdrawal = -abs(withdrawal)
#             logger.info(f"Withdrawal made negative: {withdrawal}")
        
#         logger.info("--- Formatting date ---")
#         formatted_date = datetime.strptime(date_val.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
#         logger.info(f"Formatted date: {formatted_date}")

#         # Merge Description to Reference12 in details
#         logger.info("--- Building details string ---")
#         details_list = [str(row.get(col, "")).strip() for col in [
#             "Description", "Cheque Number", "Reference5", "Remarks", 
#             "Reference7", "Reference8", "Reference9", "Reference10", 
#             "Reference11", "Reference12"
#         ]]
#         logger.info(f"Details list components: {details_list}")
#         details = '; '.join(filter(None, [str(trans_ref), str(cust_ref)] + details_list))
#         logger.info(f"Final details string: {details}")

#         logger.info("--- Creating transaction object ---")
#         new_obj = {
#             "date_and_time": formatted_date,
#             "transaction_reference": trans_ref,
#             "customer_reference": cust_ref,
#             "debit": withdrawal,
#             "Receivable_Amount": deposit+withdrawal,
#             "account_name": headersdata2[2],  
#             "currency": headersdata2[1],       
#             "details": details
#         }
#         logger.info(f"New transaction object: {new_obj}")
        
#         total_credit += deposit
#         total_debit += withdrawal
#         logger.info(f"Updated totals - total_credit: {total_credit}, total_debit: {total_debit}")
        
#         # If needed, you can add other constant header keys:
#         new_obj.update({
#             "payment_amount": total_credit,
#             "receipt_amount": total_debit,
#             "error_message": ""
#         })
#         logger.info(f"Transaction object after update: {new_obj}")
#         new_table_data.append(new_obj)

#     # Replace the original table_data with the new_table_data
#     logger.info("--- Replacing table_data with new_table_data ---")
#     logger.info(f"new_table_data length: {len(new_table_data)}")
#     table_data = new_table_data
    
#     logger.info("--- Processing file debit sign ---")
#     if isinstance(file_debit, (int, float)) and file_debit > 0:
#             file_debit = -abs(file_debit)
#             logger.info(f"File debit made negative: {file_debit}")

#     logger.info("--- Validating totals ---")
#     if headersdata3:
#         logger.info(f"Comparing totals - file_credit: {file_credit}, total_credit: {total_credit}")
#         logger.info(f"Comparing totals - file_debit: {file_debit}, total_debit: {total_debit}")
        
#         if file_credit == total_credit and file_debit == total_debit:
#             logger.info("Totals match - returning data")
#             return table_data, total_debit, total_credit, error_message #debit, credit
#         else:
#             error_message = "Credit or Debit Total in file is not matching with the actual records total."
#             logger.error(f"VALIDATION ERROR: {error_message}")
#             logger.error(f"Differences - credit: {file_credit - total_credit}, debit: {file_debit - total_debit}")

#     logger.info("--- Returning None due to validation failure or missing headers3 ---")
#     return None, None, None, error_message

# According to new format 13-03-2026
def parse_uob_bank_data(file_name):

    logger.info("=== Starting parse_uob_bank_data ===")
    logger.info(f"Input file_name: {file_name}")

    error_message = ""
    total_credit = 0
    total_debit = 0

    try:

        sheet = open_sheet(file_name, None)
        rows, cols = sheet.shape

        account_name = ""
        currency = ""

        value_date_row = None
        note_row = None
        file_credit = 0
        file_debit = 0

        logger.info("Scanning sheet for keys...")

        for r in range(rows):
            for c in range(cols):

                cell = str(sheet.iloc[r, c]).strip()

                if cell.lower() == "account name:" or cell.lower() == "account name":
                    account_name = str(sheet.iloc[r, c+1]).strip()

                if cell.lower() == "account currency:" or cell.lower() == "account currency":
                    currency = str(sheet.iloc[r, c+1]).strip()

                if cell.lower() == "value date":
                    value_date_row = r

                if cell.lower().startswith("note"):
                    note_row = r

                if "total in account currency" in cell.lower():
                    try:
                        file_credit = float(str(sheet.iloc[r, c+1]).replace(",", "").strip())
                        file_debit = float(str(sheet.iloc[r, c+2]).replace(",", "").strip())
                    except:
                        file_credit = 0
                        file_debit = 0

        logger.info(f"Account Name: {account_name}")
        logger.info(f"Currency: {currency}")
        logger.info(f"Table starts at row: {value_date_row}")
        logger.info(f"Table ends before row: {note_row}")

        table_sheet = open_sheet(file_name, value_date_row)

        table_data = parse_uob_table_data(table_sheet, note_row - value_date_row - 1)

        new_table_data = []

        for row in table_data:

            row = {k.strip(): v for k, v in row.items()}

            date_val = str(row.get("Value Date", "")).strip()
            # Skip rows with invalid dates
            if not date_val or date_val.lower() == 'nan':
                logger.warning(f"Skipping row due to invalid date: {date_val}")
                continue

            deposit = row.get("Deposit", 0)
            print('deposit', deposit, type(deposit))
            withdrawal = row.get("Withdrawal", 0)
            print('withdrawal', withdrawal, type(withdrawal))

            if pd.isna(deposit):
                deposit = 0
            if pd.isna(withdrawal):
                withdrawal = 0

            # Convert safely
            try:
                deposit = float(str(deposit).replace(",", "").strip())
            except (ValueError, TypeError):
                deposit = 0

            try:
                withdrawal = float(str(withdrawal).replace(",", "").strip())
            except (ValueError, TypeError):
                withdrawal = 0

            if withdrawal > 0:
                withdrawal = -abs(withdrawal)

            formatted_date = datetime.strptime(date_val, "%d/%m/%Y").strftime("%Y-%m-%d")

            description = str(row.get("Description", "")).strip()

            new_obj = {
                "date_and_time": formatted_date,
                "transaction_reference": "",
                "customer_reference": "",
                "debit": withdrawal,
                "Receivable_Amount": deposit + withdrawal,
                "account_name": account_name,
                "currency": currency,
                "details": description
            }

            total_credit += deposit
            total_debit += withdrawal

            new_obj.update({
                "payment_amount": total_credit,
                "receipt_amount": total_debit,
                "error_message": ""
            })

            new_table_data.append(new_obj)

        logger.info(f"File Credit: {file_credit}, Calculated Credit: {total_credit}")
        logger.info(f"File Debit: {file_debit}, Calculated Debit: {total_debit}")

        if isinstance(file_debit, (int, float)) and file_debit > 0:
            file_debit = -abs(file_debit)
            logger.info(f"File debit made negative: {file_debit}")

        if round(file_credit, 2) == round(total_credit, 2) and round(file_debit, 2) == round(total_debit, 2):
            logger.info("Totals match - returning parsed data")
            return new_table_data, total_debit, total_credit, error_message
        else:
            error_message = "Credit or Debit Total in file is not matching with the actual records total."
            logger.error(error_message)
            logger.error(f"Credit difference: {file_credit - total_credit}")
            logger.error(f"Debit difference: {file_debit - total_debit}")

            return None, None, None, error_message

    except Exception as e:

        logger.error(str(e))
        error_message = str(e)

        return None, None, None, error_message


def parse_cibc_bank_data(file_name):
    logger.info(f"In the parse_cibc_bank_data function")
    table_data, debit_amount, credit_amount, error_message = parse_cibc_bank_table_data(file_name)
    return table_data, debit_amount, credit_amount, error_message

# TYPE 2 OF BANK SHEET
def parser_2(file_name):
    # Initialize headers according to the excel sheet
    headers = [
        ["Account Number", "R"],
        ["Account Title", "R"],
        ["Account Currency", "R"],
    ]
    # Get reference to the sheet
    sheet_for_header = open_sheet(file_name)
    # get all the headers value
    headersdata = parse_headers(sheet_for_header, headers)
    dataheaders = {
        "account_number": headersdata[0],
        "account_name": headersdata[1],
        "currency": headersdata[2],
        "bank_name": "Moasic limites",  # Bank name is not availabe in the sheet so use static name
    }
    header_row = find_header_row(sheet_for_header, "Transaction Remarks")
    sheet_for_table = open_sheet(file_name, header_row)
    table_data = parse_table_data2(sheet_for_table)
    for obj in table_data:
        obj.update(dataheaders)
    return table_data


# TYPE 3 OF BANK SHEET
def parser_3(file_name):
    # Initialize headers according to the excel sheet
    headers = [
        ["Account name", "C"],
        ["Account number", "C"],
        ["Bank name", "C"],
        ["Currency", "C"],
    ]
    # Get reference to the sheet
    sheet_for_headers = open_sheet(file_name, header_row=None)
    # get all the headers value
    headersdata = parse_headers(sheet_for_headers, headers)
    dataheaders = {
        "account_number": headersdata[1],
        "account_name": headersdata[0],
        "currency": headersdata[3],
        "bank_name": headersdata[2],
    }
    header_row = find_header_row(sheet_for_headers, "IBAN")
    sheet_for_table = open_sheet(file_name, header_row)
    table_data = parse_table_data3(sheet_for_table)
    for obj in table_data:
        obj.update(dataheaders)
    return table_data
