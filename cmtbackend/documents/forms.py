from django import forms

class BrokerInformationImportForm(forms.Form):
    broker_excel_file = forms.FileField()




class CurrencyInformationImportForm(forms.Form):
    currency_excel_file = forms.FileField()


class PolicyInformationImportForm(forms.Form):
    policy_excel_file = forms.FileField()



class ExchangeRateImportForm(forms.Form):
    exchange_excel_file = forms.FileField()