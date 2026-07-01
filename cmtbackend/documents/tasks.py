from celery import shared_task
from .models import AgedDeptFileRecord
from .policy_calculation import PolicyDatabaseUpdater

@shared_task
def update_policy_calculations(file_name, file_month, file_year, record_id, AONLedger, RBSDetails, SiriusPoints, MOPMapping, is_rerun=False):
    updater = PolicyDatabaseUpdater()
    # file_month and file_year are not used in the function, but kept in the task signature for backward compatibility
    return updater.update_all_policy_calculations(
        file_name=file_name,
        record_id=record_id,
        AONLedgerFile=AONLedger,
        RBSDetailsFile=RBSDetails,
        SiriusPointsFile=SiriusPoints,
        MOPMappingFile=MOPMapping,
        is_rerun=is_rerun
    )