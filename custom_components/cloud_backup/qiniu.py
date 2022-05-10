import qiniu, uuid, os, hashlib
from homeassistant.const import __version__ as HAVERSION
from homeassistant.util import dt, json as json_util
from pathlib import Path

# 获取本机MAC地址
def get_mac_address_key(): 
    mac=uuid.UUID(int = uuid.getnode()).hex[-12:] 
    return "".join([mac[e:e+2] for e in range(0,11,2)])

def _generate_slug(date: str, name: str) -> str:
    """Generate a backup slug."""
    return hashlib.sha1(f"{date} - {name}".lower().encode()).hexdigest()[:8]

class Qiniu():

    def __init__(self, hass, access_key, secret_key, bucket_name):
        self.hass = hass
        self.auth = qiniu.Auth(access_key, secret_key)
        self.bucket_name = bucket_name
        self.prefix = f'HomeAssistant/{get_mac_address_key()}/{HAVERSION}/'

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

    def notify(self, title, message):
        self.hass.services.call('persistent_notification', 'create', {
            'title': title,
            'message': message,
            'notification_id': 'cloud_backup'
        })

    # 生成备份文件
    def generate_backup(self, backup_manager):
        backup_manager.backing_up = True

        backup_name = f"Core {HAVERSION}"
        date_str = dt.now().isoformat()
        slug = _generate_slug(date_str, backup_name)

        backup_data = {
            "slug": slug,
            "name": backup_name,
            "date": date_str,
            "type": "partial",
            "folders": ["homeassistant"],
            "homeassistant": {"version": HAVERSION},
            "compressed": True,
        }
        tar_file_path = Path(backup_manager.backup_dir, f"{backup_data['slug']}.tar")

        if not backup_manager.backup_dir.exists():
            backup_manager.backup_dir.mkdir()

        backup_manager._generate_backup_contents(tar_file_path, backup_data)
        
        backup = Backup(
            slug=slug,
            name=backup_name,
            date=date_str,
            path=tar_file_path,
            size=round(tar_file_path.stat().st_size / 1_048_576, 2),
        )
        if backup_manager.loaded_backups:
            backup_manager.backups[slug] = backup

        backup_manager.backing_up = False

        self.upload(localfile)

    def upload(self, localfile):
        if self.in_process:
            self.notify('云备份', '正在上传中...')
            return
        self.in_process = True
        self.notify('云备份', '开始上传文件到云端')
        key = self.prefix + os.path.basename(localfile)
        token = self.auth.upload_token(self.bucket_name, key, 3600)
        res = qiniu.put_file(token, key, localfile)
        print(res)
        self.in_process = False
        self.notify('文件上传成功', f'路径：<a href="https://portal.qiniu.com/kodo/bucket/resource-v2?bucketName={self.bucket_name}" target="_blank">{key}</a>')