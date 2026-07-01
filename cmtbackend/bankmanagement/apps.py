from django.apps import AppConfig


class BankmanagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bankmanagement'
    def ready(self):
        import bankmanagement.signals
        from .scheduler import run
        run()