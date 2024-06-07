import boto3
from botocore.config import Config
import botocore.exceptions
from boto3.dynamodb.conditions import Key
from langchain.llms.bedrock import Bedrock
from langchain.embeddings import BedrockEmbeddings
import logging 
import json
import os,sys
import re
import uvicorn  # ASGI server for running the app
sys.path.append("/home/ec2-user/SageMaker/llm_bedrock_v0/")
import time
import pandas as pd
import io
from boto_client import Clientmodules
from llm_basemodel import LanguageModel
from athena_execution import AthenaQueryExecute
# from openSearchVCEmbedding import EmbeddingBedrockOpenSearch
import json
from fastapi import FastAPI, Query, Header, HTTPException, Depends, Request
import datetime
import pytz
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure the middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

# Set the AWS credentials in the code

USER_POOL_ID = 'us-east-1_IHihTM4ry'

def get_user_info_from_token(access_token):
    client = boto3.client('cognito-idp',region_name='us-east-1')

    user_info = client.get_user(
        AccessToken=access_token
    )

    return user_info
session = boto3.session.Session()

glue_client = session.client('glue')
bedrock_client = session.client('bedrock')
print(bedrock_client.list_foundation_models()['modelSummaries'][0])


rqstath=AthenaQueryExecute()
# ebropen=EmbeddingBedrockOpenSearch()


class RequestQueryBedrock:
    def __init__(self):
        # self.model_id = "anthropic.claude-v2"
        self.bedrock_client = Clientmodules.createBedrockRuntimeClient()
        self.language_model = LanguageModel(self.bedrock_client)
        self.llm = self.language_model.llm
        
    # def getOpenSearchEmbedding(self,index_name,user_query):

        # vcindxdoc=ebropen.getDocumentfromIndex(index_name=index_name)
        # documnet=ebropen.getSimilaritySearch(user_query,vcindxdoc)
        
        # return ebropen.format_metadata(documnet)
    
    def answer(self, prompt) -> str:
        
        answer = self.llm.predict(prompt)
        
        return answer
    
    def generate_sql(self,prompt, max_attempt=4) ->str:
            """
            Generate and Validate SQL query.

            Args:
            - prompt (str): Prompt is user input and metadata from Rag to generating SQL.
            - max_attempt (int): Maximum number of attempts correct the syntax SQL.

            Returns:
            - string: Sql query is returned .
            """
            attempt = 0
            error_messages = []
            prompts = [prompt]

            while attempt < max_attempt:
                logger.info(f'Sql Generation attempt Count: {attempt+1}')
                try:
                    logger.info(f'we are in Try block to generate the sql and count is :{attempt+1}')
                    generated_sql = self.llm.predict(prompt)
                    print("==================generated sql in try block:", generated_sql)
                    
                    if generated_sql.find("NO") !=-1:
                        
                        return {
                            "status": "error",
                            "message": generated_sql.split("NO")[1]
                        }
                    
                    if generated_sql.find("```") == -1:
                        query_str = generated_sql
                    else :
                        query_str = generated_sql.split("```")[1]
                    query_str = " ".join(query_str.split("\n")).strip()
                    sql_query = query_str[3:] if query_str.startswith("sql") else query_str
                    print("=================Ëxtracted SQL", sql_query)

                    # return sql_query
                    syntaxcheckmsg=rqstath.syntax_checker(sql_query)
                    if syntaxcheckmsg=='Passed':
                        logger.info(f'syntax checked for query passed in attempt number :{attempt+1}')
                        return {
                                "status": "success",
                                "message": sql_query
                        }

                    else:
                        prompt = f"""{prompt}
                        This is syntax error: {syntaxcheckmsg}. 
                        To correct this, please generate an alternative SQL query which will correct the syntax error.
                        The updated query should take care of all the syntax issues encountered.
                        Follow the instructions mentioned above to remediate the error. 
                        Update the below SQL query to resolve the issue:
                        {sql_query}
                        Make sure the updated SQL query aligns with the requirements provided in the initial question.
                        Only give me SQL query with Athena syntax after this prompt and nothing else.
                        Updated SQL Query:
                        """
                        prompts.append(prompt)
                        attempt += 1
                except Exception as e:
                    logger.error('FAILED')
                    msg = str(e)
                    print("==================Failed Message", msg)
                    error_messages.append(msg)
                    attempt += 1
            return {
                "status": "error",
                "message": error_messages
            }

rqst=RequestQueryBedrock()
# index_name = 'prompt-index'

response = glue_client.get_databases()


databases = response['DatabaseList']

database_name = 'hospitaliy_chatbot_data_catalog'

response = glue_client.get_tables(DatabaseName=database_name)
tables = response['TableList']

