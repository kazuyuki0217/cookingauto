/*
 * Pinterest Sandbox test
 * 既存のコード.gsは変更しません。
 */
function PinterestSandboxアクセストークン保存() {
  var ui = SpreadsheetApp.getUi();
  var result = ui.prompt('Pinterest Sandboxアクセストークン', '作成したSandboxトークンを入力してください。', ui.ButtonSet.OK_CANCEL);
  if (result.getSelectedButton() !== ui.Button.OK) return;
  var token = result.getResponseText().trim();
  if (!token) throw new Error('Sandboxトークンが空です。');
  PropertiesService.getScriptProperties().setProperty('PINTEREST_SANDBOX_ACCESS_TOKEN', token);
  Logger.log('Sandboxトークンを保存しました。');
}

function PinterestSandbox接続テスト() {
  var token = PropertiesService.getScriptProperties().getProperty('PINTEREST_SANDBOX_ACCESS_TOKEN');
  if (!token) throw new Error('PINTEREST_SANDBOX_ACCESS_TOKEN が未登録です。先にPinterestSandboxアクセストークン保存を実行してください。');
  var res = UrlFetchApp.fetch('https://api-sandbox.pinterest.com/v5/boards?page_size=100', {
    method: 'get', headers: {Authorization: 'Bearer ' + token}, muteHttpExceptions: true
  });
  Logger.log('Pinterest Sandbox GET HTTP: ' + res.getResponseCode());
  Logger.log(res.getContentText());
  if (res.getResponseCode() === 200) Logger.log('Pinterest Sandbox API接続成功');
}

function PinterestSandboxボード一覧() {
  return PinterestSandbox接続テスト();
}
