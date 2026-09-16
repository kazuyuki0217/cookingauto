/*************************************************
 * Pinterest Standard審査用デモ
 *
 * 目的:
 * 1. Pinterest OAuth認証URLを生成
 * 2. OAuth callbackで受け取ったcodeをSandbox tokenへ交換
 * 3. SandboxでBoard取得/作成
 * 4. SandboxへPinを作成
 *
 * 既存のCode.gs / doGet / 本番Pinterest処理は変更しません。
 * Trial環境でもStandard審査用のOAuth + API統合デモを
 * Sandboxで実演できるようにするための補助ファイルです。
 *************************************************/

function PinterestStandardDemoOAuthURL() {
  var state = 'STANDARD_DEMO_' + Utilities.getUuid().replace(/-/g, '');
  PropertiesService.getScriptProperties().setProperty('PINTEREST_STANDARD_DEMO_STATE', state);

  var url = 'https://www.pinterest.com/oauth/?' + [
    'client_id=' + encodeURIComponent(KAZU_PINTEREST_APP_ID_()),
    'redirect_uri=' + encodeURIComponent(KAZU_PINTEREST_REDIRECT_URI_()),
    'response_type=code',
    'scope=' + encodeURIComponent(KAZU_PINTEREST_SCOPES_()),
    'state=' + encodeURIComponent(state)
  ].join('&');

  Logger.log('===== Pinterest Standard審査デモ OAuth URL =====');
  Logger.log(url);
  return url;
}

function PinterestStandardDemoOAuth開始() {
  var url = PinterestStandardDemoOAuthURL();
  return HtmlService.createHtmlOutput(
    '<h2>Pinterest Standard審査デモ</h2>' +
    '<p>下のボタンからOAuth認証を開始してください。</p>' +
    '<p><a href="' + url.replace(/&/g, '&amp;') + '" target="_top">Pinterestで認証する</a></p>' +
    '<p>認証後、redirect URIのURL欄に表示されるcodeを確認してください。</p>'
  );
}

function PinterestStandardDemoSandboxToken(code) {
  code = String(code || '').trim();
  if (!code) throw new Error('OAuth codeがありません。PinterestからredirectされたURLのcodeを指定してください。');

  var expectedState = PropertiesService.getScriptProperties().getProperty('PINTEREST_STANDARD_DEMO_STATE');
  if (!expectedState) throw new Error('デモ用OAuth stateがありません。先にPinterestStandardDemoOAuthURLを実行してください。');

  var auth = Utilities.base64Encode(
    KAZU_PINTEREST_APP_ID_() + ':' + KAZU_PINTEREST_CLIENT_SECRET_()
  );

  var response = UrlFetchApp.fetch('https://api-sandbox.pinterest.com/v5/oauth/token', {
    method: 'post',
    muteHttpExceptions: true,
    contentType: 'application/x-www-form-urlencoded',
    headers: {
      Authorization: 'Basic ' + auth
    },
    payload: {
      grant_type: 'authorization_code',
      code: code,
      redirect_uri: KAZU_PINTEREST_REDIRECT_URI_()
    }
  });

  var http = response.getResponseCode();
  var body = response.getContentText();
  Logger.log('Sandbox OAuth token HTTP: ' + http);

  if (http < 200 || http >= 300) {
    throw new Error('Sandbox OAuth token取得失敗 HTTP ' + http + '\n' + body);
  }

  var data = JSON.parse(body);
  if (!data.access_token) throw new Error('Sandbox access tokenが取得できません。\n' + body);

  var props = PropertiesService.getScriptProperties();
  props.setProperty('PINTEREST_SANDBOX_ACCESS_TOKEN', String(data.access_token));
  if (data.refresh_token) props.setProperty('PINTEREST_SANDBOX_REFRESH_TOKEN', String(data.refresh_token));
  if (data.scope) props.setProperty('PINTEREST_SANDBOX_GRANTED_SCOPES', String(data.scope));
  if (data.expires_in) props.setProperty('PINTEREST_SANDBOX_ACCESS_TOKEN_EXPIRES_AT', String(Date.now() + Number(data.expires_in) * 1000));
  props.deleteProperty('PINTEREST_STANDARD_DEMO_STATE');

  Logger.log('Sandbox OAuth成功');
  Logger.log('Granted scopes: ' + (data.scope || 'レスポンスにscopeなし'));
  return {
    success: true,
    accessToken: '保存済み',
    refreshToken: data.refresh_token ? '保存済み' : 'なし',
    scope: data.scope || ''
  };
}

