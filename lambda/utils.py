import hashlib
import logging
import os
from base64 import b64encode

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()
DEVICE_ID_SALT = os.getenv("DEVICE_ID_SALT")

DEFAULT_TIMEZONE = "US/Pacific"
SINGULAR_TO_PLURAL = {
    "pushup": "pushups",
    "squat": "squats",
    "dip": "dips",
    "row": "rows",
    "pullup": "pullups",
}
PLURAL_TO_SINGULAR = {v: k for k, v in SINGULAR_TO_PLURAL.items()}


def normalize_exercise_name(name: str, form: str):
    if form == "singular":
        return PLURAL_TO_SINGULAR.get(name, name)
    if form == "plural":
        return SINGULAR_TO_PLURAL.get(name, name)
    raise ValueError(f"Unrecognized normalization form {form}.")
    

# TODO: generalize this caching pattern across timezone and device_id hash lookup
def get_user_timezone(handler_input):
    session_attributes = handler_input.attributes_manager.session_attributes
    try:
        return session_attributes["user_timezone"]
    except KeyError:
        device_id = handler_input.request_envelope.context.system.device.device_id
        user_preferences_client = handler_input.service_client_factory.get_ups_service()
        user_timezone = user_preferences_client.get_system_time_zone(device_id)
        session_attributes["user_timezone"] = user_timezone
        return user_timezone
        
        
def get_hashed_device_id(handler_input):
    session_attributes = handler_input.attributes_manager.session_attributes
    try:
        return session_attributes["device_id_hash"]
    except KeyError:
        device_id = handler_input.request_envelope.context.system.device.device_id
        logger.info(device_id)
        hashed_device_id = hash_device_id(device_id)
        session_attributes["device_id_hash"] = hashed_device_id
        return hashed_device_id
    

def hash_device_id(device_id: str) -> str:
    """Generate a short hash of device id that also doubles as a query param"""
    m = hashlib.sha256()
    m.update(DEVICE_ID_SALT.encode())
    m.update(device_id.encode())
    s = b64encode(m.digest()[:4]).decode().replace("=", "")
    print(s)
    # Make URL safe
    for have, want in [("+", "-"), ("/", "_")]:
        s = s.replace(have, want)
    return s


def create_presigned_url(object_name):
    """Generate a presigned URL to share an S3 object with a capped expiration of 60 seconds

    :param object_name: string
    :return: Presigned URL as string. If error, returns None.
    """
    s3_client = boto3.client('s3',
                             region_name=os.environ.get('S3_PERSISTENCE_REGION'),
                             config=boto3.session.Config(signature_version='s3v4',s3={'addressing_style': 'path'}))
    try:
        bucket_name = os.environ.get('S3_PERSISTENCE_BUCKET')
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': object_name},
                                                    ExpiresIn=60*1)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response
    
    
def put_s3_object(object_name: str, data: bytes) -> None:
    """Puts an object in the default s3 bucket"""
    sts_client = boto3.client('sts')
    assumed_role_object = sts_client.assume_role(
        RoleArn="arn:aws:iam::937784245937:role/alexa-s3-access",
        RoleSessionName="AssumeRoleSession1",
    )
    credentials = assumed_role_object['Credentials']
    s3_client = boto3.client(
        's3',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        region_name='us-west-2',
    )

    try:
        response = s3_client.put_object(
            Key=f"public/{object_name}",
            Bucket='rep-tracker',
            Body=data,
        )
    except ClientError as e:
        logging.error(e)
        return None
    return response
    return response