from rest_framework import serializers
from .models import *
from users.serializers import MinimalUserSerializer

class PremiumBDXSerializer(serializers.ModelSerializer):
    analyst_id = MinimalUserSerializer(read_only=True)

    class Meta:
        model = PremiumBDX
        fields = '__all__'


class PaymentTreasurySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTreasury
        fields = '__all__'


class PaymentFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentFile
        fields = '__all__'


class PaymentFileOverallStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentFile
        fields = ['Overall_Status']


class PaymentTreasuryPYMTSerializer(serializers.ModelSerializer):
    updated_by = MinimalUserSerializer(read_only=True)

    class Meta:
        model = PaymentTreasuryPYMT
        fields = '__all__'


class PaymentExceptionSerializer(serializers.ModelSerializer):
    updated_by = MinimalUserSerializer(read_only=True)
    
    class Meta:
        model = PaymentException
        fields = '__all__'


class PaymentDatasheetSerializer(serializers.ModelSerializer):
    bdx = PremiumBDXSerializer(read_only=True)
    
    class Meta:
        model = PaymentDatasheet
        fields = '__all__'


class PayoutSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutSummary
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        if instance.bdx_ids:
            res = []
            id_list = instance.bdx_ids[1:-1].replace(" ", "").split(',')
            for i in id_list:
                try:
                    bdx = PremiumBDX.objects.get(id=i)
                    res.append({
                        "id": i,
                        "policy_no": bdx.certificateref,
                        "finalnetpremiumsc": bdx.finalnetpremiumsc,
                        "finalnetpremiumusd": bdx.finalnetpremiumusd,
                        "rebate": bdx.rebate,
                        "net_payment": bdx.net_payment,
                        })
                except:
                    continue
            response['bdx_ids'] = res
        return response


class CoversheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coversheet
        fields = '__all__'


class PremBDXFilesSerializer(serializers.ModelSerializer):
    uploaded_by = MinimalUserSerializer(read_only=True)
    class Meta:
        model = PremBDXFiles
        fields = '__all__'
