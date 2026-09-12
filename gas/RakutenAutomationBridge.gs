/**
 * 楽天自動化ブリッジ
 *
 * GitHub Actionsから料理名/検索キーワードを受け取り、
 * GAS Script Propertiesに保存された楽天API認証情報を使って商品検索する。
 * 楽天のアクセスキーはGitHubへ渡さない。
 * PinterestAutomationBridgeと同じGAS Webアプリを利用する。
 *
 * 2026-09-12 修正:
 * 楽天APIから REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING が返った場合、
 * はてなブログをリクエスト元として明示して再試行する。
 * 通常時は余計なヘッダーを付けず、403時だけ再試行する。
 */

function KAZU_RAKUTEN_AUTOMATION_SEARCH_(keyword, hits) {
  keyword = String(keyword || '').trim() || 'フライパン';
  hits = Number(hits || 10);
  if (hits < 1) hits = 10;
  if (hits > 30) hits = 30;

  var key = KAZU_RAKUTEN_KEY_();
  var params = [
    'applicationId=' + encodeURIComponent(KAZU_RAKUTEN_APP_ID_()),
    'accessKey=' + encodeURIComponent(key),
    'affiliateId=' + encodeURIComponent(KAZU_RAKUTEN_AFFILIATE_ID_()),
    'keyword=' + encodeURIComponent(keyword),
    'hits=' + encodeURIComponent(hits),
    'page=1',
    'format=json',
    'formatVersion=2'
  ];

  var url = KAZU_RAKUTEN_API_() + '?' + params.join('&');
  Logger.log('楽天自動化API検索開始: ' + keyword);

  var response = UrlFetchApp.fetch(url, {
    method: 'get',
    muteHttpExceptions: true,
    followRedirects: true,
    headers: {
      'Accept': 'application/json'
    }
  });

  var code = response.getResponseCode();
  var body = response.getContentText();
  Logger.log('楽天自動化API HTTP（初回）: ' + code);

  // 現在の楽天APIがRefererを要求する場合だけ再試行する。
  // 余計なRefererを常時送ると、逆にNOT_ALLOWEDになる可能性があるため、
  // 通常リクエストは従来どおりシンプルに保つ。
  if (
    code === 403 &&
    body.indexOf('REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING') !== -1
  ) {
    Logger.log('楽天APIがRefererを要求したため、はてなブログURLを付けて再試行します。');

    response = UrlFetchApp.fetch(url, {
      method: 'get',
      muteHttpExceptions: true,
      followRedirects: true,
      headers: {
        'Accept': 'application/json',
        'Origin': 'https://tansinfuninkazu.hatenablog.com',
        'Referer': 'https://tansinfuninkazu.hatenablog.com/'
      }
    });

    code = response.getResponseCode();
    body = response.getContentText();
    Logger.log('楽天自動化API HTTP（Referer再試行）: ' + code);
  }

  if (code < 200 || code >= 300) {
    throw new Error('楽天APIエラー HTTP ' + code + '\n' + body);
  }

  var data;
  try {
    data = JSON.parse(body);
  } catch (e) {
    throw new Error('楽天API JSON解析エラー\n' + body);
  }

  if (!data.items || !data.items.length) {
    throw new Error('楽天商品が見つかりません。検索語: ' + keyword);
  }

  return data;
}

function KAZU_RAKUTEN_AUTOMATION_(body) {
  if (!body || body.service !== 'rakuten') {
    return null;
  }

  var keywords = Array.isArray(body.keywords) ? body.keywords : [];
  if (!keywords.length) {
    return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
      error: '楽天検索キーワードがありません。'
    });
  }

  if (keywords.length > 5) {
    keywords = keywords.slice(0, 5);
  }

  var items = [];
  var seen = {};

  keywords.forEach(function(keyword) {
    keyword = String(keyword || '').trim();
    if (!keyword) return;

    var result = KAZU_RAKUTEN_AUTOMATION_SEARCH_(keyword, 10);
    var rows = result && result.items ? result.items : [];

    rows.forEach(function(item) {
      var affiliateUrl = String(item.affiliateUrl || item.itemUrl || '').trim();
      var itemUrl = String(item.itemUrl || '').trim();
      var key = affiliateUrl || itemUrl || String(item.itemCode || '');
      if (!key || seen[key]) return;
      seen[key] = true;

      items.push({
        itemName: String(item.itemName || ''),
        itemCode: String(item.itemCode || ''),
        itemPrice: item.itemPrice || 0,
        itemUrl: itemUrl,
        affiliateUrl: affiliateUrl,
        shopName: String(item.shopName || ''),
        imageUrl: String(
          item.mediumImageUrls && item.mediumImageUrls.length
            ? (item.mediumImageUrls[0].imageUrl || '')
            : ''
        ),
        reviewCount: Number(item.reviewCount || 0),
        reviewAverage: Number(item.reviewAverage || 0),
        keyword: keyword
      });
    });
  });

  return KAZU_PINTEREST_AUTOMATION_JSON_(true, {
    count: items.length,
    items: items
  });
}