function PinterestStandardDemoSandboxGet_(endpoint) {
  var token = PropertiesService.getScriptProperties().getProperty('PINTEREST_SANDBOX_ACCESS_TOKEN');
  if (!token) throw new Error('Sandbox access tokenがありません。先にPinterestStandardDemoSandboxTokenを実行してください。');

  var response = UrlFetchApp.fetch('https://api-sandbox.pinterest.com/v5' + endpoint, {
    method: 'get',
    muteHttpExceptions: true,
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/json'
    }
  });
  var http = response.getResponseCode();
  var body = response.getContentText();
  Logger.log('Sandbox GET ' + endpoint + ' HTTP: ' + http);
  if (http < 200 || http >= 300) throw new Error('Sandbox GET失敗 HTTP ' + http + '\n' + body);
  return body ? JSON.parse(body) : {};
}

function PinterestStandardDemoSandboxPost_(endpoint, payload) {
  var token = PropertiesService.getScriptProperties().getProperty('PINTEREST_SANDBOX_ACCESS_TOKEN');
  if (!token) throw new Error('Sandbox access tokenがありません。先にPinterestStandardDemoSandboxTokenを実行してください。');

  var response = UrlFetchApp.fetch('https://api-sandbox.pinterest.com/v5' + endpoint, {
    method: 'post',
    muteHttpExceptions: true,
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/json'
    },
    payload: JSON.stringify(payload)
  });
  var http = response.getResponseCode();
  var body = response.getContentText();
  Logger.log('Sandbox POST ' + endpoint + ' HTTP: ' + http);
  if (http < 200 || http >= 300) throw new Error('Sandbox POST失敗 HTTP ' + http + '\n' + body);
  return body ? JSON.parse(body) : {};
}

function PinterestStandardDemoSandboxBoard() {
  var props = PropertiesService.getScriptProperties();
  var saved = props.getProperty('PINTEREST_SANDBOX_BOARD_ID');
  if (saved) return saved;

  var data = PinterestStandardDemoSandboxGet_('/boards?page_size=250');
  var items = Array.isArray(data.items) ? data.items : [];
  var found = items.find(function(board) {
    return String(board.name || '') === '料理アフィリエイト自動化 Standard審査デモ';
  });
  if (found && found.id) {
    props.setProperty('PINTEREST_SANDBOX_BOARD_ID', String(found.id));
    return String(found.id);
  }

  var created = PinterestStandardDemoSandboxPost_('/boards', {
    name: '料理アフィリエイト自動化 Standard審査デモ',
    description: 'Pinterest Standardアクセス審査用のSandbox統合デモです。'
  });
  if (!created.id) throw new Error('Sandbox Board IDを取得できませんでした。');
  props.setProperty('PINTEREST_SANDBOX_BOARD_ID', String(created.id));
  return String(created.id);
}

function PinterestStandardDemoSandboxPin() {
  var boardId = PinterestStandardDemoSandboxBoard();
  var pin = PinterestStandardDemoSandboxPost_('/pins', {
    board_id: boardId,
    title: '仕事終わりに作れる簡単料理｜Pinterest API Sandboxデモ',
    description: '料理アフィリエイト自動化のPinterest API統合デモ。OAuth認証後のSandbox APIで作成したPinです。',
    link: 'https://tansinfuninkazu.hatenablog.com/',
    media_source: {
      source_type: 'image_url',
      url: 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=1200&q=80',
      is_standard: true
    }
  });

  if (!pin.id) throw new Error('Sandbox Pin IDを取得できませんでした。');
  PropertiesService.getScriptProperties().setProperty('PINTEREST_SANDBOX_PIN_ID', String(pin.id));

  Logger.log('===== Pinterest Standard審査デモ Pin作成成功 =====');
  Logger.log('Board ID: ' + boardId);
  Logger.log('Pin ID: ' + pin.id);
  Logger.log('Pinterest URL: https://www.pinterest.com/pin/' + pin.id + '/');
  return pin;
}

function PinterestStandardDemo診断() {
  var props = PropertiesService.getScriptProperties().getProperties();
  var result = {
    appId: KAZU_PINTEREST_APP_ID_(),
    redirectUri: KAZU_PINTEREST_REDIRECT_URI_(),
    scopes: KAZU_PINTEREST_SCOPES_(),
    sandboxToken: props.PINTEREST_SANDBOX_ACCESS_TOKEN ? '登録済み' : '未登録',
    sandboxScopes: props.PINTEREST_SANDBOX_GRANTED_SCOPES || '未登録',
    sandboxBoardId: props.PINTEREST_SANDBOX_BOARD_ID || '未登録',
    sandboxPinId: props.PINTEREST_SANDBOX_PIN_ID || '未登録'
  };
  Logger.log(JSON.stringify(result, null, 2));
  return result;
}
