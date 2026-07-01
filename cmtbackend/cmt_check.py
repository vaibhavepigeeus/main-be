
from importlib.resources import path
import os
# from sqlite3 import Timestamp

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cmtbackend.settings")
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

import django
django.setup()


from documents.models import *
from users.models import *
from  bankmanagement.models import *
from documents.serializers import *
from bankmanagement.serializers import *
from users.serializers import *


from cmtbackend.storage_backends import *

import json




# doc = Documents.objects.all()
# serializer = DocumentsSerializer(doc,many=True)
# dataa = serializer.data



# #
# for i in dataa:
#     print(i,"ggggggg")
#     doc_files=i["document_file"]
#     if doc_files:
#         bucket_key = doc_files.replace('https://<legacy-bucket>.s3.amazonaws.com/', '')
#         print("buket", bucket_key)
#         i['document_file'] = create_presigned_url("<legacy-bucket>", bucket_key)
#
#
# print(dataa)

{
"Bank_Transaction_Id":"",
"Accounting_Month":"datefield",
"PT_Receving_Bank_Account_Name_Entity":"",
"Receiving_Bank_Account":"",
    "Broker_Branch":"",
    "Broker":"",
    "Payment_Receive_Date":"",
    "Payment_Reference":"",
    "Payment_Currency_Code":"",
    "Bank_Currency_Code":"",
    "Bank_Exchange_Rate":"",
    "Bank_Exchange_Charges":"",
    "Bank_Charges":"",
    "Receivable_Amount":"",
    "TL_Fees":"",
    "Currency":"",
    "File_Name":"file field",
    "Created_By":"",
    "Analyst_Name":"",
    "Date_And_Time":"datetimefield",
    "Uploaded_By":""
}




#
# new_doc = BankTransaction.objects.create(Bank_Transaction_Id=data["Bank_Transaction_Id"],
#                                          Accounting_Month=data["Accounting_Month"],
#                                          PT_Receving_Bank_Account_Name_Entity=data["PT_Receving_Bank_Account_Name_Entity"],
#                                          Receiving_Bank_Account=data["Receiving_Bank_Account"],
#                                          Broker_Branch=data["Broker_Branch"],
#                                          Broker=data["Broker"],
#                                          Payment_Receive_Date=data["Payment_Receive_Date"],
#                                          Payment_Reference=data["Payment_Reference"],
#                                          Payment_Currency_Code=data["Payment_Currency_Code"],
#                                          Bank_Exchange_Rate=data["Bank_Exchange_Rate"],
#                                          Bank_Exchange_Charges=data["Bank_Exchange_Charges"],
#                                          Bank_Charges=data["Bank_Charges"],
#                                          Receivable_Amount=data["Receivable_Amount"],
#                                          TL_Fees=data["TL_Fees"],
#                                          Currency=data["Currency"],
#                                          Created_By=data["Created_By"],
#                                          Analyst_Name=data["Analyst_Name"],
#                                          Date_And_Time="",
#                                          Uploaded_By=data["Uploaded_By"],
#
#                                     )
#

# BankTransaction.objects.all().delete()




# ggg=[37,34,36,22,1,21,20,2,19,4]
#
#
# ff= Users.objects.filter(id)
#
# f=[
# "SYNAPSE PARTNERS360 ERIE BLVD ESYRA",
# "Servca Group Limited",
# "Taylor Ward Limited",
# "Tyser Belgium NV",
# "United Insurance Brokers Limited",
# "W Denis Insurance Brokers PLC",
# "Weald Insurance Broker Ltd",
# "Willis Australia Limited",
# "Willis Towers Watson BDA",
# "Willis Towers Watson Northeast, Inc.",
# "Zaman Insurance and Reinsurance Broker LLC"
# ]
#
import random
#
# h=["BNKTXN0007","BNKTXN0011","BNKTXN0006","BNKTXN0010","BNKTXN0009","BNKTXN0003","BNKTXN0008"]
#
#
# for i in h:
#     c=random.choice(f)
#     BankTransaction.objects.filter(Bank_Transaction_Id=i).update(Broker_Branch=c)



ff=[
        "Barclays",
        "CIBC",
        "Citibank",
        "FRB",
        "HSBC",
        "Lloyd's",
        "Mashreq",
        "Popular",
        "RBC",
        "UOB"
    ]



#
# gggg=BankTransaction.objects.all()
#
# for mmm in gggg:
#     c = random.choice(ff)
#     mmm.PT_Receving_Bank_Account_Name_Entity = c
#
#     mmm.save()

# BankTransaction.objects.all().update(Allocation_Status="Open")






# user_group_id_list = data["user_groups"]
# user_group_list = []
# for user_group in user_group_id_list:
#     if UserGroup.objects.filter(id=user_group["id"]).exists():
#         user_group_list.append(user_group["id"])
#     else:
#         return Response({"message": f'UserGroup with id {user_group["id"]} does not exist.'})
#
# for user_group_id in user_group_list:
#     new_workflow_step.user_groups.add(user_group_id)
# new_workflow_step.save()







# (removed dev scratch block containing credentials)


# ggg=[{'user_name': 'testingreviewer', 'id': 36}, {'user_name': 'Test_user_manager', 'id': 50}, {'user_name': 'Arvind', 'id': 22}, {'user_name': 'Nation', 'id': 21}, {'user_name': 'testingbharath123', 'id': 34}, {'user_name': 'fs', 'id': 41}, {'user_name': 'ghgjhjh', 'id': 38}, {'user_name': 'testerdd', 'id': 48}, {'user_name': 'Shivali', 'id': 39}, {'user_name': 'naveensunkis', 'id': 1}, {'user_name': '', 'id': 40}, {'user_name': 'tester', 'id': 51}, {'user_name': 'testing', 'id': 20}, {'user_name': 'user2', 'id': 56}, {'user_name': 'bharath', 'id': 37}, {'user_name': 'shivali0902', 'id': 54}, {'user_name': 'naveen', 'id': 43}
# ]
#
# lll=[]
#
# for i in ggg:
#     # print(i["id"])
#     lll.append(i["id"])
#
# print(lll)

