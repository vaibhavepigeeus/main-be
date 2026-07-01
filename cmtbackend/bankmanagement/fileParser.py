import boto3
from bankmanagement.utils.parsers.parser import parse_barclay_data, parser_2, parse_lloyds_data, parse_citibank_data, \
    parse_hsbc_data, parse_jpmorgan_chase_bank_data, parse_mashreq_bank_data, parse_uob_bank_data, parse_cibc_bank_data
from bankmanagement.utils.generalUtils import (
    convert_to_yyyy_mm_dd,
    extract_account_number_and_date,
    getExcelFiles,
    purge_file,
    get_file_path,
)
import os
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import BankReconciliation, BankTransaction, BankDetails, SchedulerCheck
from decouple import config
import datetime
from decimal import Decimal
from payment.views import upload_file_to_s3
from documents.models import BrokerInformation, BankExchangeRate
from rest_framework.response import Response
from rest_framework import status
from bankmanagement.models import AccountingMonthEnd
from django.db.models.functions import Cast
from users.models import Users              # CMT-25
from django.db.models import Func, Value, CharField, DateField          # CMT-25
from dateutil import parser
import calendar
from datetime import date
from logging import getLogger
from users.utils import send_email
from filemanagement.views import reusable_file_upload
import pandas as pd
from io import BytesIO

logger = getLogger(__name__)

BUCKET_NAME = config("AWS_S3_TEMP_BUCKET")
TARGET_BUCKET = config("AWS_S3_PROCESSED_BUCKET")
COMMON_BUCKET = config("AWS_STORAGE_BUCKET_NAME")
PATH = config("BANK_FILES_PATH")
TEMP_FILES = "./temp/"
os.environ["AWS_ACCESS_KEY_ID"] = config("AWS_ACCESS_KEY")
os.environ["AWS_SECRET_ACCESS_KEY"] = config("AWS_SECRET_KEY")

def send_rejection_email(file_name, user, error_message):
    try:
        if user and user.email:
            subject = f'File Rejection Notification - {file_name}'
            message = f'''
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #d9534f;">File Rejection Notification</h2>
                <p>Dear User,</p>
                <p>We regret to inform you that your uploaded file <strong>{file_name}</strong> has been rejected.</p>
                <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 10px; margin: 10px 0;">
                    <p style="margin: 0;"><strong>Reason for rejection:</strong> {error_message}</p>
                </div>
                <p>Please review the error message, make the necessary corrections, and upload the file again.</p>
                <p>If you need any assistance, please don't hesitate to contact our support team.</p>
                <p>Thank you for your understanding.</p>
                <p>Best regards,<br>CMT Admin Team</p>
            </body>
            </html>
            '''
            
            send_email(
                sender_email=settings.EMAIL_HOST_USER,
                recipient_email=[user.email],
                subject=subject,
                body=message
            )
    except Exception as e:
        logger.error(f"Failed to send rejection email: {str(e)}")

def upload_file(file_name, user_id):
    logger.info(f"Uploading File to bucket: {TARGET_BUCKET}")

    # If S3 object_name was not specified, use file_name
    full_file_path = get_file_path(f'{user_id}_{file_name}')
    file_name = "{}.xlsx".format(file_name.split('.')[0])

    logger.info(f"Uploading File: {file_name}")
    logger.info(f"Full File Path: {full_file_path}")
    # Upload the file
    s3_client = boto3.client("s3")
    logger.info(f"S3 Client Created.")
    try:
        logger.info(f"File Exists? : {os.path.exists(full_file_path)}")
        if os.path.exists(full_file_path):
            # Open the file in binary mode
            logger.info("Opening file in binary mode")
            with open(full_file_path, 'rb') as file:

                #uploading in the process bucket
                logger.info(f"Uploading in the process bucket : {TARGET_BUCKET}")
                s3_client.upload_file(full_file_path, TARGET_BUCKET, file_name)

                # Prepare your request_data as needed
                request_data = {
                    'module_name': 'Bank Statement',  # Replace with your actual module name
                    'bucket_name': COMMON_BUCKET,   # Replace with your actual bucket name if needed
                }
                
                # Call the reusable_file_upload function
                logger.info("Uploading in the file-managemnt bucket")
                reusable_file_upload(None, file, request_data=request_data, original_filename=full_file_path, is_upload=False)
        else:
            logger.info("The file does not exist.")
    except Exception as e:
        logger.exception("Error while uploading to S3")
        return False
    
    logger.info("File uploaded Successfully.")
    return True


