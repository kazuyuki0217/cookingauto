import json, os
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright

gas=os.environ['GAS_URL']; secret=os.environ['SECRET']
origin='https://tansinfuninkazu.hatenablog.com'
url=gas+'?'+urlencode({'service':'rakuten_browser','secret':secret,'keyword':'フライパン','hits':'3'})
with sync_playwright() as p:
    req=p.request.new_context(extra_http_headers={'Origin':origin,'Referer':origin+'/'})
    r=req.get(url,timeout=60000)
    print('GAS_STATUS='+str(r.status))
    print('GAS_CONTENT_TYPE='+str(r.headers.get('content-type')))
    print('GAS_BODY_HEAD='+r.text()[:10000])
    req.dispose()