# Print the names of the tables
database_info = {}
table_info = []
for table in tables:
    new_table = {}
    new_table["TableName"] = table["Name"]
    new_table["Columns"] = table['StorageDescriptor']['Columns']
    table_info.append(new_table)
# print(table_info)
database_info["DatabaseName"] = database_name
database_info["Tables"] = table_info
database_json_string = json.dumps(database_info)
print("=====================global",database_json_string)

def userinput(user_query):
    utc_now = datetime.datetime.now(pytz.utc)
    
    final_prompt = f"""
# Role: You are a SQL developer creating queries for Amazon Athena.

# Task: Generate SQL queries to return data based on the provided schema and user request. Also, returns SQL query created.

1. Query Decomposition and Understanding:
   - Analyze the user’s request to understand the main objective.
   - Break down reqeusts into sub-queries that can each address a part of the user's request, using the schema provided.

2. SQL Query Creation:
   - For each sub-query, use the relevant tables and fields from the provided schema.
   - Construct SQL queries that are precise and tailored to retrieve the exact data required by the user’s request.
3. It is important that the SQL query complies with Athena syntax. During join if column name are same please use alias ex llm.customer_id in select statement. It is also important to respect the type of columns: if a column is string, the value should be enclosed in quotes. If you are writing CTEs then include all the required columns. While concatenating a non string column, make sure cast the column to string. Make sure use database name correctly provided in database info. For date columns comparing to string , please cast the string input.

# Example of User questions and generated queries
    
    1.
    User Question: Show me total beverage sales cost from 1 May to 17 May in venue id 1?
    Generated Query: SELECT SUM (unnested_items.Total_Inc) AS beverage_sale_inc 
                        FROM hospitaliy_chatbot_data_catalog.hospitality_chatbot_swiftpos_sales_parquet, UNNEST(sales_details.Items) AS t (unnested_items)  
                        WHERE sales_details.Transaction_Date BETWEEN timestamp '2024-05-01 00:00:00' AND timestamp '2024-05-17 23:59:59' AND unnested_items.Master_Group_Id = 1 AND venue_id = 1
    2.
    User Question: What is daily sales cost vs timesheet wages from 2024.5.1 to 2024.5.17 in venue_id 2?
    Generated Query: 
      WITH filtered_sales AS (
        SELECT
          DATE(s.sales_details.Transaction_Date) as sale_date,
          SUM(item.Total_Inc) as total_daily_sales_inc
        FROM
          hospitaliy_chatbot_data_catalog.hospitality_chatbot_swiftpos_sales_parquet s
        CROSS JOIN UNNEST(s.sales_details.Items) AS t(item) -- Unnesting here
        WHERE
          s.venue_id = 2
          AND s.sales_details.Transaction_Date BETWEEN timestamp '2024-05-01 00:00:00.000' AND timestamp '2024-05-17 23:59:59.999'
        GROUP BY
          DATE(s.sales_details.Transaction_Date)
      ),
      filtered_timesheets AS (
        SELECT
          DATE(timesheet_date) as timesheet_date,
          SUM(timesheet_cost) as total_daily_timesheet_cost
        FROM
          hospitaliy_chatbot_data_catalog.hospitality_chatbot_humanforce_timesheets_parquet
        WHERE
          location_name = (SELECT venue_name FROM hospitaliy_chatbot_data_catalog.hospitality_chatbot_swiftpos_sales_parquet WHERE venue_id = 2 LIMIT 1)
          AND timesheet_date BETWEEN timestamp '2024-05-01 00:00:00.000' AND timestamp '2024-05-17 23:59:59.999'
        GROUP BY
          DATE(timesheet_date)
      )
      SELECT
        COALESCE(fs.sale_date, ft.timesheet_date) as date,
        COALESCE(fs.total_daily_sales_inc, 0) AS sales,
        COALESCE(ft.total_daily_timesheet_cost, 0) AS wages
      FROM
        filtered_sales fs
      FULL JOIN
        filtered_timesheets ft
      ON
        fs.sale_date = ft.timesheet_date
      ORDER BY
        date ASC;
      
      3.
      User Question: What is hourly roster vs timesheet wages in May 17, venue  Bella Vista Hotel?
      Generated Query: 
        WITH filtered_rosters AS (
          SELECT
            roster_start_time as actual_start_time,
            roster_end_time as actual_end_time,
            roster_cost,
            -- Calculate the duration in hours, ensuring at least 1 hour is counted
            GREATEST(1, DATE_DIFF('hour',roster_start_time, roster_end_time)) AS total_hours_difference
          FROM
            hospitaliy_chatbot_data_catalog.hospitality_chatbot_humanforce_rosters_parquet
          WHERE
            location_name = 'Bella Vista Hotel'             
            AND roster_start_time <= timestamp '2024-05-07 23:59:59.999'
            AND roster_end_time >= timestamp '2024-05-07 00:00:00.000'
        ),
        hourly_rosters AS (
          SELECT
            DATE_FORMAT(sequence_time, '%Y-%m-%d %H:00:00') as covered_hour,
            SUM(fr.roster_cost / fr.total_hours_difference) as hourly_cost
          FROM
            filtered_rosters fr
          CROSS JOIN
            UNNEST(SEQUENCE(fr.actual_start_time , fr.actual_end_time - INTERVAL '1' HOUR, INTERVAL '1' HOUR)) AS t(sequence_time)
          GROUP BY DATE_FORMAT(sequence_time, '%Y-%m-%d %H:00:00')
        ),
        filtered_timesheets AS (
          SELECT
            COALESCE(clocked_start_time, pay_start_time) as actual_start_time,
            COALESCE(clocked_end_time, pay_end_time) as actual_end_time,
            timesheet_cost,
            -- Calculate the duration in hours, ensuring at least 1 hour is counted
            GREATEST(1, DATE_DIFF('hour', COALESCE(clocked_start_time, pay_start_time), COALESCE(clocked_end_time, pay_end_time))) AS total_hours_difference
          FROM
            hospitaliy_chatbot_data_catalog.hospitality_chatbot_humanforce_timesheets_parquet
          WHERE
            location_name = 'Bella Vista Hotel'               
            AND COALESCE(clocked_start_time, pay_start_time) <= timestamp '2024-05-07 23:59:59.999'
            AND COALESCE(clocked_end_time, pay_end_time) >= timestamp '2024-05-07 00:00:00.000'
        ),
        hourly_timesheets AS (
          SELECT
            DATE_FORMAT(sequence_time, '%Y-%m-%d %H:00:00') as covered_hour,
            SUM(ft.timesheet_cost / ft.total_hours_difference) as hourly_cost
          FROM
            filtered_timesheets ft
          CROSS JOIN
            UNNEST(SEQUENCE(ft.actual_start_time, ft.actual_end_time - INTERVAL '1' HOUR, INTERVAL '1' HOUR)) AS t(sequence_time)
          GROUP BY (DATE_FORMAT(sequence_time, '%Y-%m-%d %H:00:00'))
        )
        SELECT
          COALESCE(hr.covered_hour, ht.covered_hour) as hour,
          COALESCE(ht.hourly_cost, 0) AS timesheet_wages,
          COALESCE(hr.hourly_cost, 0) AS roster_wages
        FROM
          hourly_rosters hr
        FULL JOIN
          hourly_timesheets ht
        ON
          hr.covered_hour = ht.covered_hour
        ORDER BY
          hour ASC;
      4.
      User Question: What is  timesheet vs roster wages from 2023.12.1 to 2024.5.17, in venue Bella Vista Hotel, totally?
      Generated Query:
        WITH filtered_timesheets AS (
          SELECT
            SUM(timesheet_cost) as total_timesheet_cost

          FROM
            hospitaliy_chatbot_data_catalog.hospitality_chatbot_humanforce_timesheets_parquet
          WHERE
            location_name = 'Bella Vista Hotel'
            AND timesheet_date BETWEEN timestamp '2023-12-01 00:00:00.000' AND timestamp '2024-05-17 23:59:59.999'
        ),
        filtered_rosters AS (
          SELECT
            SUM(roster_cost) as total_roster_cost
          FROM
            hospitaliy_chatbot_data_catalog.hospitality_chatbot_humanforce_rosters_parquet
          WHERE
            location_name = 'Bella Vista Hotel'
            AND roster_start_time BETWEEN timestamp '2023-12-01 00:00:00.000' AND timestamp '2024-05-17 23:59:59.999'

        )
        SELECT
          COALESCE(ft.total_timesheet_cost, 0) AS timesheet_wages,
          COALESCE(fr.total_roster_cost, 0) AS roster_wages
        FROM
          filtered_timesheets ft
        CROSS JOIN
          filtered_rosters fr
      User Question: List my top 10 beverage products sold over the past 3 months.
      Generated Query:
        SELECT * FROM (
          SELECT unnested_items.Product_Name, SUM(unnested_items.Quantity) AS total_quantity   FROM hospitaliy_chatbot_data_catalog.hospitality_chatbot_swiftpos_sales_parquet
          CROSS JOIN UNNEST(sales_details.Items) AS t (unnested_items)   WHERE unnested_items.Master_Group_Id = 1     
          AND sales_details.Transaction_Date BETWEEN date_add('month', -3, current_timestamp) AND current_timestamp   
          GROUP BY unnested_items.Product_Name 
        ) 
        ORDER BY total_quantity DESC LIMIT 10
# Database information:
{database_json_string}
# Additional Database Tables Explanation:
    1. hospitality_chatbot_swiftpos_sales_parquet
    This table includes infomration about the sales data, like transaction date, sales items, cost so on. You could use this table to get sales information.
    - Here, `venue_name` is equal to `location_name` in table `hospitality_chatbot_swiftpos_timesheets_parquet` and `hospitality_chatbot_swiftpos_rosters_parquet` and `venue_id` is id for `venue_name`.
    - `Member_Id`, `Member_Name`, `Member_Account_Balance`, `Member_Points_Balance` properties in `sales_details` field are customer id, customer name, customer account balance and customer points balance.
    - In `sales_details` field, you can find customer id, name, their transaction details, what items they bought, how much customer spends per each item.
     * Please use these properties if you require customer related informations.
    2. hospitality_chatbot_swiftpos_timesheets_parquet
    This table includes information of human timesheets data like timesheet start time, end time, pay start time, end time, timesheet cost so on. You could use this information to get actual wages information.
    3. hospitality_chatbot_swiftpos_rosters_parquet
    This table includes information of human rosters data like roster start time, end time, roster cost so on. You could use this information to get roster wages information.

# Critical:
    1. Only give me SQL query with Athena syntax after this prompt and nothing else.
    2. SQL query should extract all columns data that can be useful to answer the User Question.
    3. If user does not provide detail information, but you can guess it in correct way, please use default options.
    4. If you cannot make SQL query with provided info, only answer NO at first 2 Characters and from next line, provide why you are not able to understand User Question.
    5. Please use this information for today and current time. 
      a. today and current time : {utc_now}.
        - For instance, today is May 15, user question include expression like last 5 days, the date range would be from May 11  to May 15.
    6. Please make sure to use entity name like location name, product name, item name AS IS in the user query. Do not change it in SQL query.
    7. When the user request includes long period information, more than one month, please make query in total mode, not houly or daily mode.
    8. If user request requires customer-level information, please use `Member_Id`, `Member_Name`, `Member_Account_Balance`, `Member_Points_Balance` properties in `sales_details` field from table `hospitality_chatbot_swiftpos_sales_parquet`.
     - There's no customer-level table in database, so you should use this information instead. You can extract customer-level information from this sales table.
       So first unnest sales_details field then use aggregate function or group by operator to get customer-level information.
User Question: 
    {user_query}
Generated Query:
"""    
#     4. Write the Athena syntax SQL query that will retrieve all the relevant columns from the identified table(s).
# # exmaple rows in tables:    
#     {example_rows}
    # print("==============================final prompt: ", final_prompt)
    print("============================== generating sql query")
    answer = rqst.generate_sql(final_prompt)
    return answer

