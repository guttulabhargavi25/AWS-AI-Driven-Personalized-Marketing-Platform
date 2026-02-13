import os
import boto3
from moto import mock_aws

# -------------------------------------------------
# MOCK AWS CREDENTIALS (REQUIRED)
# -------------------------------------------------

os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["SNS_TOPIC_ARN"] = "test-topic"

# -------------------------------------------------
# START MOTO
# -------------------------------------------------

mock = mock_aws()
mock.start()

# -------------------------------------------------
# CREATE MOCK AWS RESOURCES FIRST
# -------------------------------------------------

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
sns = boto3.client("sns", region_name="us-east-1")

# USERS TABLE
dynamodb.create_table(
    TableName="users",
    KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
    AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
    ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
)

# CAMPAIGNS TABLE
dynamodb.create_table(
    TableName="campaigns",
    KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
    AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
    ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
)

# CUSTOMERS TABLE
dynamodb.create_table(
    TableName="customers",
    KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
    AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
    ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
)

# SNS
topic = sns.create_topic(Name="test-topic")
os.environ["SNS_TOPIC_ARN"] = topic["TopicArn"]

# -------------------------------------------------
# IMPORT FLASK APP *AFTER* MOCK SETUP
# -------------------------------------------------

from aws_app import app   # IMPORTANT: import AFTER tables exist

# -------------------------------------------------
# RUN FLASK (NO RELOADER)
# -------------------------------------------------

if __name__ == "__main__":
     # Get your local IP (run 'ip addr show' or 'ifconfig' to find it, e.g., 192.168.1.100)
    print("🚀 Running Flask with Moto mocks at http://0.0.0.0:5000")
    print("Accessible globally on your network at http://YOUR_LOCAL_IP:5000 (replace YOUR_LOCAL_IP)")
    print("Example: http://192.168.1.100:5000")
    print("Allow port 5000 in firewall if needed. Press Ctrl+C to stop.")
    try:
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
     mock.stop()