def create_reconciliation_model(data, file_name, bank_details, uploaded_status, err=None, user_id=None):
    logger.info(f"Creating Recon Entry for file = {file_name}")
    try:
        existing_data = BankReconciliation.objects.filter(file_name=file_name).first()
        logger.info(f"Recon Data exists for file {file_name}? => : {existing_data}")
        if existing_data is None:
            return BankReconciliation.objects.create(
                bank_account_no=data[0],
                file_name=file_name,
                uploaded_date=timezone.now(),
                uploaded_time=timezone.now(),
                file_date=data[1] or None,
                uploaded_status="rejected",
                credit_amount=0.00,
                debit_amount=0.00,
                total_amount=0.00,
                ct_amount=0.00,
                ct_amount_car=0.00,
                bank_charges=0.00,
                ct_bank_charges=0.00,
                ct_bank_charges_var=0.00,
                category_total=0.00,
                error_message="",
                locked=False,
                allocated_date=timezone.now(),
                analyst_comments= "",
                resolution_date=timezone.now(),
                file_name_hyperlink=file_name,
                bank_details=bank_details,
                uploaded_by=user_id            # CMT-25
            )
        else:
            if not err:
                logger.info(f"There is no error, continuing processing the file {file_name}")
                existing_data.bank_account_no = data[0]
                existing_data.file_name = file_name
                existing_data.uploaded_date = timezone.now()
                existing_data.uploaded_time = timezone.now()
                existing_data.file_date = data[1] or None
                existing_data.uploaded_status = "uploaded"
                existing_data.error_message = "No errors"
                existing_data.allocated_date = timezone.now()
                existing_data.final_status = "uploaded"
                existing_data.analyst_comments = "Waiting to be processed"
                existing_data.file_name_hyperlink = file_name
                existing_data.save()

            logger.info("Reconciliation entry already exists!")
    except Exception as e:
        logger.error(f"Reconciliation creation Error: {str(e)}")
        return None


def create_reconciliation_record_for_duplicate_file(data, file_name, bank_details, err=None, user_id=None):
    try:
        return BankReconciliation.objects.create(
            bank_account_no=data[0],
            file_name=file_name,
            uploaded_date=timezone.now(),
            uploaded_time=timezone.now(),
            file_date=data[1] or timezone.now(),
            uploaded_status="rejected",
            credit_amount=0.00,
            debit_amount=0.00,
            total_amount=0.00,
            ct_amount=0.00,
            ct_amount_car=0.00,
            bank_charges=0.00,
            ct_bank_charges=0.00,
            ct_bank_charges_var=0.00,
            category_total=0.00,
            error_message="Duplicate file uploaded",
            locked=False,
            allocated_date=timezone.now(),
            final_status="rejected",
            analyst_comments=(
                "Duplicate file uploaded"
            ),
            resolution_date=timezone.now(),
            file_name_hyperlink=file_name,
            bank_details=bank_details,
            uploaded_by=user_id            # CMT-25
        )
    except Exception as e:
        print("Reconciliation creation Error:", e)
        return None

def get_accounting_date(date_of_month, is_date=True):
    """ This method to calculate accounting month year for current month """

    if isinstance(date_of_month, str):
        date_of_month = datetime.datetime.strptime(date_of_month, "%Y-%m-%d").date()
    elif isinstance(date_of_month, datetime.datetime):
        date_of_month = date_of_month.date()

    year = date_of_month.year
    month = date_of_month.month
    last_day = calendar.monthrange(year, month)[1]

    last_day_of_month = date(year, month, last_day) if is_date else datetime(year, month, last_day)

    return last_day_of_month


