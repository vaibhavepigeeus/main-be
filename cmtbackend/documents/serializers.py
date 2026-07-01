from rest_framework import serializers
from .models import *
from users.models import Users
import json


class DocumentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documents
        fields = "__all__"


class BrokerInformationSerializer(serializers.ModelSerializer):
    decrypted_email = serializers.SerializerMethodField()
    decrypted_phone_number = serializers.SerializerMethodField()

    class Meta:
        model = BrokerInformation
        fields = '__all__'

    def get_decrypted_email(self, obj):
        email = obj.get_decrypted_email()
        if not email or email=='nan':
            return email
        try:
            user_part, domain_part = email.split("@", 1)
            # if user_part:  # Ensure there's at least one character before '@'
            #     masked_email = f"{user_part[0]}***@{domain_part}"
            # else:
            masked_email = f"***@{domain_part}"
        except:
            masked_email = email  # In case the email is not in standard format
        return masked_email

    def get_decrypted_phone_number(self, obj):
        phone_number = obj.get_decrypted_phone_number()
        if not phone_number or phone_number=='nan':
            return phone_number
        try:  # Ensure phone number is long enough
            masked_phone_number = "*****" + phone_number[-4:]
        except:
            masked_phone_number = phone_number  # In case the phone number is too short to mask
        return masked_phone_number


class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        fields = '__all__'


class CurrencyInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyDetails
        fields = '__all__'


class AllocationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = AllocationStatus
        fields = '__all__'


class PolicyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyType
        fields = '__all__'


class LOBSerializer(serializers.ModelSerializer):
    class Meta:
        model = LOB
        fields = '__all__'

        extra_kwargs = {
            'addedDateAndTime': {'read_only': True},
            'updated_fields': {'read_only': True}
        }


class SCMPartnersSerializer(serializers.ModelSerializer):
    class Meta:
        model = SCMPartners
        fields = '__all__'


class BindingAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BindingAgreement
        fields = '__all__'


class CorrectionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectionType
        fields = '__all__'

class TransactionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionCategory
        fields = '__all__'


class CashTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashTransfer
        fields = '__all__'


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = '__all__'


class IssueCatergorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueCatergory
        fields = '__all__'


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyInformation
        fields = '__all__'


class AgedebtSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgeDebtAllocations
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        queryset = AgedDebtDueManagement.objects.filter(policy_id=instance.policy, installment_number=instance.installment_number, installment_due_date=instance.installment_due_date)
        if queryset.exists():
            representation['aged_debt_due_management'] = AgedDebtDueManagementSerializer(queryset.first()).data
        else:
            representation['aged_debt_due_management'] = None
        return representation


class AgedebtDownloadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgeDebtAllocations
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert decimal fields to float for proper Excel formatting
        decimal_fields = [
            'ct_unallocated_usd', 'ct_unallocated', 'installment_amount_usd', 
            'total_receivable_usd', 'balance_after_subtraction_usd',
            'installment_amount_sett', 'total_receivable_sett', 
            'balance_after_subtraction_sett', 'brokerage_usd', 'brokerage_sett',
            'commission_usd', 'commission_sett', 'gross_written_premium_100_sett',
            'gross_written_premium_100_usd', 'net_written_premium_100_sett',
            'net_written_premium_100_usd', 'total_allocated_usd',
            'balance_after_subtraction_allocated_usd', 'total_allocated_sett',
            'balance_after_subtraction_allocated_sett'
        ]
        
        for field in decimal_fields:
            if representation.get(field) is not None:
                try:
                    representation[field] = float(representation[field])
                except (ValueError, TypeError):
                    representation[field] = 0.0
        
        queryset = AgedDebtDueManagement.objects.filter(
            policy_id=instance.policy,
            installment_number=instance.installment_number
        )
        if queryset.exists():
            obj = queryset.first()

            def safe_json_loads(value):
                try:
                    return json.loads(value) if value else None
                except (json.JSONDecodeError, TypeError):
                    return None

            cc = safe_json_loads(obj.cc_comments)
            uc = safe_json_loads(obj.underwriter_comments)

            representation['cc_comments'] = cc[-1]['value'] if cc else None
            representation['underwriter_comments'] = uc[-1]['value'] if uc else None
            representation['action'] = obj.action
            representation['category'] = obj.category
        else:
            representation['cc_comments'] = None
            representation['underwriter_comments'] = None
            representation['action'] = None
            representation['category'] = None

        return representation


class PolicyRefNoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyInformation
        fields = ("id", "Class_of_Business", "Year_of_Account", "Producing_Entity", "Syndicate_Binder", "Policy_Status",
                  "Policy_Line_Ref", "UMR_Number", "Three_Party_Capacity_Deployed", "SCM_Partner",
                  "SCM_Insurer_partner_name", "Binding_Agreement", "Broker", "Settlement_Ccy", "Settlement_ROE",
                  "Insured", "Original_Ccy")


class BankExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankExchangeRate
        fields = '__all__'


class PowerBIReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PowerBIReport
        fields = '__all__'
        
class EscalationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Escalation
        fields = '__all__' 

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['escalation_level_one'] = {'id': instance.escalation_level_one.id, 'user_name':instance.escalation_level_one.user_name}
        representation['escalation_level_two'] = {'id': instance.escalation_level_two.id, 'user_name':instance.escalation_level_two.user_name}
        representation['escalation_level_three'] = {'id': instance.escalation_level_three.id, 'user_name':instance.escalation_level_three.user_name}

        return representation           
class SLASerializer(serializers.ModelSerializer):
    class Meta:
        model = SLA
        fields = '__all__'        

class ParticipatingInsurerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParticipatingInsurer
        fields = '__all__' 

class SiriusDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiriusData
        fields = '__all__'

class RBSDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RBSDetails
        fields = '__all__'

class MOPMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MOP_mapping
        fields = '__all__'

class AONLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AON_Ledger
        fields = '__all__'

class TransactionStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionStatus
        fields = '__all__'


class AgedDeptFileRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgedDeptFileRecord
        fields = '__all__'
    

class AgedDebtDueManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgedDebtDueManagement
        fields = '__all__'

    def _process_comments(self, comments_data, sort_by_no=False):
        """Parse JSON/string comments and replace 'by' with user_name if exists."""
        try:
            comments = (
                json.loads(comments_data) 
                if isinstance(comments_data, str) else comments_data
            )
            for comment in comments:
                if "by" in comment and comment["by"] is not None:
                    user = Users.objects.filter(pk=comment["by"]).first()
                    comment["by"] = user.user_name if user else comment["by"]

                # Ensure "no" is always an integer for sorting
                if "no" in comment:
                    try:
                        comment["no"] = int(comment["no"])
                    except (ValueError, TypeError):
                        comment["no"] = 0

            # Sort comments by 'no' (descending)
            if sort_by_no:
                comments = sorted(comments, key=lambda x: x.get("no", 0), reverse=True)

            return comments
        except Exception:
            return []

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data['updated_by'] = instance.updated_by.user_name if instance.updated_by else None
        data['updated_at'] = instance.updated_at.date() if instance.updated_at else None

        # Process comments
        if data.get("cc_comments"):
            data["cc_comments"] = self._process_comments(data["cc_comments"], sort_by_no=True)

        if data.get("underwriter_comments"):
            data["underwriter_comments"] = self._process_comments(data["underwriter_comments"], sort_by_no=True)

        return data


class ChaserIndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChaserIndicator
        fields = '__all__' 

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['created_by'] = {'id': instance.created_by.id, 'user_name':instance.created_by.user_name}
        if instance.updated_by:
            representation['updated_by'] = {'id': instance.updated_by.id, 'user_name':instance.updated_by.user_name}
        else:
            representation['updated_by'] = None
        return representation           


class AgedDebtActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgedDebtAction
        fields = '__all__'


class AgedDebtCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgedDebtCategory
        fields = '__all__'