# [43, 34, 1, 20, 21, 51, 56, 54, 22, 40, 38, 39, 36, 37, 41, 48, 50]
#
#
# hhh=[36,50,22,21,34,41,38,48,39,1,40,51,20,56,37,54,43]
# print(len(hhh))
# kk=Users.objects.all()
# print(len(kk))
# oo=[]
# for i in kk:
#     pp=i.id
#     oo.append(pp)
# #     # print(pp)
# #     if not pp in hhh:
# #         print(pp,"ppp")
# #         gg=Users.objects.get(id=pp)
# #         print(gg.id,"las")
#
# # print(len(oo))
# data={
#     "user_login_id":1,
#     "Bank_Transaction_Ids":[{"id": 156}]
# }
#
# user_id=data["user_login_id"]
# Bank_Transaction_Ids=data["Bank_Transaction_Ids"]
# user_id=Users.objects.get(id=user_id)

transss=[]


# for id in Bank_Transaction_Ids:
#     trans = BankTransaction.objects.get(id=id["id"])
#     # trans.Assigned_Users.add(user_id)
#     # trans.Assigned_Users.clear()
#     ff=trans.assigned_users_list
#     print(ff)
#     if not ff:
#         number=0
#         trans.set_assigned_users_list([])
#         dd=trans.assigned_users_list
#         print(dd,"ddddddddd")
#         serializer = UserSerializer(user_id)
#         data = serializer.data
#         data["assigned_users_number"] = number
#         dd.append(data)
#         trans.set_assigned_users_list(dd)
#         trans.save()
#         ff=trans.get_assigned_users_list()
#
#
#
#
#     print(ff)
#     print(type(ff))

    # data = serializer.data
    # data["assigned_users_number"] = number
    # number = number + 1
    # assigned_users_list.append(data)
    # assigned_users_list = sorted(assigned_users_list, key=lambda d: d['assigned_users_number'])
    # trans.set_assigned_users_list(assigned_users_list)
    # trans.save()
    # transss.append(trans)


# serializer = BankTransactionSerializer(transss,many=True)
# m = serializer.data




















# f=["Completed","Incorrect Premium - XFI",
# "Missing Settlement Details",
# "No Slip/Endorsement",
# "Not Booked in GXB",
# "Bank Fees",
# "IT Defect",
# "Pending GXB transfer",
# "Returned Premium",
# "Incorrect Premium - GXB",
# "Beneficinary Details",
# "Incorrect Premium - Closing",
# "Mosaic Share / Written Line",
# "Synidcate 1609/5399",
# "Refund",
# "Not Booked in XFI",
# "In Process - CC",
# "GreenKite Binder Adjustments"]
#
# for m in f:
#     print(m)
#     IssueCatergory.objects.create(issue_catergory=m)
#     print("sssss")




# g=Users.objects.filter(status="Actiate").count()
#
#
# print(g)












# role1 = "System Admin"
#
# System_Admin= {
#    "User Management":{
#       "Add":"Y",
#       "Edit":"Y",
#        "View":"Y",
#       "In-Active":"Y",
#       "Reactive":"Y"
#    },
#     "Bank Transactions": {
#         "Creation TXN": "N",
#         "Upload file": "Y",
#         "TXN List View": "Y",
#         "Delete": "Y",
#         "Edit": "Y",
#         "View": "Y",
#         "Allocation": "Y",
#         "Assignee": "Y"
#     },
#    "Admin Table Maintenance":{
#       "Creation":"Y",
#       "Edit":"Y",
#       "View":"Y"
#    },
#     "Cash Allocation Screen":{
#       "TXN List":"Y",
#       "Edit":"Y",
#       "Delete":"Y",
#       "View":"Y",
#    }
# }
#
#


#
# role2 = "Manager"
# Manager = {
#     "User Management": {
#         "Add": "Y",
#         "Edit": "Y",
#         "View": "Y",
#         "In-Active": "Y",
#         "Reactive": "Y"
#     },
#    "Bank Transactions":{
#       "Creation TXN":"N",
#       "Upload file":"Y",
#       "TXN List View":"Y",
#       "Delete":"Y",
#       "Edit":"Y",
#       "View":"Y",
#       "Allocation":"Y",
#       "Assignee":"Y"
#    },
#    "Admin Table Maintenance":{
#       "Creation":"Y",
#       "Edit":"Y",
#       "View":"Y"
#    },
#     "Cash Allocation Screen": {
#         "TXN List": "Y",
#         "Edit": "Y",
#         "Delete": "Y",
#         "View": "Y",
#     }
# }
#
# role3 = "Lead Role"
# Lead_Role = {
#     "User Management": {
#         "Add": "N",
#         "Edit": "N",
#         "View": "Y",
#         "In-Active": "N",
#         "Reactive": "N"
#     },
#      "Bank Transactions":{
#       "Creation TXN":"Y",
#       "Upload file":"Y",
#       "TXN List View":"Y",
#       "Delete":"N",
#       "Edit":"Y",
#       "View":"Y",
#       "Allocation":"Y",
#       "Assignee":"Y"
#    },
#    "Admin Table Maintenance":{
#       "Creation":"Y",
#       "Edit":"Y",
#       "View":"Y"
#    },
#     "Cash Allocation Screen": {
#         "TXN List": "Y",
#         "Edit": "Y",
#         "Delete": "Y",
#         "View": "Y",
#     }
# }

# role4 = "CC Processor"
# CC_Processor = {
#    "User Management":{
#       "Add":"N",
#       "Edit":"N",
#        "View":"Y",
#       "In-Active":"N",
#       "Reactive":"N"
#    },
#      "Bank Transactions":{
#       "Creation TXN":"Y",
#       "Upload file":"Y",
#       "TXN List View":"Y",
#       "Delete":"N",
#       "Edit":"N",
#       "View":"Y",
#       "Allocation":"N",
#       "Assignee":"N"
#    },
#    "Admin Table Maintenance":{
#       "Creation":"N",
#       "Edit":"N",
#       "View":"N"
#    },
#     "Cash Allocation Screen": {
#         "TXN List": "Y",
#         "Edit": "Y",
#         "Delete": "Y",
#         "View": "Y",
#     }
# }
#
# role5 = "Treasury"
# Treasury = {
#     "User Management": {
#         "Add": "N",
#         "Edit": "N",
#         "View": "N",
#         "In-Active": "N",
#         "Reactive": "N"
#     },
#      "Bank Transactions":{
#       "Creation TXN":"N",
#       "Upload file":"N",
#       "TXN List View":"Y",
#       "Delete":"N",
#       "Edit":"N",
#       "View":"Y",
#       "Allocation":"N",
#       "Assignee":"N"
#    },
#    "Admin Table Maintenance":{
#       "Creation":"N",
#       "Edit":"N",
#       "View":"N"
#    },
#     "Cash Allocation Screen": {
#         "TXN List": "N",
#         "Edit": "N",
#         "Delete": "N",
#         "View": "Y",
#     }
# }

