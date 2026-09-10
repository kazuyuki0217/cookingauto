/*
 * Pinterest Sandbox test + 本番ボード設定・本番投稿テスト
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

/*
 * Sandbox用テストボードを1つ作成します。
 * 本番Pinterestのボード・データには影響しません。
 */
function PinterestSandboxテストボード作成() {
  var token = PropertiesService.getScriptProperties()
    .getProperty('PINTEREST_SANDBOX_ACCESS_TOKEN');

  if (!token) {
    throw new Error('PINTEREST_SANDBOX_ACCESS_TOKEN が未登録です。');
  }

  var payload = {
    name: '料理アフィリエイト自動化 Sandboxテスト',
    description: 'Pinterest API SandboxでのPin投稿テスト用ボードです。'
  };

  var res = UrlFetchApp.fetch(
    'https://api-sandbox.pinterest.com/v5/boards',
    {
      method: 'post',
      contentType: 'application/json',
      headers: {
        Authorization: 'Bearer ' + token
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    }
  );

  var code = res.getResponseCode();
  var body = res.getContentText();

  Logger.log('Pinterest Sandbox BOARD POST HTTP: ' + code);
  Logger.log(body);

  if (code < 200 || code >= 300) {
    throw new Error(
      'Pinterest Sandboxボード作成失敗 HTTP ' + code + '\n' + body
    );
  }

  var data = JSON.parse(body);
  if (data.id) {
    PropertiesService.getScriptProperties()
      .setProperty('PINTEREST_SANDBOX_BOARD_ID', String(data.id));
    Logger.log('SandboxテストボードIDを保存しました: ' + data.id);
  }

  return body;
}

/*
 * SandboxへPinを1件投稿します。
 * テスト画像は公開URLを使用します。
 * 本番Pinterestには投稿されません。
 */
function PinterestSandboxテスト投稿() {
  var props = PropertiesService.getScriptProperties();
  var token = props.getProperty('PINTEREST_SANDBOX_ACCESS_TOKEN');
  var boardId = props.getProperty('PINTEREST_SANDBOX_BOARD_ID');

  if (!token) {
    throw new Error('PINTEREST_SANDBOX_ACCESS_TOKEN が未登録です。');
  }

  if (!boardId) {
    throw new Error(
      'PINTEREST_SANDBOX_BOARD_ID が未登録です。先に「PinterestSandboxテストボード作成」を実行してください。'
    );
  }

  var payload = {
    board_id: boardId,
    title: 'Sandbox Pin投稿テスト',
    description: '料理アフィリエイト自動化のPinterest API Sandbox投稿テストです。',
    link: 'https://tansinfuninkazu.hatenablog.com/',
    media_source: {
      source_type: 'image_url',
      url: 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=1200&q=80'
    }
  };

  var res = UrlFetchApp.fetch(
    'https://api-sandbox.pinterest.com/v5/pins',
    {
      method: 'post',
      contentType: 'application/json',
      headers: {
        Authorization: 'Bearer ' + token
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    }
  );

  var code = res.getResponseCode();
  var body = res.getContentText();

  Logger.log('Pinterest Sandbox PIN POST HTTP: ' + code);
  Logger.log(body);

  if (code < 200 || code >= 300) {
    throw new Error(
      'Pinterest Sandbox Pin投稿失敗 HTTP ' + code + '\n' + body
    );
  }

  var data = JSON.parse(body);
  if (data.id) {
    props.setProperty('PINTEREST_SANDBOX_PIN_ID', String(data.id));
    Logger.log('Sandbox Pin IDを保存しました: ' + data.id);
  }

  Logger.log('Pinterest Sandbox Pin投稿成功');
  return body;
}

/* =====================================================
 * 本番Pinterest用
 * 本命ボード: 一人暮らし、単身赴任ごはん
 * ===================================================== */

function Pinterest本命ボード自動設定() {
  var boardId = '1098948815264117157';
  PropertiesService.getScriptProperties()
    .setProperty('PINTEREST_BOARD_ID', boardId);
  Logger.log('Pinterest本命ボードIDを設定しました: ' + boardId);
  return boardId;
}

function Pinterest本命ボード確認() {
  var boardId = PropertiesService.getScriptProperties()
    .getProperty('PINTEREST_BOARD_ID');
  Logger.log('現在のPinterest BOARD ID: ' + (boardId || '未設定'));
  return boardId || '';
}

/*
 * 本番Pinterestへ1件だけ投稿するAPI動作確認。
 * 既存のコード.gsのPinterestPin作成()を利用します。
 * 料理系の公開テスト画像を使用し、ユーザーのブログへリンクします。
 * 本番アカウントに実際のPinが1件作成されます。
 */
function Pinterest本番Pin投稿テスト() {
  var boardId = Pinterest本命ボード自動設定();
  if (!boardId) {
    throw new Error('Pinterest本命ボードIDを設定できませんでした。');
  }

  var imageUrl = 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=1200&q=80';
  var title = '仕事終わりに作れる簡単料理｜一人暮らし・単身赴任ごはん';
  var description = '仕事終わりでも作りやすい簡単料理。一人暮らし・単身赴任のリアルな料理と、料理をラクにする道具をブログで紹介しています。';
  var link = 'https://tansinfuninkazu.hatenablog.com/';

  Logger.log('本番Pin投稿開始');
  Logger.log('BOARD ID: ' + boardId);
  Logger.log('IMAGE URL: ' + imageUrl);

  var result = PinterestPin作成(imageUrl, title, description, link);
  Logger.log('本番Pinterest Pin投稿成功');
  Logger.log(result);
  return result;
}
