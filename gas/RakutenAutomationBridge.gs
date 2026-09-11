/**
 * 楽天自動化ブリッジ
 *
 * GitHub Actionsから料理名/検索キーワードを受け取り、
 * GAS Script Propertiesに保存された楽天API認証情報を使って商品検索する。
 * 楽天のアクセスキーはGitHubへ渡さない。
 * PinterestAutomationBridgeと同じGAS Webアプリを利用する。
 */

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

    var result = RAKUTEN2_search(keyword);
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
        imageUrl: String(item.imageUrl || ''),
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