# role6 = "Finance"
# Finance = {
#    "User Management":{
#       "Add":"N",
#       "Edit":"N",
#        "View":"N",
#       "In-Active":"N",
#       "Reactive":"N"
#    },
#     "Bank Transactions": {
#         "Creation TXN": "N",
#         "Upload file": "N",
#         "TXN List View": "Y",
#         "Delete": "N",
#         "Edit": "N",
#         "View": "Y",
#         "Allocation": "N",
#         "Assignee": "N"
#     },
#    "Admin Table Maintenance":{
#       "Creation":"N",
#       "Edit":"N",
#       "View":"N"
#    },
#     "Cash Allocation Screen": {
#         "TXN List": "N",
#         "Edit": "N",
#         "Delete": "N",
#         "View": "Y",
#     }
# }

role7 = "Quality Analyst"
Quality_Analyst = {
   "User Management":{
      "Add":"N",
      "Edit":"N",
       "View":"Y",
      "In-Active":"N",
      "Reactive":"N"
   },
    "Bank Transactions": {
        "Creation TXN": "N",
        "Upload file": "N",
        "TXN List View": "Y",
        "Delete": "N",
        "Edit": "N",
        "View": "Y",
        "Allocation": "N",
        "Assignee": "N"
    },
   "Admin Table Maintenance":{
      "Creation":"N",
      "Edit":"N",
      "View":"Y"
   },
   "Cash Allocation Screen":{
      "TXN List":"Y",
      "Edit":"N",
      "Delete":"N",
      "View":"Y",
   }
}
#
# ff=UserPermissions.objects.filter(role="Quality Analyst").last()
#
#
# ff.permissions_list=Quality_Analyst
#
# ff.save()

#
# user_per.permissions_list=Finance
#
# user_per.save()




#
















# CashAllocations = CashAllocation.objects.all().order_by("-id")
# g=[]
# for i in CashAllocations:
#     u={}
#     # print(i.bank_txn.Accounting_Month)
#     u["Accounting_Month"]=i.bank_txn.Accounting_Month
#     # print(i.policy_fk.Policy_Line_Ref)
#     u["Policy_Line_Ref"]=i.policy_fk.Policy_Line_Ref
#     # print(i.allocation_status)
#     u["allocation_status"]=i.allocation_status
#     # print(i.bank_curr)
#     u["bank_curr"]=i.bank_curr
#     # print(i.allocated_amt)
#     u["allocated_amt"]=i.allocated_amt
#     # print(i.cashreference)
#     u["cashreference"]=i.cashreference
#     # print(i.GXPbatchno)
#     u["GXPbatchno"]=i.GXPbatchno
#     print(i.XFIbatchno)
#     u["XFIbatchno"]=i.XFIbatchno
#     fff=i.bank_txn.Assigned_Users.all()[0]
#     if fff:
#         u["Assigned_Users"] = fff.user_name
#     g.append(u)





# BankExchangeRate.objects.all().delete()


