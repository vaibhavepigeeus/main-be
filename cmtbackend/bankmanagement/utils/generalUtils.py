import os
import pandas as pd
from os import listdir
from os.path import isfile, join
import json
import re
from datetime import datetime
from decouple import config


FILE_PATH = config("BANK_FILES_PATH")


# Check for excel files extension
def isExcelFile(file_name=""):
    return file_name.endswith(".xls") or file_name.endswith(".xlsx")


# Read current directory and return list of excel files only
def getExcelFiles(folder_path=""):
    onlyfiles = [f for f in listdir(folder_path) if isfile(join(folder_path, f))]
    excelFiles = filter(isExcelFile, onlyfiles)
    return list(excelFiles)


# open the sheet and returns its reference
def open_sheet(file_path, header_row=None):
    try:
        full_file_path = get_file_path(file_path)
        workbook = pd.read_excel(full_file_path, header=header_row, engine="openpyxl")
        return workbook
    except FileNotFoundError as e:
        print(f"Error: File not found at {file_path} and Error: {e}")
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")


# To Find header row
def find_header_row(workbook, header):
    try:
        rows, cols = workbook.shape
        for row_num in range(rows):
            for col_num in range(cols):
                cell_value = workbook.iloc[row_num, col_num]
                if str(cell_value).strip() == str(header).strip():
                    return row_num
    except Exception as e:
        print("Header Finding Error : ", e)
        return None


# This will be used to filter a list to only contain specific items
def filter_fileds(fields_given=[], fields_required=[]):
    fields = []
    for field in fields_given:
        for f in fields_required:
            if field == f[0]:
                fields.append(field)
    return fields


def save_data_to_json(parsed_data, name):
    # Check if the outputs directory exists, if not, create it
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
    # Write data to JSON file
    with open(f"outputs/{name}.json", "w") as json_file:
        json.dump(parsed_data, json_file, indent=4)


from datetime import datetime


def convert_to_yyyy_mm_dd(date_string=""):
    try:
        date_str = str(date_string).replace(" 00:00:00", "")

        # Check if the input date string is already in the desired format
        if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
            return date_str

        # Parse the input date string into a datetime object
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")

        # Format the datetime object into yyyy-mm-dd
        formatted_date = date_obj.strftime("%Y-%m-%d")
        return formatted_date
    except ValueError:
        print(
            "Invalid date format. Please enter date in yyyy-mm-dd format.", date_string
        )
        return None


def extract_account_number_and_date(file_name=""):
    # Define the regex pattern to match the file name format
    pattern = r".+-(\d{2}-\d{2}-\d{4})\.xls(x?)$"
    # Match the pattern against the file name
    match = re.match(pattern, file_name)

    if match:
        str_arr = file_name.split(".")
        extension = str_arr.pop()
        str_arr = ".".join(str_arr).split("-")
        year = int(str_arr.pop())
        month = int(str_arr.pop())
        day = int(str_arr.pop())
        account_number = "-".join(str_arr)
        date = datetime(year, month, day)

        # Relacing account number to handle /(slash) and -(hypen) case
        ac_number = account_number
        if str(account_number) ==  "16770019":
            ac_number = "1/6770/019"
        
        if str(account_number) ==  "011302460502":
            ac_number = "011-302460-502"

        if str(account_number) ==  "011248663501":
            ac_number = "011-248663-501"

        return ac_number, date, extension
    else:
        return None, None, None


def get_file_path(file_name):
    return os.path.join(FILE_PATH, file_name)


def purge_file(file_name, user_id):         # CMT-25
    try:
        full_path = get_file_path(f'{user_id}_{file_name}')
        path = get_file_path(full_path)
        os.remove(path)
    except Exception as e:

        print("Error purging file:", e)
