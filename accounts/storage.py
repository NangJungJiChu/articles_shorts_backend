from storages.backends.s3boto3 import S3Boto3Storage

class ProfileImageStorage(S3Boto3Storage):
    bucket_name = 'njjc-profile-image'
    custom_domain = f'{bucket_name}.s3.ap-northeast-2.amazonaws.com'
    file_overwrite = True
