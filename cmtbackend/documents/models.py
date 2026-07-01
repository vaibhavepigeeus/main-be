from django.db import models
import datetime
from django.core.validators import RegexValidator
from .utils.encryption_util import encrypt_text, decrypt_text, is_decrypted

def upload_to(instance, filename):
    return 'documents/media/{filename}'.format(filename=filename)


from django.db import models


class Documents(models.Model):
    document_name = models.CharField(max_length=255)
    document_date = models.DateField()
    upload_date = models.DateTimeField(auto_now_add=True)
    document_file = models.FileField(upload_to='documents/media/', blank=True, null=True)
    document_type = models.CharField(max_length=200)
    document_details = models.CharField(max_length=100, blank=True, null=True)
    archieve_by = models.CharField(max_length=100, null=True)
    archieve_datetime = models.DateTimeField(default=datetime.datetime.now())
    document_url = models.TextField(null=True)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.document_url}"


class BrokerInformation(models.Model):
    broker_name = models.CharField(max_length=100)
    broker = models.CharField(max_length=100)
    branch = models.CharField(max_length=100)
    duplicate_count = models.CharField(max_length=100)
    soa_received_from_broker = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    secondary_email = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=256, blank=True, null=True)
    broker_branch_location = models.TextField(blank=True, null=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            existing_record = BrokerInformation.objects.get(pk=self.pk)
            if is_decrypted(self.email) and self.email != existing_record.email:
                self.email = encrypt_text(self.email)
            if self.phone_number != existing_record.phone_number and is_decrypted(self.phone_number):
                self.phone_number = encrypt_text(self.phone_number)
        else:
            if is_decrypted(self.email):
                self.email = encrypt_text(self.email)
            if is_decrypted(self.phone_number):
                self.phone_number = encrypt_text(self.phone_number)
        super().save(*args, **kwargs)

    def get_decrypted_email(self):
        try:
            if is_decrypted(self.email):
                return self.email
            return decrypt_text(self.email)
        except Exception as e:
            return self.email

    def get_decrypted_phone_number(self):
        try:
            if is_decrypted(self.phone_number):
                return self.phone_number
            return decrypt_text(self.phone_number)
        except Exception as e:
            return self.phone_number

    def __str__(self):
        return self.broker_name


class BankDetails(models.Model):
    region = models.CharField(max_length=100)
    entity_number = models.CharField(max_length=100)
    msd_entity_number = models.CharField(max_length=100)
    entity_name = models.CharField(max_length=200)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=100)
    account_opening_date = models.DateField(blank=True, null=True)
    account_type = models.CharField(max_length=100)
    currency = models.CharField(max_length=100)
    msd_acct_number = models.CharField(max_length=100, null=True)
    msd_acct_name = models.CharField(max_length=200, null=True)
    prime_bank_account = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.account_number


class CurrencyDetails(models.Model):
    currency_code = models.CharField(max_length=100)
    country_and_currency = models.CharField(max_length=100)
    symbol = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.country_and_currency


class AllocationStatus(models.Model):
    allocation_status = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.allocation_status


class PolicyType(models.Model):
    policy_start_letter = models.CharField(max_length=100)
    policy_type = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.country_and_currency


class LOB(models.Model):
    lob_code = models.CharField(max_length=100)
    lob = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.lob


class SCMPartners(models.Model):
    partner_name = models.CharField(max_length=150)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.partner_name


class BindingAgreement(models.Model):
    binding_aggrement_type = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.binding_aggrement_type


class CorrectionType(models.Model):
    correction_type = models.CharField(max_length=100)
    correction_description = models.TextField(blank=True, null=True)
    allocation_status = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(default=datetime.datetime.now().date(), null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)
    archived = models.BooleanField(default=False)

    def __str__(self):
        return self.correction_type

class TransactionCategory(models.Model):
    txn_category = models.CharField(max_length=100)
    category_description = models.TextField(blank=True, null=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.txn_category


class CashTransfer(models.Model):
    cash_transfer_value = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.cash_transfer_value


class Entity(models.Model):
    entity_divisions = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)
    entity_name = models.CharField(max_length=100, null=True)

    def __str__(self):
        return self.entity_divisions


class IssueCatergory(models.Model):
    issue_catergory = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.issue_catergory