# class BankTransactionViewSet(viewsets.ModelViewSet):
#     model = BankTransaction
#     serializer_class = BankTransactionSerializer
#     parser_classes = (MultiPartParser, FormParser, JSONParser)
#
#     def get_queryset(self):
#         trans = BankTransaction.objects.all()
#         return trans
#
#     def list(self, request):
#         trans = BankTransaction.objects.all().order_by('-id')
#         serializer = BankTransactionSerializer(trans, many=True)
#         dataa = serializer.data
#         for i in dataa:
#             print(i, "ggggggg")
#             trans_files = i["File_Name"]
#             if trans_files:
#                 bucket_key = trans_files.replace('https://<legacy-bucket>.s3.amazonaws.com/', '')
#                 print("buket", bucket_key)
#                 i['File_Name'] = create_presigned_url("<legacy-bucket>", bucket_key)
#         return Response(dataa)
#
#     def retrieve(self, request, pk=None):
#         if pk:
#             trans = BankTransaction.objects.get(id=pk)
#             serializer = BankTransactionSerializer(trans)
#             dataa = serializer.data
#             trans_files = dataa["File_Name"]
#             if trans_files:
#                 print(dataa, "fffffffffffffffffffffff")
#                 bucket_key = trans_files.replace('https://<legacy-bucket>.s3.amazonaws.com/', '')
#                 print("buket", bucket_key)
#                 dataa['File_Name'] = create_presigned_url("<legacy-bucket>", bucket_key)
#             return Response(dataa)
#
#     def create(self, request, *args, **kwargs):
#
#         upload_date = datetime.now()
#         dataa = request.data
#         transactions = []
#         for data in dataa:
#             try:
#                 g = BankTransaction.objects.latest("id")
#                 last_trans_id = g.Bank_Transaction_Id
#                 if last_trans_id:
#                     ll = last_trans_id[6:]
#                     trl = str(int(ll) + 1).zfill(4)
#                     trans_id_gen = "BNKTXN" + trl
#             except BankTransaction.DoesNotExist:
#                 trans_id_gen = "BNKTXN0001"
#
#             trans = BankTransaction.objects.create(Bank_Transaction_Id=trans_id_gen,
#                                                    Accounting_Month=data["Accounting_Month"],
#                                                    PT_Receving_Bank_Name=data["PT_Receving_Bank_Name"],
#                                                    Bank_Account_Name_Entity=data["Bank_Account_Name_Entity"],
#                                                    Receiving_Bank_Account=data["Receiving_Bank_Account"],
#                                                    Broker_Branch=data["Broker_Branch"],
#                                                    Broker=data["Broker"],
#                                                    Payment_Receive_Date=data["Payment_Receive_Date"],
#                                                    Payment_Reference=data["Payment_Reference"],
#                                                    Payment_Currency_Code=data["Payment_Currency_Code"],
#                                                    Bank_Currency_Code=data["Bank_Currency_Code"],
#                                                    Bank_Exchange_Rate=data["Bank_Exchange_Rate"],
#                                                    Bank_Exchange_Charges=data["Bank_Exchange_Charges"],
#                                                    Bank_Charges=data["Bank_Charges"],
#                                                    Receivable_Amount=data["Receivable_Amount"],
#                                                    TL_Fees=data["TL_Fees"],
#                                                    Currency=data["Currency"],
#                                                    Created_By=data["Created_By"],
#                                                    Analyst_Name=data["Analyst_Name"],
#                                                    Date_And_Time=upload_date,
#                                                    Uploaded_By=data["Uploaded_By"],
#                                                    Allocation_Status=data["Allocation_Status"],
#                                                    broker_information=BrokerInformation.objects.get(
#                                                        id=data["broker_information"]),
#                                                    bank_details=BankDetails.objects.get(id=data["bank_details"])
#                                                    )
#             trans.save()
#             doc_f = data["File_Name"]
#             transactions.append(trans)
#             print("dc", doc_f)
#             if doc_f:
#                 print("hereee")
#                 trans.File_Name = data["File_Name"]
#                 trans.save()
#                 transactions.append(trans)
#         serializer = BankTransactionCreateSerializer(transactions, many=True)
#         m = serializer.data
#         for dataa in m:
#             doc_files = dataa["File_Name"]
#             if doc_files:
#                 print(dataa, "fffffffffffffffffffffff")
#                 bucket_key = doc_files.replace('https://<legacy-bucket>.s3.amazonaws.com/', '')
#                 print("buket", bucket_key)
#                 dataa['File_Name'] = create_presigned_url("<legacy-bucket>", bucket_key)
#         return Response(m)
#
#     def update(self, request, *args, **kwargs):
#
#         trans_object = self.get_object()
#         print("trans_object", trans_object)
#         data = request.data
#         trans_object.Bank_Transaction_Id = data["Bank_Transaction_Id"]
#         trans_object.Accounting_Month = data["Accounting_Month"]
#         trans_object.PT_Receving_Bank_Name = data["PT_Receving_Bank_Name"]
#         trans_object.Bank_Account_Name_Entity = data["Bank_Account_Name_Entity"]
#         trans_object.Receiving_Bank_Account = data["Receiving_Bank_Account"]
#         trans_object.Broker_Branch = data["Broker_Branch"]
#         trans_object.Broker = data["Broker"]
#         trans_object.Payment_Receive_Date = data["Payment_Receive_Date"]
#         trans_object.Bank_Exchange_Rate = data["Bank_Exchange_Rate"]
#         trans_object.Bank_Currency_Code = data["Bank_Currency_Code"]
#         trans_object.Bank_Exchange_Charges = data["Bank_Exchange_Charges"]
#         trans_object.File_Name = data["File_Name"]
#         trans_object.Bank_Charges = data["Bank_Charges"]
#         trans_object.Receivable_Amount = data["Receivable_Amount"]
#         trans_object.TL_Fees = data["TL_Fees"]
#         trans_object.Currency = data["Currency"]
#         trans_object.Created_By = data["Created_By"]
#         trans_object.Analyst_Name = data["Analyst_Name"]
#         trans_object.Date_And_Time = data["Date_And_Time"]
#         trans_object.Uploaded_By = data["Uploaded_By"]
#         trans_object.broker_information = BrokerInformation.objects.get(id=request.data['broker_information'])
#         trans_object.bank_details = BankDetails.objects.get(id=request.data['bank_details'])
#         trans_object.save()
#         serializer = BankTransactionCreateSerializer(trans_object)
#         dataa = serializer.data
#         doc_files = dataa["File_Name"]
#         print(dataa, "fffffffffffffffffffffff")
#         if doc_files:
#             bucket_key = doc_files.replace('https://<legacy-bucket>.s3.amazonaws.com/', '')
#             print("buket", bucket_key)
#             dataa['File_Name'] = create_presigned_url("<legacy-bucket>", bucket_key)
#         return Response(dataa)
#
#     def partial_update(self, request, *args, **kwargs):
#
#         doc_object = self.get_object()
#         data = request.data
#         doc_object.Bank_Transaction_Id = data.get("Bank_Transaction_Id", doc_object.Bank_Transaction_Id)
#         doc_object.Accounting_Month = data.get("Accounting_Month", doc_object.Accounting_Month)
#         doc_object.PT_Receving_Bank_Name = data.get("PT_Receving_Bank_Name", doc_object.PT_Receving_Bank_Name)
#         doc_object.Bank_Account_Name_Entity = data.get("Bank_Account_Name_Entity", doc_object.Bank_Account_Name_Entity)
#         doc_object.Receiving_Bank_Account = data.get("Receiving_Bank_Account", doc_object.Receiving_Bank_Account)
#         doc_object.Broker_Branch = data.get("Broker_Branch", doc_object.Broker_Branch)
#         doc_object.Broker = data.get("Broker", doc_object.Broker)
#         doc_object.Payment_Receive_Date = data.get("Payment_Receive_Date", doc_object.Payment_Receive_Date)
#         doc_object.Payment_Reference = data.get("Payment_Reference", doc_object.Payment_Reference)
#         doc_object.Payment_Currency_Code = data.get("Payment_Currency_Code", doc_object.Payment_Currency_Code)
#         doc_object.Bank_Currency_Code = data.get("Bank_Currency_Code", doc_object.Bank_Currency_Code)
#         doc_object.Bank_Exchange_Rate = data.get("Bank_Exchange_Rate", doc_object.Bank_Exchange_Rate)
#         doc_object.Bank_Exchange_Charges = data.get("Bank_Exchange_Charges", doc_object.Bank_Exchange_Charges)
#         doc_object.Bank_Charges = data.get("Bank_Charges", doc_object.Bank_Charges)
#         doc_object.Receivable_Amount = data.get("Receivable_Amount", doc_object.Receivable_Amount)
#         doc_object.TL_Fees = data.get("TL_Fees", doc_object.TL_Fees)
#         doc_object.Currency = data.get("Currency", doc_object.Currency)
#         doc_object.Created_By = data.get("Created_By", doc_object.Created_By)
#         doc_object.Analyst_Name = data.get("Analyst_Name", doc_object.Analyst_Name)
#         doc_object.File_Name = data.get("File_Name", doc_object.File_Name)
#         doc_object.Date_And_Time = data.get("Date_And_Time", doc_object.Date_And_Time)
#         doc_object.Uploaded_By = data.get("Uploaded_By", doc_object.Uploaded_By)
#         doc_object.updated_by = data.get("updated_by", doc_object.updated_by)
#         doc_object.updatedDateAndTime = datetime.now()
#         doc_object.broker_information = BrokerInformation.objects.get(id=data.get("broker_information")) if data.get(
#             "broker_information") else doc_object.broker_information
#         doc_object.bank_details = BankDetails.objects.get(id=data.get("bank_details")) if data.get(
#             "bank_details") else doc_object.bank_details
#         updatedatetime = datetime.now()
#         data["updatedDateAndTime"] = str(updatedatetime)
#         data_items = []
#         if doc_object.updated_fields:
#             old_list = doc_object.updated_fields
#             old_list = json.loads(old_list)
#             data_items.extend(old_list)
#         data_items.append(data)
#         changedFields = json.dumps(data_items)
#         doc_object.updated_fields = changedFields
#
#         doc_object.save()
#         serializer = BankTransactionCreateSerializer(doc_object)
#         dataa = serializer.data
#         doc_files = dataa["File_Name"]
#         print(dataa, "fffffffffffffffffffffff")
#         if doc_files:
#             bucket_key = doc_files.replace('https://<legacy-bucket>.s3.amazonaws.com/', '')
#             print("buket", bucket_key)
#             dataa['File_Name'] = create_presigned_url("<legacy-bucket>", bucket_key)
#         return Response(dataa)
#
#     def destroy(self, request, *args, **kwargs):
#         doc_object = self.get_object()
#         doc_object.delete()
#         return Response({"message": "bank statement deleted successfully"})






