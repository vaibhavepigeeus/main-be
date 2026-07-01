from django.contrib import admin

# Register your models here.
from .models import Users, ResetTokens, UserPermissions

admin.site.register(Users)
admin.site.register(UserPermissions)
admin.site.register(ResetTokens)
