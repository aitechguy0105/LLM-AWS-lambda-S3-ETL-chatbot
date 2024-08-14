import json
import boto3
import pandas as pd
from io import StringIO # python3; python2: BytesIO 
import requests
import pytz
import datetime
import json
import base64
import os

def print_key_value(obj, indent=0):
    
    # Function to print key-value pairs recursively
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                print('  ' * indent + f'{key}:')
                print_key_value(value, indent + 1)
            else:
                print('  ' * indent + f'{key}: {value}')
    elif isinstance(obj, list):
        for item in obj:
            print_key_value(item, indent + 1)
            
def get_swiftpos_token():
    # Function to get authentication token from Swiftpos API
    url = "https://api.swiftpos.com.au/api/Authorisation"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {
        "ClerkId": os.environ["clerk_id"],
        "ClientId": os.environ["client_id"],
        "CustomerId": os.environ["customer_id"],
        "Signature": os.environ["signature"],
        "Identity": os.environ["identity"]
    }
    # print(data)
    response = requests.post(url, headers=headers, data=json.dumps(data))
    api_token = response.json()["AuthorizationToken"]
    # print(api_token)
    
    return api_token
def get_humanforce_token():
    # Function to generate Basic Authentication header for Humanforce API
    api_key = os.environ["human_force_api_key"]
    api_secret = os.environ["human_force_api_secret"]

    # Concatenate the API Key and Secret with a colon
    credentials = f'{api_key}:{api_secret}'
    # print(credentials)
    # Encode the credentials to base64
    credentials_base64 = base64.b64encode(credentials.encode()).decode()

    # Create the Basic Authentication header value
    basic_auth_header = f'Basic {credentials_base64}'
    return basic_auth_header