#
# from django.http import JsonResponse
# from myapp.models import BankTransaction  # Replace 'myapp' with the name of your Django app
#
# def search_transactions(request):
#     date_and_time_frm = request.GET.get('date_and_time_frm')
#     date_and_time_to = request.GET.get('date_and_time_to')
#     bank_account_name_entity = request.GET.get('Bank_Account_Name_Entity')
#     skip = int(request.GET.get('skip', 0))
#     page_size = int(request.GET.get('pageSize', 20))
#
#     # Assuming BankTransaction model has fields like 'date_and_time', 'bank_account_name', and 'bank_transaction_id'
#     transactions = BankTransaction.objects.filter(
#         date_and_time__gte=date_and_time_frm,
#         date_and_time__lt=date_and_time_to,
#         bank_account_name=bank_account_name_entity
#     )[skip:skip+page_size]
#
#     # Assuming totalCount is the total count of transactions within the specified date range and bank account name/entity
#     total_count = BankTransaction.objects.filter(
#         date_and_time__gte=date_and_time_frm,
#         date_and_time__lt=date_and_time_to,
#         bank_account_name=bank_account_name_entity
#     ).count()
#
#     # Convert transactions queryset to JSON serializable format
#     transaction_data = [{'bank_transaction_id': transaction.bank_transaction_id, 'other_fields': 'other_values'} for transaction in transactions]
#
#     return JsonResponse({'data': transaction_data, 'totalCount': total_count})


















#
# workflow=data["workflow"]
# bank_txn_id=data["bank_txn_id"]
# changefields=data["changefields"]

# bank_txn_id="BNKTXN0320"
# changefields={"allocated_amount":9000}
# workflow=5
#
# ff=WorkFlow.objects.get(id=5)
# gg=WorkFlowSerializer(ff)
#
# hhhh=WorkflowBankTransactions.objects.create(workflow=ff,bank_txn_id=bank_txn_id)
# dict={}
# g=gg.data
# id=g["id"]
# workflow_name=g["workflow_name"]
# kkk=g["workflow_step"]
# f=[]
# for i in kkk:
#     l={}
#     l["id"]=i["id"]
#     l["ctime"]=i["ctime"]
#     l["status"]=i["status"]
#     l["uptime"]=i["uptime"]
#     l["comments"]=i["comments"]
#     l["step_name"]=i["step_name"]
#     llll=i["user"]
#     oo=[]
#     for m in llll:
#         hh={}
#         hh["id"]=m["id"]
#         hh["email"]=m["email"]
#         hh["user_name"]=m["user_name"]
#         oo.append(hh)
#     l["user"]=oo
#     f.append(l)
# workflow_step=f
# current_step="initiater"
# hhhh.changefields=changefields
#
# dict["id"]=id
# dict["workflow_name"]=workflow_name
# dict["workflow_step"]=workflow_step
# print(dict)
#
# hhhh.workflow_json_data=dict
# hhhh.current_step=current_step
#
# hhhh.save()

# current_step="initiater"
# null=""
# workflow_json_data={
#             "id": 5,
#             "workflow_name": "Change bank transaction amount",
#             "workflow_step": [
#                 {
#                     "id": 10,
#                     "user": [
#                         {
#                             "id": 39,
#                             "email": "[redacted]",
#                             "user_name": "Shivali"
#                         },
#                         {
#                             "id": 54,
#                             "email": "abcd",
#                             "user_name": "shivali0902"
#                         }
#                     ],
#                     "ctime": "2024-03-19T06:25:38.273834Z",
#                     "status": null,
#                     "uptime": null,
#                     "comments": null,
#                     "step_name": "initiater"
#                 },
#                 {
#                     "id": 11,
#                     "user": [
#                         {
#                             "id": 39,
#                             "email": "[redacted]",
#                             "user_name": "Shivali"
#                         },
#                         {
#                             "id": 54,
#                             "email": "abcd",
#                             "user_name": "shivali0902"
#                         }
#                     ],
#                     "ctime": "2024-03-19T06:27:01.531760Z",
#                     "status": null,
#                     "uptime": null,
#                     "comments": null,
#                     "step_name": "reviewer"
#                 },
#                 {
#                     "id": 12,
#                     "user": [
#                         {
#                             "id": 39,
#                             "email": "[redacted]",
#                             "user_name": "Shivali"
#                         },
#                         {
#                             "id": 54,
#                             "email": "abcd",
#                             "user_name": "shivali0902"
#                         }
#                     ],
#                     "ctime": "2024-03-19T06:27:31.845222Z",
#                     "status": null,
#                     "uptime": null,
#                     "comments": null,
#                     "step_name": "Approver"
#                 }
#             ]
#         }
#
# hhhh=WorkflowBankTransactions.objects.get(id=4)
#
# GG=workflow_json_data["workflow_step"]


data={
        "Receivable_Amount": 9000,
        "bank_txn_id": "BNKTXN03200",
        "comments":"change amount",
        "initiated_user_id":39
}
from datetime import datetime