def get_bank_exchange_rate(Bank_Currency_Code, accounting_date):
    logger.info(f"Bank_Currency_Code: {Bank_Currency_Code}")
    logger.info(f"accounting_date: {accounting_date}")
    last_day_of_month = get_accounting_date(accounting_date)
    logger.info(f"last_day_of_month: {last_day_of_month}")
    try:
        bank_exchange_rate_obj = BankExchangeRate.objects.get(
            currency_code=str(Bank_Currency_Code).strip(), month=last_day_of_month
        )
        return bank_exchange_rate_obj.exchange_rate, last_day_of_month
    except BankExchangeRate.DoesNotExist:
        try:
            # If no exact match, get the latest record before the last_day_of_month
            bank_exchange_rate_obj = BankExchangeRate.objects.filter(
                currency_code=str(Bank_Currency_Code).strip(),
                month__lt=last_day_of_month,
                month__isnull=False,
            ).latest("month")

            parsed_date = None
            if bank_exchange_rate_obj.month:
                parsed_date = parser.parse(bank_exchange_rate_obj.month).date()

            return bank_exchange_rate_obj.exchange_rate, parsed_date
        except BankExchangeRate.DoesNotExist:
            raise ValueError(
                "No valid exchange rate found for the given currency code."
            )

def get_accounting_month(creation_date):
        """
        Get accounting month based on given date using the following rules:
        - Dates from 3rd of current month to 2nd of next month -> current month end
        - Dates from 3rd of month -> that month's end date
        """
        # Convert string to date if needed
        # if isinstance(creation_date, str):
        #     creation_date = datetime.strptime(creation_date, '%Y-%m-%d').date()
        # # Convert datetime to date if needed
        # elif isinstance(creation_date, datetime):
        #     creation_date = creation_date.date()
            
        # Get all accounting months
        accounting_months = AccountingMonthEnd.objects.filter(accounting_month_start_date__lte=creation_date, accounting_month_end_date__gte=creation_date).order_by('accounting_month_end_date')
        
        # if not accounting_months:
        #     return Response(
        #         {
        #             "message": "Calendar month not defined",
        #             "status": "error"
        #         },
        #         status=status.HTTP_500_INTERNAL_SERVER_ERROR
        #     )
        # else:

        logger.info(f"accounting_months : {accounting_months}")
        return accounting_months.first().accounting_month_date

def create_bank_transaction_model(
        data, file_name, bank_reconciliation_data, bank_details, user_name=''
):
    date = convert_to_yyyy_mm_dd(data["date_and_time"])
    if date is None or bank_reconciliation_data is None:
        return None
    with transaction.atomic():
        try:
            try:
                g = BankTransaction.objects.filter(archived=False, Bank_Transaction_Id__startswith="BNKTXN").latest("id")
                last_trans_id = g.Bank_Transaction_Id
                if last_trans_id:
                    ll = last_trans_id[6:]
                    trl = str(int(ll) + 1).zfill(4)
                    bank_trx_id = "BNKTXN00" + trl
            except BankTransaction.DoesNotExist:
                bank_trx_id = "BNKTXN000001"
            #calculate receivable amount in USD
            logger.info(f"data: {data}")
            roe, roe_date = get_bank_exchange_rate(data["currency"],date)
            logger.info(f"ROE: {roe}")
            logger.info(f"ROE Date: {roe_date}")
            receivable_amount = Decimal(data["Receivable_Amount"])
            receivable_amount_usd = round(Decimal(receivable_amount) / roe, 2)
            logger.info(f"Receivable amount in USD: {receivable_amount_usd}")
            
            new_ac = get_accounting_month(datetime.datetime.now().date())
            logger.info(f"new_ac for bank_trx_id : {new_ac}")
            
            # if isinstance(new_ac, Response):
            #     new_ac = date
            bank_transaction = BankTransaction.objects.create(
                Bank_Transaction_Id=bank_trx_id,
                Accounting_Month=new_ac,
                PT_Receving_Bank_Name=data["account_name"],
                Bank_Account_Name_Entity=bank_details.entity_name,
                Receiving_Bank_Account=bank_details.account_number,
                Broker_Branch="",
                Broker="",
                Payment_Receive_Date=date,
                Payment_Reference=data['details'][0:450],
                Bank_Currency_Code=bank_details.currency,
                Payment_Currency_Code=data["currency"],
                Bank_Exchange_Rate=0.00,
                Bank_Exchange_Charges=0.00,
                Bank_Charges=0.00,
                Receivable_Amount=receivable_amount,
                Receivable_Amount_USD=receivable_amount_usd,
                TL_Fees=0.00,
                Currency=data["currency"],
                File_Name=file_name,
                Created_By=user_name,
                Analyst_Name="",
                Date_And_Time=date,
                Uploaded_By=user_name,
                assigned_users_list="",
                Allocation_Status="",
                # workflow=,
                bank_details=bank_details,
                updated_by="",
                updatedDateAndTime=timezone.now(),
                updated_fields="",
                bank_reconciliation=bank_reconciliation_data,
                auto_upload=True,
                locked=None,
                error="",
                txn_category="",
                ROE=roe,
                ROE_Date=roe_date,
                Aging_Bucket='0 - 5'
            )

            logger.info(f"Bank transaction created successfully")
            return bank_transaction
        except Exception as e:
            logger.error(f"Error creating bank transaction: {str(e)}")
            return None


