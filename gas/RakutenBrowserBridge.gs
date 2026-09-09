/**
 * 楽天APIブラウザ橋渡し
 * ブラウザ側で楽天API(JSONP)を呼び、取得結果をGASへ戻すための受け皿。
 * アクセスキーそのものはブラウザ橋渡し結果として保存しない。
 */
function 保存楽天ブラウザ検索結果(jsonText) {
  if (!jsonText) throw new Error('楽天検索結果が空です。');
  var data;
  try {
    data = JSON.parse(jsonText);
  } catch (e) {
    throw new Error('楽天検索結果JSON解析エラー');
  }
  var items = data && data.Items ? data.Items : [];
  if (!items.length) throw new Error('楽天商品が含まれていません。');

  var normalized = items.map(function(item) {
    var info = item.Item || item.item || {};
    return {
      商品名: info.itemName || '',
      価格: info.itemPrice || 0,
      商品URL: info.itemUrl || '',
      アフィリエイトURL: info.affiliateUrl || '',
      ショップ名: info.shopName || '',
      商品画像: info.mediumImageUrls && info.mediumImageUrls.length ? info.mediumImageUrls[0].imageUrl : '',
      レビュー件数: info.reviewCount || 0,
      レビュー平均: info.reviewAverage || 0
    };
  });

  PropertiesService.getScriptProperties().setProperty(
    'RAKUTEN_BROWSER_RESULTS',
    JSON.stringify({updatedAt:new Date().toISOString(),items:normalized})
  );
  Logger.log('楽天ブラウザ検索結果保存：' + normalized.length + '件');
  return {success:true,count:normalized.length,items:normalized};
}

function 楽天ブラウザ検索結果取得() {
  var text = PropertiesService.getScriptProperties().getProperty('RAKUTEN_BROWSER_RESULTS');
  if (!text) return {success:false,count:0,items:[]};
  try { return JSON.parse(text); }
  catch (e) { return {success:false,count:0,items:[]}; }
}
