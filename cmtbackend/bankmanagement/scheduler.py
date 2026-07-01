from apscheduler.schedulers.background import BackgroundScheduler
from .fileParser import process_new_files, upload_bank_files
from .agingbucket import update_aging_bucket, update_aging_bucket_in_bank_txn

def run():
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_new_files, "interval", seconds=60)
    scheduler.add_job(upload_bank_files, "interval", seconds=60)
    scheduler.add_job(update_aging_bucket, "cron", hour=1, minute=00, timezone='America/New_York')
    scheduler.add_job(update_aging_bucket_in_bank_txn, "cron", hour=1, minute=00, timezone='America/New_York')
    scheduler.start()