# bank_txn_id = data["bank_txn_id"]
# Receivable_Amount = data["Receivable_Amount"]
# comments = data["comments"]
# initiated_user_id = data["initiated_user_id"]
# user_data = Users.objects.get(id=initiated_user_id)
# id = user_data.id
# email = user_data.email
# user_name = user_data.user_name
# initiated_data = {}
# initiated_data["id"] = id
# initiated_data["email"] = email
# initiated_data["user_name"] = user_name
# gjjj = []
# gjjj.append(initiated_data)
#
# print(gjjj,"gjjjjjjjjjjjjjj")
#
# kl = {}
# kl["user"] = gjjj
# kl["comments"] = comments
# kl["status"] = "NEW"
# kl["ctime"] = str(datetime.now())
# kl["uptime"] = str()
# kl["step_name"] = "initiater"
# workflow = 5
# ff = WorkFlow.objects.get(id=workflow)
# gg = WorkFlowSerializer(ff)
# hhhh = WorkflowBankTransactions.objects.create(workflow=ff, bank_txn_id=bank_txn_id)
#
# dict = {}
# g = gg.data
# id = g["id"]
# workflow_name = g["workflow_name"]
# kkk = g["workflow_step"]
#
#
# print("kllllllllll",kl)
#
#
# f = []
# f.append(kl)
#
#
# for i in kkk:
#     l = {}
#     l["id"] = i["id"]
#     l["ctime"] = i["ctime"]
#     l["status"] = i["status"]
#     l["uptime"] = i["uptime"]
#     l["comments"] = i["comments"]
#     l["step_name"] = i["step_name"]
#     llll = i["user"]
#     oo = []
#     for m in llll:
#         hh = {}
#         hh["id"] = m["id"]
#         hh["email"] = m["email"]
#         hh["user_name"] = m["user_name"]
#         oo.append(hh)
#     l["user"] = oo
#     f.append(l)
# workflow_step =f
#
#
# print(workflow_step)
# current_step = "initiater"
# hhhh.changefields = {"Receivable_Amount": Receivable_Amount}
# dict["id"] = id
# dict["workflow_name"] = workflow_name
# dict["workflow_step"] = workflow_step
# hhhh.workflow_json_data = dict
# hhhh.current_step = current_step
# hhhh.save()
# null=""
# {
#     "id": 17,
#     "workflow_json_data": {
#         "id": 5,
#         "workflow_name": "Change bank transaction amount",
#         "workflow_step": [
#             {
#                 "user": [
#                     {
#                         "id": 39,
#                         "email": "[redacted]",
#                         "user_name": "Shivali"
#                     }
#                 ],
#                 "comments": "change amount for BNKTXN0333 is 20000",
#                 "status": "NEW",
#                 "ctime": "2024-03-21 11:21:04.814914",
#                 "uptime": "",
#                 "step_name": "initiater"
#             },
#             {
#                 "id": 11,
#                 "ctime": "2024-03-21 11:21:09.861123",
#                 "status": null,
#                 "uptime": null,
#                 "comments": null,
#                 "step_name": "reviewer",
#                 "user": [
#                     {
#                         "id": 39,
#                         "email": "[redacted]",
#                         "user_name": "Shivali"
#                     },
#                     {
#                         "id": 54,
#                         "email": "abcd",
#                         "user_name": "shivali0902"
#                     }
#                 ]
#             },
#             {
#                 "id": 12,
#                 "ctime": "2024-03-21 11:21:09.861123",
#                 "status": null,
#                 "uptime": null,
#                 "comments": null,
#                 "step_name": "Approver",
#                 "user": [
#                     {
#                         "id": 39,
#                         "email": "[redacted]",
#                         "user_name": "Shivali"
#                     },
#                     {
#                         "id": 54,
#                         "email": "abcd",
#                         "user_name": "shivali0902"
#                     }
#                 ]
#             }
#         ]
#     },
#     "changefields": {
#         "Receivable_Amount": 20000
#     },
#     "current_step": "initiater",
#     "bank_txn_id": "BNKTXN0333",
#     "workflow": 5
# }
from django.db.models import Q
# user_id_to_match=39

# g=WorkflowBankTransactions.objects.filter(workflow_json_data__workflow_step__user__id=user_id_to_match)
# queryset = WorkflowBankTransactions.objects.filter(
#     workflow_json_data__workflow_step__contains={
#         [{'user': {'id': 39}}]
#     }
# )



# matching_records = WorkflowBankTransactions.objects.filter(
#     workflow_json_data__workflow_step__contains=[{'user': {'id': 39}}]
# )
# print(matching_records)


from django.contrib.postgres.fields import JSONField
from django.db.models import F
from django.db.models.functions import Cast


# Assuming you want to find records where the user ID matches 39
# user_id_to_match = 39

# Query to find records where the user ID matches
# matching_records = WorkflowBankTransactions.objects.annotate(
#     user_id=Cast(F('workflow_json_data__workflow_step__user__id'), JSONField())
# ).filter(id=user_id_to_match)
#
# print(matching_records)


# from myapp.models import MyModel  # Import your model here

# Assuming you want to find records where a specific user ID is present within the JSON data
# user_id_to_match = 39
#




# ff=BrokerInformation.objects.all()
#
#
# for i in ff:
#     id =i.id
#
# s.strip()
# Broker_Branch_Name="Newman Pearce & Partners LLP"
# brokerDetailsObjects = BrokerInformation.objects.filter(branch=Broker_Branch_Name).order_by('id').first()
#
#
# print(brokerDetailsObjects)












#
# print("month", mon)
# todays_date = date.today()
# year = todays_date.year
# print("year", year)
# data = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6, "July": 7, "August": 8,
#         "September": 9, "October": 10, "November": 11, "December": 12}
#
# month = data[mon]
# # print(month, "after")
# # print(year, "year")
#
# if month == 12:
#     last_date = datetime(year, month, 31)
# else:
#     last_date = datetime(year, month + 1, 1) + timedelta(days=-1)
#
# first_date = datetime(year, month, 1)









# data={
# "date_and_time_frm":"2024-02-20 12:00 AM",
# "date_and_time_to": "2024-03-23 12:01 AM",
# "Bank_Account_Name_Entity":"Barclays",
# "Bank_Transaction_Id":"",
# "skip":1,
# "pageSize":20
# }
#
# date_and_time_to = data["date_and_time_to"]
# date_and_time_frm = data["date_and_time_frm"]
# Bank_Account_Name_Entity = data["Bank_Account_Name_Entity"]
# Bank_Transaction_Id = data["Bank_Transaction_Id"]
# skip = data["skip"]
# pageSize = data["pageSize"]
#
# from dateutil import parser
#
# if date_and_time_to:
#     date_and_time_to = parser.parse(date_and_time_to)
# if date_and_time_frm:
#     date_and_time_frm = parser.parse(date_and_time_frm)
#
#
# queryset = BankTransaction.objects.all()

