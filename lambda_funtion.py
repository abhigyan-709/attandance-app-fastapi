import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

    # get the length and width paramters from the event object.
    # the runtime converts the event object to a dictionary

    length = event['length']
    width = event['width']

    area = calculate_area(length, width)

    print(f"The area is {area}")

    logger.info(f"Cloudwatch logs group : {context.log_group_name}")

    # return the area as a dictionary in JSON format

    data = {"area": area}
    return json.dumps(data)

def calculate_area(length, width):
    return length * width
