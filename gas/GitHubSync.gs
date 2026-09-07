/*************************************************
 * 料理アフィリエイト自動化
 * GitHub同期システム
 *
 * 機能
 * 1. GASプロジェクト全体を取得
 * 2. GitHubへ自動バックアップ
 * 3. Code.gs / appsscript.json を保存
 *
 * 重要
 * GitHubトークンはコードに書かず、
 * GASのスクリプトプロパティから取得する。
 *************************************************/


/*************************************************
 * 設定
 *************************************************/

const GITHUB_API_BASE = 'https://api.github.com';

const GITHUB_OWNER =
  PropertiesService.getScriptProperties().getProperty('GITHUB_OWNER');

const GITHUB_REPO =
  PropertiesService.getScriptProperties().getProperty('GITHUB_REPO');

const GITHUB_BRANCH =
  PropertiesService.getScriptProperties().getProperty('GITHUB_BRANCH') || 'main';

const GITHUB_TOKEN =
  PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');


/*************************************************
 * メイン
 *
 * GAS → GitHub
 *************************************************/

function syncGasToGitHub() {

  validateGitHubSettings_();

  const scriptId = ScriptApp.getScriptId();

  console.log('GASプロジェクト取得開始');
  console.log('Script ID: ' + scriptId);

  /*
   * Apps Script APIから現在のプロジェクト内容を取得
   */
  const gasUrl =
    'https://script.googleapis.com/v1/projects/' +
    encodeURIComponent(scriptId) +
    '/content';

  const gasResponse = UrlFetchApp.fetch(gasUrl, {
    method: 'get',
    headers: {
      Authorization: 'Bearer ' + ScriptApp.getOAuthToken()
    },
    muteHttpExceptions: true
  });

  const gasCode = gasResponse.getResponseCode();

  if (gasCode !== 200) {
    throw new Error(
      'Apps Script API取得失敗 HTTP ' +
      gasCode +
      '\n' +
      gasResponse.getContentText()
    );
  }

  const projectContent =
    JSON.parse(gasResponse.getContentText());

  if (!projectContent.files) {
    throw new Error('GASプロジェクトのファイルを取得できませんでした。');
  }

  console.log(
    'GASファイル数: ' +
    projectContent.files.length
  );


  /*
   * GitHubへ保存
   */
  projectContent.files.forEach(function(file) {

    if (!file.name || typeof file.source !== 'string') {
      return;
    }

    /*
     * GitHub上では gas フォルダに保存
     */
    const githubPath =
      'gas/' + file.name;

    uploadFileToGitHub_(
      githubPath,
      file.source,
      'GAS同期: ' + githubPath
    );

    console.log(
      'GitHub保存完了: ' +
      githubPath
    );
  });


  console.log('================================');
  console.log('GAS → GitHub 同期完了');
  console.log('================================');

  return 'GAS → GitHub 同期完了';
}


/*************************************************
 * GitHubへファイル保存
 *************************************************/

function uploadFileToGitHub_(
  path,
  content,
  commitMessage
) {

  const apiUrl =
    GITHUB_API_BASE +
    '/repos/' +
    encodeURIComponent(GITHUB_OWNER) +
    '/' +
    encodeURIComponent(GITHUB_REPO) +
    '/contents/' +
    path
      .split('/')
      .map(encodeURIComponent)
      .join('/');


  /*
   * 既存ファイルのSHAを取得
   */
  let sha = null;

  const getResponse = UrlFetchApp.fetch(apiUrl, {
    method: 'get',
    headers: {
      Authorization: 'Bearer ' + GITHUB_TOKEN,
      Accept: 'application/vnd.github+json'
    },
    muteHttpExceptions: true
  });

  const getCode =
    getResponse.getResponseCode();

  if (getCode === 200) {

    const existing =
      JSON.parse(getResponse.getContentText());

    sha = existing.sha;

  } else if (getCode !== 404) {

    throw new Error(
      'GitHub既存ファイル確認失敗 HTTP ' +
      getCode +
      '\n' +
      getResponse.getContentText()
    );
  }


  /*
   * UTF-8 → Base64
   */
  const encodedContent =
    Utilities.base64Encode(
      Utilities.newBlob(
        content,
        'text/plain',
        path
      ).getBytes()
    );


  /*
   * GitHub Contents API
   */
  const payload = {
    message: commitMessage,
    content: encodedContent,
    branch: GITHUB_BRANCH
  };

  if (sha) {
    payload.sha = sha;
  }


  const putResponse = UrlFetchApp.fetch(apiUrl, {
    method: 'put',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + GITHUB_TOKEN,
      Accept: 'application/vnd.github+json'
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });


  const putCode =
    putResponse.getResponseCode();


  if (putCode !== 200 && putCode !== 201) {

    throw new Error(
      'GitHub保存失敗 HTTP ' +
      putCode +
      '\n' +
      putResponse.getContentText()
    );
  }

  return JSON.parse(
    putResponse.getContentText()
  );
}


/*************************************************
 * 設定チェック
 *************************************************/

function validateGitHubSettings_() {

  const errors = [];

  if (!GITHUB_OWNER) {
    errors.push('GITHUB_OWNER');
  }

  if (!GITHUB_REPO) {
    errors.push('GITHUB_REPO');
  }

  if (!GITHUB_TOKEN) {
    errors.push('GITHUB_TOKEN');
  }

  if (errors.length > 0) {

    throw new Error(
      'GASスクリプトプロパティが不足しています: ' +
      errors.join(', ')
    );
  }
}


/*************************************************
 * 接続テスト
 *************************************************/

function testGitHubConnection() {

  validateGitHubSettings_();

  const url =
    GITHUB_API_BASE +
    '/repos/' +
    encodeURIComponent(GITHUB_OWNER) +
    '/' +
    encodeURIComponent(GITHUB_REPO);

  const response = UrlFetchApp.fetch(url, {
    method: 'get',
    headers: {
      Authorization: 'Bearer ' + GITHUB_TOKEN,
      Accept: 'application/vnd.github+json'
    },
    muteHttpExceptions: true
  });

  const code =
    response.getResponseCode();

  console.log(
    'GitHub接続テスト HTTP: ' + code
  );

  if (code !== 200) {

    throw new Error(
      'GitHub接続失敗 HTTP ' +
      code +
      '\n' +
      response.getContentText()
    );
  }

  const repo =
    JSON.parse(response.getContentText());

  console.log(
    '接続成功: ' +
    repo.full_name
  );

  return 'GitHub接続成功: ' + repo.full_name;
}