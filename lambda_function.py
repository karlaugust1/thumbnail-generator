from datetime import datetime
import boto3
from io import BytesIO
from PIL import Image, ImageOps
import os
import uuid
import json

s3 = boto3.client('s3')
size = int(os.environ['THUMBNAIL_SIZE'])
dbtable = str(os.environ['DYNAMODB_TABLE'])
dynamodb = boto3.resource("dynamodb", region_name=str(os.environ["REGION_NAME"]))

def lambda_handler(event, context):
    #parse event
    print('EVENT: ', event)

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    img_size = event['Records'][0]['s3']['object']['size']

    if (not key.endswith("_thumbnail.png")):
        image = get_s3_image(bucket, key)
    
        thumbnail = image_to_thumbnail(image)
        thumbnail_key = new_filename(key)

        url = upload_to_s3(bucket, thumbnail_key, thumbnail, img_size)

        return url

def get_s3_image(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    imagecontent = response['Body'].read()

    file = BytesIO(imagecontent)
    img = Image.open(file)
    return img

def image_to_thumbnail(image):
    return ImageOps.fit(image, (size, size), Image.ANTIALIAS)

def new_filename(key):
    key_split = key.rsplit('.', 1)
    return key_split[0] + "_thumbnail.png"

def upload_to_s3(bucket, key, image, image_size):
    out_thumbnail = BytesIO()
    image.save(out_thumbnail, 'PNG')
    out_thumbnail.seek(0)
    response = s3.put_object(
        ACL='public-read',
        Body=out_thumbnail,
        Bucket=bucket,
        ContentType='image/png',
        Key=key
    )

    print("RESPONSE", response)

    url = '{}/{}/{}'.format(s3.meta.endpoint_url, bucket, key)
    
    save_thumbnail(url_path=url, img_size=image_size, file_name=key, thumbnail_url=url)

    return url

def save_thumbnail(url_path, img_size, file_name, thumbnail_url):
    toint = float(img_size*0.53)/1000
    table = dynamodb.Table(dbtable)
    response = table.put_item(
        Item={
            'id': str(uuid.uuid4()),
            'file_name': str(file_name),
            'thumbnail_url': str(thumbnail_url),
            'size': str(img_size) + str('KB'),
            'approx_reduced_size': str(toint) + str('KB'),
            'created_at': str(datetime.now()),
            'updated_at': str(datetime.now())
        }
    )