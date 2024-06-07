import sys
import logging
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import regexp_extract, input_file_name, to_timestamp, col

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME'])

# Configure logging
logging.basicConfig()
logger = logging.getLogger(__name__)

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read the latest JSON data from the S3 bucket
df = spark.read.json("s3://hospitality-chatbot-058264544364-us-east-1/hospitality-chatbot-humanforce-rosters/year=*/month=*/")

# Use regex to extract year, month, and day from the file path
file_path_col = input_file_name()
df = df.withColumn("year", regexp_extract(file_path_col, r"/year=(\d{4})/", 1).cast('int')) \
       .withColumn("month", regexp_extract(file_path_col, r"/month=(\d{1,2})/", 1).cast('int'))
df = df.withColumn("Roster_Start_Time", to_timestamp(col("Roster_Start_Time"), "yyyy-MM-dd'T'HH:mm:ss"))
df = df.withColumn("Roster_End_Time", to_timestamp(col("Roster_End_Time"), "yyyy-MM-dd'T'HH:mm:ss"))

# Log the extracted year, month, and day values
year_val = df.select('year').first()['year']
month_val = df.select('month').first()['month']
logger.info(f"Year: {year_val}")
logger.info(f"Month: {month_val}")


# Write the data to Parquet format, preserving the partition structure
output_path = "s3://hospitality-chatbot-058264544364-us-east-1/hospitality-chatbot-humanforce-rosters-parquet/"
df.write.mode("append").partitionBy("year", "month").option("compression", "snappy").parquet(output_path)

job.commit()
