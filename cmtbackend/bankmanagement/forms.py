from django import forms


class CashTrackerImportForm(forms.Form):
    cash_tracker_excel_file = forms.FileField()


class UploadFileForm(forms.Form):
    file = forms.FileField()
