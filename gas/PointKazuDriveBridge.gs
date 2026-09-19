/*************************************************
 * ポイントオート
 * Google Drive「ポイントレシピ投入」→ GitHub 写真投入
 *
 * スマホではGoogle Driveへ写真を1枚入れるだけ。
 * 写真本体・メタデータ・トリガーを同一処理で更新する。
 *************************************************/

var POINT_KAZU_DRIVE_FOLDER = 'ポイントレシピ投入';
var POINT_KAZU_GITHUB_PATH = 'incoming/latest_photo.b64';
var POINT_KAZU_META_PATH = 'incoming/latest_photo.json';
var POINT_KAZU_TRIGGER_PATH = 'incoming/latest_photo.trigger';
var POINT_KAZU_STATE_KEY = 'POINT_KAZU_LAST_SIGNATURE';

function PointKazuDriveSetup() {
  var folder = getOrCreatePointKazuDriveFolder_();
  var functionName = 'PointKazuDriveCheck';
  ScriptApp.getProjectTriggers().forEach(function(trigger) {
    if (trigger.getHandlerFunction() === functionName) ScriptApp.deleteTrigger(trigger);
  });
  ScriptApp.newTrigger(functionName).timeBased().everyMinutes(5).create();
  return 'ポイントレシピ投入フォルダ準備完了\n' + folder.getUrl() + '\n5分ごとに新しい料理写真を確認します。';
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
  var bytes = latest.getBlob().getBytes();
  var signature = [
    latest.getId(),
    latest.getLastUpdated().getTime(),
    latest.getSize()
  ].join('|');

  var props = PropertiesService.getScriptProperties();
  if (signature === (props.getProperty(POINT_KAZU_STATE_KEY) || '')) {
    return '処理済み：' + latest.getName();
  }

  var base64 = Utilities.base64Encode(bytes);
  var digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, bytes);
  var sha256 = digest.map(function(b) {
    var v = b < 0 ? b + 256 : b;
    return ('0' + v.toString(16)).slice(-2);
  }).join('');

  // 料理名はファイル名から安全に取得。
  // 例: 豚トロとカイワレのビアハム巻き.jpg
  var dishName = latest.getName().replace(/\.[^.]+$/, '').trim();
  if (!dishName) dishName = '料理写真';

  uploadPointKazuPhotoToGitHub_(base64, latest.getName());
  updatePointKazuMetadata_(latest, dishName, sha256, bytes.length);
  updatePointKazuTrigger_(latest, dishName, sha256);

  props.setProperty(POINT_KAZU_STATE_KEY, signature);

  return 'GitHub転送＋メタデータ＋処理開始トリガー完了：' + latest.getName() + '\nSHA256: ' + sha256;
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

  var payload = {message:'ポイントオート：料理写真を自動受信 ' + fileName, content:base64, branch:branch};
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

function updatePointKazuMetadata_(file, dishName, sha256, bytes) {
  var props = PropertiesService.getScriptProperties();
  var owner = props.getProperty('GITHUB_OWNER');
  var repo = props.getProperty('GITHUB_REPO');
  var branch = props.getProperty('GITHUB_BRANCH') || 'main';
  var token = props.getProperty('GITHUB_TOKEN');
  var path = POINT_KAZU_META_PATH;
  var url = 'https://api.github.com/repos/' + encodeURIComponent(owner) + '/' + encodeURIComponent(repo) + '/contents/' + path;
  var headers = {Authorization:'Bearer ' + token, Accept:'application/vnd.github+json'};

  var metadata = {
    photoId: 'PHOTO_' + sha256.substring(0, 16),
    photoFile: file.getName(),
    dishName: dishName,
    mimeType: file.getMimeType(),
    bytes: bytes,
    sha256: sha256,
    createdAt: new Date().toISOString(),
    source: 'Google Drive ポイントレシピ投入'
  };

  updatePointKazuTextFile_(url, headers, branch, JSON.stringify(metadata, null, 2), 'ポイントオート：写真メタデータ更新');
}

function updatePointKazuTrigger_(file, dishName, sha256) {
  var props = PropertiesService.getScriptProperties();
  var owner = props.getProperty('GITHUB_OWNER');
  var repo = props.getProperty('GITHUB_REPO');
  var branch = props.getProperty('GITHUB_BRANCH') || 'main';
  var token = props.getProperty('GITHUB_TOKEN');
  var url = 'https://api.github.com/repos/' + encodeURIComponent(owner) + '/' + encodeURIComponent(repo) + '/contents/' + POINT_KAZU_TRIGGER_PATH;
  var headers = {Authorization:'Bearer ' + token, Accept:'application/vnd.github+json'};

  var trigger = [
    'run=' + new Date().toISOString(),
    'source=Google Drive ポイントレシピ投入',
    'photo=' + file.getName(),
    'photoId=PHOTO_' + sha256.substring(0, 16),
    'dishName=' + dishName,
    'sha256=' + sha256
  ].join('\n') + '\n';

  updatePointKazuTextFile_(url, headers, branch, trigger, 'ポイントオート：写真処理トリガー更新');
}

function updatePointKazuTextFile_(url, headers, branch, content, message) {
  var current = UrlFetchApp.fetch(url + '?ref=' + encodeURIComponent(branch), {method:'get', headers:headers, muteHttpExceptions:true});
  var sha = '';
  if (current.getResponseCode() === 200) {
    try { sha = JSON.parse(current.getContentText()).sha || ''; } catch (e) {}
  }

  var payload = {message:message, content:Utilities.base64EncodeWebSafe(Utilities.newBlob(content).getBytes()), branch:branch};
  // GitHub Contents APIのcontentは通常Base64標準形式を要求するため、標準Base64に戻す。
  payload.content = Utilities.base64Encode(Utilities.newBlob(content).getBytes());
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
    throw new Error('GitHubテキスト更新失敗 HTTP ' + code + '\n' + response.getContentText());
  }
}

function PointKazuDriveTest() {
  return getOrCreatePointKazuDriveFolder_().getUrl();
}
