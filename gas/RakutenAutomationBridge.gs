/**
 * 楽天自動化ブリッジ
 *
 * GitHub Actionsから料理名/検索キーワードを受け取り、
 * GAS Script Propertiesに保存された楽天API認証情報を使って商品検索する。
 * 楽天のアクセスキーはGitHubへ渡さない。
 * PinterestAutomationBridgeと同じGAS Webアプリを利用する。
 *
 * 2026-09-12 修正:
 * 楽天API(2026-07-01)のWebアプリ型アクセス制御に合わせ、
 * 許可済みのはてなブログをOrigin/Refererとして常時明示する。
 * 403発生後だけヘッダーを付ける方式では、楽天側の
 * HTTP_REFERRER_NOT_ALLOWED 判定を正しく切り分けられないため、
 * 最初のリクエストからブラウザ由来のコンテキストを明示する。
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

  // 楽天アプリに登録済みの「許可されたウェブサイト」と一致させる。
  // 2026年版APIではOrigin/Refererによるアクセス元確認が行われるため、
  // GASのサーバーサイドUrlFetchでも両方を明示する。
  var allowedOrigin = 'https://tansinfuninkazu.hatenablog.com';
  var allowedReferer = 'https://tansinfuninkazu.hatenablog.com/';

  var response = UrlFetchApp.fetch(url, {
    method: 'get',
    muteHttpExceptions: true,
    followRedirects: true,
    headers: {
      'Accept': 'application/json',
      'Origin': allowedOrigin,
      'Referer': allowedReferer
    }
  });

  var code = response.getResponseCode();
  var body = response.getContentText();
  Logger.log('楽天自動化API HTTP: ' + code);

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
