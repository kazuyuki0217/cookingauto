import json
import os
from pathlib import Path

import requests


def required_env(name: str) -> str:
    value = os.environ.get(name, '').strip()
    if not value:
        raise RuntimeError(f'{name} がGitHub Actions Secretsに未登録です。')
    return value


# 旧デプロイURLが残っている環境もあるため、404のときだけ次候補へ切り替える。
gas_urls_raw = os.environ.get('PINTEREST_GAS_URLS', '').strip()
if gas_urls_raw:
    gas_urls = [u.strip() for u in gas_urls_raw.split(',') if u.strip()]
else:
    gas_urls = [required_env('PINTEREST_GAS_URL')]

secret = required_env('PINTEREST_AUTOMATION_SECRET')
pins_path = Path('pinterest_pins.json')
if not pins_path.exists():
    raise RuntimeError('pinterest_pins.json がありません。')

pins = json.loads(pins_path.read_text(encoding='utf-8'))
if not isinstance(pins, list) or len(pins) != 5:
    raise RuntimeError(f'Pinterest投稿データは5件必要です。現在: {len(pins) if isinstance(pins, list) else "不正"}件')

payload = {'secret': secret, 'service': 'pinterest_schedule', 'pins': pins}
response = None
last_error = None

for gas_url in gas_urls:
    print(f'GAS接続先を確認: {gas_url}')
    try:
        candidate = requests.post(gas_url, json=payload, timeout=120)
        if candidate.status_code == 404:
            print('HTTP 404。次のGASデプロイ候補へ切り替えます。')
            last_error = f'HTTP 404: {gas_url}'
            continue
        candidate.raise_for_status()
        response = candidate
        break
    except requests.RequestException as exc:
        last_error = str(exc)
        raise RuntimeError(f'GASへの接続に失敗しました: {exc}')

if response is None:
    raise RuntimeError(f'有効なGAS WebアプリURLが見つかりません。最後の結果: {last_error}')

try:
    result = response.json()
except ValueError:
    raise RuntimeError('GASからJSON形式の応答が返りませんでした。')

if not result.get('success'):
    raise RuntimeError('Pinterest自動投稿失敗: ' + str(result.get('error', result)))

count = int(result.get('count', 0))
if count != 5:
    raise RuntimeError(f'Pinterest予約件数が5件ではありません。実績: {count}件')
scheduled_count = int(result.get('scheduledCount', 0))
if scheduled_count != 5:
    raise RuntimeError(f'Pinterest予約対象が5件ではありません。実績: {scheduled_count}件')

Path('pinterest_publish_result.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8'
)
print('Pinterest 5件の予約登録成功: 07:00 / 11:30 / 15:00 / 18:30 / 21:30')
for item in result.get('results', []):
    print(f"  Pin {item.get('index')}: {item.get('id', '')}")
