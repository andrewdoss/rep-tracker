import logging
import os
import boto3
from botocore.exceptions import ClientError


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