/*
 * Pinterest Sandbox test
 * 既存のコード.gsは変更しません。
 *
 * トークン入力に Browser.inputBox() は使用しません。
 * GASのスクリプトプロパティへ安全に保存する方式です。
 */

function PinterestSandboxアクセストークン保存() {
  var token = PropertiesService.getScriptProperties()
    .getProperty('PINTEREST_SANDBOX_ACCESS_TOKEN');

  if (!token) {
    throw new Error(
      'Sandboxトークンが未登録です。' +
      'GASの「プロジェクトの設定」→「スクリプト プロパティ」で、' +
      'PINTEREST_SANDBOX_ACCESS_TOKEN にSandboxトークンを登録してください。'
    );
  }

  Logger.log('PINTEREST_SANDBOX_ACCESS_TOKEN は登録済みです。');
}

function PinterestSandbox接続テスト() {
  var token = PropertiesService.getScriptProperties()
    .getProperty('PINTEREST_SANDBOX_ACCESS_TOKEN');

  if (!token) {
    throw new Error(
      'PINTEREST_SANDBOX_ACCESS_TOKEN が未登録です。'
    );
  }

  var res = UrlFetchApp.fetch(
    'https://api-sandbox.pinterest.com/v5/boards?page_size=100',
    {
      method: 'get',
      headers: {
        Authorization: 'Bearer ' + token
      },
      muteHttpExceptions: true
    }
  );

  var code = res.getResponseCode();
  var body = res.getContentText();

  Logger.log('Pinterest Sandbox GET HTTP: ' + code);
  Logger.log(body);

  if (code === 200) {
    Logger.log('Pinterest Sandbox API接続成功');
    return 'Pinterest Sandbox API接続成功';
  }

  throw new Error(
    'Pinterest Sandbox API接続失敗 HTTP ' + code + '\n' + body
  );
}

function PinterestSandboxボード一覧() {
  return PinterestSandbox接続テスト();
}