def move_file_to_bucket(source_bucket, source_key, destination_bucket):
    s3_client = boto3.client("s3")
    try:
        # Copy the object to the destination bucket
        s3_client.copy_object(
            Bucket=destination_bucket,
            CopySource={"Bucket": source_bucket, "Key": source_key},
            Key=source_key,
        )
        # Delete the object from the source bucket
        s3_client.delete_object(Bucket=source_bucket, Key=source_key)

        print(
            f"File '{source_key}' moved successfully from '{source_bucket}' to '{destination_bucket}'"
        )
        return True
    except Exception as e:
        print(f"Error moving file: {e}")
        return False


def move_failed_local_file(file_name, user_id):
    """Move failed local files to prevent reprocessing"""
    try:
        FAILED_DIR = os.path.join(PATH, "failed")
        print("FAILED_DIR", FAILED_DIR)
        if not os.path.exists(FAILED_DIR):
            os.makedirs(FAILED_DIR)
        
        source_path = get_file_path(f'{user_id}_{file_name}')
        dest_path = os.path.join(FAILED_DIR, f'{user_id}_{file_name}')
        
        if os.path.exists(source_path):
            import shutil
            shutil.move(source_path, dest_path)
            logger.info(f"Moved failed local file {file_name} to failed directory")
    except Exception as e:
        logger.error(f"Error moving failed local file: {str(e)}")


def get_ac_details(ac_number):
    try:
        return BankDetails.objects.filter(account_number=ac_number).first()
    except Exception as e:
        print("Account details Error:", e)
        return None


def process_sheet_data(file_path, bank_type, user_id):
    file_path = f'{user_id}_{file_path}'        # CMT-25
    table_data = None
    payment_amount = None
    receipt_amount = None

    if bank_type == "barclay":
        table_data, payment_amount, receipt_amount, err_msg = parse_barclay_data(file_path)

    elif bank_type == "lloyds":
        table_data, payment_amount, receipt_amount, err_msg = parse_lloyds_data(file_path)

    elif bank_type == "citibank":
        table_data, payment_amount, receipt_amount, err_msg = parse_citibank_data(file_path)

    elif bank_type == "hsbc":
        table_data, payment_amount, receipt_amount, err_msg = parse_hsbc_data(file_path)

    elif bank_type == "jpmorgan_chase_bank":
        table_data, payment_amount, receipt_amount, err_msg = parse_jpmorgan_chase_bank_data(file_path)

    elif bank_type == "mashreq_bank":
        table_data, payment_amount, receipt_amount, err_msg = parse_mashreq_bank_data(file_path)

    elif bank_type == "uob_bank":
        table_data, payment_amount, receipt_amount, err_msg = parse_uob_bank_data(file_path)

    elif bank_type == "cibc_bank":
        table_data, payment_amount, receipt_amount, err_msg = parse_cibc_bank_data(file_path)

    return table_data, payment_amount, receipt_amount, err_msg


