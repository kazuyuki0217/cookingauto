/*************************************************
 * 料理アフィリエイト自動化
 * 料理写真コレクション → Pointカズ自動連携
 *
 * ユーザーがGoogle Driveの「料理写真コレクション」に
 * 料理写真を入れると、最新写真をGitHubへ自動転送する。
 *************************************************/

var POINT_KAZU_DRIVE_FOLDER = '料理写真コレクション';
var POINT_KAZU_GITHUB_PATH = 'incoming/latest_photo.b64';
var POINT_KAZU_STATE_KEY = 'POINT_KAZU_LAST_FILE_ID';

function PointKazuDriveSetup() {
  var folder = getOrCreatePointKazuDriveFolder_();

  var functionName = 'PointKazuDriveCheck';
  var triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(function(trigger) {
    if (trigger.getHandlerFunction() === functionName) ScriptApp.deleteTrigger(trigger);
  });

  ScriptApp.newTrigger(functionName).timeBased().everyMinutes(5).create();

  return '料理写真コレクション準備完了\n' + folder.getUrl() + '\n5分ごとに新しい料理写真を確認します。';
}

function PointKazuDriveCheck() {
  var folder = getOrCreatePointKazuDriveFolder_();
  var files = folder.getFiles();
  var candidates = [];

  while (files.hasNext()) {
    var file = files.next();
    var mime = String(file.getMimeType() || '').toLowerCase();
    if (mime.indexOf('image/jpeg') >= 0 || mime.indexOf('image/png') >= 0 || mime.indexOf('image/webp') >= 0) {
      candidates.push(file);
    }
  }

  if (!candidates.length) return '新しい料理写真はありません。';

  candidates.sort(function(a, b) {
    return b.getLastUpdated().getTime() - a.getLastUpdated().getTime();
  });

  var latest = candidates[0];
  var props = PropertiesService.getScriptProperties();
  var lastId = props.getProperty(POINT_KAZU_STATE_KEY) || '';
  if (latest.getId() === lastId) return '処理済み：' + latest.getName();

  var blob = latest.getBlob();
  var bytes = blob.getBytes();
  var base64 = Utilities.base64Encode(bytes);
  uploadPointKazuPhotoToGitHub_(base64, latest.getName());

  props.setProperty(POINT_KAZU_STATE_KEY, latest.getId());
  return 'GitHub転送完了：' + latest.getName();
}

function getOrCreatePointKazuDriveFolder_() {
  var props = PropertiesService.getScriptProperties();
  var savedId = props.getProperty('POINT_KAZU_DRIVE_FOLDER_ID');

  if (savedId) {
    try { return DriveApp.getFolderById(savedId); } catch (e) {}
  }

  var folders = DriveApp.getFoldersByName(POINT_KAZU_DRIVE_FOLDER);
  var folder = folders.hasNext() ? folders.next() : DriveApp.createFolder(POINT_KAZU_DRIVE_FOLDER);
  props.setProperty('POINT_KAZU_DRIVE_FOLDER_ID', folder.getId());
  return folder;
}

function uploadPointKazuPhotoToGitHub_(base64, fileName) {
  var props = PropertiesService.getScriptProperties();
  var owner = props.getProperty('GITHUB_OWNER');
  var repo = props.getProperty('GITHUB_REPO');
  var branch = props.getProperty('GITHUB_BRANCH') || 'main';
  var token = props.getProperty('GITHUB_TOKEN');

  if (!owner || !repo || !token) {
    throw new Error('GitHub設定が不足しています。GITHUB_OWNER / GITHUB_REPO / GITHUB_TOKENを確認してください。');
  }

  var url = 'https://api.github.com/repos/' + encodeURIComponent(owner) + '/' + encodeURIComponent(repo) + '/contents/' + POINT_KAZU_GITHUB_PATH;
  var headers = {Authorization:'Bearer ' + token, Accept:'application/vnd.github+json'};
  var current = UrlFetchApp.fetch(url + '?ref=' + encodeURIComponent(branch), {method:'get', headers:headers, muteHttpExceptions:true});
  var sha = '';
  if (current.getResponseCode() === 200) {
    try { sha = JSON.parse(current.getContentText()).sha || ''; } catch (e) {}
  }

  var payload = {
    message: 'Pointカズ：料理写真を自動受信 ' + fileName,
    content: base64,
    branch: branch
  };
  if (sha) payload.sha = sha;

  var response = UrlFetchApp.fetch(url, {
    method:'put',
    headers:headers,
    contentType:'application/json',
    payload:JSON.stringify(payload),
    muteHttpExceptions:true
  });

  var code = response.getResponseCode();
  if (code < 200 || code >= 300) {
    throw new Error('GitHub写真転送失敗 HTTP ' + code + '\n' + response.getContentText());
  }
}

function PointKazuDriveTest() {
  var folder = getOrCreatePointKazuDriveFolder_();
  return '料理写真コレクション：' + folder.getUrl();
}
