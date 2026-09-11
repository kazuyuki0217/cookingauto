import json
import os
from pathlib import Path

import requests


def required_env(name: str) -> str:
    value = os.environ.get(name, '').strip()
    if not value:
        raise RuntimeError(f'{name} がGitHub Actions Secretsに未登録です。')
    return value


gas_url = required_env('PINTEREST_GAS_URL')
secret = required_env('PINTEREST_AUTOMATION_SECRET')
pins_path = Path('pinterest_pins.json')
if not pins_path.exists():
    raise RuntimeError('pinterest_pins.json がありません。')

pins = json.loads(pins_path.read_text(encoding='utf-8'))
if not isinstance(pins, list) or len(pins) != 5:
    raise RuntimeError(f'Pinterest投稿データは5件必要です。現在: {len(pins) if isinstance(pins, list) else "不正"}件')

payload = {'secret': secret, 'pins': pins}
response = requests.post(gas_url, json=payload, timeout=120)
response.raise_for_status()

try:
    result = response.json()
except ValueError:
    raise RuntimeError('GASからJSON形式の応答が返りませんでした。')

if not result.get('success'):
    raise RuntimeError('Pinterest自動投稿失敗: ' + str(result.get('error', result)))

count = int(result.get('count', 0))
if count != 5:
    raise RuntimeError(f'Pinterest投稿件数が5件ではありません。実績: {count}件')

Path('pinterest_publish_result.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8'
)
print('Pinterest実投稿成功: 5件')
for item in result.get('results', []):
    print(f"  Pin {item.get('index')}: {item.get('id', '')}")
