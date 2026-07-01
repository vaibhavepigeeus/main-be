from ..models import CashAllocation, CashAllocationLockedUnlockedHistory
from django.db import transaction
from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.apps import apps


def lock_or_unlock_cash_allocation(locked, start_date, end_date, request_user):
    """
    Locks or unlocks CashAllocation objects based on accounting_monthyear and allocation_status,
    and creates a corresponding history entry in an atomic transaction if applicable.

    Args:
        locked (bool): Whether to lock (True) or unlock (False) the CashAllocation.
        start_date (date): The accounting month/year to filter records with start date.
        end_date (date): The accounting month/year to filter records with start date.
        request_user (User): The authenticated user performing the operation.

    Returns:
        int: The number of CashAllocation objects updated (0 or 1).
    """

    with transaction.atomic():
        num_updated = CashAllocation.objects.filter(
            # archived=False,
            Q(allocation_status='Allocated') &
            Q(accounting_monthyear__gte=start_date) &
            Q(accounting_monthyear__lte=end_date) &
            (Q(locked=False) | Q(locked=None)), archived=False
        ).update(
            locked=locked,
            locked_by=request_user,
            locked_datetime=timezone.now()
        )

        # Create history entry only if CashAllocation objects were updated (num_updated > 0)
        if num_updated > 0:
            date_range = f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}"
            update_field_name = 'locked' if locked else 'unlocked'
            CashAllocationLockedUnlockedHistory.objects.create(
                date_range=date_range,
                no_of_record=num_updated,
                locked_unlocked_by=request_user,
                **{update_field_name: True}
            )

    return num_updated


def update_cash_allocation(app_model_name, cash_allocation_id_key, cash_allocation_id, accounting_date):
    """
    Updates the cashallocation for a specific model instance

    Args:
        app_model_name (str): The name of the model to update (e.g., "CashAllocation")
        cash_allocation_id_key (str): The ID of the CashAllocation to update
        cash_allocation_id (int): The ID of the CashAllocation to update
        accounting_date (date): The new accounting_monthyear value
    """
    try:
        # Get the model class using Django's app registry
        app_label, model_name = app_model_name.split(".")
        # Get the model class using Django's app registry
        model = apps.get_model(app_label, model_name)
    except LookupError:
        print(f"Invalid model name provided: {model_name}")
        return

    # Update the model instance
    updated_count = model.objects.filter(**{cash_allocation_id_key: cash_allocation_id}).update(accounting_monthyear=accounting_date)


    # Check if update was successful
    if updated_count > 0:
        print(f"{model_name} updated successfully!")
    else:
        print(f"{model_name} update failed. Object not found.")


# Example usage

