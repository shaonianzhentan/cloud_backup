import qiniu, time, os
from homeassistant.const import __version__ as current_version
from homeassistant.util.json import load_json
from homeassistant.helpers.storage import STORAGE_DIR

HA_UUID = load_json(os.path.abspath(f'{STORAGE_DIR}/core.uuid'))['data']['uuid']

class Qiniu():

    def __init__(self, hass, access_key, secret_key, bucket_name):
        self.hass = hass
        self.auth = qiniu.Auth(access_key, secret_key)
        self.bucket_name = bucket_name
        self.prefix = f'HomeAssistant/{HA_UUID}/{current_version}/'
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
        today = time.strftime('%y_%m_%d_', time.localtime(time.time()))
        key = self.prefix + today + os.path.basename(localfile)
        token = self.auth.upload_token(self.bucket_name, key, 3600)
        res = qiniu.put_file(token, key, localfile)
        return res[0]['key']