/**
 * Pinterest自動投稿ブリッジ
 *
 * GitHub Actionsから5件のPinデータを受け取り、
 * Code.gsに保存されているPinterest OAuthトークンを利用して投稿する。
 *
 * 楽天商品検索も同じ認証済みブリッジ経由で実行する。
 * 楽天アクセスキーはGitHubへ渡さない。
 *
 * セキュリティ:
 * - PINTEREST_AUTOMATION_SECRETはScript Propertiesに保存
 * - Pinterestアクセストークン/refresh tokenはGitHubへ渡さない
 * - 楽天API認証情報もScript Propertiesからのみ取得
 */

function KAZU_PINTEREST_AUTOMATION_SECRET_() {
  var secret = KAZU_PROP_('PINTEREST_AUTOMATION_SECRET');
  if (!secret) throw new Error('PINTEREST_AUTOMATION_SECRETがScript Propertiesに未登録です。');
  return secret;
}

function KAZU_PINTEREST_AUTOMATION_JSON_(success, data) {
  var result = data || {};
  result.success = success;
  return ContentService
    .createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}

function KAZU_PINTEREST_EXISTING_PIN_KEYS_() {
  var boardId = KAZU_PROP_('PINTEREST_BOARD_ID');
  if (!boardId) return {};

  var seen = {};
  var bookmark = '';

  for (var page = 0; page < 10; page++) {
    var endpoint = '/boards/' + encodeURIComponent(boardId) + '/pins?page_size=100';
    if (bookmark) endpoint += '&bookmark=' + encodeURIComponent(bookmark);

    var data = KAZU_PIN_GET_(endpoint);
    var pins = data && Array.isArray(data.items) ? data.items : [];

    pins.forEach(function(pin) {
      var title = String(pin.title || '').trim();
      var link = String(pin.link || '').trim();
      if (title && link) seen[title + '\n' + link] = String(pin.id || '');
    });

    bookmark = String(data && data.bookmark ? data.bookmark : '').trim();
    if (!bookmark || pins.length === 0) break;
  }

  return seen;
}

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error:'POSTデータがありません。'});
    }

    var body;
    try {
      body = JSON.parse(e.postData.contents);
    } catch (parseError) {
      return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error:'JSON解析に失敗しました。'});
    }

    var expected = KAZU_PINTEREST_AUTOMATION_SECRET_();
    if (!body.secret || body.secret !== expected) {
      return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error:'認証に失敗しました。'});
    }

    if (body.service === 'rakuten') {
      return KAZU_RAKUTEN_AUTOMATION_(body);
    }

    var pins = body.pins;
    if (!Array.isArray(pins) || pins.length !== 5) {
      return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
        error:'Pinterest投稿データは5件必要です。',
        count:Array.isArray(pins) ? pins.length : 0
      });
    }

    // 同じ記事をActionsから再実行しても、同じtitle + linkのPinを二重投稿しない。
    var existing = KAZU_PINTEREST_EXISTING_PIN_KEYS_();
    var results = [];

    for (var i = 0; i < pins.length; i++) {
      var pin = pins[i] || {};
      if (!pin.imageUrl || !pin.title || !pin.link) {
        return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
          error:'Pin ' + (i + 1) + ' にimageUrl/title/linkのいずれかがありません。'
        });
      }

      var title = String(pin.title);
      var link = String(pin.link);
      var key = title.trim() + '\n' + link.trim();
      var existingId = existing[key] || '';

      if (existingId) {
        results.push({
          index: i + 1,
          id: existingId,
          success: true,
          skipped: true,
          reason: '同一title+linkのPinが既に存在'
        });
        continue;
      }

      var result = PinterestPin作成(
        String(pin.imageUrl),
        title,
        String(pin.description || ''),
        link
      );

      results.push({
        index: i + 1,
        id: result && result.id ? String(result.id) : '',
        success: true,
        skipped: false
      });

      if (i < pins.length - 1) Utilities.sleep(1500);
    }

    return KAZU_PINTEREST_AUTOMATION_JSON_(true, {
      count: results.length,
      results: results,
      skippedCount: results.filter(function(item) { return item.skipped; }).length
    });

  } catch (error) {
    return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
      error: String(error && error.message ? error.message : error)
    });
  }
}

function Pinterest自動投稿ブリッジ設定確認() {
  var props = PropertiesService.getScriptProperties().getProperties();
  return {
    automationSecret: props.PINTEREST_AUTOMATION_SECRET ? '登録済み' : '未登録',
    pinterestAccessToken: props.PINTEREST_ACCESS_TOKEN ? '登録済み' : '未登録',
    pinterestRefreshToken: props.PINTEREST_REFRESH_TOKEN ? '登録済み' : '未登録',
    pinterestBoardId: props.PINTEREST_BOARD_ID || '未登録'
  };
}