def swiftpos_sales(token, s3, bucket_name, prev_time, current_time):
    # Function to fetch sales data from Swiftpos API and save it to S3
    print("start swiftpos_sales: ", datetime.datetime.now(pytz.utc))
    formatted_prev_time = prev_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    formatted_current_time = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    url = "https://api.swiftpos.com.au/api/Sale"
    headers = {
        "accept": "application/json",
        "AuthorizationToken": token
    }
    params = {
        "from": formatted_prev_time,
        "to": formatted_current_time
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data_list = response.json()
        
        for data in data_list:
            
            data["Venue_Id"] = data.pop("Id")
            data["Venue_Name"] = data.pop("Name")
            data["Sales"] = data.pop("Sales")
            for sale_data in data["Sales"]:
                if "SaleType" in sale_data:
                    print ('====================del saleType')
                    del sale_data["SaleType"]
                sale_data["Sales_Id"] = sale_data.pop("Id")
                del sale_data["ReceiptId"]
                
                sale_data["Location_Id"] = sale_data["Location"]["Id"]
                sale_data["Location_Name"] = sale_data["Location"]["Name"]
                del sale_data["Location"]
                
                sale_data["Terminal_Id"] = sale_data["Terminal"]["Id"]
                sale_data["Terminal_Name"] = sale_data["Terminal"]["Name"]
                del sale_data["Terminal"]

                sale_data["Clerk_Id"] = sale_data["Clerk"]["Id"]
                sale_data["Clerk_Name"] = sale_data["Clerk"]["Name"]
                del sale_data["Clerk"]

                sale_data["Member_Id"] = sale_data["Customer"]["Id"]
                sale_data["Member_Name"] = sale_data["Customer"]["Name"]
                sale_data["Classification_Id"] = sale_data["Customer"]["Classification"]["Id"]
                sale_data["Classification_Name"] = sale_data["Customer"]["Classification"]["Name"]
                sale_data["Member_Account_Balance"] = sale_data["Customer"]["Balance"]["Account"]
                sale_data["Member_Points_Balance"] = sale_data["Customer"]["Balance"]["Points"]
                del sale_data["Customer"]

                sale_data["Transaction_Date"] = sale_data.pop("TransactionDate")
                sale_data["Transaction_Type"] = sale_data.pop("TransactionType")

                sale_data["Table_Id"] = sale_data["Table"]["Id"]
                sale_data["Adult_Covers"] = sale_data["Table"]["AdultCovers"]
                sale_data["Child_Covers"] = sale_data["Table"]["ChildCovers"]
                del sale_data["Table"]
                
                print(sale_data["Items"])
                sale_data["Items"] = sale_data.pop("Items")

                
                for item in sale_data["Items"]:

                    item["Inventory_Code"] = item.pop("InventoryCode")
                    
                    item["Product_Plu"] = item.pop("Plu")
                    item["Product_Name"] = item.pop("Name")
                    

                    item["Category_Id"] = item["Category"]["Id"]
                    item["Category_Name"] = item["Category"]["Name"]
                    del item["Category"]


                    item["Group_Id"] = item["Group"]["Id"]
                    item["Group_Name"] = item["Group"]["Name"]
                    del item["Group"]

                    item["Master_Group_Id"] = item["MasterGroup"]["Id"]
                    item["Master_Group_Name"] = item["MasterGroup"]["Name"]
                    del item["MasterGroup"]
                    
                    item["Price_Level_Id"] = item["PriceLevel"]["Id"]
                    item["Price_Level_Name"] = item["PriceLevel"]["Name"]
                    del item["PriceLevel"]
                    item["Quantity"] = item.pop("Quantity")

                    item["Total_Ex"] = item.pop("TotalEx")
                    item["Total_Inc"] = item.pop("TotalInc")
                    item["Normal_Price"] = item.pop("NormalPrice")
                    item["Item_Cost"] = item.pop("ItemCost")

                    del item["HostId"]
                    del item["Size"]
                    del item["Clerk"]
                    del item["Location"]
                    del item["Counter"]
                    del item["ParentCounter"]
                    del item["Barcode"]
                    del item["Tax"]
                    del item["TaxFree"]
                    del item["IsDiscount"]
                    del item["IsRefund"]
                    del item["IsVoid"]
                    del item["IsSurcharge"]
                    del item["IsPromotion"]
                    del item["DiscountId"]
                    del item["DiscountName"]
                    del item["SurchargeId"]
                    del item["SurchargeName"]
                    del item["Reason"]
                    
                sale_data["Media"] = sale_data.pop("Media")
                for media in sale_data["Media"]:
                    
                    media["Media_Id"] = media.pop("Id")
                    media["Media_Name"] = media.pop("Name")
                    media["Amount"] = media.pop("Amount")
                    media["Rounded_Amount"] = media.pop("RoundedAmount")

                    del media["Clerk"]
                    del media["RedemptionRatio"]
                    del media["EpurseId"]
                del sale_data["Reason"]


        # print_key_value(data_list)
        formatted_current_time_filename = current_time.strftime('%Y-%m-%dT%H-%M-%S.%f')[:-3] + 'Z'
        
        file_path = f"hospitality-chatbot-swiftpos-sales/year={current_time.year}/month={current_time.month}/day={current_time.day}/hospitality-chatbot-swiftpos-sales-{formatted_current_time_filename}.json"
        
        # Write the list to the file in JSON format
        json_data = json.dumps(data_list)
        
        s3.put_object(Bucket=bucket_name, Key=file_path, Body=json_data)
 
    else:
        print("Failed to retrieve data. Status code:", response.status_code)
    print("end swiftpos_sales: ", datetime.datetime.now(pytz.utc))
    
def swiftpos_member_transactions(token, s3, bucket_name, prev_time, current_time):
    # Function to fetch member transactions data from Swiftpos API and save it to S3
    print("start swiftpos_transactions: ", datetime.datetime.now(pytz.utc))

    formatted_prev_time = prev_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    formatted_current_time = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    print("Current time in GMT timezone:", formatted_current_time)
    memberID = os.environ["member_id"]
    url = f"https://api.swiftpos.com.au/api/Member/{memberID}/Transaction"
    headers = {
        "accept": "application/json",
        "AuthorizationToken": token
    }
    params = {
        "from": formatted_prev_time,
        "to": formatted_current_time
    }
    response = requests.get(url, headers=headers, params=params)


    if response.status_code == 200:
        data_list = response.json()

        for transaction_data in data_list:
            del transaction_data["Id"]
            transaction_data["Transaction_Date"] = transaction_data.pop("TransactionDate")
            transaction_data["Location_Id"] = transaction_data.pop("LocationId")
            transaction_data["Location_Name"] = transaction_data.pop("LocationName")
            transaction_data["Transaction_Total"] = transaction_data.pop("TransactionTotal")
            transaction_data["Charge_Total"] = transaction_data.pop("ChargeTotal")
            transaction_data["Payment_Total"] = transaction_data.pop("PaymentTotal")
            transaction_data["Points_Total"] = transaction_data.pop("PointsTotal")
            transaction_data["Items"] = transaction_data.pop("Items")
            for item in transaction_data["Items"]:
    
                item["Product_Plu"] = item.pop("Id")
                item["Product_Name"] = item.pop("Name")
                item["Product_Quantity"] = item.pop("Quantity")
                item["Product_Total"] = item.pop("Total")
    
    
            transaction_data["Medias"] = transaction_data.pop("Medias")
            for media in transaction_data["Medias"]:
                
                media["Media_Id"] = media.pop("Id")
                media["Media_Name"] = media.pop("Name")
                media["Amount"] = media.pop("Amount")
                del media["ePurseId"]
        
        # print_key_value(data_list)

        formatted_current_time_filename = current_time.strftime('%Y-%m-%dT%H-%M-%S.%f')[:-3] + 'Z'
        file_path = f"hospitality-chatbot-swiftpos-transactions/year={current_time.year}/month={current_time.month}/day={current_time.day}/hospitality-chatbot-swiftpos-member-transactions-{formatted_current_time_filename}.json"
    
        # Write the list to the file in JSON format
        json_data = json.dumps(data_list)
        
        s3.put_object(Bucket=bucket_name, Key=file_path, Body=json_data)
    else:
        print("Failed to retrieve data. Status code:", response.status_code)
    print("end swiftpos_transactions: ", datetime.datetime.now(pytz.utc))
def swiftpos_products(token, s3, bucket_name, prev_time, current_time):
    # Function to fetch product data from Swiftpos API and save it to S3
    print("start swiftpos_products: ", datetime.datetime.now(pytz.utc))
    formatted_prev_time = prev_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    formatted_current_time = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    url = f"https://api.swiftpos.com.au/api/Product"
    headers = {
        "accept": "application/json",
        "AuthorizationToken": token
    }
    params = {
        "memberId": 310005,
        "categoryId": 1,
        "groupId": 1,
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data_list = response.json()

        for product_data in data_list:
            product_data["Product_Id"] = product_data.pop("Id")
            product_data["Inventory_Code"] = product_data.pop("InventoryCode")
            
            product_data["Description_Standard"] = product_data["Description"]["Standard"]
            del product_data["Description"]
            
            product_data["Category_Id"] = product_data["Category"]["Id"]
            product_data["Category_Name"] = product_data["Category"]["Name"]
            del product_data["Category"]
    
            product_data["Group_Id"] = product_data["Group"]["Id"]
            product_data["Group_Name"] = product_data["Group"]["Name"]
            del product_data["Group"]
    
            product_data["Barcodes"] = product_data.pop("Barcodes")
            product_data["Product_Price"] = product_data.pop("Price")
            product_data["Stock_Level"] = product_data.pop("StockLevel")
            del product_data["ProductGuid"]
            del product_data["Image"]
            del product_data["HostId"]
            del product_data["Allergens"]
            del product_data["Nutritions"]
    
        formatted_current_time_filename = current_time.strftime('%Y-%m-%dT%H-%M-%S.%f')[:-3] + 'Z'
        file_path = f"hospitality-chatbot-swiftpos-products/{current_time.year}/{current_time.month}/{current_time.day}/hospitality-chatbot-swiftpos-products-{formatted_current_time_filename}.json"

        # Write the list to the file in JSON format
        json_data = json.dumps(data_list)
        
        s3.put_object(Bucket=bucket_name, Key=file_path, Body=json_data)
    else:
        print("Failed to retrieve data. Status code:", response.status_code)
    print("end swiftpos_products: ", datetime.datetime.now(pytz.utc))
def humanforce_timesheets(token, s3, bucket_name, prev_time, current_time):
    
    # Function to fetch timesheets data from Humanforce API and save it to S3
    print("start humanforce_timesheets: ", datetime.datetime.now(pytz.utc))
    formatted_prev_time = prev_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    formatted_current_time = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    url = 'https://apidemo.humanforce.com/api/1.0/timesheets'
    headers = {
        'Accept': 'application/json',
        'Authorization': token
    }
    params = {
        'dateMin': formatted_prev_time,
        'dateMax': formatted_current_time,
        'usePayDate': 'true'
    }

    response = requests.get(url, headers=headers, params=params)


    if response.status_code == 200:
        data_list = response.json()

        for timesheet_data in data_list:
            del timesheet_data["GuidKey"]
            del timesheet_data["LastEdit"]
            del timesheet_data["LastEditBy"]
            
            timesheet_data["Employee_Code"] = timesheet_data["Employee"]["EmployeeCode"]
            timesheet_data["Employee_Name"] = timesheet_data["Employee"]["Name"]
            timesheet_data["Employment_Type"] = timesheet_data["Employee"]["EmploymentType"]["Name"]
            del timesheet_data["Employee"]        
    
            timesheet_data["Timesheet_Date"] = timesheet_data.pop("DateStart")
    
            timesheet_data["Pay_Date"] = timesheet_data.pop("PayDate")
            timesheet_data["Pay_Start_Time"] = timesheet_data.pop("PayStartTime")
            timesheet_data["Pay_End_Time"] = timesheet_data.pop("PayEndTime")
            timesheet_data["Clocked_Start_Time"] = timesheet_data.pop("ClockedStartTime")
            timesheet_data["Clocked_End_Time"] = timesheet_data.pop("ClockedEndTime")
            timesheet_data["Gross_Minutes"] = timesheet_data.pop("GrossMinutes")
            timesheet_data["Net_Minutes"] = timesheet_data.pop("NetMinutes")
    
    
            del timesheet_data["Breaks"]
            timesheet_data["Break_Minutes_Unpaid"] = timesheet_data.pop("BreakMinutesUnpaid")
            timesheet_data["Break_Minutes_Paid"] = timesheet_data.pop("BreakMinutesPaid")
            timesheet_data["Roster_Start_Time"] = timesheet_data.pop("RosterStartTime")
            timesheet_data["Roster_End_Time"] = timesheet_data.pop("RosterEndTime")
            del timesheet_data["RosterGuidKey"]
    
            timesheet_data["Location_Name"] = timesheet_data["Location"]["Name"]
            del timesheet_data["Location"]
            timesheet_data["Department_Name"] = timesheet_data["Department"]["Name"]
            del timesheet_data["Department"]
            timesheet_data["Role_Name"] = timesheet_data["Role"]["Name"]
            del timesheet_data["Role"]
            timesheet_data["Timesheet_Cost"] = timesheet_data.pop("Cost")
    
            del timesheet_data["Profile"]
            del timesheet_data["Period"]
            del timesheet_data["Area"]
            del timesheet_data["Event"]
            del timesheet_data["EventFunction"]
            del timesheet_data["ShiftType"]
    
            del timesheet_data["Authorised"]
            del timesheet_data["AuthorisedBy"]
            del timesheet_data["AuthorisedAt"]
            del timesheet_data["Paid"]
            del timesheet_data["Started"]
            del timesheet_data["Ended"]
            del timesheet_data["AdminLock"]
            del timesheet_data["Reversal"]
            del timesheet_data["Comments"]
            del timesheet_data["Deleted"]
            del timesheet_data["PayTypes"]
         
        
    
        formatted_current_time_filename = current_time.strftime('%Y-%m-%dT%H-%M-%S.%f')[:-3] + 'Z'
        file_path = f"hospitality-chatbot-humanforce-timesheets/year={current_time.year}/month={current_time.month}/hospitality-chatbot-humanforce-timesheets-{formatted_current_time_filename}.json"

        # Write the list to the file in JSON format
        json_data = json.dumps(data_list)
        
        s3.put_object(Bucket=bucket_name, Key=file_path, Body=json_data)
    else:
        print("Failed to retrieve data. Status code:", response.status_code)
    print("end humanforce_timesheets: ", datetime.datetime.now(pytz.utc))

def humanforce_rosters(token, s3, bucket_name, prev_time, current_time):
    # Function to fetch rosters data from Humanforce API and save it to S3
    print("start humanforce_rosters: ", datetime.datetime.now(pytz.utc))
    formatted_prev_time = prev_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    formatted_current_time = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    url = 'https://apidemo.humanforce.com/api/1.0/rosterItems'
    headers = {
        'Accept': 'application/json',
        'Authorization': token
    }
    params = {
        'dateMin': formatted_prev_time,
        'dateMax': formatted_current_time
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data_list = response.json()
        # print(data_list)
        for roster_data in data_list:
    
            roster_data["Roster_Start_Time"] = roster_data.pop("StartTime")
            roster_data["Roster_End_Time"] = roster_data.pop("EndTime")
    
            del roster_data["RosterBaseGuidKey"]
            del roster_data["GuidKey"]
            del roster_data["LastEdit"]
            del roster_data["DateActual"]
            roster_data["Employee_Code"] = None
            roster_data["Employee_Name"] = None
            if roster_data.get("Employee") is not None:
                roster_data["Employee_Code"] = roster_data["Employee"]["EmployeeCode"]
                roster_data["Employee_Name"] = roster_data["Employee"]["Name"]
            del roster_data["Employee"]
    
            del roster_data["LastEditBy"]
            
            roster_data["Gross_Minutes"] = roster_data.pop("GrossMinutes")
            roster_data["Time_Of_Break"] = roster_data.pop("TimeOfBreak")
            roster_data["Break_Minutes"] = roster_data.pop("BreakMinutes")
            roster_data["Net_Mintes"] = roster_data.pop("NetMinutes")
    
            roster_data["Location_Name"] = roster_data["Location"]["Name"]
            del roster_data["Location"]
            
            roster_data["Department_Name"] = roster_data["Department"]["Name"]
            del roster_data["Department"]
            
            roster_data["Role_Name"] = roster_data["Role"]["Name"]
            del roster_data["Role"]
    
            roster_data["Roster_Cost"] = roster_data.pop("Cost")
            del roster_data["Period"]
            del roster_data["Area"]
            del roster_data["Event"]
            del roster_data["EventFunction"]
            del roster_data["ShiftType"]
            del roster_data["ShiftDefinition"]
            del roster_data["Confirmed"]
            del roster_data["Changed"]
            del roster_data["NonAttended"]
            del roster_data["Published"]
            del roster_data["PublishedBy"]
            del roster_data["PublishedAt"]
    
            del roster_data["ReadOnly"]
            del roster_data["ReadOnlySetBy"]
            del roster_data["ReadOnlySetAt"]
            del roster_data["RosterData1"]
            del roster_data["RosterData2"]
            del roster_data["RosterData3"]
            del roster_data["Deleted"]
            del roster_data["Comments"]
    
    
        formatted_current_time_filename = current_time.strftime('%Y-%m-%dT%H-%M-%S.%f')[:-3] + 'Z'
        file_path = f"hospitality-chatbot-humanforce-rosters/year={current_time.year}/month={current_time.month}/hospitality-chatbot-humanforce-rosters-{formatted_current_time_filename}.json"

        # Write the list to the file in JSON format
        json_data = json.dumps(data_list)
        
        s3.put_object(Bucket=bucket_name, Key=file_path, Body=json_data)
    else:
        print("Failed to retrieve data. Status code:", response.status_code)
    print("end humanforce_rosters: ", datetime.datetime.now(pytz.utc))
def aristocrat(s3, bucket_name, prev_time, current_time):
    # Function to fetch aristocrat data from aristocrat API and save it to S3
    print("start aristocrat: ", datetime.datetime.now(pytz.utc))
    file_key = 'hospitality-chatbot-aristocrat-src/test.csv'
    obj = s3.get_object(Bucket=bucket_name, Key=file_key)
    df = pd.read_csv(obj['Body'])
    
    # Extract the desired properties
    extracted_data = df[['Venue', 'Date', 'Time', 'EGM Turnover', 'EGM Wins']]
    extracted_data = extracted_data.rename(columns={'Venue': 'Venue_Id'})
    
    # Convert the extracted data to a CSV string
    csv_buffer = StringIO()
    extracted_data.to_csv(csv_buffer, index=False)
    
    # Write the extracted data to a new CSV file in S3
    output_file_key = f'hospitality-chatbot-aristocrat/{current_time.year}/{current_time.month}/{current_time.day}/output.csv'
    s3.put_object(Bucket=bucket_name, Key=output_file_key, Body=csv_buffer.getvalue())
    print("end aristocrat: ", datetime.datetime.now(pytz.utc))

def lambda_handler(event, context):
    
    # Main Lambda function to orchestrate the data retrieval and processing
    gmt = pytz.timezone('GMT')
    
    # Get the current time in GMT timezone with millisecond accuracy
    current_time = datetime.datetime.now(tz=gmt)
    print ("current time: ", current_time)
    # # # Get Token
    swiftpos_token = get_swiftpos_token()
    
    
    s3 = boto3.client('s3')
    bucket_name = os.environ["bucket_name"] # already created on S3
    
    # Read the time from the text file in S3
    swiftpos_file_key = 'prev_time_record/swiftpos_prev_time.txt'
    date_format = '%Y-%m-%d %H:%M:%S.%fZ'
    
    response = s3.get_object(Bucket=bucket_name, Key=swiftpos_file_key)
    swiftpos_prev_time_str = response['Body'].read().decode('utf-8').strip()
    
    # Convert the string to a datetime object
    swiftpos_prev_time = datetime.datetime.strptime(swiftpos_prev_time_str, date_format)
    swiftpos_prev_time = swiftpos_prev_time.replace(tzinfo=gmt)
    
    
    print("swiftpos_prev_time: ", swiftpos_prev_time)
    
    time_diff_salesforce = current_time - swiftpos_prev_time
    if time_diff_salesforce > datetime.timedelta(minutes=15) or time_diff_salesforce < datetime.timedelta(seconds = 0):
        swiftpos_prev_time = current_time - datetime.timedelta(minutes=15)
        
    # test case to collect data
    b_test = True
    if b_test == False:
        formatted_current_time = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
        # Save the current time to the text file in S3
        s3.put_object(Bucket=bucket_name, Key=swiftpos_file_key, Body=formatted_current_time + 'Z')
        swiftpos_sales(swiftpos_token, s3, bucket_name, swiftpos_prev_time, current_time)
        
        # aristocrat(s3, bucket_name, prev_time, current_time)
        # swiftpos_member_transactions(swiftpos_token, s3, bucket_name, swiftpos_prev_time, current_time)
        # swiftpos_products(swiftpos_token, s3, bucket_name, swiftpos_prev_time, current_time)
       
    else:
            
        tmp_time = swiftpos_prev_time
        
        for i in range(24 * 2 * 10):
            
            current_time = tmp_time - datetime.timedelta(minutes = 30 * i)
            
            swiftpos_prev_time = current_time - datetime.timedelta(minutes=30)
    
            formatted_current_time = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
            # Save the current time to the text file in S3
            s3.put_object(Bucket=bucket_name, Key=swiftpos_file_key, Body=formatted_current_time + 'Z')
    
            swiftpos_sales(swiftpos_token, s3, bucket_name, swiftpos_prev_time, current_time)
        
    return {
        "statusCode": 200,
        "body": "\"Hi, this is test from Lambda!\""
    }