def get_answer(user_query, context):
    prompt = f"""
        You are a helpful data analysis and financial planning assistant. You should answer the user question provided in a conversational and natural tone. 
        Here is user question:
        <user_question>{user_query}</user_question>
        Here is necessary context:
        <context>{context}</context>
        # Follow the rules below:

          1. Only answer the user question with the given context.
          2. Provide responses naturally like human and write related data in context. 
           - If provided context is not sufficient, please DO answer to user question based on context. It is ok if your answer is not perfect for user question.
          3. Keep the focus on the user question and avoid mentioning any internal mechanisms.
          4. If User Question include specific venue name or id, and provided context is not include relevant information about venue name or id in columns, please assume context is for given venue name or id. 
          5. Do not write your answer inside any specific tags or formats.
            - This is wrong format: <response> [your answer] </response>
                    
        Answer:
    """
    
    answer = rqst.answer(prompt)
    
    return answer

@app.post("/chat")
async def chat_with_teacher_agent(request: Request):
  try:
        
    id_token = request.headers.get("id_token")
    access_token = request.headers.get("access_token")
    data = await request.json()
    user_query = data["query"]
    print("=========user_query: ", user_query)
    print("====================start================")
    user_info = get_user_info_from_token(access_token)
    print('==========user_info', user_info)
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # Substitute your table name here
    table = dynamodb.Table('user_role')
    
    result = table.query(
        KeyConditionExpression=Key('username').eq(user_info['UserAttributes'][0]['Value'])
    )
    print('=============dynamodb user info', result)
    role =  result['Items'][0]['role']
    print('==========role', role)
    
    if role == 'analysis' or role == 'admin':
      res = userinput(user_query)
    else:
        return {'error': 'Permission Denied'},
  

    print("Response : ", res)

    if res["status"] == "success":
        result=rqstath.execute_query(res["message"])
        # res["table"] = result.to_json(orient='records')
        answer = get_answer(user_query, result.to_string(index = False))
        res["message"] = answer
  
    return res
  except Exception as e:
    return {
        "error": e
    }

# Main entry point to run the app with Uvicorn when script is executed directly
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
    # uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)


        
    