def process_s3_file(file_name, user_id, user):
    logger.info(f"Processing S3 File {file_name}")
    try:
        barclays = [
            "62514844",
            "53549925",
            "53242122",
            "56878488",
            "BE0190078",
            "BE0190079",
            "BE0190080",
        ]
        lloyds = [
            "30963411988808",
            "GB12LOYD30801222032537",
            "GB16LOYD30801286692374",
            "GB26LOYD30801211988808",
            "GB90LOYD30801221687268",
            "GB90LOYD30801223067868",
            "B77LOYD30801212016893",
        ]
        citibank = ["20240021609", "13726185", "416092"]
        hsbc = [
            "1/6770/019",
            "889031312",
            "889031339",
            "889031347",
            "011-302460-502",
            "011-248663-501",
        ]

        jpmorgan_chase_bank = [
            "80009471527",
            "80009950108",
            "80010417022",
            "80009842677"
        ]

        mashreq_bank = [
            "19000073673",
            "19000073674",
            "19000073675",
        ]

        uob_bank = [
            "7799225208",
            "7793085226",
            "7729309684",
            "7729309692"
        ]

        cibc_bank = [
            "20218316",
            "21000500",
            "29006117"
        ]

        data = extract_account_number_and_date(file_name)
        logger.info(f"Account and Date Details = {str(data)}")

        if data[0] and data[1]:
            processed_data = None
            payment_amount = 0
            receipt_amount = 0
            bank_reconciliation = BankReconciliation.objects.get(file_name=file_name)

            bank_details = get_ac_details(ac_number=data[0])
            logger.info(f"BANK DETAILS : {bank_details}")

            # Add more cases
            if data[0] in barclays:
                logger.info(f"Processing barclay sheet data for file {file_name}")
                processed_data, payment_amount, receipt_amount, err_msg = process_sheet_data(
                    file_name, "barclay", user_id
                )
            elif data[0] in lloyds:
                logger.info(f"Processing lloyds sheet data for file {file_name}")
                processed_data, payment_amount, receipt_amount, err_msg = process_sheet_data(
                    file_name, "lloyds", user_id
                )
            elif data[0] in citibank:
                logger.info(f"Processing citibank sheet data for file {file_name}")
                processed_data, payment_amount, receipt_amount, err_msg = process_sheet_data(
                    file_name, "citibank", user_id
                )
            elif data[0] in hsbc:
                logger.info(f"Processing hsbc sheet data for file {file_name}")
                processed_data, payment_amount, receipt_amount, err_msg = process_sheet_data(
                    file_name, "hsbc", user_id
                )
            elif data[0] in jpmorgan_chase_bank:
                logger.info(f"Processing jpmorgan_chase_bank sheet data for file {file_name}")
                processed_data, payment_amount, receipt_amount, err_msg = process_sheet_data(
                    file_name, "jpmorgan_chase_bank", user_id
                )
            elif data[0] in mashreq_bank:
                logger.info(f"Processing mashreq_bank sheet data for file {file_name}")
                processed_data, payment_amount, receipt_amount, err_msg = process_sheet_data(
                    file_name, "mashreq_bank", user_id
                )
            elif data[0] in uob_bank:
                logger.info(f"Processing uob_bank sheet data for file {file_name}")
                processed_data, payment_amount, receipt_amount, err_msg = process_sheet_data(
                    file_name, "uob_bank", user_id
                ) 
            elif data[0] in cibc_bank:
                logger.info(f"Processing cibc_bank sheet data for file {file_name}")
                processed_data, payment_amount, receipt_amount, err_msg = process_sheet_data(
                    file_name, "cibc_bank", user_id
                ) 
            
                    
            else:
                create_reconciliation_model(
                    [bank_details.account_number, data[1]],
                    file_name,
                    bank_details,
                    uploaded_status="rejected",
                    err="Bank account is yet to be automated",
                    user_id=user_id
                )

            logger.info(
                f"Processed sheet data, processed_data = : {processed_data}, payment_amount = {payment_amount}, receipt_amount = {receipt_amount}"
            )

            if err_msg not in ['', None]:
                bank_reconciliation.error_message = err_msg
                bank_reconciliation.analyst_comments = err_msg
                bank_reconciliation.uploaded_status = "rejected"
                bank_reconciliation.save()
                move_failed_local_file(file_name, user_id)

            if not processed_data:
                logger.info(f"No processed data for file {file_name}, moving to failed folder")
                move_failed_local_file(file_name, user_id)
                return None

            bank_reconciliation.credit_amount = Decimal(receipt_amount)
            bank_reconciliation.ct_amount_car = Decimal(receipt_amount)
            bank_reconciliation.debit_amount = Decimal(payment_amount)
            bank_reconciliation.total_amount = (
                bank_reconciliation.credit_amount + bank_reconciliation.debit_amount
            )

            for data in processed_data:
                create_bank_transaction_model(
                    data, file_name, bank_reconciliation, bank_details, user_name=user.user_name
                )
            if processed_data:
                logger.info("File Processed Successfully")
                bank_reconciliation.final_status = "processed"
                bank_reconciliation.analyst_comments = (
                    "File has been processed successfully"
                )
                bank_reconciliation.uploaded_status = "uploaded"

            else:
                # Exit processing if bank transaction creation failed
                bank_reconciliation.uploaded_status = "rejected"
                bank_reconciliation.final_status = "error"
                bank_reconciliation.error_message = data["error_message"]
                bank_reconciliation.analyst_comments = data["error_message"]
            bank_reconciliation.save()
        else:
            logger.info("File name does not match the pattern")
    except Exception as e:
        logger.error(f"Process s3 file error : {str(e)}")
        try:
            bank_reconciliation.final_status = "error"
            bank_reconciliation.uploaded_status = "rejected"
            bank_reconciliation.error_message = str(e)[:450]
            bank_reconciliation.analyst_comments = bank_reconciliation.error_message
            bank_reconciliation.save()
        except Exception as db_error:
            logger.error(f"Failed to update bank reconciliation record: {str(db_error)}")
        
        # Move failed local file to prevent reprocessing
        move_failed_local_file(file_name, user_id)

    # Doesnt require here as we are doing it over its parent function so Temporarily commented
    # upload_file(file_name)
    # purge_file(file_name)


