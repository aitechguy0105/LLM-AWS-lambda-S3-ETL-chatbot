import logging 
import json
import os,sys
import re
# sys.path.append("/home/ec2-user/SageMaker/llm_bedrock_v0/")
from boto_client import Clientmodules
import time
import pandas as pd
import io

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class AthenaQueryExecute:
    def __init__(self):
        self.glue_databucket_name='llm-athena-output-058264544364-us-east-1'
        self.athena_client=Clientmodules.createAthenaClient()
        self.s3_client=Clientmodules.createS3Client()
    
    def execute_query(self, query_string):
        # print("Inside execute query", query_string)
        result_folder='athena_output'
        result_config = {"OutputLocation": f"s3://{self.glue_databucket_name}/{result_folder}"}
        query_execution_context = {
            "Catalog": "AwsDataCatalog",
        }
        print(f"Executing: {query_string}")
        response = self.athena_client.start_query_execution(
            QueryString=query_string,
            ResultConfiguration=result_config,
            QueryExecutionContext=query_execution_context,
        )

        query_execution_id = response['QueryExecutionId']
        query_status = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        while query_status['QueryExecution']['Status']['State'] in ['QUEUED', 'RUNNING']:
            query_status = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            time.sleep(1)
        
        file_name = f"{result_folder}/{query_execution_id}.csv"
        logger.info(f'checking for file :{file_name}')
        

        print(f"Calling download fine with params {file_name}, {result_config}")
        obj = self.s3_client.get_object(Bucket= self.glue_databucket_name , Key = file_name)
        df = pd.read_csv(io.BytesIO(obj['Body'].read()), encoding='utf8')
        # print(df.head())
        return df
        
    def syntax_checker(self,query_string):
        # print("Inside execute query", query_string)
        query_result_folder='athena_query_output/'
        query_config = {"OutputLocation": f"s3://{self.glue_databucket_name}/{query_result_folder}"}
        query_execution_context = {
            "Catalog": "AwsDataCatalog",
        }
        # query_string="Explain  "+query_string
        print(f"=========Executing for syntax check: {query_string}")
        try:
            print(" I am checking the syntax here")
            response = self.athena_client.start_query_execution(
                QueryString=query_string,
                ResultConfiguration=query_config,
                QueryExecutionContext=query_execution_context,
            )

            query_execution_id = response['QueryExecutionId']
            query_status = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            while query_status['QueryExecution']['Status']['State'] in ['QUEUED', 'RUNNING']:
                query_status = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
                time.sleep(1)
            
            print(f"============= results: {query_status}")
            status=query_status['QueryExecution']['Status']
            print("==============Status :",status)
            if status['State']=='SUCCEEDED':
                return "Passed"
            else:  
                print(query_status['QueryExecution']['Status']['StateChangeReason'])
                errmsg=query_status['QueryExecution']['Status']['StateChangeReason']
                print("=========== StateChangeReason    errmsg: ", errmsg)
                return errmsg
            # return results
        except Exception as e:
            print("Error in exception")
            msg = str(e)
            print("================Exception Error", msg)