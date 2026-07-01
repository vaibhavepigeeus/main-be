from documents.models import BrokerInformation
from users.models import Users
from django.core.management.base import BaseCommand
from documents.utils.encryption_util import encrypt_text, is_decrypted


class Command(BaseCommand):
    help = 'Encrypts the email address of all brokers'

    def handle(self, *args, **kwargs):
        print("User email encryption started...")
        for user in Users.objects.all():
            print("user id", user.pk, user.email, user.get_decrypted_email())
            if is_decrypted(user.email) and len(user.email) > 3:
                user.email = encrypt_text(user.email)
                user.save()
                print(user.get_decrypted_email())
        self.stdout.write(self.style.SUCCESS('Successfully encrypted email addresses of all users'))

        print("Broker email encryption started...")
        for broker in BrokerInformation.objects.all():
            print("broker id", broker.pk, broker.get_decrypted_email())
            if is_decrypted(broker.email) and len(broker.email) > 3:
                broker.email = encrypt_text(broker.email)
                broker.save()
                print(broker.get_decrypted_email())
        self.stdout.write(self.style.SUCCESS('Successfully encrypted email addresses of all brokers'))