def parse_files(files):
    logger.info("Parsing files Triggered for Bank Statements")
    try:
        for file in files:
            logger.info(f"Parsing file {file}")

            # CMT-25
            filename = file.split("_")
            user_id = filename[0]
            user = Users.objects.get(id=user_id) if Users.objects.filter(id=user_id).exists() and user_id != "None" else None
            file_proceed = is_file_proceed(filename[1])
            file = filename[1]
            logger.info(f"Is File Proceed = {file_proceed}")

            # Get the file name/key of the object
            ac_number, date, extension = extract_account_number_and_date(file)
            logger.info(
                f"Details after matching pattern, ac_number = {ac_number}, date = {date}, extension = {extension}"
            )

            bank_details = get_ac_details(ac_number)
            logger.info(f"Bank Details for ac_number = {ac_number} = {bank_details}")

            # CMT-25
            if not file_proceed:
                logger.info(
                    f"Processing file as Bank recon doesn't exists for file {file} as status = uploaded"
                )
                if not (extension == "xls" or extension == "xlsx"):
                    logger.info(f"Extension not valid for file {file}")
                    create_reconciliation_model(
                        [bank_details.account_number, date],
                        file,
                        bank_details,
                        uploaded_status="rejected",
                        err="Invalid file extention - accepted xls or xlsx",
                        user_id=user
                    )
                    # send_rejection_email(
                    #     file,
                    #     user,
                    #     "Invalid file extension - accepted xls or xlsx"
                    # )
                elif ac_number and not bank_details:
                    logger.info(
                        f"ac_number or bank_details are not valid for file {file}"
                    )
                    create_reconciliation_model(
                        [bank_details.account_number, date],
                        file,
                        bank_details,
                        uploaded_status="rejected",
                        err="Invalid bank account number",  ### change
                        user_id=user
                    )
                    # send_rejection_email(
                    #     file,
                    #     user,
                    #     "Invalid bank account number"
                    # )
                elif date is None:
                    logger.info(f"Date not valid for file {file}")
                    create_reconciliation_model(
                        [bank_details.account_number or "", date],
                        file,
                        bank_details,
                        uploaded_status="rejected",
                        err="Invalid file name - should be 'ACC_NO-DD-MM-YYYY'",  ## change
                        user_id=user
                    )
                    # send_rejection_email(
                    #     file,
                    #     user,
                    #     "Invalid file name - should be 'ACC_NO-DD-MM-YYYY'"
                    # )
                else:
                    create_reconciliation_model([bank_details.account_number, date], file, bank_details, uploaded_status="rejected", user_id=user)
                    process_s3_file(file, user_id, user)
                    # send_rejection_email(
                    #     file,
                    #     user,
                    #     "Invalid file'"
                    # )

                upload_file(file, user_id)
            else:
                logger.info(
                    f"Duplicate file as Bank recon exists for file {file} as status = uploaded"
                )
                create_reconciliation_record_for_duplicate_file(
                    [bank_details.account_number or "", date],
                    file,
                    bank_details,
                    "Duplicate file",
                )

            purge_file(file, user_id)
    except Exception as e:
        logger.error(f"Parsing files failed with Error: {str(e)}")


def is_file_proceed(file):
    return BankReconciliation.objects.filter(
        file_name=file, uploaded_status="uploaded"
    ).exists()


