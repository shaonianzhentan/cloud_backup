import qiniu
from homeassistant.const import __version__ as current_version

class Qiniu():

    def __init__(self, access_key, secret_key, bucket_name):
        self.auth = qiniu.Auth(access_key, secret_key)
        self.bucket_name = bucket_name

    def get_list(self):
        bucket = qiniu.BucketManager(self.auth)
        prefix = 'HomeAssistant/' + current_version
        limit = 1
        marker = current_version
        delimiter = None
        ret, eof, info = bucket.list(self.bucket_name, prefix, marker, limit, delimiter)
        print(info)