/*************************************************
 * Pinterest OAuth state 修正版
 *
 * 既存のOAuth処理を壊さず、認証URLを1回だけ生成するための
 * 安全な入口。既存のdoGetコールバックと同じ
 * PINTEREST_OAUTH_STATE を使用する。
 *************************************************/

function PinterestOAuth開始URL_修正版() {
  var state = Utilities.getUuid().replace(/-/g, '');
  PropertiesService.getScriptProperties().setProperty('PINTEREST_OAUTH_STATE', state);

  var url = 'https://www.pinterest.com/oauth/?' + [
    'client_id=' + encodeURIComponent(KAZU_PINTEREST_APP_ID_()),
    'redirect_uri=' + encodeURIComponent(KAZU_PINTEREST_REDIRECT_URI_()),
    'response_type=code',
    'scope=' + encodeURIComponent(KAZU_PINTEREST_SCOPES_()),
    'state=' + encodeURIComponent(state)
  ].join('&');

  Logger.log('Pinterest OAuth 修正版URL: ' + url);
  return url;
}

function PinterestOAuth状態クリア_() {
  PropertiesService.getScriptProperties().deleteProperty('PINTEREST_OAUTH_STATE');
  Logger.log('Pinterest OAuth stateをクリアしました。');
  return 'OK';
}