# Entry point for scheduler
def process_new_files():
    logger.info("Scheduler Triggered for Bank Statements")
    logger.info(f"time for trigger => {str(datetime.datetime.now())}")

    # Log the current directory and file name on scheduler trigger
    current_directory = os.getcwd()
    logger.info(f"Scheduler triggered from : {current_directory}")

    # Check if scheduler is already running
    is_scheduler_locked = get_scheduler_check()
    logger.info(f"Is Scheduler Locked: {is_scheduler_locked}")
    if is_scheduler_locked:
        return
    else:
        update_scheduler_check(locked_type=True)
        logger.info("Locking Scheduler for Bank Statements. Value = True")
    
    if not os.path.exists(PATH):
        os.makedirs(PATH)

    files = getExcelFiles(PATH)
    logger.info(f"Files Found in directory {files}")

    try:
        parse_files(files)
        update_scheduler_check(locked_type=False)
        logger.info("UnLocking Scheduler for Bank Statements. Value = False")
    except Exception as e:
        logger.error(f"Processing Bank Statements Failed with exception e: {str(e)}")
        update_scheduler_check(locked_type=False)
        logger.info("UnLocking Scheduler for Bank Statements. Value = False")


def create_scheduler_check():
    pass


def get_scheduler_check():
    records = SchedulerCheck.objects.get(lock_type='bank-statement')
    return True if records.locked else False


def update_scheduler_check(locked_type):
    obj = SchedulerCheck.objects.get(lock_type='bank-statement')
    obj.locked = locked_type
    obj.save()
    return obj.locked


def get_prembdx_scheduler_check():
    records = SchedulerCheck.objects.get(lock_type='prembdx')
    logger.info(f"records.locked: {records.locked}")
    return True if records.locked else False


def update_prembdx_scheduler_check(locked_type):
    obj = SchedulerCheck.objects.get(lock_type='prembdx')
    obj.locked = locked_type
    obj.save()
    return obj.locked

from payment.models import PremBDXFiles
from payment.views import get_df
from bankmanagement.prembdx_helper import save_premBDX, save_exception_data 

def upload_bank_files():
    logger.info("Started upload bank files Scheduler-----------------------------")
    BDX_FILES_PATH = config('BDX_FILES_PATH')
    if get_prembdx_scheduler_check():
        logger.info("prembdx scheduler is locked")
        return
    else:
        update_prembdx_scheduler_check(locked_type=True)

    prembdxfiles_queryset = PremBDXFiles.objects.filter(archived=False, upload_status=False)
    logger.info(f"Records founds for upload : {str((prembdxfiles_queryset.count()))}")
    for row in prembdxfiles_queryset:
        try:
            logger.info("PremBDXFiles id: " + str(row.id))

            file_path = os.path.join(BDX_FILES_PATH, row.filename)

            # Extracting Data as DF from excel
            df, data = get_df(str(row.filename), file_path, row.sheet_name)
            
            logger.info(f"df: {type(df)}")
            logger.info(f"data: {type(data)}, {len(data)}")
            if not isinstance(df, str) and row.month:
                try:
                    save_premBDX(data, row)
                except Exception as e:
                    print("Error saving premBDX:", e)
                    if row.error_message:
                        row.error_message += ", Failed to save premBDX"
                    else:
                        row.error_message = "Failed to save premBDX"
                try:
                    save_exception_data(row)
                except Exception as e:
                    print("Error saving exception data:", e)
                    if row.error_message:
                        row.error_message += ", Failed to save exception data"
                    else:
                        row.error_message = "Failed to save exception data"
            # else:
            #     raise Exception("Failed to save premBDX. Please check the file format")
            
        except Exception as e:
            print("Exception e:", str(e))

            # Updating Db error message for UI
            if row.error_message:
                row.error_message += ", Failed to save premBDX"
            else:
                row.error_message = "Failed to save premBDX"

        # set upload_status flag true for not coming file second time.
        row.upload_status = True

        # save the prembdxfile object
        row.save()
    
    try:
        for row in PremBDXFiles.objects.filter(upload_status=True, deleted=False):
            file_path = os.path.join(BDX_FILES_PATH, row.filename)
            os.remove(file_path)
            # set delete flag true when file is deleted
            row.deleted = True
            row.save()
    except Exception as e:
        pass
    update_prembdx_scheduler_check(locked_type=False)