/* 料理写真コレクション: Google Drive受信箱 -> GitHub incoming/latest_photo.b64 */
const RYORI_PHOTO_DRIVE_FOLDER = '料理写真コレクション';
const RYORI_PHOTO_GITHUB_PATH = 'incoming/latest_photo.b64';
const RYORI_PHOTO_STATE_KEY = 'RYORI_PHOTO_LAST_FILE_ID';

function 料理写真コレクションSetup() {
  const folder = getOrCreateRyoriPhotoDriveFolder_();
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction() === '料理写真コレクションCheck') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('料理写真コレクションCheck').timeBased().everyMinutes(5).create();
  console.log('料理写真コレクション: ' + folder.getUrl());
  return folder.getUrl();
}

function 料理写真コレクションCheck() {
  const folder = getOrCreateRyoriPhotoDriveFolder_();
  const files = folder.getFiles();
  const candidates = [];
  while (files.hasNext()) {
    const f = files.next();
    const m = f.getMimeType();
    if (m === 'image/jpeg' || m === 'image/png' || m === 'image/webp') candidates.push(f);
  }
  if (!candidates.length) return 'NO_IMAGE';
  candidates.sort(function(a,b){ return b.getLastUpdated().getTime() - a.getLastUpdated().getTime(); });
  const latest = candidates[0];
  const props = PropertiesService.getScriptProperties();
  if (latest.getId() === props.getProperty(RYORI_PHOTO_STATE_KEY)) return 'ALREADY_PROCESSED';
  const encoded = Utilities.base64Encode(latest.getBlob().getBytes());
  uploadRyoriPhotoToGitHub_(encoded, latest.getName());
  props.setProperty(RYORI_PHOTO_STATE_KEY, latest.getId());
  return 'UPLOADED: ' + latest.getName();
}

function getOrCreateRyoriPhotoDriveFolder_() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty('RYORI_PHOTO_DRIVE_FOLDER_ID');
  if (id) { try { return DriveApp.getFolderById(id); } catch(e) {} }
  const it = DriveApp.getFoldersByName(RYORI_PHOTO_DRIVE_FOLDER);
  const folder = it.hasNext() ? it.next() : DriveApp.createFolder(RYORI_PHOTO_DRIVE_FOLDER);
  props.setProperty('RYORI_PHOTO_DRIVE_FOLDER_ID', folder.getId());
  return folder;
}

function uploadRyoriPhotoToGitHub_(content, originalName) {
  const p = PropertiesService.getScriptProperties();
  const owner = p.getProperty('GITHUB_OWNER');
  const repo = p.getProperty('GITHUB_REPO');
  const branch = p.getProperty('GITHUB_BRANCH') || 'main';
  const token = p.getProperty('GITHUB_TOKEN');
  if (!owner || !repo || !token) throw new Error('GITHUB_OWNER / GITHUB_REPO / GITHUB_TOKEN が必要です。');
  const url = 'https://api.github.com/repos/' + encodeURIComponent(owner) + '/' + encodeURIComponent(repo) + '/contents/' + RYORI_PHOTO_GITHUB_PATH;
  const get = UrlFetchApp.fetch(url, {method:'get', headers:{Authorization:'Bearer '+token,Accept:'application/vnd.github+json'}, muteHttpExceptions:true});
  let sha = null;
  if (get.getResponseCode() === 200) sha = JSON.parse(get.getContentText()).sha;
  else if (get.getResponseCode() !== 404) throw new Error('GitHub確認失敗 HTTP '+get.getResponseCode());
  const payload = {message:'料理写真コレクション: 写真を受信 '+originalName, content:content, branch:branch};
  if (sha) payload.sha = sha;
  const put = UrlFetchApp.fetch(url, {method:'put', contentType:'application/json', headers:{Authorization:'Bearer '+token,Accept:'application/vnd.github+json'}, payload:JSON.stringify(payload), muteHttpExceptions:true});
  if (put.getResponseCode() !== 200 && put.getResponseCode() !== 201) throw new Error('GitHub転送失敗 HTTP '+put.getResponseCode()+' '+put.getContentText());
}

function 料理写真コレクションTest() {
  return getOrCreateRyoriPhotoDriveFolder_().getUrl();
}
