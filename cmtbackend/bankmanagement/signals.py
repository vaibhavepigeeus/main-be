from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CashAllocation, FollowUp

@receiver(post_save, sender=CashAllocation)
def create_ca(sender, instance, created, **kwargs):
    if not created and instance.archived:
        objects = FollowUp.objects.filter(cash_allocation=instance.id)
        for i in objects:
            i.archived = True
            i.save()