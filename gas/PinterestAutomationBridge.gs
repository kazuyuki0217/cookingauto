/**
 * Pinterest自動投稿ブリッジ
 *
 * GitHub Actionsから5件のPinデータを受け取り、
 * Code.gsに保存されているPinterest OAuthトークンを利用して投稿する。
 *
 * セキュリティ:
 * - PINTEREST_AUTOMATION_SECRETはScript Propertiesに保存
 * - Pinterestアクセストークン/refresh tokenはGitHubへ渡さない
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

    var pins = body.pins;
    if (!Array.isArray(pins) || pins.length !== 5) {
      return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
        error:'Pinterest投稿データは5件必要です。',
        count:Array.isArray(pins) ? pins.length : 0
      });
    }

    var results = [];
    for (var i = 0; i < pins.length; i++) {
      var pin = pins[i] || {};
      if (!pin.imageUrl || !pin.title || !pin.link) {
        return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
          error:'Pin ' + (i + 1) + ' にimageUrl/title/linkのいずれかがありません。'
        });
      }

      var result = PinterestPin作成(
        String(pin.imageUrl),
        String(pin.title),
        String(pin.description || ''),
        String(pin.link)
      );

      results.push({
        index: i + 1,
        id: result && result.id ? String(result.id) : '',
        success: true
      });

      if (i < pins.length - 1) Utilities.sleep(1500);
    }

    return KAZU_PINTEREST_AUTOMATION_JSON_(true, {
      count: results.length,
      results: results
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
