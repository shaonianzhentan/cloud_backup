import qiniu, uuid, os
from homeassistant.const import __version__ as current_version

# 获取本机MAC地址
def get_mac_address_key(): 
    mac=uuid.UUID(int = uuid.getnode()).hex[-12:] 
    return "".join([mac[e:e+2] for e in range(0,11,2)])

class Qiniu():

    def __init__(self, access_key, secret_key, bucket_name):
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

    def notify(self, hass, title, message):
        hass.services.call('persistent_notification', 'create', {
            'title': title,
            'message': message,
            'notification_id': 'cloud_backup'
        })

    def upload(self, localfile, hass):
        if self.in_process:
            self.notify(hass, '云备份', '正在上传中...')
            return
        self.notify(hass, '云备份', '开始上传文件到云端')
        self.in_process = True
        key = self.prefix + os.path.basename(localfile)
        token = self.auth.upload_token(self.bucket_name, key, 3600)
        res = qiniu.put_file(token, key, localfile)
        print(res)
        self.in_process = False
        self.notify(hass, '文件上传成功', f'路径：<a href="https://portal.qiniu.com/kodo/bucket/resource-v2?bucketName={self.bucket_name}" target="_blank">{key}</a>')