# views.py
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status


# class BankTransactionListCreate(generics.ListCreateAPIView):
#     queryset = BankTransaction.objects.all()
#     serializer_class = BankTransactionSerializer
#     pagination_class = YourPaginationClass  # Replace YourPaginationClass with the pagination class you want to use
#
#     def create(self, request, *args, **kwargs):
#         # Extracting data from request payload
#         date_from = request.data.get('date_from')
#         date_to = request.data.get('date_to')
#         bank_name = request.data.get('bank_name')
#         transaction_details = request.data.get('transaction_details')
#
#         # Validating data
#         if not (date_from and date_to and bank_name and transaction_details):
#             return Response({"message": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)
#
#         # Creating bank transaction instance
#         bank_transaction_data = {
#             'date_from': date_from,
#             'date_to': date_to,
#             'bank_name': bank_name,
#             'transaction_details': transaction_details,
#             # Add other fields as needed
#         }
#         serializer = self.get_serializer(data=bank_transaction_data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#
#         return Response(serializer.data, status=status.HTTP_201_CREATED)
#
#
# from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination, CursorPagination
#
# class MyPageNumberPagination(PageNumberPagination):
#     page_size = 10
#     page_size_query_param = 'page_size'
#     max_page_size = 100
#
# class MyLimitOffsetPagination(LimitOffsetPagination):
#     default_limit = 10
#     max_limit = 100
#
# class MyCursorPagination(CursorPagination):
#     page_size = 10
#     ordering = 'created_at'  # Specify the field to order results
#
#
# class MyListView(generics.ListAPIView):
#     queryset = MyModel.objects.all()
#     serializer_class = MyModelSerializer
#     pagination_class = MyPageNumberPagination  # or MyLimitOffsetPagination or MyCursorPagination
#
#
# from rest_framework import generics
# from rest_framework.pagination import CursorPagination
# from .models import BankTransaction
# from .serializers import BankTransactionSerializer
#
# class BankTransactionList(generics.ListAPIView):
#     serializer_class = BankTransactionSerializer
#     pagination_class = LargeDataCursorPagination
#
#     def get_queryset(self):
#         queryset = BankTransaction.objects.all()
#
#         # Extract search parameters from query parameters
#         date_from = self.request.query_params.get('date_from')
#         date_to = self.request.query_params.get('date_to')
#         bank_name = self.request.query_params.get('bank_name')
#         transaction_id = self.request.query_params.get('transaction_id')
#
#         # Filter queryset based on search parameters
#         if date_from:
#             queryset = queryset.filter(date__gte=date_from)
#         if date_to:
#             queryset = queryset.filter(date__lte=date_to)
#         if bank_name:
#             queryset = queryset.filter(bank_name__icontains=bank_name)
#         if transaction_id:
#             queryset = queryset.filter(transaction_id__icontains=transaction_id)
#
#         return queryset
#
# class LargeDataCursorPagination(CursorPagination):
#     page_size = 1000
#     ordering = '-id'  # Use the primary key or another unique field for ordering
#     cursor_query_param = 'cursor'
#
#
#
# # serializers.py
# from rest_framework import serializers
# from .models import YourModel
#
# class YourModelSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = YourModel
#         fields = '__all__'
#
# # views.py
# from rest_framework import generics
# from rest_framework import filters
# from .models import YourModel
# from .serializers import YourModelSerializer
#
# class YourModelList(generics.ListAPIView):
#     queryset = YourModel.objects.all()
#     serializer_class = YourModelSerializer
#     filter_backends = [filters.SearchFilter]
#     search_fields = ['field1', 'field2']  # Add fields you want to search
#
#     # Pagination
#     pagination_class = YourPaginationClass  # Use appropriate pagination class
#
# # pagination.py
# from rest_framework.pagination import PageNumberPagination
#
# class YourPaginationClass(PageNumberPagination):
#     page_size = 10  # Number of records per page
#     page_size_query_param = 'page_size'
#     max_page_size = 100  # Maximum number of records per page
#
# # urls.py
# from django.urls import path
# from .views import YourModelList
#
# urlpatterns = [
#     path('your-models/', YourModelList.as_view(), name='your-model-list'),
# ]
#
# # settings.py
# REST_FRAMEWORK = {
#     'DEFAULT_PAGINATION_CLASS': 'yourapp.pagination.YourPaginationClass',
#     'PAGE_SIZE': 10  # Default page size
# }
#
# # views.py
# from rest_framework import generics
# from .models import BankTransaction
# from .serializers import BankTransactionSerializer
# from rest_framework.pagination import PageNumberPagination
#
# class BankTransactionList(generics.ListAPIView):
#     serializer_class = BankTransactionSerializer
#     pagination_class = PageNumberPagination
#
#     def get_queryset(self):
#         queryset = BankTransaction.objects.all()
#
#
#         date_and_time_frm = self.request.data.get('date_and_time_frm')
#         date_and_time_to = self.request.data.get('date_and_time_to')
#         if date_and_time_frm and date_and_time_to:
#             queryset = queryset.filter(date_and_time__gte=date_and_time_frm, date_and_time__lt=date_and_time_to)
#
#         # Filtering by Bank_Account_Name_Entity
#         bank_account_name_entity = self.request.data.get('Bank_Account_Name_Entity')
#         if bank_account_name_entity:
#             queryset = queryset.filter(bank_account_name_entity=bank_account_name_entity)
#
#         # Filtering by Bank_Transaction_Id
#         bank_transaction_id = self.request.data.get('Bank_Transaction_Id')
#         if bank_transaction_id:
#             queryset = queryset.filter(bank_transaction_id=bank_transaction_id)
#
#         return queryset
#
#
# from datetime import datetime
#
# date_string = "23-03-2024"
# date_format = "%d-%m-%Y"
# converted_date = datetime.strptime(date_string, date_format)
#
# print(converted_date)


# WorkFlow.objects.filter(id=5).update(workflow_name="CHANGE_BANK_TRANSACTION_AMOUNT")
from dateutil import parser
# date_and_time_to = data["date_and_time_to"]
# date_and_time_to = "03-19-2024"
# date_and_time_frm = data["date_and_time_frm"]
# date_and_time_frm = "03-28-2024"
#
# if date_and_time_to:
#     date_and_time_to =datetime.strptime(date_and_time_to, "%m-%d-%Y")
#     print(date_and_time_to)
# if date_and_time_frm:
#     date_and_time_frm = datetime.strptime(date_and_time_frm, "%m-%d-%Y")
#     print(date_and_time_frm)
















