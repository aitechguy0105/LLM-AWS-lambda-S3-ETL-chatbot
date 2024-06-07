import sys
import logging
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import regexp_extract, input_file_name, to_timestamp, col, explode

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
df = spark.read.json("s3://hospitality-chatbot-058264544364-us-east-1/hospitality-chatbot-swiftpos-sales/year=*/month=*/day=*/")

# Use regex to extract year, month, and day from the file path
file_path_col = input_file_name()
df = df.withColumn("year", regexp_extract(file_path_col, r"/year=(\d{4})/", 1).cast('int')) \
       .withColumn("month", regexp_extract(file_path_col, r"/month=(\d{1,2})/", 1).cast('int')) \
       .withColumn("day", regexp_extract(file_path_col, r"/day=(\d{1,2})/", 1).cast('int'))

# Log the extracted year, month, and day values
year_val = df.select('year').first()['year']
month_val = df.select('month').first()['month']
day_val = df.select('day').first()['day']
logger.info(f"Year: {year_val}")
logger.info(f"Month: {month_val}")
logger.info(f"Day: {day_val}")

# Explode the sales array column to access its fields
df = df.withColumn("sales_exploded", explode(col("Sales")))

df = df.withColumn("sales_exploded", 
    col("sales_exploded").withField(
        "Transaction_Date", 
        to_timestamp(col("sales_exploded.Transaction_Date"), "yyyy-MM-dd'T'HH:mm:ss.SSS")
    )
)

# Select only the necessary columns along with 'year', 'month', 'day', and reorder them
other_columns = [c for c in df.columns if c not in {'year', 'month', 'day', 'Sales', 'sales_exploded'}]
df = df.select('year', 'month', 'day', *other_columns, col("sales_exploded").alias("Sales_Details"))


# Write the data to Parquet format, preserving the partition structure
output_path = "s3://hospitality-chatbot-058264544364-us-east-1/hospitality-chatbot-swiftpos-sales-parquet/"
df.write.mode("append").partitionBy("year", "month", "day").option("compression", "snappy").parquet(output_path)

job.commit()
