/*************************************************
 * 料理アフィリエイト自動化
 * GitHub → GAS Web同期ブートストラップ 完全版
 *
 * 目的:
 * GitHub上の最新版GitHubSmartSyncを取得し、
 * GAS側で実行してGitHub → GAS同期を行う。
 *
 * 重要:
 * GH_APIはこのファイルでは宣言しない。
 * GitHubSmartSync / GitHubReverseFixの評価時に
 * 重複宣言が発生しないよう、実行用ローカル名を使う。
 *************************************************/

function githubWebSync() {
  console.log('================================');
  console.log('GitHubWebSync 開始');

  try {
    var smartSyncSource = githubWebSync_fetchFile_('gas/GitHubSmartSync');

    console.log('GitHub最新版 GitHubSmartSync 取得成功');
    console.log('GitHub最新版同期エンジン実行開始');

    var result = githubWebSync_execute_(smartSyncSource);

    console.log('GitHub最新版同期エンジン実行完了');
    console.log('結果: ' + result);
    console.log('================================');

    return result;

  } catch (error) {
    var message = error && error.message ? error.message : String(error);
    console.log('GitHubWebSync エラー');
    console.log(message);
    console.log('================================');
    throw new Error('GitHub最新版同期エンジン実行失敗 ' + message);
  }
}

function githubWebSync_execute_(smartSyncSource) {
  var reverseFixSource = githubWebSync_fetchFile_('gas/GitHubReverseFix');
  var githubSyncSource = githubWebSync_fetchFile_('gas/GitHubSync');

  /*
   * GH_APIの重複宣言対策。
   * GitHubReverseFixはGH_APIを参照するため、グローバル値として提供する。
   * const / let / var による再宣言は一切行わない。
   */
  var sources = [];
  sources.push(
    'globalThis.GH_API = "https://api.github.com";\n' +
    githubSyncSource
  );
  sources.push(reverseFixSource);
  sources.push(smartSyncSource);

  /*
   * 既存のGAS側WebSyncにGH_API宣言が残っていても、
   * 今回の評価コードでは新しい宣言を行わない。
   */
  var combined = sources.join('\n\n');

  eval(combined);

  if (typeof runGitHubSmartSync !== 'function') {
    throw new Error('runGitHubSmartSync が評価後に見つかりません。');
  }

  return runGitHubSmartSync();
}

function githubWebSync_fetchFile_(path) {
  var props = PropertiesService.getScriptProperties();
  var owner = props.getProperty('GITHUB_OWNER');
  var repo = props.getProperty('GITHUB_REPO');
  var branch = props.getProperty('GITHUB_BRANCH') || 'main';
  var token = props.getProperty('GITHUB_TOKEN');

  if (!owner || !repo || !token) {
    throw new Error('GitHub設定が不足しています。GITHUB_OWNER / GITHUB_REPO / GITHUB_TOKEN を確認してください。');
  }

  var url =
    'https://api.github.com/repos/' +
    encodeURIComponent(owner) + '/' +
    encodeURIComponent(repo) + '/contents/' +
    path.split('/').map(encodeURIComponent).join('/') +
    '?ref=' + encodeURIComponent(branch);

  console.log('GitHubファイル取得URL: ' + url);

  var response = UrlFetchApp.fetch(url, {
    method: 'get',
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json'
    },
    muteHttpExceptions: true
  });

  var code = response.getResponseCode();
  var body = response.getContentText();

  console.log('GitHubファイル取得HTTP: ' + code);

  if (code !== 200) {
    throw new Error('GitHubファイル取得失敗 HTTP ' + code + '\n' + body);
  }

  var data = JSON.parse(body);

  if (!data.content) {
    throw new Error('GitHubファイル本文が取得できません: ' + path);
  }

  var encoded = String(data.content).replace(/\s/g, '');
  var bytes = Utilities.base64Decode(encoded);
  var source = Utilities.newBlob(bytes).getDataAsString('UTF-8');

  console.log('GitHubファイル取得成功: ' + path);
  console.log('文字数: ' + source.length);

  return source;
}

function githubWebSyncTest() {
  console.log('GitHubWebSync 接続テスト開始');

  var source = githubWebSync_fetchFile_('gas/GitHubSmartSync');

  console.log('GitHubSmartSync取得成功');
  console.log('文字数: ' + source.length);

  return 'GitHubWebSync接続成功 / GitHubSmartSync取得成功';
}

function githubWebSyncSetupTrigger() {
  var functionName = 'githubWebSync';
  var triggers = ScriptApp.getProjectTriggers();

  triggers.forEach(function(trigger) {
    if (trigger.getHandlerFunction() === functionName) {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  ScriptApp.newTrigger(functionName)
    .timeBased()
    .everyHours(1)
    .create();

  console.log('GitHubWebSyncの1時間ごとの自動実行を設定しました。');
  return 'GitHubWebSync自動実行設定完了';
}