# BrokerInformation.objects.filter(branch=" LOCKTON SOUTHEAST").update(branch="LOCKTON SOUTHEAST")
#
#
# user=22
#
#
# user_data=Users.objects.get(id=user)
#
# id = user_data.id
# email = user_data.email
# user_name = user_data.user_name
# initiated_data = {}
# initiated_data["id"] = id
# initiated_data["email"] = email
# initiated_data["user_name"] = user_name
# # print(initiated_data)
# queryset = WorkflowBankTransactions.objects.filter(
#     **{
#         'workflow_json_data__workflow_step__contains': [
#          {'user': [initiated_data]}
#         ]
#     }
# )
# print(len(queryset))
#
# serializer = WorkflowBankTransactionsSerializer(queryset,many=True)
#
# querysets=serializer.data
#
# g=[]
#
# for i in querysets:
#     curr=i.current_step
#     print(curr)
#     if curr=="reviewer":
#         curr == "reviewer"
#     if curr=="Approver":
#         curr == "Approver"
#     c=i.workflow_json_data["workflow_step"]
#     for m in c:
#         f=m["user"]
#         for ddd in f:
#             if ddd["id"]==user and m["step_name"]==curr:
#                 g.append(i)
#             elif ddd["id"]==user and m["step_name"]=="initiater":
#                 g.append(i)
#
#
#
# print(len(g))

# @csrf_exempt
# def getWorkflowList(request):
#     if request.method == "GET":
#         user_id = request.GET.get('user_id')
#         user_data = Users.objects.get(id=user_id)
#         id = user_data.id
#         email = user_data.email
#         user_name = user_data.user_name
#         initiated_data = {}
#         initiated_data["id"] = id
#         initiated_data["email"] = email
#         initiated_data["user_name"] = user_name
#         queryset = WorkflowBankTransactions.objects.filter(
#             **{
#                 'workflow_json_data__workflow_step__contains': [
#                     {'user': [initiated_data]}
#                 ]
#             }
#         )
#
#         g = []
#
#         for wf in queryset:  # taking each WF
#             # print(i)
#             curr = wf.current_step
#             wfsteps = wf.workflow_json_data.get("workflow_step", [])  # steps in WF
#             for wfstep in wfsteps:
#                 stepname = wfstep.get("step_name", [])
#                 wfstepusers = wfstep.get("user", [])
#                 print("stepname:", stepname, "userid=", wfstepusers, " user id:", user_id)
#             if stepname == curr or stepname == "initiater":  # initiater is hardcoded
#                 if stepname == curr:  # initiater is hardcoded
#                     for user in wfstepusers:
#                         userid = user.get("id", [])
#                         if str(userid) == str(user_id):
#                             g.append(wf)
#
#         serializer = WorkflowBankTransactionsSerializer(g, many=True)
#         return JsonResponse(serializer.data, safe=False)

# Lead_Role = {
#     "User Management": {
#         "Add": "N",
#         "Edit": "N",
#         "View": "Y",
#         "In-Active": "N",
#         "Reactive": "N"
#     },
#      "Bank Transactions":{
#       "Creation TXN":"Y",
#       "Upload file":"Y",
#       "TXN List View":"Y",
#       "Delete":"N",
#       "Edit":"Y",
#       "View":"Y",
#       "Allocation":"Y",
#       "Assignee":"Y"
#    },
#    "Admin Table Maintenance":{
#       "Creation":"Y",
#       "Edit":"Y",
#       "View":"Y"
#    },
#     "Cash Allocation Screen": {
#         "TXN List": "Y",
#         "Edit": "Y",
#         "Delete": "Y",
#         "View": "Y",
#     }
# }

# UserPermissions.objects.create(role="Lead Analyst",permissions_list=Lead_Role)



# (removed dev scratch block containing credentials)


# allocation_invoice_verification = models.CharField(max_length=100, null=True)
# receivable_amt = models.DecimalField(decimal_places=2, max_digits=12, null=True)
# Accounting_Month= models.DateField()
# Payment_Receive_Date = models.DateTimeField()












null=""

# data={
#   "bank_account_no": "3229839823",
#   "file_name": "example_file.csv",
#   "uploaded_date": "2024-04-05",
#   "uploaded_time": "2024-04-05T15:30:00",
#   "file_date": "2024-04-04",
#   "uploaded_status": "uploaded",
#   "credit_amount": 300.00,
#   "debit_amount": 300.00,
#   "total_amount": 600.00,
#   "ct_amount": 500.00,
#   "ct_amount_car": 50.00,
#   "bank_charges": 10.00,
#   "ct_bank_charges": 10.00,
#   "ct_bank_charges_var": 0.00,
#   "category_total": 560.00,
#   "error_message": null,
#   "locked": "No",
#   "allocated_analyst_id": 141,
#   "allocated_date": "2024-04-05",
#   "final_status": "pending",
#   "analyst_comments": "Needs further review",
#   "resolution_date": "2024-04-10",
#   "file_name_hyperlink": null
# }
#
#
#
# BankReconciliation.objects.create(bank_account_no=data["bank_account_no"],
#                                 file_name=data["file_name"],
#                                 uploaded_date=data["uploaded_date"],
#                                 uploaded_time=data["uploaded_time"],
#                                 file_date=data["file_date"],
#                                 uploaded_status=data["uploaded_status"],
#                                 credit_amount=data["credit_amount"],
#                                 debit_amount=data["debit_amount"],
#                                 total_amount=data["total_amount"],
#                                 ct_amount=data["ct_amount"],
#                                 ct_amount_car=data["ct_amount_car"],
#                                 bank_charges=data["bank_charges"],
#                                 ct_bank_charges=data["ct_bank_charges"],
#                                 ct_bank_charges_var=data["ct_bank_charges_var"],
#                                 category_total=data["category_total"],
#                                 error_message=data["error_message"],
#                                 locked=data["locked"],
#                                 allocated_analyst_id=Users.objects.get(id=data['allocated_analyst_id']),
#                                 final_status=data["final_status"],
#                                 analyst_comments=data["analyst_comments"],
#                                 resolution_date=data["resolution_date"],
#                                 allocated_date=data["allocated_date"]
#                                 )