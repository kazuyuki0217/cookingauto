/*************************************************
 * 料理アフィリエイト自動化
 * GitHub → GAS Web同期ブートストラップ
 *
 * 既存のGAS同期関数を外部入口から安全に呼び出すための薄い入口。
 * 本体コード.gsは変更しない。
 *************************************************/

function githubWebSync_() {
  if (typeof runGitHubSmartSync !== 'function') {
    throw new Error('runGitHubSmartSync がGAS側にありません。先にGitHubSmartSyncを反映してください。');
  }
  return runGitHubSmartSync();
}

function githubWebSyncStatus_() {
  return typeof getGitHubAutoSyncStatus === 'function'
    ? getGitHubAutoSyncStatus()
    : 'GitHub自動同期ステータス関数がありません。';
}
