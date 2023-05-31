import os
import boto3
from dotenv import load_dotenv

load_dotenv()


class S3Wrapper:

    ACCESS_KEY= os.environ.get("ACCESS_KEY")
    SECRET_KEY= os.environ.get("SECRET_KEY")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

    def __init__(self):
        self.client = boto3.client('s3', 
                                    aws_access_key_id=self.ACCESS_KEY,
                                    aws_secret_access_key=self.SECRET_KEY
                                    )
        


    def upload_image(self, img_name, img_content):
        with open(f'{img_name}.jpg', "wb") as f:
            f.write(img_content)
                
        self.client.upload_file(f"{img_name}.jpg", self.S3_BUCKET_NAME, f"images/{img_name}.jpg")

        image_url = f"https://{self.S3_BUCKET_NAME}.s3.amazonaws.com/images/{img_name}.jpg"

        if os.path.exists(f"{img_name}.jpg"):
            os.remove(f"{img_name}.jpg")

        return image_url