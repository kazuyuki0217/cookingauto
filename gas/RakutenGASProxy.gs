/**
 * GAS保存済み楽天認証の安全な中継。
 * アクセスキーそのものはレスポンスに返さない。
 * GitHub Actionsからは既存のPINTE​REST_AUTOMATION_SECRETで認証する。
 */
function 楽天自動化検索プロキシ_(e) {
  try {
    var body = JSON.parse(e.postData.contents || '{}');
    var expected = KAZU_PROP_('PINTEREST_AUTOMATION_SECRET');
    if (!expected || body.secret !== expected) {
      return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error:'認証に失敗しました。'});
    }
    var keywords = Array.isArray(body.keywords) ? body.keywords.slice(0, 3) : [];
    if (!keywords.length) return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error:'検索キーワードがありません。'});
    var items = [];
    var seen = {};
    keywords.forEach(function(keyword) {
      var data = KAZU_RAKUTEN_AUTOMATION_SEARCH_(keyword, 10);
      (data.items || []).forEach(function(item) {
        var url = String(item.affiliateUrl || item.itemUrl || '');
        if (!url || seen[url]) return;
        seen[url] = true;
        items.push({
          itemName: String(item.itemName || ''),
          itemPrice: Number(item.itemPrice || 0),
          itemUrl: String(item.itemUrl || ''),
          affiliateUrl: url,
          shopName: String(item.shopName || ''),
          reviewCount: Number(item.reviewCount || 0),
          reviewAverage: Number(item.reviewAverage || 0)
        });
      });
    });
    return KAZU_PINTEREST_AUTOMATION_JSON_(true, {count:items.length, items:items});
  } catch (err) {
    return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error:String(err && err.message ? err.message : err)});
  }
}
