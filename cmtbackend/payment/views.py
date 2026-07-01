from django.shortcuts import render
from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework import status
from .pagination import *
from .serializers import *
from rest_framework import generics, status
from rest_framework.response import Response
import pandas as pd
import math
import os
import datetime
from pathlib import Path
from decouple import config
from pandas import *

from sqlalchemy import create_engine
from django.conf import settings
from rest_framework.views import APIView
import re
from documents.models import Documents, BankExchangeRate
import boto3
from django.db.models.functions import Cast
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from .models import PaymentTreasury, PaymentFile
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend

import csv
import psycopg2
# import xlrd
from openpyxl import Workbook
import numpy as np
import requests
from rest_framework.exceptions import APIException
import logging

logger = logging.getLogger('bankmanagement')
from .models import PaymentDatasheet
from bankmanagement.models import CashAllocation, CashTrackerReport, CashAllocationCorrective
from django.db import connection
from decimal import Decimal
from django.db import transaction
import random
from django.db.models import Max, Sum, Q, DateField, FloatField

from django.core.serializers import serialize
import json
import csv
from rest_framework.renderers import JSONRenderer
from rest_framework.decorators import api_view
import locale
from django.db.models import Subquery, OuterRef

column_check_patterns = {
    'coverholdname': r'^coverholder\s*name$',
    'yearofaccount': r'^year\s*of\s*account$|^yoa$|^yearofaccount$',
    'umr': r'^umr$|^unique\s*market\s*reference\s*\(umr\)$',
    'agreementno': r'^agreement\s*no$|^agreement\s*number$',
    'certificateref': r'^certificate\s*ref$|^certificate\s*reference$',
    'classofbusiness': r'^class\s*of\s*business$',
    'risktransactiontype': r'^risk,\s*transaction\s*type$|^transaction\s*type$',
    'country': r'^\s*(domicile\s+country|risk\s+location\s+country|country)\s*$',
    'participatinginsure': r'^insure$|^insurer$|^insured$|^participating\s*insurer$',
    'settlementcurrency': r'^(settlement\s*currency|sett\s*ccy)$',
    'originalcurrency': r'^original\s*currency$|^orig\s*ccy$',
    'commissionper': r'^commission\s*%$',
    'brokpremper': r'^brokerage\s*%$|^brokerage\s*% of gross\s*premium$',
    'percentforlloyds': r'^% for lloyd\'s$|^lloyds\s*%$',
    'rateofexchange': r'^rate\s*of\s*exchange$|^sett\s*roe$',
    'grosspremiumpaidthistime': r'^gross\s*premium\s*paid\s*this\s*time$',
    'commissionamount': r'^commission\s*amount$',
    'finalnetpremiumsc': r'^final\s*net\s*premium\s*\(settlement\s*currency\)$|^final\s*net\s*premium\s*sett$|^final\s*net$',
    'brokerageamountsc': r'^brokerage\s*amount\s*\(settlement\s*currency\)$',
}

