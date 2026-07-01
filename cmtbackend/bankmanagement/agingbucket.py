# Entry point for scheduler
import csv
import datetime
import logging

from django.conf import settings
from django.db.models import Count, Q
from decouple import config
from users.utils import send_email

from .models import BankTransaction, CashTrackerReport

logger = logging.getLogger(__name__)


def update_aging_bucket():
    """
    Function to update the aging bucket for Cash Traker Report
    """
    are_records_updated = False
    mail_body = ""

    try:
        logger.info("Update Aging Bucket Cron Triggered")
        all_ct_objs = CashTrackerReport.objects.filter(
            (Q(Aging_Bucket__isnull=True) | Q(Aging_Bucket=""))
            | ~Q(cash_allocation__allocation_status="Allocated")
        )

        logger.info("Aging Bucket Updation for CTR Started")
        logger.info("Records to update: %s", str(len(all_ct_objs)))

        # Check if there are records to update
        if len(all_ct_objs) > 0:
            are_records_updated = True

            # Updating Aging Bucket for CTR records
            success_records_counter = 0
            failed_records_counter = 0
            for obj in all_ct_objs:
                try:
                    if not (obj and obj.bank_txn and obj.bank_txn.Payment_Receive_Date):
                        continue

                    diff_delta = (
                        datetime.datetime.now(obj.bank_txn.Payment_Receive_Date.tzinfo)
                        - obj.bank_txn.Payment_Receive_Date
                    )
                    diff_days = diff_delta.days

                    logger.info("Bank Txn Id: %s", str(obj.bank_txn.Bank_Transaction_Id))
                    logger.info("Payment Date: %s", str(obj.bank_txn.Payment_Receive_Date))
                    logger.info("No. of days diff: %s", str(diff_days))

                    if 365 >= diff_days >= 181:
                        obj.Aging_Bucket = "181-365"

                    elif 180 >= diff_days >= 121:
                        obj.Aging_Bucket = "121-180"

                    elif 120 >= diff_days >= 91:
                        obj.Aging_Bucket = "91-120"

                    elif 90 >= diff_days >= 61:
                        obj.Aging_Bucket = "61-90"

                    elif 60 >= diff_days >= 31:
                        obj.Aging_Bucket = "31-60"

                    elif 30 >= diff_days >= 16:
                        obj.Aging_Bucket = "16-30"

                    elif 15 >= diff_days >= 6:
                        obj.Aging_Bucket = "6-15"

                    elif 5 >= diff_days >= 0:
                        obj.Aging_Bucket = "0 - 5"

                    else:
                        obj.Aging_Bucket = "Over 365"

                    obj.save()
                    success_records_counter += 1

                except Exception as e:
                    logger.info("Error processing object %s: %s", str(obj.id), str(e))
                    failed_records_counter += 1
                    continue

            logger.info("Aging Bucket Updation for CTR Completed")

            if success_records_counter > 0:
                mail_body += f"Aging Bucket Updated Successfully, Records: {success_records_counter}\n"

            if failed_records_counter > 0:
                mail_body += (
                    f"Aging Bucket Updation Failed, Records: {failed_records_counter}"
                )

    except Exception as e:
        logger.info("Error in Updating Aging Bucket for Cash Tracker Report %s", str(e))
        mail_body = "Error in Updating Aging Bucket for Cash Tracker Report: " + str(e)

    if are_records_updated:
        # Getting env
        ENV = config("ENVIRONMENT")
        mail_body += f"\n\n ENV: {ENV}"

        logger.info("Sending mail after trigger...")
        send_email(
            sender_email=settings.EMAIL_HOST_USER,
            recipient_email=settings.EMAIL_NOTIFICATION_RECIPIENTS,
            subject="CTR Aging Bucket Update Status",
            body=mail_body,
        )

        logger.info("Mail sent successfully")


def update_aging_bucket_in_bank_txn():
    """
    Function to update the aging bucket for Bank Transactions
    """
    all_bt_objs = (
        BankTransaction.objects.annotate(allocation_count=Count("cashallocation"))
        .filter(archived=False, allocation_count=0)
        .order_by("allocation_count")
    )

    # Open a CSV file to write the aging bucket data
    with open("bt_aging_bucket.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "payment_receive_date", "diff_days", "aging_bucket"])
        for obj in all_bt_objs:
            try:
                payment_date = obj.Payment_Receive_Date
                diff_days = (
                    datetime.datetime.now(payment_date.tzinfo) - payment_date
                ).days
            except Exception as e:
                logger.info(f"Error processing date for object {obj.id}: {str(e)}")
                continue

            if 365 >= diff_days >= 181:
                obj.Aging_Bucket = "181-365"
            elif 180 >= diff_days >= 121:
                obj.Aging_Bucket = "121-180"
            elif 120 >= diff_days >= 91:
                obj.Aging_Bucket = "91-120"
            elif 90 >= diff_days >= 61:
                obj.Aging_Bucket = "61-90"
            elif 60 >= diff_days >= 31:
                obj.Aging_Bucket = "31-60"
            elif 30 >= diff_days >= 16:
                obj.Aging_Bucket = "16-30"
            elif 15 >= diff_days >= 6:
                obj.Aging_Bucket = "6-15"
            elif 5 >= diff_days >= 0:
                obj.Aging_Bucket = "0 - 5"
            else:
                obj.Aging_Bucket = "Over 365"

            # Write data to CSV
            writer.writerow(
                [obj.id, obj.Payment_Receive_Date, diff_days, obj.Aging_Bucket]
            )
            obj.save()
