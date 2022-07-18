import qiniu, uuid, os, hashlib, zipfile, tempfile
from homeassistant.const import __version__ as HAVERSION
from homeassistant.util import dt, json as json_util
from homeassistant.components.backup.manager import Backup
from pathlib import Path

# 获取本机MAC地址
def get_mac_address_key(): 
    mac=uuid.UUID(int = uuid.getnode()).hex[-12:] 
    return "".join([mac[e:e+2] for e in range(0,11,2)])

class Qiniu():

    def __init__(self, hass, access_key, secret_key, bucket_name):
        self.hass = hass
        self.auth = qiniu.Auth(access_key, secret_key)
        self.bucket_name = bucket_name
        self.prefix = f'HomeAssistant/{get_mac_address_key()}/{HAVERSION}/'
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

    def notify(self, message):
        self.hass.services.call('persistent_notification', 'create', {
            'title': '云备份',
            'message': message,
            'notification_id': 'cloud_backup'
        })

    '''
    root_path: 压缩目录
    filter_dir: 过滤目录
    filter_name: 全局过滤名称
    '''
    def zip(self, root_path, zip_name, filter_dir=None, filter_name=None, tmpdir=None):
        # 临时目录
        if tmpdir is None:
            tmpdir = tempfile.gettempdir()
        # print(tmpdir)
        # 压缩文件
        zf = os.path.join(tmpdir, zip_name)
        with zipfile.ZipFile(zf, 'w', zipfile.ZIP_DEFLATED) as zip:
            # 遍历文件
            for file_name in os.listdir(root_path):
                    file_path = os.path.join(root_path, file_name)
                    # 压缩目录
                    if os.path.isdir(file_path):
                        for path, dirnames, filenames in os.walk(file_path):
                            # 去掉目标跟路径，只对目标文件夹下边的文件及文件夹进行压缩
                            fpath = path.replace(root_path, '')
                            # 格式化文件名称（斜杠转义）
                            format_name = fpath.replace('\\', '/').strip('/')
                            # 过滤的文件
                            if filter_dir is not None and len(list(filter(lambda x: format_name.startswith(x), filter_dir))) > 0:
                                continue
                            # 全局过滤
                            if filter_name is not None and len(list(filter(lambda x: x in format_name, filter_name))) > 0:
                                continue
                            print('压缩目录：' + format_name)
                            for filename in filenames:
                                zip.write(os.path.join(path, filename), os.path.join(fpath, filename))
                    else:
                        zip.write(file_path, file_name)
        return zf

    async def upload(self, call):
        data = call.data

        if self.in_process:
            self.notify('正在上传中...')
            return

        self.in_process = True
        filter_dir = data.get('filter', [])
        filter_dir.extend([
            'deps', 
            'media', 
            'core', 
            'backups',
            'custom_components/ha_file_explorer',
            'home-assistant_v2.db',
            'home-assistant_v2.db-shm',
            'home-assistant_v2.db-wal',
            'home-assistant.log',
            'home-assistant.log.fault',
            'home-assistant.log.1'
        ])
        filter_name = [
            'node_modules', '__pycache__', '.npm'
        ]
        self.notify('开始压缩上传备份文件')
        root_path = self.hass.config.path('./')
        localfile = self.zip(root_path,
            f"_{HAVERSION}_{int(time.time())}.zip",
            filter_dir,
            filter_name,
            f'{root_path}backups/')

        self.notify('开始上传文件到云端')
        key = self.prefix + os.path.basename(localfile)
        token = self.auth.upload_token(self.bucket_name, key, 3600)
        res = qiniu.put_file(token, key, localfile)
        print(res)
        self.in_process = False
        self.notify(f'文件上传成功\n\n路径：<a href="https://portal.qiniu.com/kodo/bucket/resource-v2?bucketName={self.bucket_name}" target="_blank">{key}</a>')