def write_dict_to_csv(data_dict, file_name):
    # Determine the year from the file name or another relevant field
    year = extract_year(file_name)
    premium_bdx_folder = config('BDX_FILES_PATH')
    year_folder_path = '{}/{}'.format(premium_bdx_folder, year)
    full_path = os.path.join(year_folder_path, file_name)

    # Ensure the directory exists
    os.makedirs(year_folder_path, exist_ok=True)

    # Write data to CSV
    with open(full_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Assuming the dictionary is a list of dictionaries
        headers = data_dict[0].keys() if data_dict else []
        writer.writerow(headers)
        for row in data_dict:
            writer.writerow(row.values())

    return full_path

def write_queryset_to_csv(queryset, file_name):
    # Serialize queryset to JSON then convert to dictionary
    data_json = serialize('json', queryset)
    data_dict = json.loads(data_json)

    # Extract actual data from serialization
    clean_data = [item['fields'] for item in data_dict]

    # Now use the same CSV writing logic
    return write_dict_to_csv(clean_data, file_name)


AWS_S3_PROCESSED_BUCKET = config('AWS_S3_PROCESSED_BUCKET')
bucket_name = config('PREMIUMBDX_FILE_STORAGE_BUCKET')


def convert_date(dateStr):
    format_str = "%d-%m-%Y %H:%M"
    formattedDate = datetime.datetime.strptime(dateStr, format_str).strftime('%Y-%m-%d %H:%M')
    return formattedDate

def extract_month(file_name):
    try:
        month_abbr = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        month_full = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        all_months = month_abbr + month_full
        # all_months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC', 'SEPT']
        elements = [element.strip().lower() for element in file_name.split('_')]
        month = list(set(all_months).intersection(set(elements)))[0]
        return month
    except Exception as e:
        raise APIException("No relevant month was provided in the file name, accpted months: ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC', 'SEPT']")


def extract_year(file_name):
    pattern = r'(\d+)'
    match = re.findall(pattern, file_name.replace('1609', ''))
    if match:
        return match[0]
    else:
        raise APIException("No relevant year was provided in the file name")


def upload_file_to_s3(file, bucketname, recon=None):
    s3_client = boto3.client('s3')
    str_file_name = str(file)
    print("starting upload")
    try:

        if recon:
            full_file_path = config('BANK_FILES_PATH')
            file_path = "{}/{}xlsx".format(AWS_S3_PROCESSED_BUCKET, str_file_name.split('xlsx')[0])
            s3_client.upload_file("{}/{}".format(full_file_path, file), bucketname, file_path)
            s3_file_url = "https://{}.s3.amazonaws.com/{}".format(bucketname, file_path)
            return s3_file_url

        queryset = PremiumBDX.objects.filter(filename=str_file_name, archived=False)
        s3_file_url = None
        if queryset:
            file_path = write_queryset_to_csv(queryset, str_file_name)
            # full_file_path = write_file(file)
            # year = extract_year(str_file_name)
            # file_path = "{}_files/{}xlsx".format(year, str_file_name.split('xlsx')[0])
            s3_client.upload_file(file_path, bucketname, file_path)
            s3_file_url = "https://{}.s3.amazonaws.com/{}".format(bucketname, file_path)

        return s3_file_url

    except Exception as e:
        print("Error while uploading file", str(e))


def extract_brinding_agreement(file_name):
    if 'SCM' in file_name:
        return 'SCM'
    if '1609' in file_name:
        return '1609'


def get_engine():
    db_settings = settings.DATABASES['default']
    try:
        engine = create_engine(
            f"postgresql://{db_settings['USER']}:{db_settings['PASSWORD']}@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}")

    except:
        raise ValueError("Unsupported database backend")
    return engine


# def check_file_exists(file):
#     str_file_name = str(file)
#     year = extract_year(file)
#     premium_bdx_folder = config('PREMIUM_BDX_FILES')
#     PATH = '{}/{}'.format(premium_bdx_folder, year)
#     file_path = "{}/{}".format(PATH, str_file_name)
#     if os.path.exists(file_path):
#         return file_path
#     return False


def write_file(file):
    year = extract_year(str(file))
    premium_bdx_folder = config('BDX_FILES_PATH')
    year_folder_path = '{}/{}'.format(premium_bdx_folder, year)
    full_path = os.path.join(year_folder_path, str(file))
    with open(full_path, 'wb') as actual_file:
        actual_file.write(file.read())
    return full_path


def replace_file(file_name, file_path):
    os.remove(file_path)
    import time
    full_path = os.path.join(file_path, str(file_name))
    with open(full_path, 'wb') as actual_file:
        actual_file.write(file_name.read())
    return True

def check_sheet_exists(file, tab_name):
    df = pd.ExcelFile(file)
    if tab_name in df.sheet_names:
        return True
    else:
        return False

def purge_file(path):
    try:
        os.remove(path)
    except Exception as e:
        print("Error purging file:", e)

def extract_lob(file_name):
    lob_mapping = {
        'CY': 'Cyber',
        'FI': 'Financial Institutions',
        'M&A': 'Merger and Acquisition',
        'OC': 'OCIL',
        'PR': 'Political Risk',
        'PV': 'Political Violence',
        'PL': 'Professional Liability',
        'TL': 'Transactional Liability',
        'WT': 'War and Terrorism',
        'EN': 'Evnironmental',
    }

    try:
        elements = [element.strip().upper() for element in file_name.split('_')]
        lob = list(set(lob_mapping.keys()).intersection(set(elements)))[0]
        return lob
    except Exception as e:
        raise APIException("No relevant LOB was provided in the file name, accepted LOBs: ['CY', 'FI', 'M&A', 'OC', 'PR', 'PV', 'PL', 'TL', 'WT', 'EN']")

def get_header(file,tab_name):
    df = pd.read_excel(file, sheet_name=tab_name, nrows=2000, header=None, engine='openpyxl')
    for index, row in df.iterrows():
        if 'Coverholder Name' in row.values:
            return index 
    raise APIException("Header not found!")

def get_df(filename_str, file, tab_name):
    try:
        split_filename = filename_str.split('_')
        month_abbr = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        month_full = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        months = month_abbr + month_full

        if split_filename[0].lower() != 'prembdx':
            return "error", "Prefix of filename is not valid!"
        elif split_filename[1].lower() not in ['scm', '1609']:
            return "error", "SCM value not allowed!"
        elif split_filename[2].lower() not in ["cy", "fi", "m&a", "oc", "pr", "pv", "pl", "tl", "w&t", "wt", "war & terrorism", "en"]:
            return "error", "LOB value not allowed!"
        elif split_filename[3].lower() not in ["mais", "mas1", "mca1", "mdu1", "meea", "meu2", "msbl", "mssl", "mpte", "misc", "dubai", "difc", "asta", "germany", "msbl", "singapore", "transverse"]:
            return "error", "Entity value not allowed!"
        elif split_filename[4].lower() in months or split_filename[5].lower() in months:
            if split_filename[4].lower() not in months:
                if split_filename[4].lower() not in ['acrisure', 'bms', 'aon', 'willis', 'incyde', 'transverse', 'everen', 'accredited', 'pg', 'project genie', 'correction', 'project arch', 'ate', 'lancashire', 'aspen', 'fineart']:
                    return "error", "Partner value not allowed!"
                elif len(split_filename[6]) == 4:
                    try:
                        int(split_filename[6])
                    except:
                        return "error", "Year value not allowed!"
            elif len(split_filename[5]) == 4:
                try:
                    int(split_filename[5])
                except:
                    return "error", "Year value not allowed!"
        else:
            return "error", "Month value not allowed!"
        
    except Exception as e:
        return "error", "Invalid filename format!"

    month = extract_month(filename_str)
    year = extract_year(filename_str)
    filename = filename_str
    lob = extract_lob(filename_str)
    folder = 'premiumbdx'
    try:
        header_value = get_header(file, tab_name)
        df = pd.read_excel(file, sheet_name=tab_name, header=header_value, nrows=2000, engine='openpyxl')
    except Exception as e:
        return "error", str(e)
    
    df = df.replace({pd.NaT: 0.00})
    
    if not df['Coverholder Name'].isnull().all():
        df = df.fillna(0.00)
        df = df[df['Coverholder Name'].str.contains('mosaic', case=False, na=False)]
    else:
        return "error", "Bank value not allowed in Coverholder Name column!"

    xl = pd.ExcelFile(file)
    bindingagreement = extract_brinding_agreement(filename_str)
    sheettab = xl.sheet_names
    processingdate = datetime.datetime.now().date().strftime("%Y-%m-%d")
    pd.set_option('display.max_columns', 200)
    columns_dict = df.to_dict('list')
    all_columns = ["Coverholder Name", "Unique Market Reference (UMR)","umr",  "Agreement No", "Certificate Ref","certificate reference", "Year of Account","yoa", "Class of Business", "Risk, Transaction Type","transaction type", "Country", "Insure","participating insurer","insurer", "insured",  "Settlement Currency (see code list)","sett ccy","settlement currency", "Original Currency","orig ccy", "rate of exchange","sett roe", "Commission %","brokerage %", "Brokerage % of gross premium", "% for Lloyd's", "brokerage","% for lloyd's", "lloyds %", "Gross premium paid this time", "Terrorism premium", "Commission Amount", "Accessori (Italy)", "accessori (italy)", "accessori", "Total Taxes and Levies", "total tax", "Final Net Premium (Original Currency)", "final net premium", "Brokerage Amount (Original Currency)", "Final Net Premium (Settlement Currency)", "final net premium sett", "Brokerage Amount (Settlement Currency)", "brokerage sett", "Folder", "File Name", "Sheet/ Tab", "Binding Agreement", "LOB", "Processing Date", "Month", "Year"]
    keys_to_delete = [column for column in columns_dict.keys() if column.strip().lower() not in [col.lower() for col in all_columns]]
    for column in keys_to_delete:
        del columns_dict[column]
    columns_dict['month'] = [ month for j in range(len(columns_dict[list(columns_dict.keys())[0]])) ]
    columns_dict['year'] = [ year for j in range(len(columns_dict[list(columns_dict.keys())[0]])) ]
    columns_dict['filename'] = [ filename for j in range(len(columns_dict[list(columns_dict.keys())[0]])) ]
    columns_dict['lob'] = [ lob for j in range(len(columns_dict[list(columns_dict.keys())[0]])) ]
    columns_dict['folder'] = [ folder for j in range(len(columns_dict[list(columns_dict.keys())[0]])) ]
    columns_dict['sheettab'] = [tab_name for j in range(len(columns_dict[list(columns_dict.keys())[0]]))]
    columns_dict['bindingagreement'] = [ bindingagreement for j in range(len(columns_dict[list(columns_dict.keys())[0]])) ]
    columns_dict['processingdate'] = [ processingdate for j in range(len(columns_dict[list(columns_dict.keys())[0]])) ]
    columns_dict['archived'] = [ False for j in range(len(columns_dict[list(columns_dict.keys())[0]])) ]
    columns_dict['document_id'] =  [ None for j in range(len(columns_dict[list(columns_dict.keys())[0]])) ]
    return df, columns_dict


def save_datasheet(bdx_id, category):
    bdx_obj = PremiumBDX.objects.get(id=bdx_id)

    if PaymentDatasheet.objects.filter(bdx=bdx_obj).exists():
        datasheet_obj = PaymentDatasheet.objects.filter(bdx=bdx_obj).last()
        return datasheet_obj
    else:
        # line_of_business determination
        lob_map = {
            "CY": "Cyber",
            "FI": "Financial Institutions",
            "M&A": "Merger and Acquisition",
            "OC": "OCIL",
            "PR": "Political Risk",
            "PV": "Political Violence",
            "PL": "Professional Liability",
            "TL": "Transactional Liability",
            "W&T": "War and Terrorism",
            "WT": "War and Terrorism",
            "War & Terrorism": "War and Terrorism",
            "EN": "Environmental"
        }
        lob = ""
        for key, value in lob_map.items():
            if key in bdx_obj.certificateref:
                lob = value
                break

        # Raw SQL to fetch placingbroker based on matching UMR
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT a.placingbroker, a.participation
                FROM prem_scmagreement a
                JOIN payment_premiumbdx b ON a.umr = b.umr
            """)
            result = cursor.fetchall()

        # Process the result of placing_broker
        try:
            placing_broker = result[0][0]
            participation = result[0][1]
        except:
            placing_broker = None
            participation = None

        # Getting value of rebet
        if placing_broker == "Everen" or "Inver Re" or "Transverse" or "Aon":
            rebate = 0
        elif bdx_obj.umr == 23 and participation == "mosaic":
            rebate = 0
        else:
            rebate = ((bdx_obj.grosspremiumpaidthistime * 0.025) * 0.5) / bdx_obj.rateofexchange

        # Optimized retrieval of bank account details
        cash_allocation = CashAllocation.objects.filter(policy_id=bdx_obj.certificateref).first()
        if cash_allocation and cash_allocation.bank_txn:
            transfer_to_pt_bank_account_name = cash_allocation.bank_txn.PT_Receving_Bank_Name
            bank_details = cash_allocation.bank_txn.bank_details
            if bank_details:
                receiving_bank_account_name = bank_details.bank_name
                receiving_bank_account = bank_details.account_number
            else:
                receiving_bank_account_name = None
                receiving_bank_account = None
        else:
            transfer_to_pt_bank_account_name = None
            receiving_bank_account_name = None
            receiving_bank_account = None

        # Getting value of payment_id

        try:
            if bdx_obj.month.isdigit():
                payment_id = placing_broker[:4] + str(bdx_obj.year)[2:4] + bdx_obj.month
            else:
                month_number = {
                    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                    'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                    'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                }.get(bdx_obj.month[:3].lower(), '01')
                payment_id = placing_broker[:4] + str(bdx_obj.year)[2:4] + month_number
        except:
            try:
                payment_id = placing_broker[:4] + str(bdx_obj.year)[2:4] + bdx_obj.month
            except:
                payment_id = str(random.randint(1000, 9999)) + str(bdx_obj.year)[2:4] + bdx_obj.month

        # Getting value of rateofexchange
        rateofexchange = CashTrackerReport.objects.filter(Policy=bdx_obj.certificateref).first().ROE_Bank_Statement if CashTrackerReport.objects.filter(Policy=bdx_obj.certificateref).exists() else None

        # Getting value of treasury_transfer_date
        treasury_transfer_date = CashAllocationCorrective.objects.filter(policy_id=bdx_obj.certificateref).first().treasury_confirmed_transfer_date if CashAllocationCorrective.objects.filter(policy_id=bdx_obj.certificateref).exists() else None

        # creating datasheet object
        datasheet_obj = PaymentDatasheet.objects.create(
            bdx = bdx_obj,
            amount = None,
            rateofexchange = rateofexchange,
            bdx_month = bdx_obj.month,
            bdx_year = bdx_obj.year,
            line_of_business = lob,
            producing_coverholder = bdx_obj.coverholdname,
            receiving_bank_account_name = receiving_bank_account_name,
            receiving_bank_account = receiving_bank_account,
            transfer_to_pt_bank_account_name = transfer_to_pt_bank_account_name,
            treasury_transfer_date = treasury_transfer_date,
            invoice_bank_account = None,
            final_bank_account = 'ABCD123456789',
            final_bank_name = f'Bank {bdx_obj.id}',
            SCM_NonSCM = bdx_obj.bindingagreement,
            Placing_Broker = placing_broker,
            rebate = rebate,
            net_payment = bdx_obj.finalnetpremiumusd - rebate if bdx_obj.finalnetpremiumusd and rebate else None,
            gross_prem_sett_arch = None,
            net_prem_sett_incld_rebate_arch = None,
            category = category,
            payment_id = payment_id
        )
        print("Datasheet created===========>")
        return datasheet_obj


class PremBDXFileViewSet(viewsets.ModelViewSet):
    pagination_class = CustomPagination
    serializer_class = PremBDXFilesSerializer

    def get_queryset(self):
        return PremBDXFiles.objects.values('id', 'filename', 'sheet_name', 'month', 'year', 'upload_at', 'lob',
                                         'uploaded_by', 'archived', 'number_of_records_uploaded', 'error_message', 
                                         'commission_amount', 'columns_not_found', 'deleted', 'upload_status', 
                                         'is_prembdx_generated', 'is_exception_generated').exclude(archived=True).annotate(total=Sum('final_net_payment')).annotate(
            total=Sum(Cast('final_net_payment', output_field=FloatField()))
        )

    def list(self, request, *args, **kwargs):
        page_number = int(request.GET.get("skip", 0))
        pageSize = int(request.GET.get("pageSize", 20))
        year = int(request.GET.get("year")) if request.GET.get("year") else None
        month = request.GET.get("month", None)
        lob = request.GET.get("lob", None)
        action = request.GET.get("action", None)
        tab_name = request.GET.get('tab_name', None)
        file_name = request.GET.get('file_name', None)
        from_date = request.GET.get('from_date', '1900-04-17')
        to_date = request.GET.get('to_date', '3024-04-17')

        if action == 'view':
            try:
                prem_bdx_objs = PremiumBDX.objects.filter(filename=file_name, sheettab=tab_name, archived=False).order_by(
                    'processingdate').reverse()
                count = len(prem_bdx_objs)

                excel_columns = ['Coverholder Name', 'Year of Account', 'Unique Market Reference (UMR)',
                                 'Agreement No ', 'Certificate Ref', 'Class of Business', 'Risk, Transaction Type',
                                 'Country', 'Settlement Currency', 'Original Currency', 'Commission %',
                                 'Brokerage % of gross premium', "% for Lloyd's", 'Rate of Exchange',
                                 'Gross premium paid this time', 'Commission Amount',
                                 'Final Net Premium (Settlement Currency)', 'Brokerage Amount (Settlement Currency)',
                                 'Total Taxes and Levies', 'Accessori (Italy)', 'Terrorism premium', 'Participating Insurer', 'File Name',
                                 'Month', 'Year', 'LOB', 'Final Net Premium (Original Currency)', 'Folder', 'Sheettab',
                                 'Binding Agreement', 'Processing Date', 'Archived', 'Document']

                columns_dict = {column: [] for column in excel_columns}

                mapping_columns = {
                    'Coverholder Name': 'coverholdname',
                    'Year of Account': 'yearofaccount',
                    'Unique Market Reference (UMR)': 'umr',
                    'Agreement No ': 'agreementno',
                    'Certificate Ref': 'certificateref',
                    'Class of Business': 'classofbusiness',
                    'Risk, Transaction Type': 'risktransactiontype',
                    'Country': 'country',
                    'Settlement Currency': 'settlementcurrency',
                    'Original Currency': 'originalcurrency',
                    'Commission %': 'commissionper',
                    'Brokerage % of gross premium': 'brokpremper',
                    "% for Lloyd's": 'percentforlloyds',
                    'Rate of Exchange': 'rateofexchange',
                    'Gross premium paid this time': 'grosspremiumpaidthistime',
                    'Commission Amount': 'commissionamount',
                    'Final Net Premium (Settlement Currency)': 'finalnetpremiumsc',
                    'Final Net Premium (Original Currency)': 'fnporiginalcurrency',
                    'Brokerage Amount (Settlement Currency)': 'brokerageamountsc',
                    'Total Taxes and Levies': 'totaltaxesandlevies',
                    'Accessori (Italy)': 'accessoriitaly',
                    'Terrorism premium': 'terrorismpremium',
                    'Folder': 'folder',
                    'Sheettab': 'sheettab',
                    'Binding Agreement': 'bindingagreement',
                    'Processing Date': 'processingdate',
                    'Archived': 'archived',
                    'Document': 'document',
                    'File Name': 'filename',
                    'Month': 'month',
                    'Year': 'year',
                    'LOB': 'lob',
                    'Participating Insurer': 'insure'
                }

                for prem_bdx_obj in prem_bdx_objs:
                    for key in mapping_columns.keys():
                        if key == 'Document':
                            columns_dict[key].append(
                                getattr(prem_bdx_obj, mapping_columns[key]).document_name) if getattr(prem_bdx_obj,
                                                                                                      mapping_columns[
                                                                                                          key]) else None
                        else:
                            # Set the locale to 'en_US.UTF-8' to ensure numbers are formatted with commas
                            try:
                                locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
                            except locale.Error:
                                print("Locale not supported, falling back to default.")
                                locale.setlocale(locale.LC_ALL, '')  # Use the default locale; may not format with commas
                            value = getattr(prem_bdx_obj, mapping_columns[key])
                            # listed all the amount fields and adding comma and decimal places
                            if key in ['Commission %', 'Brokerage % of gross premium', "% for Lloyd's", 'Rate of Exchange', 'Gross premium paid this time', 'Commission Amount', 'Final Net Premium (Settlement Currency)', 'Brokerage Amount (Settlement Currency)', 'Total Taxes and Levies', 'Accessori (Italy)', 'Terrorism premium', 'Final Net Premium (Original Currency)'] and value is not None:
                                formatted_value = locale.format_string("%0.2f", value, grouping=True)
                                columns_dict[key].append(formatted_value)
                            # adding date format                          
                            elif key in ['Processing Date']:
                                # Check if the value is an instance of a date before formatting
                                if isinstance(value, datetime.date):
                                    columns_dict[key].append(value.strftime('%d-%m-%Y'))
                                else:
                                    # Handle the case where value is not a date (e.g., return as is or log a warning)
                                    columns_dict[key].append(value)  # or handle it differently if needed
                            else:
                                columns_dict[key].append(value)                
                    total_aggregates = self.get_queryset().filter(
                        filename=file_name,
                        sheet_name=tab_name
                    ).aggregate(
                        total=Sum(Cast('final_net_payment', FloatField())),
                        total_commission=Sum(Cast('commission_amount', FloatField()))
                    )

                    total_value = total_aggregates['total']
                    total_commission = total_aggregates['total_commission']
                return Response({'Response': columns_dict, 'count': count, 'total': total_value, 'total_commission': total_commission, 'tab_name': tab_name}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'Response': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'download':
            try:
                prem_bdx_objects = PremiumBDX.objects.filter(filename=file_name, sheettab=tab_name, archived=False)
                response = {}
                for prem_bdx_obj in prem_bdx_objects:
                    doc_objs = Documents.objects.filter(id=prem_bdx_obj.document_id)
                    for doc_obj in doc_objs:
                        response[doc_obj.document_name] = doc_obj.document_url
                return Response({'Data': response}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'Response': str(e)}, status=status.HTTP_400_BAD_REQUEST)


        skip = page_number * pageSize

        # Consolidate filter conditions
        filter_conditions = Q(archived=False, upload_at__gt=from_date, upload_at__lt=to_date)
        
        # Add conditional filters based on the presence of query parameters
        if month:
            filter_conditions &= Q(month__startswith=month[:3].upper())
        if file_name:
            filter_conditions &= Q(filename__icontains=file_name)
        if lob:
            filter_conditions &= Q(lob__icontains=lob)
        if year:
            filter_conditions &= Q(year__icontains=str(year))

        # Retrieve the filtered queryset and annotate with processing date as date
        filtered_queryset = self.get_queryset().filter(filter_conditions).annotate(
            processingdate_as_date=Cast('upload_at', DateField())
        ).order_by('-upload_at')  # Use '-' prefix for descending order directly

        pk = request.query_params.get('pk')
        if pk:
            try:
                doc = self.get_queryset().get(pk=pk)
                serializer = self.serializer_class(doc)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except PremBDXFiles.DoesNotExist:
                return Response({"message": "PremiumBDX File instance not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Prefetch user names to reduce database hits
            user_ids = {query['uploaded_by'] for query in filtered_queryset}
            user_names = Users.objects.filter(id__in=user_ids).values_list('id', 'user_name')
            user_name_map = {user_id: name for user_id, name in user_names}

            # Generate data list
            data_list = [
                {
                    'id': query['id'],
                    'filename': query['filename'],
                    'sheettab': query['sheet_name'],
                    'month': query['month'],
                    'year': query['year'],
                    'processingdate': query['upload_at'],
                    'total': query['total'],
                    'count': query['number_of_records_uploaded'],
                    'Analyst Name': user_name_map.get(query['uploaded_by']),
                    'lob': query['lob'],
                    'archived': query['archived'],
                    'error_message': query['error_message'],
                    'commission_amount': query['commission_amount'],
                    'columns_not_found': query['columns_not_found'],
                    'deleted': query['deleted'],
                    'upload_status': query['upload_status'],
                    'is_prembdx_generated': query['is_prembdx_generated'],
                    'is_exception_generated': query['is_exception_generated']
                }
                for query in filtered_queryset
            ]
            if data_list:
                return Response({'data': data_list[skip: skip + pageSize], 'count': len(data_list)},
                                status=status.HTTP_200_OK)
            else:
                return Response({'data': data_list, 'count': 0}, status=status.HTTP_200_OK)

class PremiumBDXReport(generics.ListAPIView):
    pagination_class = CustomPagination
    serializer_class = PremiumBDXSerializer

    def save_uploaded_file_to_new_folder(self, file):
        try:
            new_folder = config('BDX_FILES_PATH')
            os.makedirs(new_folder, exist_ok=True)
            file_path = os.path.join(new_folder, file.name)
            
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            return True, "File saved successfully."
        except Exception as e:
            print("error in save_uploaded_file_to_new_folder", e)
            return False, str(e)

    def get_queryset(self):

        return PremiumBDX.objects.filter(archived=False).values('filename', 'sheettab', 'month', 'year', 'processingdate', 'lob',
                                         'analyst_id_id', 'archived').annotate(total=Sum('fnporiginalcurrency'))

    def get(self, request, *args, **kwargs):
        page_number = int(request.GET.get("skip", 0))
        pageSize = int(request.GET.get("pageSize", 20))
        year = int(request.GET.get("year")) if request.GET.get("year") else None
        month = request.GET.get(""
                                "h", None)
        lob = request.GET.get("lob", None)
        action = request.GET.get("action", None)
        tab_name = request.GET.get('tab_name', None)
        file_name = request.GET.get('file_name', None)
        from_date = request.GET.get('from_date', '1900-04-17')
        to_date = request.GET.get('to_date', '3024-04-17')
        certificateref = request.GET.get('Certificate_Ref', None)

        # print("certref", certificateref)

        if action == 'view':
            try:
                prem_bdx_objs = PremiumBDX.objects.filter(filename=file_name, sheettab=tab_name, archived=False).order_by(
                    'processingdate').reverse()
                data_dict = {}
                excel_columns = ['Coverholder Name', 'Year of Account', 'Unique Market Reference (UMR)',
                                 'Agreement No ', 'Certificate Ref', 'Class of Business', 'Risk, Transaction Type',
                                 'Country', 'Settlement Currency', 'Original Currency', 'Commission %',
                                 'Brokerage % of gross premium', "% for Lloyd's", 'Rate of Exchange',
                                 'Gross premium paid this time', 'Commission Amount',
                                 'Final Net Premium (Settlement Currency)', 'Brokerage Amount (Settlement Currency)',
                                 'Total Taxes and Levies', 'Accessori (Italy)', 'Terrorism premium', 'filename',
                                 'month', 'year', 'lob', 'Final Net Premium (Original Currency)', 'Folder', 'Sheettab',
                                 'Binding Agreement', 'Processing Date', 'Archived', 'Document']

                columns_dict = {column: [] for column in excel_columns}

                mapping_columns = {
                    'Coverholder Name': 'coverholdname',
                    'Year of Account': 'yearofaccount',
                    'Unique Market Reference (UMR)': 'umr',
                    'Agreement No ': 'agreementno',
                    'Certificate Ref': 'certificateref',
                    'Class of Business': 'classofbusiness',
                    'Risk, Transaction Type': 'risktransactiontype',
                    'Country': 'country',
                    'Settlement Currency': 'settlementcurrency',
                    'Original Currency': 'originalcurrency',
                    'Commission %': 'commissionper',
                    'Brokerage % of gross premium': 'brokpremper',
                    "% for Lloyd's": 'percentforlloyds',
                    'Rate of Exchange': 'rateofexchange',
                    'Gross premium paid this time': 'grosspremiumpaidthistime',
                    'Commission Amount': 'commissionamount',
                    'Final Net Premium (Settlement Currency)': 'finalnetpremiumsc',
                    'Final Net Premium (Original Currency)': 'fnporiginalcurrency',
                    'Brokerage Amount (Settlement Currency)': 'brokerageamountsc',
                    'Total Taxes and Levies': 'totaltaxesandlevies',
                    'Accessori (Italy)': 'accessoriitaly',
                    'Terrorism premium': 'terrorismpremium',
                    'Folder': 'folder',
                    'Sheettab': 'sheettab',
                    'Binding Agreement': 'bindingagreement',
                    'Processing Date': 'processingdate',
                    'Archived': 'archived',
                    'Document': 'document',
                }

                for prem_bdx_obj in prem_bdx_objs:
                    for key in mapping_columns.keys():
                        if key == 'Document':
                            columns_dict[key].append(
                                getattr(prem_bdx_obj, mapping_columns[key]).document_name) if getattr(prem_bdx_obj,
                                                                                                      mapping_columns[
                                                                                                          key]) else None
                        else:
                            columns_dict[key].append(getattr(prem_bdx_obj, mapping_columns[key]))
                return Response({'Response': columns_dict}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'Response': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'download':
            try:
                prem_bdx_objects = PremiumBDX.objects.filter(filename=file_name, sheettab=tab_name, archived=False)
                response = {}
                for prem_bdx_obj in prem_bdx_objects:
                    doc_objs = Documents.objects.filter(id=prem_bdx_obj.document_id, archived=False)
                    for doc_obj in doc_objs:
                        response[doc_obj.document_name] = doc_obj.document_url
                return Response({'Data': response}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'Response': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        skip = page_number * pageSize

        queryset = (
            self.get_queryset()
        )
        filtered_queryset = queryset.annotate(
            processingdate_as_date=Cast('processingdate', DateField())
        ).filter(
            processingdate_as_date__gt=from_date
        ).filter(
            processingdate_as_date__lt=to_date
        ).filter(
            archived=False
        ).order_by('processingdate').reverse()
        pk = request.query_params.get('pk')
        if pk:
            try:
                doc = PremiumBDX.objects.get(pk=pk)
                serializer = self.serializer_class(doc)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except PremiumBDX.DoesNotExist:
                return Response({"message": "PremiumBDX instance not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            # data = self.get_queryset()
            print("filtered queryset", filtered_queryset)

            data_list = [
                {
                    'filename': query['filename'],
                    'sheettab': query['sheettab'],
                    'month': query['month'],
                    'year': query['year'],
                    'processingdate': query['processingdate'],
                    'total': query['total'],
                    'count': PremiumBDX.objects.filter(filename=query['filename'], archived=False).count(),
                    'Analyst Name': (Users.objects.filter(id=query['analyst_id_id']).first()).user_name if (
                        Users.objects.filter(id=query['analyst_id_id']).first()) else None,
                    'lob': query['lob'],
                    'archived': query['archived']
                }
                for query in filtered_queryset if (not month or month.lower() in query['month'].lower())
                                                  and (not file_name or file_name.lower() in query[
                    'filename'].lower())
                                                  and (not lob or lob.lower() in query['lob'].lower())
                                                  and (not year or str(year).lower() in str(query['year']).lower())
            ]
            # print("data list", data_list)
            if data_list:
                return Response({'data': data_list[skip: skip + pageSize], 'count': len(data_list)},
                                status=status.HTTP_200_OK)
            else:
                return Response({'data': data_list, 'count': 0}, status=status.HTTP_200_OK)

    def post(self, request):
        # Check payload data and return error if any
        action = request.data['action']
        tab_name = request.data.get('tab_name')
        if not tab_name:
            return Response({"message": "Tab name is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        analyst_id = request.data.get('analyst_id')
        if not analyst_id:
            return Response({"message": "Analyst id is required."}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES.get('file')
        if not file:
            return Response({"message": "File is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Save uploaded file
        self.save_uploaded_file_to_new_folder(file)
        try:
            for i in tab_name.split(","):
                tab_name = i
                str_file_name = str(file)

                if action == 'parse':
                    try:
                        df, columns_dict = get_df(str_file_name, file, tab_name)
                        if PremBDXFiles.objects.filter(filename=str_file_name, sheet_name=tab_name, archived=False).exists():
                            prem_bdx_obj = PremBDXFiles.objects.create(
                            filename=str_file_name,
                            sheet_name=tab_name,
                            upload_status=True,
                            error_message="Duplicate file"
                        )
                        else:
                            prem_bdx_obj = PremBDXFiles.objects.create(
                                filename=str_file_name,
                                sheet_name=tab_name
                            )
                            # Save only filename, sheetname and error message if any
                            if isinstance(df, str):
                                prem_bdx_obj.error_message = columns_dict
                                prem_bdx_obj.upload_status = True
                                prem_bdx_obj.save()
                                # return Response({'Response': columns_dict}, status=status.HTTP_400_BAD_REQUEST)
                                continue

                            # Sum of Final Net Premium (Settlement Currency)
                            premium_total = 0
                            commission_amount_total = 0
                            try:
                                premium_total = sum(columns_dict.get('Final Net Premium Sett', [])) or sum(columns_dict.get('Final Net Premium (Settlement Currency)', []))
                                if not premium_total:
                                    prem_bdx_obj.columns_not_found = "Final Net Premium Sett or Final Net Premium (Settlement Currency)"
                                    prem_bdx_obj.save()
                            except:
                                pass
                            
                            try:
                                # Use values from column_check_patterns as required columns
                                required_columns = list(column_check_patterns.keys())
                                matched_columns = {}
                                for column in df.columns:
                                    # Strip spaces from column name
                                    stripped_column = column.strip()
                                    for key, pattern in column_check_patterns.items():
                                        if re.match(pattern, stripped_column, re.IGNORECASE):
                                            matched_columns[key] = column
                                            break

                                # Now use matched_columns to sum up the 'commissionamount' if it exists
                                commission_key = 'commissionamount'
                                if commission_key in matched_columns:
                                    commission_amount_total = df[matched_columns[commission_key]].sum()

                                # Check if all required columns were found
                                missing_columns = []
                                for col in required_columns:
                                    if col not in matched_columns:
                                        if col in ['participatinginsure', 'brokerageamountsc'] and '1609' in prem_bdx_obj.filename:
                                            pass
                                        else:
                                            missing_columns.append(col)
                                        
                                if missing_columns:
                                    # Collect actual column names for the missing columns
                                    # actual_missing_columns = [column_check_patterns[col] for col in missing_columns]
                                    missing_columns_str = ", ".join(missing_columns)
                                    if prem_bdx_obj.columns_not_found:
                                        prem_bdx_obj.columns_not_found += f", {missing_columns_str}"
                                    else:
                                        prem_bdx_obj.columns_not_found = missing_columns_str
                                    prem_bdx_obj.save()

                            except Exception as e:
                                print("An error occurred while processing columns", e)
                            
                            # Check for null values in columns
                            null_columns = []
                            for key, actual_column in matched_columns.items():
                                if df[actual_column].isnull().all() or (df[actual_column] == 0).all() or (df[actual_column] == 0.0).all():
                                    null_columns.append(actual_column)

                            if null_columns:
                                null_message = ", ".join([f"{field} have all values null" for field in null_columns])
                                prem_bdx_obj.error_message = null_message
                                prem_bdx_obj.save()

                            # create a new object in PremBDXFiles
                            prem_bdx_obj.entity_name=''
                            prem_bdx_obj.month=columns_dict['month'][0]
                            prem_bdx_obj.year=columns_dict['year'][0]
                            prem_bdx_obj.version=''
                            prem_bdx_obj.lob=columns_dict['lob'][0]
                            prem_bdx_obj.scm_status=columns_dict['bindingagreement'][0]
                            prem_bdx_obj.number_of_records_uploaded=len(columns_dict['bindingagreement'])
                            prem_bdx_obj.final_net_payment=premium_total
                            prem_bdx_obj.commission_amount=commission_amount_total
                            prem_bdx_obj.uploaded_by=Users.objects.get(id=analyst_id)
                            prem_bdx_obj.archived=False
                            prem_bdx_obj.save()
                            print("prem_bdx_obj saved=====>")
                    except Exception as e:               
                        # return Response({'Response': str(e)}, status=status.HTTP_400_BAD_REQUEST)
                        continue

                if action == 'replace':
                    ## existing files are getting archive and new files will be saved. It is basically add plus archive
                    try:
                        file = request.FILES['file']
                        tab_name = request.data['tab_name']
                        analyst_id = request.data['analyst_id']
                        old_file_name = request.data['old_file_name']
                        old_tab_name = request.data['old_tab_name']
                        str_file_name = str(file)
                        document_time = datetime.datetime.now()

                        # Upload file to S3
                        file_url = upload_file_to_s3(file, bucket_name)

                        # Insert same file into document
                        document_obj = Documents.objects.create(document_name=str(file),
                                                                document_date=datetime.datetime.now().date(),
                                                                document_type='Premium BDX', archieve_by='Analyst',
                                                                archieve_datetime=document_time, document_url=file_url)

                        # Enter sheet txs in premiumbdx table
                        df = pd.read_excel(file, header=2)
                        df, columns_dict = get_df(str_file_name, file, tab_name)
                        df = pd.DataFrame(columns_dict)
                        df = df.assign(analyst_id_id=[analyst_id for _ in range(0, df.shape[0])])
                        df = df.assign(document_id=[document_obj.id for _ in range(0, df.shape[0])])
                        df = df.assign(old_file_name=[old_file_name for _ in range(0, df.shape[0])])
                        df = df.assign(old_tab_name=[old_tab_name for _ in range(0, df.shape[0])])
                        df = df.assign(migrated_data=[False for _ in range(0, df.shape[0])])
                        df = df.assign(updated_datetime=[document_time for _ in range(0, df.shape[0])])

                        engine = get_engine()
                        df.to_sql('payment_premiumbdx', engine, if_exists='append', index=False, chunksize=100)

                        # Archive old file name and tab name txs
                        prem_bdx_objects = PremiumBDX.objects.filter(filename=old_file_name, sheettab=old_tab_name,
                                                                    migrated_data=False, archived=False)

                        for prem_bdx_obj in prem_bdx_objects:
                            prem_bdx_obj.analyst_id = Users.objects.get(id=analyst_id)
                            prem_bdx_obj.updated_datetime = datetime.datetime.now()
                            prem_bdx_obj.archived = True
                            doc_objs = Documents.objects.filter(id=prem_bdx_obj.document_id, archived=False)
                            for doc_obj in doc_objs:
                                doc_obj.archived = True
                                doc_obj.archieve_by = analyst_id
                                doc_obj.archieve_datetime = datetime.datetime.now()
                                doc_obj.save()

                        return Response({'Message': 'File is replaced successfully'}, status=status.HTTP_200_OK)
                    except Exception as e:
                        return Response({'Response': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            return Response(status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'Error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        id = request.GET.get('id', None)
        analyst_id = request.GET.get('analyst_id', None)
        if id:
            prem_bdx_obj = PremBDXFiles.objects.get(id=id)
            prem_bdx_obj.archived = True
            prem_bdx_obj.save()
            if prem_bdx_obj.month:
                for j in PremiumBDX.objects.filter(filename=prem_bdx_obj.filename, sheettab=prem_bdx_obj.sheet_name, archived=False):
                    j.archived = True
                    j.save()
            # for i in PremiumBDX.objects.filter(filename=file_name, sheettab=tab_name, archived=False):
            #     i.archived = True
            #     i.save()
            # for i in Documents.objects.filter(document_name=file_name, archived=False):
            #     if analyst_id:
            #         i.archieve_by = Users.objects.get(id=analyst_id).user_name
            #     i.archived = True
            #     i.archieve_datetime = datetime.datetime.now()
            #     i.document_url = None
            #     i.save()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response({"error": "Record not found"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST']) 
def read_data(request):
    tab_name = request.POST.get('tab_name')
    file = request.FILES['file']
    analyst_id = request.POST.get('analyst_id')

    try:
        df, columns_dict = get_df(str(file), file, tab_name)
    except Exception as e:
        return Response({'Error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Check for required columns and calculate total if present
    total = 0
    required_columns = ['Final Net Premium Sett', 'Final Net Premium (Settlement Currency)']
    for column in required_columns:
        if column in columns_dict:
            total = sum(columns_dict.get(column, []))
            break
    else:
        return Response({'Response': f'None of the required columns {required_columns} are present.'}, status=status.HTTP_400_BAD_REQUEST)

    # Prepare and return the response
    response_data = {
        'Response': columns_dict,
        'count': len(next(iter(columns_dict.values()), [])),
        'total': total
    }
    return Response(response_data, status=status.HTTP_200_OK)


class PaymentTreasuryViewSet(viewsets.ModelViewSet, generics.UpdateAPIView):
    """
    API endpoint for managing PaymentTreasury objects.
    """
    pagination_class = CustomPagination
    queryset = PaymentTreasury.objects.all()
    serializer_class = PaymentTreasurySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['file_name', 'certificate_ref', 'type_of_payment']

    def get_permissions(self):
        """
        Implement custom permissions if needed (e.g., authentication)
        """
        return []  # Allow all users for now (consider adding authentication later)

    def list(self, request):
        """
        Handles GET requests to retrieve a list of PaymentTreasury objects.
        """
        page_number = int(request.GET.get("skip", 0))
        rows_per_page = int(request.GET.get("pageSize", 20))
        skip = page_number * rows_per_page

        queryset = self.filter_queryset(self.get_queryset())[
                   skip: skip + rows_per_page
                   ]

        # Apply variance condition here

        serializer = self.get_serializer(queryset, many=True)
        response_data = serializer.data
        data = {"count": self.get_queryset().count(), "data": response_data}

        return Response(data)

    def create(self, request):
        """
        Handles POST requests to create a new PaymentTreasury object.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        """
        Handles PATCH requests to partially update a PaymentTreasury object.
        """
        instance = self.get_object()  # Retrieve the object based on the primary key (pk)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PaymentFileViewSet(viewsets.ModelViewSet, generics.UpdateAPIView):
    """
    API endpoint for managing PaymentFile objects.
    """
    pagination_class = CustomPagination
    queryset = PaymentFile.objects.all().order_by('created_date').reverse()
    serializer_class = PaymentFileSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['bdx_file_name', 'certificate_ref']

    def get_permissions(self):
        """
        Implement custom permissions if needed (e.g., authentication)
        """
        return []  # Allow all users for now (consider adding authentication later)

    def list(self, request):
        """
        Handles GET requests to retrieve a list of PaymentTreasury objects.
        """
        page_number = int(request.GET.get("skip", 0))
        rows_per_page = int(request.GET.get("pageSize", 20))
        skip = page_number * rows_per_page

        # June 23 2024 by Aparajita
        overall_status = request.GET.get("overall_status", None)
        overall_status_contains = request.GET.get("overall_status_contains", None)

        queryset = self.filter_queryset(self.get_queryset())
        #
        # Apply variance condition here
        # June 23 2024, by Aparajita
        if overall_status:
            overall_status = overall_status.split(",")
            queryset = queryset.filter(Overall_Status__in=overall_status)
        elif overall_status_contains:
            queryset = queryset.filter(Overall_Status__icontains=overall_status_contains)
        #
        # Apply variance condition here

        # serializer = self.get_serializer(queryset, many=True)
        # response_data = serializer.data
        # June 23 2024, by Aparajita
        count = queryset.count()
        queryset = queryset[
                   skip: skip + rows_per_page
                   ]
        #
        serializer = self.get_serializer(queryset, many=True)
        response_data = serializer.data
        data = {"count": count, "data": response_data}

        return Response(data)

    def create(self, request):
        """
        Handles POST requests to create a new PaymentTreasury object.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        """
        Handles PATCH requests to partially update a PaymentTreasury object.
        """
        instance = self.get_object()  # Retrieve the object based on the primary key (pk)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class ExceptionFileAPIView(APIView, ):
    @transaction.atomic
    def post(self, request):
        try:
            def make_conn():
                try:
                    connection = psycopg2.connect(
                        user=config('DATABASE_USER'),
                        password=config('DATABASE_PASSWORD'),
                        host=config('DATABASE_HOST'),
                        port='5432',
                        database=config('DATABASE_NAME')
                    )
                    return connection

                except (Exception, psycopg2.Error) as error:
                    print("Error while connecting to PostgreSQL:", error)

            def check_entry_one(query):
                connection = make_conn()
                cursor = connection.cursor()
                cursor.execute(query)
                try:
                    data = cursor.fetchone()
                except:
                    data = None
                cursor.close()
                connection.close()
                return data

            def check_entry_all(query):
                connection = make_conn()
                cursor = connection.cursor()
                cursor.execute(query)
                try:
                    data = cursor.fetchall()
                except:
                    data = None
                cursor.close()
                connection.close()
                return data

            def getmonth(filename):

                lfilename = filename.lower()

                # print(f"{lfilename}")

                if "jan" in lfilename:
                    month1 = "January"
                elif "feb" in lfilename:
                    month1 = "February"
                elif "mar" in lfilename:
                    month1 = "March"
                elif "apr" in lfilename:
                    month1 = "April"
                elif "may" in lfilename:
                    month1 = "May"
                elif "jun" in lfilename:
                    month1 = "June"
                elif "jul" in lfilename:
                    month1 = "July"
                elif "aug" in lfilename:
                    month1 = "August"
                elif "sep" in lfilename:
                    month1 = "September"
                elif "oct" in lfilename:
                    month1 = "October"
                elif "nov" in lfilename:
                    month1 = "November"
                elif "dec" in lfilename:
                    month1 = "December"
                else:
                    month1 = ""

                return month1

            def getyear(filename):

                if "2024" in filename or "24" in filename:
                    yearf = "2024"
                elif "2023" in filename or "23" in filename:
                    yearf = "2022"
                elif "2022" in filename or "22" in filename:
                    yearf = "2023"
                elif "2021" in filename or "21" in filename:
                    yearf = "2021"
                else:
                    yearf = ""

                return yearf
            
            action = request.data['action']
            analyst_id = request.data['analyst_id']
            data = request.data['response']
            file_name = data['filename'][0]
            sheet_tab = data['sheettab'][0]
            comments_wf = request.data['comments']

            if action == 'archieve':
                old_file_name = request.data['old_file_name']
                try:
                    prem_bdx_objects = PremiumBDX.objects.filter(filename=old_file_name, archived=False)
                    for prem_bdx_obj in prem_bdx_objects:
                        prem_bdx_obj.archived = True
                        prem_bdx_obj.save()
                        doc_objs = Documents.objects.filter(id=prem_bdx_obj.id)
                        for doc_obj in doc_objs:
                            doc_obj.archived = True
                            doc_obj.archieve_datetime = datetime.datetime.now()
                            doc_obj.archieve_by = analyst_id
                            doc_obj.save()
                    for i in PremBDXFiles.objects.filter(filename=old_file_name, archived=False):
                        i.archived = True
                        i.save() 
                except Exception as e:
                    print("the errror", str(e))
                    return Response({'Error': '{} not found'.format(str(old_file_name))},
                                    status=status.HTTP_404_NOT_FOUND)
                # return Response({'Message': '{} archived successfully'.format(file_name)}, status=status.HTTP_200_OK)

            def get_column_mappings(data, field_patterns):
                column_mappings = {}
                for standard_field, pattern in field_patterns.items():
                    regex = re.compile(pattern, re.IGNORECASE)  # Case insensitive regex
                    matched_key = None
                    for key in data.keys():
                        if regex.match(key):
                            matched_key = key
                            break
                    column_mappings[standard_field] = matched_key
                return column_mappings

            if action == 'add' or action == 'archieve':
                field_patterns = {
                    'coverholdname': r'^coverholder\s*name$',
                    'yearofaccount': r'^year\s*of\s*account$|^yoa$|^yearofaccount$',
                    'umr': r'^umr$|^unique\s*market\s*reference\s*\(umr\)$',
                    'agreementno': r'^agreement\s*no$|^agreement\s*number$',
                    'certificateref': r'^certificate\s*ref$|^certificate\s*reference$',
                    'lob': r'^lob$|^line\s*of\s*business$',
                    'classofbusiness': r'^class\s*of\s*business$',
                    'risktransactiontype': r'^risk,\s*transaction\s*type$|^transaction\s*type$',
                    'country': r'^\s*(domicile\s+country|risk\s+location\s+country|country)\s*$',
                    'category': r'^category$',
                    'placingbroker': r'^placing\s*broker$',
                    'insure': r'^insure$|^insurer$|^insured$|^participating\s*insurer$',
                    'settlementcurrency': r'^(settlement\s*currency|sett\s*ccy)$',
                    'originalcurrency': r'^original\s*currency$|^orig\s*ccy$',
                    'commissionper': r'^commission\s*%$',
                    'brokpremper': r'^brokerage\s*%$|^brokerage\s*% of gross\s*premium$',
                    'percentforlloyds': r'^% for lloyd\'s$|^lloyds\s*%$',
                    'rateofexchange': r'^rate\s*of\s*exchange$|^sett\s*roe$',
                    'grosspremiumpaidthistime': r'^gross\s*premium\s*paid\s*this\s*time$',
                    'gppsettlement': r'^gpp\s*settlement$',
                    'commissionamount': r'^commission\s*amount$',
                    'commissionamountsettlement': r'^commission\s*amount\s*settlement$',
                    'fnporiginalcurrency': r'^final\s*net\s*premium\s*\(original\s*currency\)$',
                    'brokerageamountoc': r'^brokerage\s*amount\s*\(original\s*currency\)$',
                    'finalnetpremiumsc': r'^final\s*net\s*premium\s*\(settlement\s*currency\)$|^final\s*net\s*premium\s*sett$|^final\s*net$',
                    'brokerageamountsc': r'^brokerage\s*amount\s*\(settlement\s*currency\)$',
                    'totaltaxesandlevies': r'^total\s*(taxes\s*and\s*levies|tax)$',
                    'totaltaxesandleviessc': r'^total\s*taxes\s*and\s*levies\s*\(settlement\s*currency\)$',
                    'accessoriitaly': r'^accessori\s*\(italy\)$',
                    'terrorismpremium': r'^terrorism\s*premium$',
                    'finalnetpremiumusd': r'^final\s*net\s*premium\s*\(usd\)$|^final\s*net\s*premium\s*\(original\s*currency\)$',
                    'filename': r'^filename$',
                    'paymentrequestid': r'^payment\s*request\s*id$',
                    'sheettab': r'^sheettab$',
                    'bindingagreement': r'^binding\s*agreement$',
                    'month': r'^month$',
                    'year': r'^year$',
                    'processingdate': r'^processing\s*date$',
                    'folder': r'^folder$',
                    'archived': r'^archived$',
                    'document': r'^document(_id)?$',
                    'analyst_id': r'^analyst(_id)?_id$'
                }

                # Check if file already exists in BDX table
                object_premium_bdx_report = PremiumBDX.objects.filter(filename=file_name, sheettab=sheet_tab, archived=False)

                if object_premium_bdx_report:
                    return Response({'Response': 'File already exists'}, status=status.HTTP_400_BAD_REQUEST)

                column_mappings = get_column_mappings(data, field_patterns)

                for row in range(len(data[list(data.keys())[0]])):
                    try:
                        try:
                            coverholdname = data[column_mappings['coverholdname']][row]
                            if coverholdname=="" or coverholdname==0.00:
                                return Response({'Response': 'Null values not allowed in the "Coverholder Name" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            coverholdname = ""
                        
                        try: 
                            yearofaccount = int(data[column_mappings['yearofaccount']][row])
                            if yearofaccount=="" or yearofaccount==0.00:
                                return Response({'Response': 'Null values not allowed in the "Year of Account(YOA)" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            yearofaccount = ""

                        try:
                            umr = data[column_mappings['umr']][row]
                            if umr=="" or umr==0.00:
                                return Response({'Response': 'Null values not allowed in the "UMR" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            umr = ""
                        
                        try:
                            agreementno = data[column_mappings['agreementno']][row]
                            if agreementno=="" or agreementno==0.00:
                                return Response({'Response': 'Null values not allowed in the "Agreement No" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            agreementno = ""
                        
                        try:
                            certificateref = data[column_mappings['certificateref']][row]
                            if certificateref=="" or certificateref==0.00:
                                return Response({'Response': 'Null values not allowed in the "Certificate Ref" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            certificateref = ""
                        
                        try:
                            lob = data[column_mappings['lob']][row]
                        except:
                            lob = ""
                        
                        try:
                            classofbusiness = data[column_mappings['classofbusiness']][row]
                        except:
                            classofbusiness = ""
                        
                        try:
                            risktransactiontype = data[column_mappings['risktransactiontype']][row]
                        except:
                            risktransactiontype = ""
                        
                        try:
                            country = data[column_mappings['country']][row]
                        except:
                            country = ""
                        
                        try:
                            category = data[column_mappings['category']][row]
                        except:
                            category = ""
                        
                        try:
                            placingbroker = data[column_mappings['placingbroker']][row]
                        except:
                            placingbroker = ""

                        try:
                            bindingagreement = data[column_mappings['bindingagreement']][row]
                        except:
                            bindingagreement = ""
                        
                        try:
                            insure = data[column_mappings['insure']][row]
                            if bindingagreement == "SCM" and insure=="" or insure==0.00:
                                return Response({'Response': 'Null values not allowed in the "Insure/Insurer/Insured/Participating Insurer" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            insure = ""
                        
                        try:
                            settlementcurrency = data[column_mappings['settlementcurrency']][row]
                            if settlementcurrency=="" or settlementcurrency==0.00:
                                return Response({'Response': 'Null values not allowed in the "Settlement Currency/Sett ccy" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            settlementcurrency = ""
                        
                        try:
                            originalcurrency = data[column_mappings['originalcurrency']][row]
                            if originalcurrency=="" or originalcurrency==0.00:
                                return Response({'Response': 'Null values not allowed in the "Original Currency/Orig ccy" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            originalcurrency = ""
                        
                        try:
                            commissionper = data[column_mappings['commissionper']][row]
                            if commissionper=="":
                                return Response({'Response': 'Null values not allowed in the "Commission %/Comm %" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            commissionper = 0.00
                        
                        try:
                            brokpremper = data[column_mappings['brokpremper']][row]
                            if bindingagreement == "SCM" and brokpremper=="":
                                return Response({'Response': 'Null values not allowed in the "Brokerage %/Brokerage % of gross premium" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            brokpremper = 0.00
                        
                        try:
                            percentforlloyds = data[column_mappings['percentforlloyds']][row]
                            if bindingagreement == "SCM" and percentforlloyds=="":
                                return Response({'Response': 'Null values not allowed in the "% for Lloyd\'s/Lloyds %" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            percentforlloyds = 0.00
                        
                        try:
                            rateofexchange = data[column_mappings['rateofexchange']][row]
                            if rateofexchange=="":
                                return Response({'Response': 'Null values not allowed in the "Rate of Exchange/Sett Roe" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            rateofexchange = 0.00
                        
                        try:
                            grosspremiumpaidthistime = data[column_mappings['grosspremiumpaidthistime']][row]
                            if grosspremiumpaidthistime=="":
                                return Response({'Response': 'Null values not allowed in the "Gross Premium Paid This Time/GPP This Time" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            grosspremiumpaidthistime = 0.00
                        
                        try:
                            gppsettlement = data[column_mappings['gppsettlement']][row]
                        except:
                            gppsettlement = 0.00
                        
                        try:
                            commissionamount = data[column_mappings['commissionamount']][row]
                            if commissionamount=="":
                                return Response({'Response': 'Null values not allowed in the "Commission Amount/Comm Amount" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            commissionamount = 0.00
                        
                        try:
                            commissionamountsettlement = data[column_mappings['commissionamountsettlement']][row]
                        except:
                            commissionamountsettlement = 0.00
                        
                        try:
                            fnporiginalcurrency = data[column_mappings['fnporiginalcurrency']][row]
                        except:
                            fnporiginalcurrency = None
                        
                        try:
                            brokerageamountoc = data[column_mappings['brokerageamountoc']][row]
                            if brokerageamountoc=="":
                                return Response({'Response': 'Null values not allowed in the "Brokerage Amount (Original Currency)" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            brokerageamountoc = 0.00
                        
                        try:
                            finalnetpremiumsc = data[column_mappings['finalnetpremiumsc']][row]
                            if finalnetpremiumsc=="":
                                return Response({'Response': 'Null values not allowed in the "Final Net Premium (Settlement Currency)" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            finalnetpremiumsc = 0.00
                        
                        try:
                            brokerageamountsc = data[column_mappings['brokerageamountsc']][row]
                        except:
                            brokerageamountsc = None
                        
                        try:
                            totaltaxesandlevies = data[column_mappings['totaltaxesandlevies']][row]
                        except:
                            totaltaxesandlevies = None
                        
                        try:
                            totaltaxesandleviessc = data[column_mappings['totaltaxesandleviessc']][row]
                        except:
                            totaltaxesandleviessc = 0.00
                        
                        try:
                            accessoriitaly = data[column_mappings['accessoriitaly']][row]
                            if bindingagreement == "1609" and accessoriitaly=="":
                                return Response({'Response': 'Null values not allowed in the "Accessories (Italy)" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            accessoriitaly = None
                        
                        try:
                            terrorismpremium = data[column_mappings['terrorismpremium']][row]
                            if bindingagreement == "1609" and terrorismpremium=="":
                                return Response({'Response': 'Null values not allowed in the "Terrorism Premium" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            terrorismpremium = 0.00
                        
                        try:
                            finalnetpremiumusd = data[column_mappings['finalnetpremiumusd']][row]
                            if finalnetpremiumusd=="":
                                return Response({'Response': 'Null values not allowed in the "Final Net Premium (USD)" column!'}, status=status.HTTP_400_BAD_REQUEST)
                        except:
                            finalnetpremiumusd = 0.00
                        
                        try:
                            filename = data[column_mappings['filename']][row]
                        except:
                            filename = ""
                        
                        try:
                            paymentrequestid = data[column_mappings['paymentrequestid']][row]
                        except:
                            paymentrequestid = ""
                        
                        try:
                            sheettab = data[column_mappings['sheettab']][row]
                        except:
                            sheettab = ""
                        
                        try:
                            month = data[column_mappings['month']][row]
                        except:
                            month = ""
                        
                        try:
                            year = data[column_mappings['year']][row]
                        except:
                            year = ""
                        
                        try:
                            processingdate = data[column_mappings['processingdate']][row]
                        except:
                            processingdate = None
                        
                        try:
                            folder = data[column_mappings['folder']][row]
                        except:
                            folder = ""
                        
                        try:
                            archived = data[column_mappings['archived']][row]
                        except:
                            archived = None
                        
                        # try:
                        #     document = Documents.objects.get(id=int(row[column_mappings['document']]))
                        # except:
                        #     document = None
                        
                        try:
                            analyst_id = Users.objects.get(id=int(data[column_mappings['analyst_id']][row]))
                        except:
                            analyst_id = None

                        # Upload file to S3
                        file_url = upload_file_to_s3(filename, bucket_name)

                        current_time = datetime.datetime.now()
                        document_obj = Documents.objects.create(document_name=str(filename),
                                                                    document_date=current_time.date(),
                                                                    document_type='Premium BDX', archieve_by='Analyst',
                                                                    archieve_datetime=current_time, document_url=file_url)
                        # if PremiumBDX.objects.last():
                        #     pbdx_obj = PremiumBDX.objects.last()
                        #     pk_id = pbdx_obj.id + 1
                        # else:
                        #     pk_id = 1
                        max_id = PremiumBDX.objects.aggregate(Max('id'))['id__max'] or 0
                        PremiumBDX.objects.create(
                            id = max_id + 1,
                            coverholdname=coverholdname,
                            yearofaccount=yearofaccount,
                            umr=umr,
                            agreementno=agreementno,
                            certificateref=certificateref,
                            lob=lob,
                            classofbusiness=classofbusiness,
                            risktransactiontype=risktransactiontype,
                            country=country,
                            category=category,
                            placingbroker=placingbroker,
                            insure=insure,
                            settlementcurrency=settlementcurrency,
                            originalcurrency=originalcurrency,
                            commissionper=commissionper,
                            brokpremper=brokpremper,
                            percentforlloyds=percentforlloyds,
                            rateofexchange=rateofexchange,
                            grosspremiumpaidthistime=grosspremiumpaidthistime,
                            gppsettlement=gppsettlement,
                            commissionamount=commissionamount,
                            commissionamountsettlement=commissionamountsettlement,
                            fnporiginalcurrency=fnporiginalcurrency,
                            brokerageamountoc=brokerageamountoc,
                            finalnetpremiumsc=finalnetpremiumsc,
                            brokerageamountsc=brokerageamountsc,
                            totaltaxesandlevies=totaltaxesandlevies,
                            totaltaxesandleviessc=totaltaxesandleviessc,
                            accessoriitaly=accessoriitaly,
                            terrorismpremium=terrorismpremium,
                            finalnetpremiumusd=finalnetpremiumusd,
                            filename=filename,
                            paymentrequestid=paymentrequestid,
                            sheettab=sheettab,
                            bindingagreement=bindingagreement,
                            month=month,
                            year=year,
                            processingdate=processingdate,
                            folder=folder,
                            archived=archived,
                            document=document_obj,
                            analyst_id=analyst_id,
                            migrated_data = False,
                            created_at = datetime.datetime.now(),
                            updated_datetime = datetime.datetime.now(),
                        )
                        print("inserted data")
                        
                    except Exception as e:
                        print("Error generated: ",str(e))
                        raise Exception("Error while saving BDX data")
                    
                    try:
                        # update status of the file in PremBDXFiles
                        prem_bdx_file = PremBDXFiles.objects.get(filename=filename, sheet_name=sheettab, archived=False)
                        prem_bdx_file.upload_status = True
                        prem_bdx_file.save()
                    except Exception as e:
                        print("Error generated: ",str(e))
                        raise Exception("Error while update BDX file data")
            # return Response({'Response': 'Inserted data'}, status=status.HTTP_200_OK)

            # Define the PostgreSQL connection parameters
            postgres_params = {
                'database': config('DATABASE_NAME'),
                'user': config('DATABASE_USER'),
                'password': config('DATABASE_PASSWORD'),
                'host': config('DATABASE_HOST'),
                'port': '5432'
            }

            paymentfile = "paymentfile 20240620.xlsx"

            # Connect to the PostgreSQL database
            connection = psycopg2.connect(**postgres_params)

            cursor = connection.cursor()

            # -- Concatenate policy numbers and file names, store unique values in an array
            e1sql = "SELECT concat(certificateref, '-', filename) FROM payment_premiumbdx group by concat(certificateref, '-', filename);"

            t1s = check_entry_all(e1sql)

            # print(t1s)

            # print(t1s)

            wb = Workbook()
            ws = wb.active

            cashpartners = ['BMS', 'Everen', 'Inver Re', 'Transverse', 'Aon', 'ARN']
            noncashpartners = ['Mosaic']

            expected_heading = ["Certificate Ref",
                                "BDX File name",
                                "YOA",
                                "UMR",
                                "Yr_Month",
                                "CT_Status",
                                "Allocation Date",
                                "Settlement Currency",
                                "BDx Gross Premium",
                                "BDx Brokerage",
                                "Tax",
                                "Net of Brokerage",
                                "% for Lloyd's",
                                "Lloyds Market",
                                "Receivable Amount",
                                "Net Premium",
                                "CT Allocation Amt",
                                "Bank Charges",
                                "Variance with CT",
                                "Unpaid Surplus (Alloc - Paid)",
                                "Surplus remaining if payment made",
                                "Sample test",
                                "Overall Status",
                                "CT Reconiliation to BDX Comments",
                                "Treasury Policy Level Payment Verification",
                                "Amount Match1",
                                "Cash BDx Amt",
                                "Non Cash BDx Amt",
                                "Potential Payment Indicator",
                                "Comments - Audit",
                                "Payment File Name",
                                "BDX Paid against",
                                "Payment Reference",
                                "Payment Date",
                                "Cash Bank Ref ",
                                "Cash Payment Date ",
                                "1609 Bank Ref ",
                                "1609 Payment Date ",
                                "Commision ",
                                "Rebate",
                                "Commision Bank Ref ",
                                "Commision Payment Date",
                                "Comment",
                                "Process Messages"
                                ]

            headers = [col for col in expected_heading]
            ws.append(expected_heading)
            wb.save(paymentfile)

            # Split each string in the array
            premreport = []
            t1s = request.data['response']

            if t1s.get('Certificate Ref'):
                certs = t1s['Certificate Ref']
            elif t1s.get('certificateref'):
                certs = t1s['certificateref']
            elif t1s.get('Certificate Reference'):
                certs = t1s['Certificate Reference']
            filename = t1s['filename']
            premreport = [[a, b] for a, b in zip(certs, filename)]
            # i = 0
            # for t1 in t1s:
            #     i = i + 1
                
            #     policy_number = t1['certno']
            #     file_name = t1['filename']
            #     premreport.append((policy_number, file_name))

            # Print the split values
            # for policy_number, file_name in premreport:
            #    print("Policy Number:", policy_number)
            #    print("File Name:", file_name)
            #    print()  # Add an empty line for separation

            prem_row_data = []
            i = 0
            for premrec in premreport:
                i = i + 1
                error = None
                process_messages = ""
                try:
                    # print("certificate no.:", type(premrec))
                    try:
                        certno = premrec[0]
                    except Exception as e:
                        certno = None
                        error = error + "Certificate# Not Found"

                    filename = premrec[1]
                    prembdx1 = PremiumBDX.objects.filter(certificateref=certno, filename=filename, archived=False).values('id', 'yearofaccount', 'settlementcurrency', 'umr', 'insure').last()
                except Exception as e:
                    # print(elsql)
                    # print(prembdx1)
                    print("skipping the record1:", e)

                monthf = getmonth(filename)
                yearf = getyear(filename)
                yr_month = monthf + "-" + yearf

                try:
                    # e1sql = f"""SELECT sum(gppsettlement), sum(brokerageamountsc), sum(totaltaxesandleviessc), sum(finalnetpremiumsc), sum(percentforlloyds), sum(commissionamount) FROM prem_premiumbdx where certificateref = '{certno}' and filename = '{filename}';"""
                    # cursor.execute(e1sql)
                    # pbdxsumvalues = check_entry_one(e1sql)
                    queryset = PremiumBDX.objects.filter(certificateref=certno, filename=filename, archived=False)
                    pbdxsumvalues = queryset.aggregate(
                        total_gppsettlement=Sum('gppsettlement'),
                        total_brokerageamountsc=Sum('brokerageamountsc'),
                        total_taxesandleviessc=Sum('totaltaxesandleviessc'),
                        total_finalnetpremiumsc=Sum('finalnetpremiumsc'),
                        total_percentforlloyds=Sum('percentforlloyds'),
                        total_commissionamount=Sum('commissionamount')
                    )
                except Exception as e:
                    print("skipped record2:", e)

                try:
                    e1sql = f"""SELECT allocationstatus FROM prem_cashtracker where policy = '{certno}';"""
                    # cursor.execute(e1sql)
                    allocationstatus = check_entry_one(e1sql)[0]
                except Exception as e:
                    print("skipped record3:", e)

                # changed to allocated amount - 21/05/2024
                try:
                    e1sql = f"""SELECT sum(allocatedamount), SUM(CAST(bankcharges AS FLOAT)) FROM prem_cashtracker where policy = '{certno}';"""
                    # cursor.execute(e1sql)
                    ctsumvalues = check_entry_one(e1sql)
                    # print(f"ctsumvalues: {ctsumvalues}")
                except Exception as e:
                    print("skipped record4:", e)

                try:
                    e1sql = f"""SELECT max(gxballocationdate) FROM prem_cashtracker where policy = '{certno}';"""
                    # cursor.execute(e1sql)
                    allocationdate = check_entry_one(e1sql)[0]
                except Exception as e:
                    print("skipped record5:", e)

                try:

                    e1sql = f"""SELECT sum(netpremiumtolondon) FROM prem_treasurypayment where certificateref = '{certno}';"""
                    # cursor.execute(e1sql)
                    netpremiumtolondon = check_entry_one(e1sql)
                    # print(f"netpremiumtolondon: {netpremiumtolondon}")

                except Exception as e:
                    print("skipped record6:", e)

                try:
                    e1sql = f"""SELECT bankreference FROM prem_treasurypayment where certificateref = '{certno}';"""
                    # cursor.execute(e1sql)
                    aabankreference = check_entry_one(e1sql)
                    # print(f"bankref: {aabankreference}")
                except Exception as e:
                    print("skipped record7:", e)

                aabankreferences = None

                try:
                    e1sql = f"""SELECT paymentto FROM prem_treasurypayment where certificateref = '{certno}';"""
                    # cursor.execute(e1sql)
                    aabankreferences = check_entry_all(e1sql)
                    # print(f"bankref: {aabankreference}")
                except Exception as e:
                    print("skipped record7a:", e)

                tfilename = None
                tbdxnamemonthandyear = None
                tbankreference = None
                tpaymentdate = None

                if aabankreferences:
                    # print("1 {aabankreferences}")
                    for aabankreference in aabankreferences:
                        # print(f"2 {aabankreference}")
                        for aabankt in aabankreference:
                            # print(f"3 {aabankt}")
                            if 'Transverse' in aabankt or 'Acrisure' in aabankt or 'BMS' in aabankt or 'Inverre' in aabankt:
                                try:
                                    e1sql = f"""SELECT filename, bdxnamemonthandyear, bankreference, paymentdate FROM prem_treasurypayment where certificateref = '{certno}';"""
                                    # cursor.execute(e1sql)
                                    aabankreferences1 = check_entry_one(e1sql)
                                    # print(f"bankref: {aabankreference}")
                                except Exception as e:
                                    print("skipped record7b:", e)

                                if aabankreferences1:
                                    # print (f"treasury details: {aabankreferences1}")
                                    tfilename = aabankreferences1[0]
                                    tbdxnamemonthandyear = aabankreferences1[1]
                                    tbankreference = aabankreferences1[2]
                                    tpaymentdate = aabankreferences1[3]
                                break

                wfnpsc = []

                umr = None
                category = None
                partner = None
                if prembdx1:
                    yoa = prembdx1['yearofaccount']
                    settlement_currency = prembdx1['settlementcurrency']
                    umr = prembdx1['umr']
                    insure = prembdx1['insure']

                    # if '1609' in filename:
                    #     category = 'Non Cash'
                    #     partner = None
                    # else:
                    #     for noncashpartner in noncashpartners:
                    #         if noncashpartner in insure:
                    #             category = 'Non Cash'
                    #             partner = noncashpartner
                    #             break
                    #     if category == None:
                    #         for cashpartner in cashpartners:
                    #             if cashpartner in insure:
                    #                 category = 'Cash'
                    #                 partner = cashpartner
                    #                 break
                else:
                    yoa = None
                    settlement_currency = None
                    umr = None

                try:
                    sql_query = f"""SELECT scmpartner FROM prem_scmagreement where umr = '{umr}';"""
                    partner_values = check_entry_all(sql_query)
                    partner = partner_values[0][0]
                except:
                    pass

                process_messages = process_messages + "partner & category: " + str(partner) + str(category)

                try:
                    e1sql = f"""SELECT sum(finalnetpremiumsc) FROM prem_premiumbdx where certificateref = '{certno}' and filename = '{filename}';"""
                    # print(e1sql)
                    cursor.execute(e1sql)
                except Exception as e:
                    continue
                # print("skipped record8:", e)

                try:
                    # if 1==1:
                    # Assign values for append

                    certificate_ref = certno  # 1
                    bdx_file_name = filename

                    # print("umr: ", umr)

                    ct_status = None
                    if isinstance(allocationstatus, np.ndarray):
                        ct_status = allocationstatus[0]
                    else:
                        ct_status = allocationstatus
                        # ct_status = "Allocated"
                        # allocation_date = None    
                    # print("print 1: ", certno, allocationstatus, ct_status, allocationdate)

                    bdx_gross_premium = pbdxsumvalues['total_gppsettlement']
                    bdx_brokerage = pbdxsumvalues['total_brokerageamountsc']
                    tax = pbdxsumvalues['total_taxesandleviessc']  # 10

                    brokerageamount = float(bdx_gross_premium or 0.0) + float(bdx_brokerage or 0.0) + float(tax or 0.0)

                    llyods_market = None
                    recevable_amount = None
                    net_premium = pbdxsumvalues['total_finalnetpremiumsc']
                    llyods_percentage = pbdxsumvalues['total_percentforlloyds']
                    commissionamt = pbdxsumvalues['total_commissionamount']
                    ct_allocation_amount = ctsumvalues[0]
                    ct_bank_charges = ctsumvalues[1]
                    variance_with_ct = float(ctsumvalues[0] or 0.0) - float(ctsumvalues[1] or 0.0) - float(
                        brokerageamount or 0.0)
                except Exception as e:
                    print("exception: ", e)

                ##rebate calculation
                rebate = 0
                try:
                    e1sql = f"""SELECT placingbroker, participation FROM prem_scmagreement where umr = '{umr}';"""
                    # cursor.execute(e1sql)
                    scmagreementvalues = check_entry_one(e1sql)
                    if scmagreementvalues:
                        if 'Transverse' in scmagreementvalues[0] or 'BMS' in scmagreementvalues[0] or 'Inver re' in \
                                scmagreementvalues[0]:
                            rebate = 0;
                        elif 'Acrisure' in scmagreementvalues[0]:
                            if 'Mosaic' in scmagreementvalues[1]:
                                rebate = 0;
                        elif '23' in umr:
                            e1sql = f"""SELECT grosspremiumpaidthistime as grosspremiumpaidthistime, rateofexchange FROM prem_premiumbdx where insure like '%Acrisure%' and umr like '%23%' """
                            # cursor.execute(e1sql)
                            prembdx1 = check_entry_one(e1sql)
                            grossp = prembdx1[0]
                            roe = prembdx1[1]
                            rebate = ((grossp * .025) * 0.5) / roe
                        elif '24' in umr:
                            acri = "Acrisure"
                            e1sql = f"""SELECT grosspremiumpaidthistime as grosspremiumpaidthistime, rateofexchange FROM prem_premiumbdx where insure like '%Acrisure%' and umr like '%24%'"""
                            # cursor.execute(e1sql)
                            prembdx1 = check_entry_one(e1sql)
                            grossp = prembdx1[0]
                            roe = prembdx1[1]
                            rebate = ((grossp * .025) * 0.4) / roe

                except Exception as e:
                    rebate = 0
                    print("skipped rebate calculation set to zero:", e)

                try:
                    if '1609' in filename:
                        category = 'Cash'
                        partner = None
                    elif 'BMS' in scmagreementvalues[0] or 'Inver re' in scmagreementvalues[0] or 'Transverse' in scmagreementvalues[0] or 'AON' in scmagreementvalues[0]:
                        category = 'Cash'
                    elif 'Acrisure' in scmagreementvalues[0] and 'ARN' in umr:
                        category = 'Cash'
                    elif 'Acrisure' in scmagreementvalues[0] and 'LNR' in umr and 'Mosaic' in scmagreementvalues[1]:
                        category = 'Non Cash'
                    elif 'Acrisure' in scmagreementvalues[0] and '24LNR' in umr and 'Mosaic' in scmagreementvalues[1]:
                        category = 'Non Cash'
                except:
                    category = None


                if category == 'Cash':
                    e1sql = f"""SELECT sum(finalnetpremiumsc) FROM payment_premiumbdx where certificateref = '{certno}' and filename = '{filename}';"""
                    wfnpsc = check_entry_one(e1sql)
                    cash_bdx_amt = wfnpsc[0]
                else:
                    cash_bdx_amt = 0.0
                
                noncash_bdx_amt = 0.0
                if category == 'Non Cash':
                    xfnpsc = check_entry_one(e1sql)
                    noncash_bdx_amt = xfnpsc[0]

                # added variance condition
                try:
                    va = float(ct_bank_charges or 0.0) + float(variance_with_ct or 0.0)

                    if (va >= -25 and va <= 25) or (variance_with_ct == ct_bank_charges):
                        ct_recontobdx_comments = "No Variance"

                    else:
                        ct_recontobdx_comments = "Investigate"  # 20

                    vfound = 0

                    if umr:
                        ct_allocation_amount = ctsumvalues[0]
                        try:
                            e1sql = f"""SELECT umr, partner, partnershare, range_check FROM prem_partnershare where umr = '{umr}';"""
                            # cursor.execute(e1sql)
                            parnersharevalues = check_entry_all(e1sql)
                            # print(f"parnersharevalues: {parnersharevalues}")

                            for psv in parnersharevalues:
                                # print("psv: ", umr, psv)

                                range_check = psv[3]
                                # print (f"range check: ", range_check)
                                if range_check == 0:
                                    varianceallowed = ct_allocation_amount * psv[2]
                                    # print("Range 0: ", psv[2], varianceallowed, variance_with_ct)
                                    if round(varianceallowed, 2) == round(variance_with_ct, 2):
                                        ct_recontobdx_comments = "No Variance"
                                        process_messages = process_messages + str(psv[0]) + str(psv[1]) + str(psv[2])
                                        vfound = 1

                                if range_check == 1:
                                    for value in np.arange(0.1, 1.0, 0.1):
                                        varianceallowed = ct_allocation_amount * value
                                        # print("Range 0: ", value, varianceallowed, variance_with_ct, varianceallowed-variance_with_ct )
                                        if round(varianceallowed, 2) == round(variance_with_ct, 2):
                                            ct_recontobdx_comments = "No Variance"
                                            process_messages = process_messages + str(psv[0]) + str(psv[1]) + value
                                            vfound = 1
                                            break
                                    vfound = 1
                                if vfound == 1:
                                    break

                        except Exception as e:
                            print("skipped variance:", e)

                    treasury_policy_level_payment_verification = netpremiumtolondon[0]

                    tplpv = treasury_policy_level_payment_verification

                    if tplpv == None:
                        tplpv = 0

                    if treasury_policy_level_payment_verification == net_premium:
                        amount_match1 = True
                    else:
                        amount_match1 = False

                    unpaid_surplus = ct_allocation_amount - tplpv
                    surplus_remaining = unpaid_surplus - brokerageamount
                    sample_test = ct_allocation_amount * 0.5333333

                    if net_premium == None:
                        net_premium = 0

                    tplpv = float(tplpv) if tplpv is not None else 0.0
                    if tplpv == 0 or tplpv == None:
                        potential_payment_indicator = "Initiate Payment"
                    elif round(tplpv, 0) == round(noncash_bdx_amt if noncash_bdx_amt else 0, 0):
                        potential_payment_indicator = "1609 Payment Done"
                    elif round(tplpv, 0) == round(cash_bdx_amt if cash_bdx_amt else 0, 0):
                        potential_payment_indicator = "Partner Payment Done"
                    elif round(tplpv, 0) == round(net_premium, 0):
                        potential_payment_indicator = "Payment Fully Done"
                    else:
                        potential_payment_indicator = "Investigate"

                    overall_status = ct_recontobdx_comments + " " + potential_payment_indicator

                    comments_audit = None

                    if aabankreference:
                        cash_bank_reference = aabankreference[0]
                    else:
                        cash_bank_reference = None

                    cash_payment_date = None
                    bank_ref1609 = None
                    payment_date1609 = None  # 30
                    commission = None
                    commission_bank_ref = None
                    commission_payment_date = None
                    comments = None
                    inull = ""

                    try:
                        exceptional_obj = PaymentException.objects.create(
                            certificate_ref=certificate_ref,
                            bdx_file_name=bdx_file_name,
                            yoa=yoa,
                            yr_month=yr_month,
                            ct_status=ct_status,
                            allocation_date=convert_date(allocationdate) if allocationdate else None,
                            settlement_currency=settlement_currency,
                            bdx_gross_premium=bdx_gross_premium,
                            bdx_brokerage=bdx_brokerage,
                            tax=tax,
                            net_of_brokerage=brokerageamount,
                            percentage_for_lloyd=llyods_percentage,
                            lloyds_market=llyods_market,
                            receivable_amount=recevable_amount,
                            net_premium=net_premium,
                            ct_allocation_amt=ct_allocation_amount,
                            bank_charges=ct_bank_charges,
                            variance_with_ct=variance_with_ct,
                            overall_status=overall_status,
                            ct_reconiliation_to_bdx_comments=ct_recontobdx_comments,
                            treasury_policy_level_payment_verification=treasury_policy_level_payment_verification,
                            amount_match1=amount_match1,
                            cash_bdx_amt=cash_bdx_amt,
                            non_cash_bdx_amt=noncash_bdx_amt,
                            potential_payment_indicator=potential_payment_indicator,
                            comments_audit=comments_audit,
                            cash_bank_ref=cash_bank_reference,
                            cash_payment_date=convert_date(cash_payment_date) if cash_payment_date else None,
                            sixteen_hundred_nine_bank_ref=bank_ref1609,
                            sixteen_hundred_nine_payment_date=payment_date1609,
                            commission=commissionamt,
                            commission_bank_ref=commission_bank_ref,
                            commission_payment_date=commission_payment_date,
                            comment=comments,
                        )
                        print("inserted record")


                        print("overall status", exceptional_obj.overall_status)

                        # if "no variance" in exceptional_obj.overall_status:
                        print("yes record found")
                        bdx_object = PremiumBDX.objects.filter(certificateref=certificate_ref, archived=False).last()
                        datasheet_obj = save_datasheet(bdx_object.id, category)
                        if datasheet_obj:
                            print("datasheet_obj", datasheet_obj, datasheet_obj.id)
                            final_bank_account = datasheet_obj.final_bank_account
                            final_bank_name = datasheet_obj.final_bank_name
                            to_bank_account_name = datasheet_obj.receiving_bank_account_name
                            to_bank_account = datasheet_obj.receiving_bank_account
                            sum_of_rebate = datasheet_obj.rebate
                            payment_id = datasheet_obj.payment_id
                            rebate = datasheet_obj.rebate
                        else:
                            final_bank_account = None
                            final_bank_name = None
                            to_bank_account_name = None
                            to_bank_account = None
                            sum_of_rebate = 0.0
                            payment_id = None
                            rebate = 0.0

                        sum_of_final_net_premium_settlement_currency = bdx_object.finalnetpremiumusd
                        commission_amount = bdx_object.commissionamount
                        if PayoutSummary.objects.filter(bdx_file_name=exceptional_obj.bdx_file_name, final_bank_account=to_bank_account, settlement_currency=exceptional_obj.settlement_currency).exists():
                            payout_summary_obj = PayoutSummary.objects.filter(bdx_file_name=exceptional_obj.bdx_file_name, final_bank_account=to_bank_account, settlement_currency=exceptional_obj.settlement_currency).last()
                            if datasheet_obj.category:
                                if payout_summary_obj.payment_type == "Cash":
                                    payout_summary_obj.sum_of_final_net_premium_settlement_currency += bdx_object.finalnetpremiumsc
                                    payout_summary_obj.sum_of_rebate += rebate
                                    payout_summary_obj.sum_of_net_payment = payout_summary_obj.sum_of_final_net_premium_settlement_currency - payout_summary_obj.sum_of_rebate
                                elif payout_summary_obj.payment_type == "Non Cash":
                                    payout_summary_obj.sum_of_net_payment += sum_of_final_net_premium_settlement_currency
                                elif payout_summary_obj.payment_type == "Rebate":
                                    payout_summary_obj.sum_of_rebate += rebate
                                elif payout_summary_obj.payment_type == "Commission":
                                    payout_summary_obj.sum_of_net_payment += commission_amount
                            payout_summary_obj.save()
                            print("PayoutSummary updated")
                        else:
                            if datasheet_obj.category:
                                # calculate payout summary for partner
                                if datasheet_obj.category == "Cash":
                                    PayoutSummary.objects.create(
                                        certificate_ref = certificate_ref,
                                        bdx_file_name = exceptional_obj.bdx_file_name,
                                        coverholder_name = bdx_object.coverholdname,
                                        final_bank_account = final_bank_account,
                                        final_bank_name = final_bank_name,
                                        to_bank_account_name = to_bank_account_name,
                                        to_bank_account = to_bank_account,
                                        settlement_currency = bdx_object.settlementcurrency,
                                        sum_of_final_net_premium_settlement_currency = sum_of_final_net_premium_settlement_currency,
                                        sum_of_rebate = sum_of_rebate,
                                        sum_of_net_payment = sum_of_final_net_premium_settlement_currency - sum_of_rebate if sum_of_final_net_premium_settlement_currency and sum_of_rebate else sum_of_final_net_premium_settlement_currency if sum_of_final_net_premium_settlement_currency else sum_of_rebate if sum_of_rebate else 0,
                                        payment_id = payment_id,
                                        payment_type = "Syndicate"
                                    )
                                # calculate payout summary for syndicate
                                elif datasheet_obj.category == "Non Cash":
                                    PayoutSummary.objects.create(
                                        certificate_ref = certificate_ref,
                                        bdx_file_name = exceptional_obj.bdx_file_name,
                                        coverholder_name = bdx_object.coverholdname,
                                        final_bank_account = final_bank_account,
                                        final_bank_name = final_bank_name,
                                        to_bank_account_name = to_bank_account_name,
                                        to_bank_account = to_bank_account,
                                        settlement_currency = bdx_object.settlementcurrency,
                                        sum_of_net_payment = sum_of_final_net_premium_settlement_currency,
                                        payment_id = payment_id,
                                        payment_type = "Partner"
                                    )
                            # calculate payout summary for rebate
                            PayoutSummary.objects.create(
                                certificate_ref = certificate_ref,
                                bdx_file_name = exceptional_obj.bdx_file_name,
                                coverholder_name = bdx_object.coverholdname,
                                final_bank_account = final_bank_account,
                                final_bank_name = final_bank_name,
                                to_bank_account_name = to_bank_account_name,
                                to_bank_account = to_bank_account,
                                settlement_currency = bdx_object.settlementcurrency,
                                sum_of_rebate = sum_of_rebate,
                                payment_id = payment_id,
                                payment_type = "Rebate"
                            )
                            # calculate payout summary for commission
                            PayoutSummary.objects.create(
                                certificate_ref = certificate_ref,
                                bdx_file_name = exceptional_obj.bdx_file_name,
                                coverholder_name = bdx_object.coverholdname,
                                final_bank_account = final_bank_account,
                                final_bank_name = final_bank_name,
                                to_bank_account_name = to_bank_account_name,
                                to_bank_account = to_bank_account,
                                settlement_currency = bdx_object.settlementcurrency,
                                sum_of_net_payment = commission_amount,
                                payment_id = payment_id,
                                payment_type = "Commission"
                            )
                            print("PayoutSummary created")
                    except Exception as e:
                        print("Error creating record:", e)

                except Exception as e:
                    print("skipped record10:", e)

            try:
                auth_header = request.META.get('HTTP_AUTHORIZATION')
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]

                domain_url = config('DOMAIN_URL')
                url = '{}/api/bankmanagement/workflow_bank_transactions/'.format(domain_url)
                data = {
                    "file_name": bdx_file_name,
                    "bank_txn_id": sheet_tab,
                    "analyst_id": request.data['analyst_id'],
                    "workflow_name": "WF_PAYMENT_NOVARIANCE",
                    "comments": comments_wf,
                    "initiated_user_id": request.data['analyst_id']
                }
                headers = {'Authorization': f'Bearer {token}'}
                resp = requests.post(url, data=data, headers=headers)
                print("Workflow sucess")
            except Exception as e:
                print("Error creating record:", e)
            if resp.status_code == 200:
                return Response({"Message": "Exception report generated and workflow initiated"}, status=status.HTTP_201_CREATED)
            raise Exception("Please check your inputs")
        except Exception as e:
            print("Error creating record:", e)
            raise Exception("Please check your inputs")

    def get(self, request):
        id = request.GET.get("id", None)
        certificate_ref = request.GET.get("certificate_ref", None)
        bdx_file_name = request.GET.get("bdx_file_name", None)
        overall_status = request.GET.get("overall_status", None)
        overall_status_contains = request.GET.get("overall_status_contains", None)
        page_number = int(request.GET.get("skip", 0))
        rows_per_page = int(request.GET.get("pageSize", 20))
        skip = page_number * rows_per_page
        filter_conditions = Q()
        if certificate_ref:
            filter_conditions &= Q(certificate_ref__icontains=certificate_ref)
        if bdx_file_name:
            filter_conditions &= Q(bdx_file_name__icontains=bdx_file_name)
        if id:
            filter_conditions &= Q(id__icontains=id)
        if overall_status:
            overall_status = overall_status.split(",")
            filter_conditions &= Q(overall_status__in=overall_status)
        elif overall_status_contains:
            filter_conditions &= Q(overall_status__icontains=overall_status_contains)

        # First, create a subquery to select the maximum id for each combination of certificate_ref and bdx_file_name
        subquery = PaymentException.objects.filter(
            filter_conditions,
            certificate_ref=OuterRef('certificate_ref'),
            bdx_file_name=OuterRef('bdx_file_name'),
        ).order_by('-id').values('id')[:1]

        # Subquery to exclude archived PremBDXFiles
        archived_files = PremBDXFiles.objects.filter(archived=True).values('filename')

        # Main query
        data = PaymentException.objects.filter(
            ~Q(bdx_file_name__in=Subquery(archived_files)),
            id__in=Subquery(subquery)
        ).order_by('-id', '-version')

        count = data.count()
        serializer = PaymentExceptionSerializer(data[skip: skip + rows_per_page], many=True)
        return Response({"data": serializer.data, "count":count}, status=status.HTTP_200_OK)

    def patch(self, request, pk, *args, **kwargs):
        instance = PaymentException.objects.get(id=pk)
        serializer = PaymentExceptionSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentFileOverallStatusViewSet(viewsets.ModelViewSet, generics.UpdateAPIView):


    """
    API endpoint for managing PaymentFile objects.
    """
    pagination_class = CustomPagination
    queryset = PaymentFile.objects.all().order_by('created_date').reverse()
    serializer_class = PaymentFileOverallStatusSerializer

    def get_permissions(self):
        """
        Implement custom permissions if needed (e.g., authentication)
        """
        return []  # Allow all users for now (consider adding authentication later)

    def list(self, request):
        """
        Handles GET requests to retrieve a list of PaymentFile Overall_Status objects.
        """

        overall_status = PaymentFile.objects.values("Overall_Status").distinct()
        print("overall status", overall_status)
        overall_status_list = [d['Overall_Status'] for d in overall_status]
        # serializer = self.get_serializer(overall_status, many=True)
        # response_data = serializer.data
        data = {"data": overall_status_list}

        return Response(data)
    

class PaymentTreasuryPYMTViewSet(viewsets.ModelViewSet, generics.UpdateAPIView):
    """
    API endpoint for managing PaymentTreasury objects.
    """
    pagination_class = CustomPagination
    queryset = PaymentTreasuryPYMT.objects.all().order_by('-id')
    serializer_class = PaymentTreasuryPYMTSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['file_name', 'certificate_ref', 'type_of_payment']

    def get_permissions(self):
        """
        Implement custom permissions if needed (e.g., authentication)
        """
        return []  # Allow all users for now (consider adding authentication later)

    def list(self, request):
        """
        Handles GET requests to retrieve a list of PaymentTreasury objects.
        """
        page_number = int(request.GET.get("skip", 0))
        rows_per_page = int(request.GET.get("pageSize", 20))
        type_of_payment = request.GET.get("type_of_payment", None)
        certificate_ref = request.GET.get("certificate_ref", None)
        file_name = request.GET.get("file_name", None)
        payment_id = request.GET.get("payment_id", None)

        skip = page_number * rows_per_page
        filter_conditions = Q()
        if type_of_payment:
            filter_conditions &= Q(type_of_payment__icontains=type_of_payment)
        if certificate_ref:
            filter_conditions &= Q(certificate_ref__icontains=certificate_ref)
        if file_name:
            filter_conditions &= Q(file_name__icontains=file_name)
        if payment_id:
            filter_conditions &= Q(payment_id__icontains=payment_id)

        queryset = self.get_queryset().filter(filter_conditions)[
                   skip: skip + rows_per_page
                   ]
        # Apply variance condition here

        output = []

        if type_of_payment == "MGA Commission":
            for i in queryset:
                result = {}
                if len(output) > 0:
                    for j in output:
                        if j['certificate_ref'] == i.certificate_ref:
                            j['commission'] += i.mga_commision
                else:
                    result['id'] = i.id
                    result['payment_id'] = i.payment_ids
                    result['category'] = i.category
                    result['file_name'] = i.file_name
                    result['certificate_ref'] = i.certificate_ref
                    result['coverholder_name'] = i.coverholder_name
                    result['settlement_currency'] = i.sett_currency
                    result['receiving_bank_account_name'] = i.coverholder_entity
                    result['receiving_bank_account'] = i.bank_account
                    result['commission'] = i.mga_commision
                    output.append(result)

            data = {"count": len(output), "data": output}
        else:
            serializer = self.get_serializer(queryset, many=True)
            response_data = serializer.data
            data = {"count": self.get_queryset().filter(filter_conditions).count(), "data": response_data}

        return Response(data)

    def create(self, request):
        """
        Handles POST requests to create a new PaymentTreasury object.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        """
        Handles PATCH requests to partially update a PaymentTreasury object.
        """
        instance = self.get_object()  # Retrieve the object based on the primary key (pk)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class GetAllPaymentId(APIView):
    def get(self, request):
        data = PayoutSummary.objects.all().values_list('payment_id', flat=True).distinct()
        return Response({"data": list(data)}, status=status.HTTP_200_OK)
    

class InitiateWFException(APIView):
    def post(self, request):
        domain_url = config('DOMAIN_URL')
        url = '{}/api/bankmanagement/workflow_bank_transactions/'.format(domain_url)
        data = request.data
        resp = requests.post(url, data=data)
        if resp.status_code == 200:
            return Response({"Message: Work flow is initiated"}, status=status.HTTP_201_CREATED)
        return Response({"Message: Failed to create a workflow"}, status=status.HTTP_400_BAD_REQUEST)


class PaymentDatasheetViewSet(viewsets.ModelViewSet):
    pagination_class = CustomPagination
    queryset = PaymentDatasheet.objects.all()
    serializer_class = PaymentDatasheetSerializer

    def create(self, request):
        try:
            """
            Handles GET requests to retrieve a list of PaymentTreasury objects.
            """

            bdx_obj = PremiumBDX.objects.all(archived=False)

            for i in bdx_obj:
                if PaymentDatasheet.objects.filter(bdx=i).exists():
                    pass
                else:

                    # line_of_business determination
                    lob_map = {
                        "CY": "Cyber",
                        "FI": "Financial Institutions",
                        "MA": "Merger and Acquisition",
                        "OC": "OCIL",
                        "PR": "Political Risk",
                        "PV": "Political Violence",
                        "PL": "Professional Liability",
                        "TL": "Transactional Liability",
                        "W&T": "War and Terrorism",
                        "WT": "War and Terrorism",
                        "War & Terrorism": "War and Terrorism",
                        "EN": "Environmental"
                    }
                    lob = ""
                    for key, value in lob_map.items():
                        if key in i.certificateref:
                            lob = value
                            break

                    # Raw SQL to fetch placingbroker based on matching UMR
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT a.placingbroker, a.participation
                            FROM prem_scmagreement a
                            JOIN payment_premiumbdx b ON a.umr = b.umr
                        """)
                        result = cursor.fetchall()

                    # Process the result of placing_broker
                    try:
                        placing_broker = result[0][0]
                        participation = result[0][1]
                    except:
                        placing_broker = None
                        participation = None

                    # Getting value of rebet
                    if placing_broker == "Everen" or "Inver Re" or "Transverse" or "Aon":
                        rebate = 0
                    elif i.umr == 23 and participation == "mosaic":
                        rebate = 0
                    else:
                        rebate = ((i.grosspremiumpaidthistime * 0.025) * 0.5) / i.rateofexchange

                    # Optimized retrieval of bank account details
                    cash_allocation = CashAllocation.objects.filter(policy_id=i.certificateref).first()
                    if cash_allocation and cash_allocation.bank_txn:
                        transfer_to_pt_bank_account_name = cash_allocation.bank_txn.PT_Receving_Bank_Name
                        bank_details = cash_allocation.bank_txn.bank_details
                        if bank_details:
                            receiving_bank_account_name = bank_details.bank_name
                            receiving_bank_account = bank_details.account_number
                        else:
                            receiving_bank_account_name = None
                            receiving_bank_account = None
                    else:
                        transfer_to_pt_bank_account_name = None
                        receiving_bank_account_name = None
                        receiving_bank_account = None

                    try:
                        if i.month.isdigit():
                            payment_id = placing_broker[:4] + i.year[2:4] + i.month
                        else:
                            month_number = {
                                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                            }.get(i.month[:3].lower(), '01')
                            payment_id = placing_broker[:4] + i.year[2:4] + month_number
                    except:
                        payment_id = placing_broker[:4] + i.year[2:4] + i.month

                    # Getting value of rateofexchange
                    rateofexchange = CashTrackerReport.objects.filter(Policy=i.certificateref).first().ROE_Bank_Statement if CashTrackerReport.objects.filter(Policy=i.certificateref).exists() else None

                    # Getting value of treasury_transfer_date
                    treasury_transfer_date = CashAllocationCorrective.objects.filter(policy_id=i.certificateref).first().treasury_confirmed_transfer_date if CashAllocationCorrective.objects.filter(policy_id=i.certificateref).exists() else None

                    # creating datasheet object
                    PaymentDatasheet.objects.create(
                        bdx = i,
                        amount = None,
                        rateofexchange = rateofexchange,
                        bdx_month = i.month,
                        bdx_year = i.year,
                        line_of_business = lob,
                        producing_coverholder = i.coverholdname,
                        receiving_bank_account_name = receiving_bank_account_name,
                        receiving_bank_account = receiving_bank_account,
                        transfer_to_pt_bank_account_name = transfer_to_pt_bank_account_name,
                        treasury_transfer_date = treasury_transfer_date,
                        invoice_bank_account = None,
                        final_bank_account = None,
                        final_bank_name = None,
                        SCM_NonSCM = i.bindingagreement,
                        Placing_Broker = placing_broker,
                        rebate = rebate,
                        net_payment = i.finalnetpremiumusd - rebate if i.finalnetpremiumusd and rebate else None,
                        gross_prem_sett_arch = None,
                        net_prem_sett_incld_rebate_arch = None,
                        category = i.category,
                        payment_id = payment_id
                    )
            return Response(status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST)
    
    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    

class PayoutSummaryViewSet(generics.ListAPIView, generics.UpdateAPIView):
    serializer_class = PayoutSummarySerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return PayoutSummary.objects.all().order_by('-id')

    def get(self, request):
        queryset = self.get_queryset()
        # Retrieve query parameters from the GET request

        placingbroker = request.GET.get('placing_broker')
        category = request.GET.get('category')
        scm_non_scm = request.GET.get('scm_type')
        partner_name = request.GET.get('partner')
        payment_id = request.GET.get('payment_id')
        type_of_payment = request.GET.get('type_of_payment')
        overall_status = request.GET.get('overall_status')
        payment_status = request.GET.get('payment_status')
        coverholder_name = request.GET.get('coverholder_name')
        settlement_currency = request.GET.get('settlement_currency')
        final_bank_account_name = request.GET.get('final_bank')
        file_name = request.GET.get('file_name')
        page_number = int(request.GET.get("skip", 0))
        rows_per_page = int(request.GET.get("pageSize", 20))

        skip = page_number * rows_per_page
        # Initialize a Q object for dynamic filtering
        filter_conditions = Q()

        # Apply conditions to the Q object based on the query parameters
        if placingbroker:
            filter_conditions &= Q(placing_broker=placingbroker)

        if category:
            filter_conditions &= Q(category=category)

        if scm_non_scm:
            bindingagreement = scm_non_scm.lower()
            if bindingagreement in ['non-scm', '1609']:
                filter_conditions &= Q(scm_non_scm='1609')
            elif bindingagreement == 'scm':
                filter_conditions &= Q(scm_non_scm__iexact='SCM')

        if partner_name:
            filter_conditions &= Q(partner_name=partner_name)

        if payment_id:
            filter_conditions &= Q(payment_id=payment_id)

        if type_of_payment:
            if type_of_payment == "MGA Commission":
                filter_conditions &= Q(payment_type__icontains="Commission")
            elif type_of_payment == "Internal Broking":
                filter_conditions &= Q(payment_type__icontains="Partner")
            elif type_of_payment == "Rebate":
                filter_conditions &= Q(payment_type__icontains="Rebate")
            elif type_of_payment == "Syndicate Payment":
                filter_conditions &= Q(payment_type__icontains="Syndicate")

        if overall_status:
            overall_status = overall_status.split(',')
            filter_conditions &= Q(overall_status__in=overall_status)

        if settlement_currency:
            filter_conditions &= Q(settlement_currency=settlement_currency)

        if coverholder_name:
            filter_conditions &= Q(coverholder_name__icontains=coverholder_name)

        if final_bank_account_name:
            filter_conditions &= Q(final_bank_name=final_bank_account_name)

        if file_name:
            filter_conditions &= Q(bdx_file_name__icontains=file_name)
        
        payment_status = True if payment_status == "true" else False
        filter_conditions &= Q(payment_status=payment_status)
        
        # Apply the combined Q conditions to the queryset
        queryset = queryset.filter(filter_conditions, overall_status__icontains="no variance")
        serializer = self.serializer_class(queryset[skip: skip + rows_per_page], many=True)
        return Response({'data': serializer.data, 'count': queryset.count()}, status=status.HTTP_200_OK)
    
    def post(self, request):
        try:
            for i in request.data['ids']:
                instance = PayoutSummary.objects.get(id=i)
                instance.payment_status = True
                instance.save()
                print("Record updated successfully.")
                # if Coversheet.objects.filter(final_bank_account=instance.final_bank_account, settlement_currency=instance.settlement_currency).exists():
                #     cover_sheet = Coversheet.objects.get(final_bank_account=instance.final_bank_account, settlement_currency=instance.settlement_currency)
                #     cover_sheet.sum_of_final_net_premium_settlement_currency += Decimal(instance.sum_of_final_net_premium_settlement_currency) if instance.sum_of_final_net_premium_settlement_currency is not None else Decimal(0.0)
                #     cover_sheet.sum_of_rebate += Decimal(instance.sum_of_rebate) if instance.sum_of_rebate is not None else Decimal(0.0)
                #     cover_sheet.sum_of_net_payment += Decimal(instance.sum_of_net_payment) if instance.sum_of_net_payment is not None else Decimal(0.0)
                #     cover_sheet.save()
                #     print("Coversheet already exists and updated")
                # else:
                #     Coversheet.objects.create(
                #         certificate_ref = instance.certificate_ref,
                #         coverholder_name = instance.coverholder_name,
                #         final_bank_account = instance.final_bank_account,
                #         final_bank_name = instance.final_bank_name,
                #         to_bank_account_name = instance.to_bank_account_name,
                #         to_bank_account = instance.to_bank_account,
                #         settlement_currency = instance.settlement_currency,
                #         sum_of_final_net_premium_settlement_currency = instance.sum_of_final_net_premium_settlement_currency if instance.sum_of_final_net_premium_settlement_currency is not None else 0.0,
                #         sum_of_rebate = instance.sum_of_rebate if instance.sum_of_rebate is not None else 0.0,
                #         sum_of_net_payment = instance.sum_of_net_payment if instance.sum_of_net_payment is not None else 0.0,
                #         payment_id = instance.payment_id,
                #         payment_type = instance.payment_type
                #     )
                #     print("Coversheet created")
            return Response({"Message": "Record updated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"Message": "Failed to update record."}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk, *args, **kwargs):
        instance = PayoutSummary.objects.get(id=pk)
        serializer = PayoutSummarySerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Save TreasuryPYMT record
        bdx_ids = instance.bdx_ids.replace('[', '').replace(']', '').split(',')
        for bdx_id in bdx_ids:
            bdx_obj = PremiumBDX.objects.get(id=bdx_id)
            max_id = PaymentTreasuryPYMT.objects.aggregate(Max('id'))['id__max'] or 0
            PaymentTreasuryPYMT.objects.create(
                id = max_id + 1,
                category = instance.category,
                type_of_payment = instance.payment_type,
                payment_to = instance.placing_broker,
                source_input = "BDX",
                file_name = bdx_obj.filename,
                bdx_name_month_and_year = bdx_obj.filename,
                bdx_month_and_year_only_2024 = str(bdx_obj.month).capitalize() + "'" + str(bdx_obj.year)[2:4],
                coverholder_name = instance.coverholder_name,
                coverholder_entity = None,
                payment_type = instance.payment_type,
                certificate_ref = bdx_obj.certificateref,
                lob = bdx_obj.lob,
                umr = bdx_obj.umr,
                sett_currency = bdx_obj.settlementcurrency,
                mga_commision = instance.sum_of_net_payment if instance.payment_type == "MGA Commission" else 0.0,
                net_premium_to_london = instance.sum_of_net_payment,
                adjustment_or_rebate = instance.sum_of_rebate,
                net_transfer = instance.sum_of_net_payment,
                usd_value = BankExchangeRate.objects.filter(currency_code=bdx_obj.settlementcurrency, month=bdx_obj.month).first().exchange_rate * instance.sum_of_net_payment if BankExchangeRate.objects.filter(currency_code=bdx_obj.settlementcurrency, month=bdx_obj.month).exists() else 0.0,
                bank_account = instance.final_bank_account,
                bank_reference = None,
                payment_date = None,
                year = bdx_obj.year,
                month = bdx_obj.month,
                bdx_location_link = None,
                user_allocated = None,
                comments = None,
                bdx_name_original = bdx_obj.filename,
                payment_id = instance.payment_id,
                payment_status = instance.payment_complete_status
            )
        return Response(serializer.data, status=status.HTTP_200_OK)

class PayoutSummaryIDViewSet(APIView):
    def get(self, request):
        queryset = PayoutSummary.objects.all().values_list('payment_id', flat=True).distinct()
        return Response({"data": list(queryset)}, status=status.HTTP_200_OK)
    

class CoversheetViewSet(viewsets.ModelViewSet, generics.UpdateAPIView):
    """
    API endpoint for managing PaymentTreasury objects.
    """
    pagination_class = CustomPagination
    queryset = Coversheet.objects.all()
    serializer_class = CoversheetSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['payment_id']

    def list(self, request):
        """
        Handles GET requests to retrieve a list of PaymentTreasury objects.
        """
        page_number = int(request.GET.get("skip", 0))
        rows_per_page = int(request.GET.get("pageSize", 20))
        payment_type = request.GET.get("type_of_payment", None)
        # certificate_ref = request.GET.get("certificate_ref", None)
        # file_name = request.GET.get("file_name", None)
        payment_id = request.GET.get("payment_id", None)

        skip = page_number * rows_per_page
        filter_conditions = Q()
        # if certificate_ref:
        #     filter_conditions &= Q(certificate_ref__icontains=certificate_ref)
        # if file_name:
        #     filter_conditions &= Q(file_name__icontains=file_name)
        if payment_id:
            filter_conditions &= Q(payment_id__icontains=payment_id)

        if payment_type == "MGA Commission":
            filter_conditions &= Q(payment_type__icontains="Commission")

        if payment_type == "Internal Broking":
            filter_conditions &= Q(payment_type__icontains="Partner")

        if payment_type == "Rebate":
            filter_conditions &= Q(payment_type__icontains="Rebate")

        if payment_type == "Syndicate Payment":
            filter_conditions &= Q(payment_type__icontains="Syndicate")

        queryset = self.get_queryset().filter(filter_conditions)[
                   skip: skip + rows_per_page
                   ]

        # Apply variance condition here

        # output = []

        # if type_of_payment == "MGA Commission":
        #     for i in queryset:
        #         result = {}
        #         if len(output) > 0:
        #             for j in output:
        #                 if j['certificate_ref'] == i.certificate_ref:
        #                     j['commission'] += i.mga_commision
        #         else:
        #             result['category'] = i.category
        #             result['file_name'] = i.file_name
        #             result['certificate_ref'] = i.certificate_ref
        #             result['coverholder_name'] = i.coverholder_name
        #             result['settlement_currency'] = i.sett_currency
        #             result['receiving_bank_account_name'] = i.coverholder_entity
        #             result['receiving_bank_account'] = i.bank_account
        #             result['commission'] = i.mga_commision
        #             output.append(result)

        #     data = {"count": len(output), "data": output}
        # else:
        serializer = self.get_serializer(queryset, many=True)
        response_data = serializer.data
        data = {"count": self.get_queryset().filter(filter_conditions).count(), "data": response_data}

        return Response(data)