class PolicyInformation(models.Model):
    Producing_Entity = models.CharField(max_length=100, null=True)
    Class_of_Business = models.CharField(max_length=100, null=True)
    Year_of_Account = models.CharField(max_length=100, null=True)
    Syndicate_Binder = models.CharField(max_length=100, null=True)
    Policy_Line_Ref = models.CharField(max_length=100, null=True)
    Policy_Status = models.CharField(max_length=100, null=True)
    Inception_Date = models.DateField(default=None, null=True)
    Expired_Date = models.DateField(default=None, null=True)
    UMR_Number = models.CharField(max_length=100, null=True)
    Three_Party_Capacity_Deployed = models.CharField(max_length=100, null=True)
    SCM_Partner = models.CharField(max_length=100, null=True)
    Signed_Line_Pct = models.DecimalField(decimal_places=3, max_digits=12, default=0.00, null=True)
    Broker_Order_Pct = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Signed_Order_Pct = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Broker_Commision_Pct = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Coverholder_Commision_Pct = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    MOP = models.CharField(max_length=100, null=True)
    Broker = models.CharField(max_length=100, null=True)
    Insured = models.CharField(max_length=100, null=True)
    Summary_Currency = models.CharField(max_length=100, null=True)
    Summary_ROE = models.DecimalField(decimal_places=6, max_digits=12, default=0.00, null=True)
    Settlement_Ccy = models.CharField(max_length=200, null=True)
    Settlement_ROE = models.DecimalField(decimal_places=6, max_digits=12, default=0.00, null=True)
    Gross_Written_Premium_100_in_Sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Net_Written_Premium_100_in_Sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    True_Net_Written_Premium_100_in_Sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Original_Ccy = models.CharField(max_length=100, null=True)
    Original_ROE = models.DecimalField(decimal_places=6, max_digits=12, default=0.00, null=True)
    Gross_Written_Premium_100_in_Orig = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Gross_Written_Premium_Agency_Share_in_Orig = models.DecimalField(decimal_places=2, max_digits=12, default=0.00,
                                                                     null=True)
    Gross_Written_Premium_Syndicate_Share_in_Orig = models.DecimalField(decimal_places=2, max_digits=12, default=0.00,
                                                                        null=True)
    Gross_Written_Premium_Non_Syndicate_Share_in_Orig = models.DecimalField(decimal_places=2, max_digits=12,
                                                                            default=0.00, null=True)
    Net_Written_Premium_100_in_Orig = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Net_Written_Premium_Agency_Share_in_Orig = models.DecimalField(decimal_places=2, max_digits=12, default=0.00,
                                                                   null=True)
    Net_Written_Premium_Syndicate_Share_in_Orig = models.DecimalField(decimal_places=2, max_digits=12, default=0.00,
                                                                      null=True)
    Net_Written_Premium_Non_Syndicate_Share_in_Orig = models.DecimalField(decimal_places=2, max_digits=12, default=0.00,
                                                                          null=True)
    True_Net_Written_Premium_100_in_Orig = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    True_Net_Written_Premium_Syndicate_Share_in_Orig = models.DecimalField(decimal_places=2, max_digits=12,
                                                                           default=0.00, null=True)
    True_Net_Written_Premium_Agency_Share_in_Orig = models.DecimalField(decimal_places=2, max_digits=12, default=0.00,
                                                                        null=True)
    True_Net_Written_Premium_Non_Syndicate_Share_in_Orig = models.DecimalField(decimal_places=2, max_digits=12,
                                                                               default=0.00, null=True)
    Gross_Written_Premium_100_in_USD = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Net_Written_Premium_100_in_USD = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    True_Net_Written_Premium_100_in_USD = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    PremiumBasis = models.CharField(max_length=100, null=True)
    Instalment_Nbr = models.CharField(max_length=100, null=True)
    Installment_Category = models.CharField(max_length=100, null=True)
    Installment_Due_date = models.CharField(max_length=100, null=True)
    Installment_Ccy_in_Orig = models.CharField(max_length=100, null=True)
    Installment_Agency_Amount_in_Orig = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Installment_Agency_Amount_in_Sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Installment_Agency_Amount_in_USD = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Installment_Amount_Syndicate_Share_in_Orig = models.DecimalField(decimal_places=2, max_digits=12, default=0.00,
                                                                     null=True)
    Installment_Amount_Syndicate_Share_in_Sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00,
                                                                     null=True)
    Installment_Amount_Syndicate_Share_in_USD = models.DecimalField(decimal_places=2, max_digits=12, default=0.00,
                                                                    null=True)
    Paid_Amount_in_USD = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Diff_in_USD = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    Overdue_Days = models.IntegerField(default=0, null=True)
    Overdue_Category = models.CharField(max_length=100, null=True)
    SCM_Insurer_partner_name = models.CharField(max_length=100, null=True)
    Binding_Agreement = models.CharField(max_length=100, null=True)
    Last_Allocation_Date = models.DateField(default=None, null=True)  # added
    Gross_Written_Premium_Syndicate_Share_in_USD = models.DecimalField(decimal_places=2, max_digits=12,
                                                                       default=0.0, null=True)  # added
    Gross_Written_Premium_Agency_Share_in_USD = models.DecimalField(decimal_places=2, max_digits=12,
                                                                    default=0.0, null=True)  # added
    Master_Broker = models.CharField(max_length=100, null=True)  # added
    Underwriter = models.CharField(max_length=100, null=True)  # added
    Broker_Reference = models.CharField(max_length=100, null=True)  # added
    Transaction_Status = models.CharField(max_length=100, null=True)  # added
    Cancellation_Reason = models.CharField(max_length=100, null=True)  # added
    Date_Cancelled = models.DateField(default=None, null=True)  # added
    Policy_Activity_Status = models.CharField(max_length=100, null=True)  # added
    file_month = models.CharField(max_length=2, validators=[RegexValidator(r'^[0][1-9]|1[0-2]$')], null=True)  # added
    file_year = models.IntegerField(validators=[RegexValidator(r'^\d{4}$')], null=True)  # added
    uploaded_by = models.CharField(max_length=100, null=True)  # added
    uploaded_datetime = models.DateTimeField(auto_now_add=True, null=True)  # added
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    historical = models.BooleanField(default=False, null=True)  # added
    archived = models.BooleanField(default=False, null=True, blank=True)
    market_source = models.CharField(max_length=255, null=True, blank=True)
    i_policy_key = models.IntegerField(null=True, blank=True)
    cancellation_type = models.CharField(max_length=255, null=True, blank=True)
    line_ref_1609_5399 = models.CharField(max_length=255, null=True, blank=True)
    line_ref_2610_5431 = models.CharField(max_length=255, null=True, blank=True)
    #new columns
    Class_of_Business_Remapped = models.CharField(default=None, max_length=100, null=True) #BR-added
    Facility = models.CharField(default=None, max_length=100, null=True) #BS-added
    SP_PER = models.CharField(default=0, max_length=100, null=True, blank=True) #BT-added
    MOP_Mapped = models.CharField(default=None, max_length=100, null=True) #BU-added
    Agency_Commission = models.CharField(default=0, max_length=100, null=True) #BV-added
    Brokerage_Installment_Sett = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #BW-added
    Agency_Commission_USD = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #BX-added
    Sirius_Point_Amount_GWP_USD = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #BY-added
    Archre_Amount_GWP_USD = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #BZ-added
    ArchRe_Amount_Received = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CA-added
    ArchRe_Outstanding = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CB-added
    Commission = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CC
    Gross_Written_Premium_100_USD_Agency_DUA_Earned = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CD-added
    Gross_Written_Premium_100_USD_Syndicate = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CE
    Gross_Written_Premium_100_USD_SCM = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CF
    Net_Written_Premium_100_USD_Agency = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CG
    Net_Written_Premium_100_USD_Syndicate = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CH
    Net_Written_Premium_100_USD_SCM = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CI
    CT_Receivable_Total_Agency_Sett = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CJ-added (for now need to use default)
    CT_Receivable_Total_Syndicate = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CK
    CT_Receivable_Total_SCM = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CL
    CT_Allcoated_Total_Agency = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CM
    CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CN
    CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt_USD = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CO
    Money_To_Collect_Syndicate = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CP
    Money_To_Collect_USD_SCM = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CQ
    Future_Due_45_Days_From_Reporting_Period = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CR
    CT_Rcvd_vs_Instalment_Syndicate = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CS
    CT_Rcvd_vs_Instalment_SCM = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CT
    USM	= models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CU
    CT_Unallocated	= models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CV
    CT_Unallocated_USD	= models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CW
    CT_Unallocated_USD_Syndicate	= models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CX
    CT_Unallocated_USD_SCM	= models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CY
    Brokerage_USD	= models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #CZ
    Agency_Commission_USD2	= models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #DA
    Aged_Bucket_By_Period_Receivable = models.CharField(max_length=100, default=None, null=True, blank=True) #DB
    AON_Collection_Status = models.CharField(max_length=100, default=None, null=True, blank=True) #DC
    Aged_Bucket_By_Period_All = models.CharField(max_length=100, default=None, null=True, blank=True) #DD
    Policy_Version = models.IntegerField(null=True, blank=True) #DE-added
    Last_Allocation_Date_CT = models.DateField(default=None, null=True) #DF	
    Progress_Status = models.CharField(max_length=100, default=None, null=True, blank=True) #DG
    CC = models.CharField(max_length=100, default=None, null=True, blank=True) #DH
    Status_update_date = models.DateField(default=None, null=True) #DI
    Comments = models.TextField(default=None, null=True, blank=True) #DJ
    CT_Receivable_Total_Agency_USD_Gross = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True) #DK
    ARCH_Status = models.CharField(max_length=100, default=None, null=True, blank=True) #DL 	 
    Sum_of_Inst_NWP_USD_values_25 = models.CharField(max_length=100, default=None, null=True, blank=True) #DM 	 
    No_Funds_Receive = models.CharField(max_length=100, default=None, null=True, blank=True) #DN 	 
    SP_Percent_0_Not_on_SP_File = models.CharField(max_length=100, default=None, null=True, blank=True) #DO 	 
    Payment_Received = models.CharField(max_length=100, default=None, null=True, blank=True) #DP 	 
    Pending_Client_Payment = models.CharField(max_length=100, default=None, null=True, blank=True) #DQ 	 
    Comments_to_follow_up = models.CharField(max_length=100, default=None, null=True, blank=True) #DR 	 
    Claims = models.CharField(max_length=100, default=None, null=True, blank=True) #DS 	 
    Original_Cur_vs_Settlement = models.CharField(max_length=100, default=None, null=True, blank=True) #DT 	 
    Currency_Test = models.TextField(null=True, default=None, blank=True) #DU
    file_name = models.CharField(max_length=100, default=None, null=True, blank=True) #DV
    exception = models.TextField(null=True, blank=True)

    # Copy fields which are using CA/CTR data
    cp_CT_Receivable_Total_Agency_USD_Gross = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_ArchRe_Amount_Received = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_ArchRe_Outstanding = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_CT_Receivable_Total_Syndicate = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_CT_Receivable_Total_Agency_Sett = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_CT_Receivable_Total_SCM = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_CT_Unallocated = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_CT_Unallocated_USD = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_CT_Unallocated_USD_Syndicate = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_CT_Unallocated_USD_SCM = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_Money_To_Collect_Syndicate = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_Money_To_Collect_USD_SCM = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_CT_Rcvd_VS_Inst_Amt_Agcy_Unalloc_To_Clt_USD = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_CT_Rcvd_vs_Instalment_Syndicate = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_CT_Rcvd_vs_Instalment_SCM = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)
    cp_Aged_Bucket_By_Period_Receivable = models.CharField(max_length=100, default=None, null=True, blank=True)
    cp_CT_Allcoated_Total_Agency = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, null=True)

    def __str__(self):
        return f"{self.SCM_Insurer_partner_name} - {self.id}"


