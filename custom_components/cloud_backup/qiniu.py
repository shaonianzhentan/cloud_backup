import qiniu, uuid, os
from homeassistant.const import __version__ as current_version

# 获取本机MAC地址
def get_mac_address_key(): 
    mac=uuid.UUID(int = uuid.getnode()).hex[-12:] 
    return "".join([mac[e:e+2] for e in range(0,11,2)])

class Qiniu():

    def __init__(self, hass, access_key, secret_key, bucket_name):
        self.hass = hass
        self.auth = qiniu.Auth(access_key, secret_key)
        self.bucket_name = bucket_name
        self.prefix = f'HomeAssistant/{get_mac_address_key()}/{current_version}/'
        self.in_process = False

    def validate(self) -> bool:
        bucket = qiniu.BucketManager(self.auth)
        limit = 1
        marker = None
        delimiter = None
        ret, eof, info = bucket.list(self.bucket_name, self.prefix, marker, limit, delimiter)
        '''
        print('========')
        print(ret)
        print(eof)
        print(info)
        '''
        return eof

    def upload(self, localfile):
        key = self.prefix + os.path.basename(localfile)
        token = self.auth.upload_token(self.bucket_name, key, 3600)
        res = qiniu.put_file(token, key, localfile)
        return res[0]['key']