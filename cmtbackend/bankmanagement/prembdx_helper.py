from payment.models import PremBDXFiles, PremiumBDX, PaymentException, PayoutSummary
import re
from rest_framework.response import Response
from rest_framework import status
import datetime
from payment.models import Documents, Users, PaymentTreasuryPYMT
from payment.views import upload_file_to_s3, save_datasheet
from django.db.models import Max, Sum, Q, DateField, FloatField
import psycopg2
from openpyxl import Workbook
import numpy as np
from decouple import config
from bankmanagement.models import CashTrackerReport, CashAllocation, CashAllocationCorrective
from django.db import connection
from documents.models import LOB, PayeeBankAccountDetails, BankDetails
from decimal import Decimal
from logging import getLogger

logger = getLogger(__name__)
bucket_name = config('PREMIUMBDX_FILE_STORAGE_BUCKET')

field_patterns = {
    'coverholdname': r'^coverholder\s*name$',
    'yearofaccount': r'^year\s*of\s*account$|^yoa$|^yearofaccount$',
    'umr': r'^umr$|^unique\s*market\s*reference\s*\(umr\)$',
    'agreementno': r'(?i)^agreement\s*(no|number)$',
    'certificateref': r'^certificate\s*ref$|^certificate\s*reference$',
    'lob': r'^lob$|^line\s*of\s*business$',
    'classofbusiness': r'^class\s*of\s*business$',
    'risktransactiontype': r'^risk,\s*transaction\s*type$|^transaction\s*type$',
    'country': r'^country$',
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

expected_heading = [
    "Certificate Ref",
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

def get_column_mappings(data, field_patterns):
    column_mappings = {}
    for standard_field, pattern in field_patterns.items():
        regex = re.compile(pattern, re.IGNORECASE)  # Case insensitive regex
        matched_key = None
        for key in data.keys():
            if regex.match(key.strip()):
                matched_key = key
                break
        column_mappings[standard_field] = matched_key
    return column_mappings

def check_file_exists(file_name, sheet_tab):
    # Check if file already exists in BDX table
    object_premium_bdx_report = PremiumBDX.objects.filter(filename=file_name, sheettab=sheet_tab, archived=False)

    if object_premium_bdx_report:
        return Response({'Response': 'File already exists'}, status=status.HTTP_400_BAD_REQUEST)

def save_premBDX(data, prem_bdx_file_obj):
    column_mappings = get_column_mappings(data, field_patterns)
    logger.info(f"data.keys() = {str(len(data[list(data.keys())[0]]))}")
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
                # if yearofaccount=="" or yearofaccount==0.00:
                #     return Response({'Response': 'Null values not allowed in the "Year of Account(YOA)" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                yearofaccount = ""

            try:
                umr = data[column_mappings['umr']][row]
                # if umr=="" or umr==0.00:
                #     return Response({'Response': 'Null values not allowed in the "UMR" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                umr = ""
            
            try:
                agreementno = data[column_mappings['agreementno']][row]
                # if agreementno=="" or agreementno==0.00:
                #     return Response({'Response': 'Null values not allowed in the "Agreement No" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                agreementno = ""
            
            try:
                certificateref = (data[column_mappings['certificateref']][row]).strip()
                # if certificateref=="" or certificateref==0.00:
                #     return Response({'Response': 'Null values not allowed in the "Certificate Ref" column!'}, status=status.HTTP_400_BAD_REQUEST)
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
                # if bindingagreement == "SCM" and insure=="" or insure==0.00:
                #     return Response({'Response': 'Null values not allowed in the "Insure/Insurer/Insured/Participating Insurer" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                insure = ""
            
            try:
                settlementcurrency = data[column_mappings['settlementcurrency']][row]
                # if settlementcurrency=="" or settlementcurrency==0.00:
                #     return Response({'Response': 'Null values not allowed in the "Settlement Currency/Sett ccy" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                settlementcurrency = ""
            
            try:
                originalcurrency = data[column_mappings['originalcurrency']][row]
                # if originalcurrency=="" or originalcurrency==0.00:
                #     return Response({'Response': 'Null values not allowed in the "Original Currency/Orig ccy" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                originalcurrency = ""
            
            try:
                commissionper = data[column_mappings['commissionper']][row]
                # if commissionper=="":
                #     return Response({'Response': 'Null values not allowed in the "Commission %/Comm %" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                commissionper = 0.00
            
            try:
                brokpremper = data[column_mappings['brokpremper']][row]
                # if bindingagreement == "SCM" and brokpremper=="":
                #     return Response({'Response': 'Null values not allowed in the "Brokerage %/Brokerage % of gross premium" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                brokpremper = 0.00
            
            try:
                percentforlloyds = data[column_mappings['percentforlloyds']][row]
                # if bindingagreement == "SCM" and percentforlloyds=="":
                #     return Response({'Response': 'Null values not allowed in the "% for Lloyd\'s/Lloyds %" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                percentforlloyds = 0.00
            
            try:
                rateofexchange = data[column_mappings['rateofexchange']][row]
                # if rateofexchange=="":
                #     return Response({'Response': 'Null values not allowed in the "Rate of Exchange/Sett Roe" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                rateofexchange = 0.00
            
            try:
                grosspremiumpaidthistime = data[column_mappings['grosspremiumpaidthistime']][row]
                # if grosspremiumpaidthistime=="":
                #     return Response({'Response': 'Null values not allowed in the "Gross Premium Paid This Time/GPP This Time" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                grosspremiumpaidthistime = 0.00
            
            try:
                gppsettlement = data[column_mappings['gppsettlement']][row]
            except:
                gppsettlement = 0.00
            
            try:
                commissionamount = data[column_mappings['commissionamount']][row]
                # if commissionamount=="":
                #     return Response({'Response': 'Null values not allowed in the "Commission Amount/Comm Amount" column!'}, status=status.HTTP_400_BAD_REQUEST)
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
                # if brokerageamountoc=="":
                #     return Response({'Response': 'Null values not allowed in the "Brokerage Amount (Original Currency)" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                brokerageamountoc = 0.00
            
            try:
                finalnetpremiumsc = data[column_mappings['finalnetpremiumsc']][row]
                # if finalnetpremiumsc=="":
                #     return Response({'Response': 'Null values not allowed in the "Final Net Premium (Settlement Currency)" column!'}, status=status.HTTP_400_BAD_REQUEST)
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
                # if bindingagreement == "1609" and accessoriitaly=="":
                #     return Response({'Response': 'Null values not allowed in the "Accessories (Italy)" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                accessoriitaly = None
            
            try:
                terrorismpremium = data[column_mappings['terrorismpremium']][row]
                # if bindingagreement == "1609" and terrorismpremium=="":
                #     return Response({'Response': 'Null values not allowed in the "Terrorism Premium" column!'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                terrorismpremium = 0.00
            
            try:
                finalnetpremiumusd = data[column_mappings['finalnetpremiumusd']][row]
                # if finalnetpremiumusd=="":
                #     return Response({'Response': 'Null values not allowed in the "Final Net Premium (USD)" column!'}, status=status.HTTP_400_BAD_REQUEST)
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
            
            # try:
            #     analyst_id = Users.objects.get(id=int(data[column_mappings['analyst_id']][row]))
            # except:
            #     analyst_id = None

            # Upload file to S3
            file_url = upload_file_to_s3(filename, bucket_name)

            current_time = datetime.datetime.now()
            document_obj = Documents.objects.create(document_name=str(filename),
                                                        document_date=current_time.date(),
                                                        document_type='Premium BDX', archieve_by='Analyst',
                                                        archieve_datetime=current_time, document_url=file_url)
            
            # Datasheet calculation:

            try:
                # line_of_business determination
                lob = LOB.objects.filter(lob_code=certificateref[1:3]).first().lob_code
            except:
                logger.info(f"LOB not found for Policy {certificateref}")
                if prem_bdx_file_obj.error_message:
                    prem_bdx_file_obj.error_message += f", LOB not found for Policy {certificateref}"
                else:
                    prem_bdx_file_obj.error_message = f"LOB not found for Policy {certificateref}"

            # Optimized retrieval of bank account details
            cash_allocation = CashAllocation.objects.filter(archived=False, policy_id=certificateref).first()
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

            # # roe calculation
            # rateofexchange = CashTrackerReport.objects.filter(Policy=certificateref).first().ROE_Bank_Statement if CashTrackerReport.objects.filter(Policy=certificateref).exists() else None

            # Getting value of treasury_transfer_date
            treasury_transfer_date = CashAllocationCorrective.objects.filter(policy_id=certificateref).first().treasury_confirmed_transfer_date if CashAllocationCorrective.objects.filter(policy_id=certificateref).exists() else None
            
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
            elif umr == 23 and participation == "mosaic":
                rebate = 0
            else:
                rebate = ((grosspremiumpaidthistime * 0.025) * 0.5) / rateofexchange

            # Calculate netpayment
            net_payment = finalnetpremiumusd - rebate if finalnetpremiumusd and rebate else None

            # Retrive Category
            try:
                e1sql = f"""SELECT placingbroker, participation FROM prem_scmagreement where umr = '{umr}';"""
                scmagreementvalues = check_entry_one(e1sql)

                if '1609' in prem_bdx_file_obj.scm_status:
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
                category = ''

            # Create payment_id
            month = prem_bdx_file_obj.month
            year = prem_bdx_file_obj.year
            try:
                month_number = {
                    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                    'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                    'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                }.get(month[:3].lower(), '01')
                payment_id = placing_broker[:4] + str(year)[2:4] + month_number
            except:
                payment_id = str(9999) + str(year)[2:4] + month


            # Get to bank account details from the payee bank account details table and bank details table
            try:
                if category == 'Cash':
                    to_account_name = PayeeBankAccountDetails.objects.filter(to_acc_name_benificiary_name=placingbroker+settlementcurrency, type='Cash').first().to_acc_name_benificiary_name
                    bank_account_number = PayeeBankAccountDetails.objects.filter(to_acc_name_benificiary_name=placingbroker+settlementcurrency, type='Cash').first().bank_acc_no
                else:
                    to_account_name = PayeeBankAccountDetails.objects.filter(Settlement_currency=settlementcurrency, type='Non-Cash').first().credit_bank_account_name_1609
                    bank_account_number = PayeeBankAccountDetails.objects.filter(Settlement_currency=settlementcurrency, type='Non-Cash').first().bank_acc_no
            except:
                to_account_name = None
                bank_account_number = None


            # if coverholdname == 'Mosaic Services Bermuda Limited' and receiving_bank_account_name == 'FRB':
            #     commission_transfer_from_bank_acc_number = BU5
            # else:
            commission_transfer_from_bank_acc_number = receiving_bank_account

            try:
                commission_transfer_from_bank_acc_name = BankDetails.objects.filter(account_number=commission_transfer_from_bank_acc_number).first().bank_name
            except:
                commission_transfer_from_bank_acc_name = None

            try:
                coverholdname_commission_bank = "Mosaic Syndicate Services Limited" if coverholdname == "Mosaic Europe" else coverholdname
                commission_bank_transfer_account_number = PayeeBankAccountDetails.objects.filter(from_account_name_benificiary_name=coverholdname_commission_bank).first().bank_acc_no
            except:
                commission_bank_transfer_account_number = None

            try:
                commission_bank_transfer_name = PayeeBankAccountDetails.objects.filter(from_account_name_benificiary_name=coverholdname).first().to_acc_name_benificiary_name
            except:
                commission_bank_transfer_name = None

            # Save the data to the PremiumBDX table
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
                analyst_id=prem_bdx_file_obj.uploaded_by,
                migrated_data = False,
                created_at = datetime.datetime.now(),
                updated_datetime = datetime.datetime.now(),
                receiving_bank_account_name = receiving_bank_account_name,
                receiving_bank_account = receiving_bank_account,
                transfer_to_pt_bank_account_name = transfer_to_pt_bank_account_name,
                treasury_transfer_date = treasury_transfer_date,
                invoice_bank_account = receiving_bank_account,
                final_bank_account = receiving_bank_account,
                final_bank_name = receiving_bank_account_name,
                rebate = rebate,
                net_payment = net_payment,
                gross_prem_sett_arch = None,
                net_prem_sett_incld_rebate_arch = None,
                payment_id = payment_id,
                to_account_name = to_account_name,
                bank_account_number = bank_account_number,
                commission_transfer_from_bank_acc_name = commission_transfer_from_bank_acc_name,
                commission_transfer_from_bank_acc_number = commission_transfer_from_bank_acc_number,
                commission_bank_transfer_account_number = commission_bank_transfer_account_number,
                commission_bank_transfer_name = commission_bank_transfer_name
            )
            print("inserted data")
            logger.info("PremBDX data inserted successfully")

            # update status of the file in PremBDXFiles
            prem_bdx_file_obj.is_prembdx_generated = True
            prem_bdx_file_obj.save()
        except Exception as e:
            print("Error generated: ",str(e))
            logger.info(f"Error generated: {str(e)}")
            if prem_bdx_file_obj.error_message:
                prem_bdx_file_obj.error_message += ", Error while saving BDX data"
            else:
                prem_bdx_file_obj.error_message = "Error while saving BDX data"

            prem_bdx_file_obj.save()
            raise Exception("Error while saving BDX data")

def db_connection():
    # Define the PostgreSQL connection parameters
    postgres_params = {
        'database': config('DATABASE_NAME'),
        'user': config('DATABASE_USER'),
        'password': config('DATABASE_PASSWORD'),
        'host': config('DATABASE_HOST'),
        'port': '5432'
    }

    # Connect to the PostgreSQL database
    connection = psycopg2.connect(**postgres_params)
    cursor = connection.cursor()
    return connection, cursor

def check_entry_all(query):
    connection, cursor = db_connection()
    cursor.execute(query)
    try:
        data = cursor.fetchall()
    except:
        data = None
    cursor.close()
    connection.close()
    return data

def check_entry_one(query):
    connection, cursor = db_connection()
    cursor.execute(query)
    try:
        data = cursor.fetchone()
    except:
        data = None
    cursor.close()
    connection.close()
    return data

def getmonth(filename):
    lfilename = filename.lower()
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

def convert_date(date_str):
    for fmt in ('%Y-%m-%d', '%d-%m-%Y %H:%M'):
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    raise ValueError("no valid date format found")

def save_exception_data(prem_bdx_file_obj):
    # -- Concatenate policy numbers and file names, store unique values in an array
    e1sql = "SELECT concat(certificateref, '-', filename), array_agg(id) FROM payment_premiumbdx where filename = '" + prem_bdx_file_obj.filename + "' and archived = False group by concat(certificateref, '-', filename);"

    t1s = check_entry_all(e1sql)

    # # Split each string in the array
    # premreport = []

    # for t1 in t1s:
    #     output = t1[0].split('-')
    #     policy_number = output[0]
    #     file_name = output[1]
    #     sheet_name = output[2]
    #     premreport.append((policy_number, file_name, sheet_name))

    for premrec in t1s:
        output = premrec[0].split('-')
        prem_bdx_ids = premrec[1]
        error = None
        process_messages = ""
        try:
            # print("certificate no.:", type(premrec))
            try:
                certno = output[0]
            except Exception as e:
                certno = None
                error = error + "Certificate# Not Found"

            filename = prem_bdx_file_obj.filename
            prembdx1 = PremiumBDX.objects.filter(certificateref=certno, filename=filename, archived=False).values('id', 'yearofaccount', 'settlementcurrency', 'umr', 'insure').last()
        except Exception as e:
            print("skipping the record1:", e)

        monthf = prem_bdx_file_obj.month
        yearf = prem_bdx_file_obj.year
        yr_month = monthf + "-" + yearf

        try:
            # e1sql = f"""SELECT sum(gppsettlement), sum(brokerageamountsc), sum(totaltaxesandleviessc), sum(finalnetpremiumsc), sum(percentforlloyds), sum(commissionamount) FROM prem_premiumbdx where certificateref = '{certno}' and filename = '{filename}';"""
            # cursor.execute(e1sql)
            # pbdxsumvalues = check_entry_one(e1sql)
            queryset = PremiumBDX.objects.filter(certificateref=certno, filename=filename, archived=False)
            pbdxsumvalues = queryset.aggregate(
                total_gross_paid_this_time = Sum('grosspremiumpaidthistime'),
                total_gppsettlement=Sum('gppsettlement'),
                total_brokerageamountsc=Sum('brokerageamountsc'),
                total_taxesandlevies=Sum('totaltaxesandlevies'),
                total_finalnetpremiumsc=Sum('finalnetpremiumsc'),
                total_percentforlloyds=Sum('percentforlloyds'),
                total_commissionamount=Sum('commissionamount')
            )
        except Exception as e:
            print("skipped record2:", e)

        try:
            # e1sql = f"""SELECT allocationstatus FROM prem_cashtracker where policy = '{certno}';"""
            e1sql = f"""SELECT "allocation status" FROM financial_data_bankview01 WHERE "Policy" = '{certno}';"""
            # cursor.execute(e1sql)
            allocationstatus = check_entry_one(e1sql)[0]
        except Exception as e:
            allocationstatus = None
            print("skipped record3:", e)

        # changed to allocated amount - 21/05/2024
        try:
            # e1sql = f"""SELECT sum(allocatedamount), SUM(CAST(bankcharges AS FLOAT)) FROM prem_cashtracker where policy = '{certno}';"""
            e1sql = f"""SELECT sum("Allocated Amount"), SUM(CAST("Bank Charge (USD)" AS FLOAT)) FROM financial_data_bankview01 where "Policy" = '{certno}';"""
            # cursor.execute(e1sql)
            ctsumvalues = check_entry_one(e1sql)
            # print(f"ctsumvalues: {ctsumvalues}")
        except Exception as e:
            print("skipped record4:", e)

        try:
            # e1sql = f"""SELECT max(gxballocationdate) FROM prem_cashtracker where policy = '{certno}';"""
            e1sql = f"""SELECT max("GXB Allocation Date") FROM financial_data_bankview01 where "Policy" = '{certno}';"""
            # cursor.execute(e1sql)
            allocationdate = check_entry_one(e1sql)[0]
        except Exception as e:
            print("skipped record5:", e)

        # try:

        #     e1sql = f"""SELECT sum(netpremiumtolondon) FROM prem_treasurypayment where certificateref = '{certno}';"""
        #     # cursor.execute(e1sql)
        #     netpremiumtolondon = check_entry_one(e1sql)
        #     # print(f"netpremiumtolondon: {netpremiumtolondon}")

        # except Exception as e:
        #     print("skipped record6:", e)

        # try:
        #     e1sql = f"""SELECT bankreference FROM prem_treasurypayment where certificateref = '{certno}';"""
        #     # cursor.execute(e1sql)
        #     aabankreference = check_entry_one(e1sql)
        #     # print(f"bankref: {aabankreference}")
        # except Exception as e:
        #     print("skipped record7:", e)

        aabankreference = PaymentTreasuryPYMT.objects.filter(certificate_ref=certno, file_name=filename).values('bank_reference')

        # try:
        #     e1sql = f"""SELECT paymentto FROM prem_treasurypayment where certificateref = '{certno}';"""
        #     # cursor.execute(e1sql)
        #     aabankreferences = check_entry_all(e1sql)
        #     # print(f"bankref: {aabankreference}")
        # except Exception as e:
        #     print("skipped record7a:", e)

        # aabankreferences = PaymentTreasuryPYMT.objects.filter(certificate_ref=certno, file_name=filename).values('payment_to')

        # tfilename = None
        # tbdxnamemonthandyear = None
        # tbankreference = None
        # tpaymentdate = None

        # if aabankreferences:
        #     # print("1 {aabankreferences}")
        #     for aabankreference in aabankreferences:
        #         # print(f"2 {aabankreference}")
        #         for aabankt in aabankreference:
        #             # print(f"3 {aabankt}")
        #             if 'Transverse' in aabankt or 'Acrisure' in aabankt or 'BMS' in aabankt or 'Inverre' in aabankt:
        #                 try:
        #                     e1sql = f"""SELECT filename, bdxnamemonthandyear, bankreference, paymentdate FROM prem_treasurypayment where certificateref = '{certno}';"""
        #                     # cursor.execute(e1sql)
        #                     aabankreferences1 = check_entry_one(e1sql)
        #                     # print(f"bankref: {aabankreference}")
        #                 except Exception as e:
        #                     print("skipped record7b:", e)

        #                 if aabankreferences1:
        #                     # print (f"treasury details: {aabankreferences1}")
        #                     tfilename = aabankreferences1[0]
        #                     tbdxnamemonthandyear = aabankreferences1[1]
        #                     tbankreference = aabankreferences1[2]
        #                     tpaymentdate = aabankreferences1[3]
        #                 break

        wfnpsc = []

        umr = None
        category = ''
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

        # try:
        #     e1sql = f"""SELECT sum(finalnetpremiumsc) FROM prem_premiumbdx where certificateref = '{certno}' and filename = '{filename}';"""
        #     # print(e1sql)
        #     cursor.execute(e1sql)
        # except Exception as e:
        #     continue
        # print("skipped record8:", e)

        ct_bank_charges = None
        try:
            # if 1==1:
            # Assign values for append

            certificate_ref = certno  # 1

            # print("umr: ", umr)

            ct_status = None
            if allocationstatus and isinstance(allocationstatus, np.ndarray):
                ct_status = allocationstatus[0]
            else:
                ct_status =  allocationstatus if allocationstatus else None
                # ct_status = "Allocated"
                # allocation_date = None    
            # print("print 1: ", certno, allocationstatus, ct_status, allocationdate)

            bdx_gross_premium = pbdxsumvalues['total_gross_paid_this_time']
            bdx_brokerage = pbdxsumvalues['total_brokerageamountsc']
            tax = pbdxsumvalues['total_taxesandlevies']  # 10

            brokerageamount = float(bdx_gross_premium or 0.0) + float(bdx_brokerage or 0.0) + float(tax or 0.0)

            llyods_market = None
            recevable_amount = None
            net_premium = pbdxsumvalues['total_finalnetpremiumsc']
            llyods_percentage = pbdxsumvalues['total_percentforlloyds']
            commissionamt = pbdxsumvalues['total_commissionamount']
            ct_allocation_amount = ctsumvalues[0]
            ct_bank_charges = ctsumvalues[1]
            # variance_with_ct = float(ctsumvalues[0] or 0.0) - float(ctsumvalues[1] or 0.0) - float(
            #     brokerageamount or 0.0)
            variance_with_ct = float(ct_allocation_amount or 0.0) - float(brokerageamount or 0.0)
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
                    rebate = 0
                elif 'Acrisure' in scmagreementvalues[0]:
                    if 'Mosaic' in scmagreementvalues[1]:
                        rebate = 0
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

        # try:
        #     if '1609' in filename:
        #         category = 'Cash'
        #         partner = None
        #     elif 'BMS' in scmagreementvalues[0] or 'Inver re' in scmagreementvalues[0] or 'Transverse' in scmagreementvalues[0] or 'AON' in scmagreementvalues[0]:
        #         category = 'Cash'
        #     elif 'Acrisure' in scmagreementvalues[0] and 'ARN' in umr:
        #         category = 'Cash'
        #     elif 'Acrisure' in scmagreementvalues[0] and 'LNR' in umr and 'Mosaic' in scmagreementvalues[1]:
        #         category = 'Non Cash'
        #     elif 'Acrisure' in scmagreementvalues[0] and '24LNR' in umr and 'Mosaic' in scmagreementvalues[1]:
        #         category = 'Non Cash'
        # except:
        #     category = None

        bdx_object = PremiumBDX.objects.filter(certificateref=certificate_ref, filename=filename, archived=False).last()
        category = bdx_object.category

        if category == 'Cash':
            cash_query = f"""SELECT sum(finalnetpremiumsc) FROM payment_premiumbdx where certificateref = '{certno}' and filename = '{filename}' and category = 'Cash';"""
            wfnpsc = check_entry_one(cash_query)
            cash_bdx_amt = wfnpsc[0]
        else:
            cash_bdx_amt = 0.0
        
        noncash_bdx_amt = 0.0
        if category == 'Non Cash':
            try:
                noncash_query = f"""SELECT sum(finalnetpremiumsc) FROM payment_premiumbdx where certificateref = '{certno}' and filename = '{filename}' and category = 'Non Cash';"""
                xfnpsc = check_entry_one(noncash_query)
                noncash_bdx_amt = xfnpsc[0]
            except:
                noncash_bdx_amt = 0.0

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
                            varianceallowed = ct_allocation_amount * Decimal(psv[2])
                            # print("Range 0: ", psv[2], varianceallowed, variance_with_ct)
                            if round(varianceallowed, 2) == round(variance_with_ct, 2):
                                ct_recontobdx_comments = "No Variance"
                                process_messages = process_messages + str(psv[0]) + str(psv[1]) + str(psv[2])
                                vfound = 1

                        if range_check == 1:
                            for value in np.arange(0.1, 1.0, 0.1):
                                varianceallowed = ct_allocation_amount * Decimal(value)
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

            netpremiumtolondon = PaymentTreasuryPYMT.objects.filter(certificate_ref=certno, file_name=filename).last()
            treasury_policy_level_payment_verification = netpremiumtolondon.net_premium_to_london if netpremiumtolondon else 0
 
            tplpv = treasury_policy_level_payment_verification

            if tplpv == None:
                tplpv = 0

            if treasury_policy_level_payment_verification == net_premium:
                amount_match1 = True
            else:
                amount_match1 = False

            # unpaid_surplus = ct_allocation_amount - tplpv
            # surplus_remaining = unpaid_surplus - brokerageamount
            # sample_test = ct_allocation_amount * 0.5333333

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
                version = 1
                if PaymentException.objects.filter(certificate_ref=certificate_ref, bdx_file_name=filename).exists():
                    old_exceptional_obj = PaymentException.objects.filter(certificate_ref=certificate_ref, bdx_file_name=filename).last()
                    version = old_exceptional_obj.version + 1

                exceptional_obj = PaymentException.objects.create(
                    certificate_ref=certificate_ref,
                    bdx_file_name=filename, 
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
                    version=version
                )
                print("inserted record")

                # Update exception report is generated status
                prem_bdx_file_obj.is_exception_generated = True
                prem_bdx_file_obj.save()

            except Exception as e:
                exceptional_obj = None
                if prem_bdx_file_obj.error_message:
                    prem_bdx_file_obj.error_message += ", Error creating Exception record"
                else:
                    prem_bdx_file_obj.error_message = "Error creating Exception record"
                prem_bdx_file_obj.save()
                print("Error creating Exception record:", e)

            try:
                if exceptional_obj:
                    # datasheet_obj = save_datasheet(bdx_object.id, category)
                    if bdx_object:
                        final_bank_account = bdx_object.final_bank_account
                        final_bank_name = bdx_object.final_bank_name
                        to_bank_account_name = bdx_object.receiving_bank_account_name
                        to_bank_account = bdx_object.receiving_bank_account
                        sum_of_rebate = bdx_object.rebate
                        payment_id = bdx_object.payment_id
                        rebate = bdx_object.rebate
                        placing_broker = bdx_object.placingbroker or None
                        scm_non_scm = prem_bdx_file_obj.scm_status or None
                        category = bdx_object.category or None
                        partner_name = bdx_object.insure or None
                        overall_status = exceptional_obj.overall_status or None
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
                    if PayoutSummary.objects.filter(final_bank_account=to_bank_account, settlement_currency=exceptional_obj.settlement_currency, to_bank_account=bdx_object.bank_account_number).exists():
                        payout_summary_obj = PayoutSummary.objects.filter(final_bank_account=to_bank_account, settlement_currency=exceptional_obj.settlement_currency, to_bank_account=bdx_object.bank_account_number).last()
                        if bdx_object.category:
                            if payout_summary_obj.payment_type == "Cash":
                                payout_summary_obj.sum_of_final_net_premium_settlement_currency += bdx_object.finalnetpremiumsc
                                payout_summary_obj.sum_of_rebate += rebate
                                payout_summary_obj.sum_of_net_payment = float(payout_summary_obj.sum_of_final_net_premium_settlement_currency) - float(payout_summary_obj.sum_of_rebate) if payout_summary_obj.sum_of_final_net_premium_settlement_currency and payout_summary_obj.sum_of_rebate else float(payout_summary_obj.sum_of_final_net_premium_settlement_currency) if payout_summary_obj.sum_of_final_net_premium_settlement_currency else float(payout_summary_obj.sum_of_rebate) if payout_summary_obj.sum_of_rebate else 0
                            elif payout_summary_obj.payment_type == "Non Cash":
                                payout_summary_obj.sum_of_net_payment += sum_of_final_net_premium_settlement_currency
                            elif payout_summary_obj.payment_type == "Rebate":
                                payout_summary_obj.sum_of_rebate += rebate
                            elif payout_summary_obj.payment_type == "Commission":
                                payout_summary_obj.sum_of_net_payment += commission_amount
                        placing_broker = placing_broker
                        scm_non_scm = scm_non_scm
                        category = category
                        partner_name = partner_name
                        overall_status = overall_status
                        payout_summary_obj.save()
                        print("PayoutSummary updated")
                    else:
                        if bdx_object.category:
                            # calculate payout summary for partner
                            if bdx_object.category == "Cash":
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
                                    sum_of_net_payment = float(sum_of_final_net_premium_settlement_currency) - float(sum_of_rebate) if sum_of_final_net_premium_settlement_currency and sum_of_rebate else float(sum_of_final_net_premium_settlement_currency) if sum_of_final_net_premium_settlement_currency else float(sum_of_rebate) if sum_of_rebate else 0,
                                    payment_id = payment_id,
                                    payment_type = "Syndicate",
                                    placing_broker = placing_broker,
                                    scm_non_scm = scm_non_scm,
                                    category = category,
                                    partner_name = partner_name,
                                    overall_status = overall_status,
                                    bdx_ids = prem_bdx_ids
                                )
                            # calculate payout summary for syndicate
                            elif bdx_object.category == "Non Cash":
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
                                    payment_type = "Partner",
                                    placing_broker = placing_broker,
                                    scm_non_scm = scm_non_scm,
                                    category = category,
                                    partner_name = partner_name,
                                    overall_status = overall_status,
                                    bdx_ids = prem_bdx_ids
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
                            payment_type = "Rebate",
                            placing_broker = placing_broker,
                            scm_non_scm = scm_non_scm,
                            category = category,
                            partner_name = partner_name,
                            overall_status = overall_status,
                            bdx_ids = prem_bdx_ids
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
                            payment_type = "Commission",
                            placing_broker = placing_broker,
                            scm_non_scm = scm_non_scm,
                            category = category,
                            partner_name = partner_name,
                            overall_status = overall_status,
                            bdx_ids = prem_bdx_ids
                        )
                        print("PayoutSummary created")
                else:
                    print("Exception record not exists")
            except Exception as e:
                if prem_bdx_file_obj.error_message:
                    prem_bdx_file_obj.error_message += ", Error creating Payout Summary"
                else:
                    prem_bdx_file_obj.error_message = "Error creating Payout Summary"
                prem_bdx_file_obj.save()
                print("Error creating Payout Summary:", e)

        except Exception as e:
            print("skipped record10:", e)
            if prem_bdx_file_obj.error_message:
                prem_bdx_file_obj.error_message += ", Error creating Exception record"
            else:
                prem_bdx_file_obj.error_message = "Error creating Exception record"
            prem_bdx_file_obj.save()

# def bank_workflow(bdx_file_name, sheet_tab, comments_wf):
#     try:
#         auth_header = request.META.get('HTTP_AUTHORIZATION')
#         if auth_header and auth_header.startswith('Bearer '):
#             token = auth_header.split(' ')[1]

#         domain_url = config('DOMAIN_URL')
#         url = '{}/api/bankmanagement/workflow_bank_transactions/'.format(domain_url)
#         data = {
#             "file_name": bdx_file_name,
#             "bank_txn_id": sheet_tab,
#             "analyst_id": request.data['analyst_id'],
#             "workflow_name": "WF_PAYMENT_NOVARIANCE",
#             "comments": comments_wf,
#             "initiated_user_id": request.data['analyst_id']
#         }
#         headers = {'Authorization': f'Bearer {token}'}
#         resp = requests.post(url, data=data, headers=headers)
#         print("Workflow sucess")
#     except Exception as e:
#         print("Error creating record:", e)
    
#     if resp.status_code == 200:
#         return Response({"Message": "Exception report generated and workflow initiated"}, status=status.HTTP_201_CREATED)