class BankExchangeRate(models.Model):
    month = models.CharField(max_length=100)
    currency_code = models.CharField(max_length=100)
    exchange_rate = models.DecimalField(decimal_places=6, max_digits=12)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.currency_code


class PowerBIReport(models.Model):
    report_name = models.CharField(max_length=100)
    report_url = models.TextField(null=True)
    environment = models.CharField(max_length=100, null=True)
    report_sequence = models.IntegerField()
    active = models.BooleanField(default=False)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.report_name} - {self.report_url}"
    
class Escalation(models.Model):
    organization = models.CharField(max_length=100, null=True, blank=True)
    transaction_type = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=100, null=True, blank=True)
    escalation_level_one = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True, blank=True, related_name='escalation_level_one')
    escalation_level_two = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True, blank=True, related_name='escalation_level_two')
    escalation_level_three = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True, blank=True, related_name='escalation_level_three')
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.organization}"   
      
class SLA(models.Model):
    sla = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True) 

    def __str__(self):
        return f"{self.sla}"
       
class ParticipatingInsurer(models.Model):
    participating_insurer = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)   

    def __str__(self):
        return self.participating_insurer


class PayeeBankAccountDetails(models.Model):
    placing_broker = models.CharField(max_length=100, null=True, blank=True)
    to_acc_name_benificiary_name = models.CharField(max_length=100, null=True, blank=True)
    settlement_ccy = models.CharField(max_length=100, null=True, blank=True)
    bank_acc_no = models.CharField(max_length=100, null=True, blank=True)
    bank_sort_code = models.CharField(max_length=100, null=True, blank=True)
    bank_swift_bic = models.CharField(max_length=100, null=True, blank=True)
    iban_number = models.CharField(max_length=100, null=True, blank=True)
    type = models.CharField(max_length=100, null=True, blank=True)
    type_of_request = models.CharField(max_length=100, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    credit_bank_account = models.CharField(max_length=100, null=True, blank=True)
    credit_bank_account_name = models.CharField(max_length=100, null=True, blank=True)
    credit_bank_account_name_1609 = models.CharField(max_length=100, null=True, blank=True)
    from_account_name_benificiary_name = models.CharField(max_length=100, null=True, blank=True)
              

class SiriusData(models.Model):
    policy_line_reference = models.CharField(max_length=255, null=True, blank=True)
    umr = models.CharField(max_length=255, null=True, blank=True)
    agreement_name = models.CharField(max_length=255, null=True, blank=True)
    xfi_policy_status = models.CharField(max_length=255, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    producing_mosaic_entity = models.CharField(max_length=255, null=True, blank=True)
    inception_date = models.DateField(null=True, blank=True)
    service_company = models.CharField(max_length=255, null=True, blank=True)
    class_of_business = models.CharField(max_length=255, null=True, blank=True)
    industry = models.CharField(max_length=255, null=True, blank=True)
    insured_name = models.CharField(max_length=255, null=True, blank=True)
    insured_domicile = models.CharField(max_length=255, null=True, blank=True)
    insured_state = models.CharField(max_length=255, null=True, blank=True)
    master_broker = models.CharField(max_length=255, null=True, blank=True)
    producing_broker = models.CharField(max_length=255, null=True, blank=True)
    program = models.CharField(max_length=255, null=True, blank=True)
    placing_broker = models.CharField(max_length=255, null=True, blank=True)
    master_partner = models.CharField(max_length=255, null=True, blank=True)
    limit_100_percent = models.FloatField(null=True, blank=True)
    premium_100_percent = models.FloatField(null=True, blank=True)
    excess = models.FloatField(null=True, blank=True)
    deductible = models.FloatField(null=True, blank=True)
    service_company_line_percent = models.FloatField(null=True, blank=True)
    service_company_limit = models.FloatField(null=True, blank=True)
    service_company_premium = models.FloatField(null=True, blank=True)
    revenue_turnover = models.FloatField(null=True, blank=True)
    partner_name = models.CharField(max_length=255, null=True, blank=True)
    brokerage_percent = models.FloatField(null=True, blank=True)
    brokerage = models.FloatField(null=True, blank=True)
    partner_percent = models.FloatField(null=True, blank=True)
    partner_limit = models.FloatField(null=True, blank=True)
    partner_premium = models.FloatField(null=True, blank=True)
    sirius_point_percent = models.FloatField(null=True, blank=True)
    umr_1 = models.CharField(max_length=255, null=True, blank=True)
    arch_no_participant = models.FloatField(null=True, blank=True)
    umr_yoa = models.CharField(max_length=255, null=True, blank=True)
    umr_2 = models.CharField(max_length=255, null=True, blank=True)
    umr_23_24 = models.FloatField(null=True, blank=True)
    policy_line_reference_1 = models.CharField(max_length=255, null=True, blank=True)
    partner_percent_1 = models.FloatField(null=True, blank=True)
    file_name = models.CharField(null=True, blank=True, max_length=255)

    # Additional tracking fields
    uploaded_by = models.CharField(null=True, blank=True, max_length=255)
    uploaded_datetime = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    created_on = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    updated_on = models.DateTimeField(null=True, blank=True, auto_now=True)

class RBSDetails(models.Model):
    class_of_business = models.CharField(max_length=255, null=True, blank=True)
    service_company = models.CharField(max_length=255, null=True, blank=True)
    producing_mosaic_entity = models.CharField(max_length=255, null=True, blank=True)
    inception_year = models.IntegerField(null=True, blank=True)
    agreement_yoa = models.IntegerField(null=True, blank=True)
    inception_date = models.DateField(null=True, blank=True)
    fon_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    accumulates_on_agreement = models.CharField(max_length=255, null=True, blank=True)
    accumulates_on_dec = models.CharField(max_length=255, null=True, blank=True)
    carrier_reference = models.CharField(max_length=255, null=True, blank=True)
    master_policy_number = models.CharField(max_length=255, null=True, blank=True)
    policy_line_reference = models.CharField(max_length=255, null=True, blank=True)
    unique_market_reference = models.CharField(max_length=255, null=True, blank=True)
    asta_umr_agreement = models.CharField(max_length=255, null=True, blank=True)
    is_third_party_capacity_deployed = models.CharField(max_length=255, null=True, blank=True)
    underwriter_name = models.CharField(max_length=255, null=True, blank=True)
    producing_underwriter_name = models.CharField(max_length=255, null=True, blank=True)
    master_broker = models.CharField(max_length=255, null=True, blank=True)
    broker_name = models.CharField(max_length=255, null=True, blank=True)
    broker_key = models.CharField(max_length=255, null=True, blank=True)
    insured = models.CharField(max_length=255, null=True, blank=True)
    obligor = models.CharField(max_length=255, null=True, blank=True)
    reinsured = models.CharField(max_length=255, null=True, blank=True)
    commodity = models.CharField(max_length=255, null=True, blank=True)
    fund_code_as_per_xfi = models.CharField(max_length=255, null=True, blank=True)
    policy_period_days = models.IntegerField(null=True, blank=True)
    tenor_in_month = models.IntegerField(null=True, blank=True)
    method_of_placement = models.CharField(max_length=255, null=True, blank=True)
    mapped_mop = models.CharField(max_length=255, null=True, blank=True)
    territory = models.CharField(max_length=255, null=True, blank=True)
    insured_domicile = models.CharField(max_length=255, null=True, blank=True)
    insured_state = models.CharField(max_length=255, null=True, blank=True)
    reinsured_domicile = models.CharField(max_length=255, null=True, blank=True)
    industry = models.CharField(max_length=255, null=True, blank=True)
    bank_non_bank = models.CharField(max_length=255, null=True, blank=True)
    naic_company_code = models.CharField(max_length=255, null=True, blank=True)
    naic_description = models.CharField(max_length=255, null=True, blank=True)
    slip_lead = models.CharField(max_length=255, null=True, blank=True)
    bureau_lead = models.CharField(max_length=255, null=True, blank=True)
    agency_line_share_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avg_agency_line_share_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mosaic_1609_line_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avg_mosaic_1609_line_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mosaic_1609_order_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    limit_currency = models.CharField(max_length=255, null=True, blank=True)
    limit_original_currency = models.CharField(max_length=255, null=True, blank=True)
    type_of_layer = models.CharField(max_length=255, null=True, blank=True)
    enterprise_value_original = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    enterprise_value_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    excess_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    excess_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    deductible_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    deductible_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    gross_written_premium_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    premium_currency = models.CharField(max_length=255, null=True, blank=True)
    gross_written_premium_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    gross_written_premium_by_yoa_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    minimum_deposit_premium_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    premium_type = models.CharField(max_length=255, null=True, blank=True)
    lloyds_risk_code = models.CharField(max_length=255, null=True, blank=True)
    agency_gelr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mosaic_gelr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    brokerage_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ceding_commission_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    third_party_coverholder_commission_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    original_commission_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mosaic_1609_agency_commission_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mosaic_1609_total_commission_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    third_party_agency_commission_pct = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    third_party_total_commission_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    agency_share_gwp_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_share_gwp_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    business_plan_loss_ratio_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mosaic_1609_share_benchmark_premium_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_share_benchmark_premium_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    achieved_price_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mosaic_1609_exposure_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_share_gwp_gbp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_original_commission_amount_gbp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_agency_commission_amount_gbp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_expected_claims_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_expected_claims_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_expected_claims_gbp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_expected_claims_by_yoa_gbp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    agency_expected_claims_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    agency_expected_claims_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    agency_expected_claims_gbp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    agency_expected_claims_by_yoa_gbp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_exposure_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_share_gwp_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_original_commission_amount_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_agency_commission_amount_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    agency_share_gwp_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    agency_exposure_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    agency_exposure_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    third_party_agency_commission_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_brokerage_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_exposure_by_yoa_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_share_gwp_by_yoa_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_original_commission_amount_by_yoa_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_agency_commission_amount_by_yoa_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    agency_share_gwp_by_yoa_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    agency_exposure_by_yoa_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    third_party_agency_commission_by_yoa_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_brokerage_by_yoa_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_share_gwp_by_yoa_gbp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_original_commission_amount_by_yoa_gbp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_agency_commission_amount_by_yoa_gbp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    booking_completed_date = models.DateField(null=True, blank=True)
    policy_created_by = models.CharField(max_length=255, null=True, blank=True)
    date_written = models.DateField(null=True, blank=True)
    peer_reviewer = models.CharField(max_length=255, null=True, blank=True)
    peer_reviewed_date = models.DateField(null=True, blank=True)
    assets_under_management = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    asset_size = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    jurisdiction_country = models.CharField(max_length=255, null=True, blank=True)
    jurisdiction_state = models.CharField(max_length=255, null=True, blank=True)
    cyber_clause_status = models.CharField(max_length=255, null=True, blank=True)
    clause_code = models.CharField(max_length=255, null=True, blank=True)
    clause_title = models.CharField(max_length=255, null=True, blank=True)
    rev_turnover = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    no_of_employees = models.IntegerField(null=True, blank=True)
    policy_status = models.CharField(max_length=255, null=True, blank=True)
    xfi_policy_level_status = models.CharField(max_length=255, null=True, blank=True)
    xfi_policy_activity_status = models.CharField(max_length=255, null=True, blank=True)
    xfi_policy_line_status = models.CharField(max_length=255, null=True, blank=True)
    renewal_status = models.CharField(max_length=255, null=True, blank=True)
    defense_costs_covered = models.CharField(max_length=255, null=True, blank=True)
    onshore_offshore = models.CharField(max_length=255, null=True, blank=True)
    limit_basis = models.CharField(max_length=255, null=True, blank=True)
    renewal_found_in_xfi = models.CharField(max_length=255, null=True, blank=True)
    renewed_policy_line_reference = models.CharField(max_length=255, null=True, blank=True)
    rarc_pct = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expired_gross_premium_usd_100pct = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    expired_gross_premium_agency_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    mosaic_1609_expired_gross_premium_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    amount_paid_by_insured_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    net_premium_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    amount_paid_by_insured_by_yoa_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    net_premium_by_yoa_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    file_name = models.CharField(null=True, blank=True, max_length=255)

    # Tracking fields
    uploaded_by = models.CharField(max_length=255, null=True, blank=True)
    uploaded_datetime = models.DateTimeField(auto_now_add=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

class MOP_mapping(models.Model):
    method_of_placement = models.CharField(max_length=255, null=True, blank=True)
    mapped_mop = models.CharField(max_length=255, null=True, blank=True)
    file_name = models.CharField(null=True, blank=True, max_length=255)
    
    # Tracking fields
    uploaded_by = models.CharField(max_length=255, null=True, blank=True)
    uploaded_datetime = models.DateTimeField(auto_now_add=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

class AON_Ledger(models.Model):
    uw_ba_id = models.CharField(max_length=255, null=True, blank=True)
    underwriter_reference_number = models.CharField(max_length=255, null=True, blank=True)
    entry_number = models.CharField(max_length=255, null=True, blank=True)
    bureau_non_bureau = models.CharField(max_length=255, null=True, blank=True)
    underwriter_name = models.CharField(max_length=255, null=True, blank=True)
    l2_name = models.CharField(max_length=255, null=True, blank=True)
    policy_no = models.CharField(max_length=255, null=True, blank=True)
    your_reference_number = models.CharField(max_length=255, null=True, blank=True)
    assured = models.CharField(max_length=255, null=True, blank=True)
    client_name = models.CharField(max_length=255, null=True, blank=True)
    transaction_no = models.CharField(max_length=255, null=True, blank=True)
    tran_version = models.CharField(max_length=255, null=True, blank=True)
    instalment_no = models.CharField(max_length=255, null=True, blank=True)
    txn_type = models.CharField(max_length=255, null=True, blank=True)
    trans_desc_1 = models.CharField(max_length=255, null=True, blank=True)
    trans_desc_2 = models.CharField(max_length=255, null=True, blank=True)
    narrative = models.TextField(null=True, blank=True)
    entry_date = models.DateField(null=True, blank=True)
    inception_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    uw_due_date = models.DateField(null=True, blank=True)
    uw_due_age_band = models.CharField(max_length=255, null=True, blank=True)
    ppw_date = models.DateField(null=True, blank=True)
    ebot = models.CharField(max_length=255, null=True, blank=True)
    ebot_status_date = models.DateField(null=True, blank=True)
    pap = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=255, null=True, blank=True)
    original_currency = models.CharField(max_length=10, null=True, blank=True)
    settlement_currency = models.CharField(max_length=10, null=True, blank=True)
    gross_prem_hard_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    amount_outstanding_settlement_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    ipt_hard = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    gross_commission_hard = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    amount_os_original_currency = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    gbp_os = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    division = models.CharField(max_length=255, null=True, blank=True)
    department = models.CharField(max_length=255, null=True, blank=True)
    team = models.CharField(max_length=255, null=True, blank=True)
    broker = models.CharField(max_length=255, null=True, blank=True)
    processing_technician_name = models.CharField(max_length=255, null=True, blank=True)
    underwriter_ac_handler = models.CharField(max_length=255, null=True, blank=True)
    exposure_ageband = models.CharField(max_length=255, null=True, blank=True)
    insured = models.CharField(max_length=255, null=True, blank=True)
    file_name = models.CharField(null=True, blank=True, max_length=255)

    # Tracking fields
    uploaded_by = models.CharField(max_length=255, null=True, blank=True)
    uploaded_datetime = models.DateTimeField(auto_now_add=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)


class TransactionStatus(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AgedDeptFileRecord(models.Model):
    file_name = models.CharField(max_length=255)
    no_of_records = models.IntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    uploaded_date_time = models.DateTimeField()
    archived = models.BooleanField(default=True)
    status = models.CharField(max_length=100, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    uploaded_by = models.CharField(max_length=255, null=True, blank=True)
    last_run_by = models.CharField(max_length=255, null=True, blank=True)
    last_run_time = models.DateTimeField(null=True, blank=True)
    calculation_files = models.JSONField(blank=True, null=True)
    progress = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"NewFileRecord(file_name={self.file_name}, no_of_records={self.no_of_records})" 


class AgedDebtAction(models.Model):
    aged_debt_action = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)


class AgedDebtCategory(models.Model):
    aged_debt_category = models.CharField(max_length=100)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)


class AgedDebtDueManagement(models.Model):
    policy_id = models.CharField(max_length=100, null=True, blank=True)
    installment_number = models.CharField(max_length=100, null=True, blank=True)
    installment_due_date = models.CharField(max_length=100, null=True)
    action = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    cc_comments = models.TextField(null=True, blank=True)
    underwriter_comments = models.TextField(null=True, blank=True)
    updated_by = models.ForeignKey('users.Users', on_delete=models.CASCADE, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)


class ChaserIndicator(models.Model):
    green_to_yellow = models.CharField(max_length=100, null=True, blank=True)
    yellow_to_red = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True, blank=True, related_name="chaser_created_by")
    updated_by = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True, blank=True, related_name="chaser_updated_by")
    addedDateAndTime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updatedDateAndTime = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_fields = models.TextField(null=True, blank=True)   

    def __str__(self):
        return f"green_to_yellow={self.green_to_yellow}, yellow_to_red={self.yellow_to_red}"


class AgeDebtAllocations(models.Model):
    policy_information = models.ForeignKey(PolicyInformation, on_delete=models.SET_NULL, null=True, blank=True, related_name='ageddebt_policy_info')
    policy = models.CharField(max_length=100, null=True, blank=True)
    policy_status = models.CharField(max_length=100, null=True, blank=True)
    installment_number = models.CharField(max_length=100, null=True, blank=True)
    installment_due_date = models.CharField(max_length=100, null=True, blank=True)
    master_broker = models.CharField(max_length=100, null=True, blank=True)
    cob = models.CharField(max_length=100, null=True, blank=True)
    mop = models.CharField(max_length=100, null=True, blank=True)
    umr = models.CharField(max_length=100, null=True, blank=True)
    binding_agreement = models.CharField(max_length=100, null=True, blank=True)
    yoa = models.CharField(max_length=100, null=True, blank=True)
    broker_reference = models.CharField(max_length=100, null=True, blank=True)
    insured = models.TextField(null=True, blank=True)
    ct_unallocated_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    ct_unallocated = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    installment_amount_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    total_receivable_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    balance_after_subtraction_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    installment_amount_sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    total_receivable_sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    balance_after_subtraction_sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    brokerage_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    brokerage_sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    commission_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    commission_sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    status_usd = models.CharField(max_length=100, null=True, blank=True)
    status_sett = models.CharField(max_length=100, null=True, blank=True)
    gross_written_premium_100_sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    gross_written_premium_100_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    net_written_premium_100_sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    net_written_premium_100_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    file_name = models.CharField(max_length=100, null=True, blank=True)
    market_source = models.CharField(max_length=100, null=True, blank=True)
    underwriter = models.CharField(max_length=100, null=True, blank=True)
    inception_date = models.DateField(null=True, blank=True)
    expired_date = models.DateField(null=True, blank=True)
    settlement_ccy = models.CharField(max_length=100, null=True, blank=True)
    producing_entity = models.CharField(max_length=100, null=True, blank=True)
    transaction_status = models.CharField(max_length=100, null=True, blank=True)
    estimated_closing_date = models.DateTimeField(null=True, blank=True)
    partial_payment_status = models.CharField(max_length=100, null=True, blank=True)
    expired_policy_status = models.CharField(max_length=100, null=True, blank=True)
    claims = models.CharField(max_length=100, null=True, blank=True)
    total_allocated_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    balance_after_subtraction_allocated_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    total_allocated_sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    balance_after_subtraction_allocated_sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    bank_account_number = models.CharField(max_length=100, null=True, blank=True)
    broker_branch = models.CharField(max_length=150, null=True, blank=True)
    ytbp_ageing_usd = models.CharField(max_length=255, null=True, blank=True)
    ytbp_ageing_sett = models.CharField(max_length=255, null=True, blank=True)
    cancellation_type = models.CharField(max_length=255, null=True, blank=True)
    xfi_installment_index = models.IntegerField(null=True, blank=True)
    xfi_reverse_installment_index = models.IntegerField(null=True, blank=True)
    xfi_installment_count = models.IntegerField(null=True, blank=True)
    overpaid_amount_sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    overpaid_amount_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    overpaid_allocated_amount_sett = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    overpaid_allocated_amount_usd = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    error_message = models.TextField(null=True, blank=True)
    original_ccy = models.CharField(max_length=255, null=True, blank=True)
    settlement_ccy = models.CharField(max_length=255, null=True, blank=True)
    original_ccy_amt = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    signed_line_pct = models.DecimalField(decimal_places=2, max_digits=12, default=0.00, null=True)
    insured_any_payment = models.CharField(max_length=255, null=True, blank=True)

class CommonAudit(models.Model):
    table_name = models.CharField(max_length=100, null=True, blank=True)
    record_id = models.IntegerField(null=True, blank=True)
    field_name = models.CharField(max_length=100, null=True, blank=True)
    old_value = models.JSONField(null=True)
    new_value = models.JSONField(null=True)
    changed_by = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_user")
    event_type = models.CharField(max_length=100, null=True, blank=True)
    previous_time = models.DateTimeField(null=True, blank=True)
    current_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
