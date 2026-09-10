/**
 * Pinterest本命ボード設定・本番投稿テスト用の安全な補助ファイル
 * code.gs本体を変更せず、Spreadsheet UIにも依存しません。
 */
function Pinterest本命ボード自動設定() {
  var boardId = '1098948815264117157';
  PropertiesService.getScriptProperties().setProperty('PINTEREST_BOARD_ID', boardId);
  Logger.log('Pinterest本命ボードIDを設定しました: ' + boardId);
  return boardId;
}

function Pinterest本命ボード確認() {
  var boardId = PropertiesService.getScriptProperties().getProperty('PINTEREST_BOARD_ID');
  Logger.log('現在のPinterest BOARD ID: ' + (boardId || '未設定'));
  return boardId || '';
}
