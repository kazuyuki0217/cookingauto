/*************************************************
 * 料理アフィリエイト自動化
 * Cloud記事生成エンジン
 *
 * 目的:
 * GitHub Actions側で行っていた「写真→記事本文生成」を
 * Google Apps Script + Gemini APIへ移行する。
 *
 * 既存の楽天・Pinterest・Hatena機能には触れない。
 * GEMINI_API_KEY はGASのScript Propertiesから取得する。
 *************************************************/

function generateArticleFromCloud_(imageBase64, mimeType) {
  if (!imageBase64) throw new Error('料理写真のBase64データがありません。');

  var apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!apiKey) throw new Error('GEMINI_API_KEY がGASのScript Propertiesに設定されていません。');

  var prompt = [
    'あなたは料理ブログの記事編集者です。',
    '添付された料理写真を観察し、日本語で「一人暮らし・単身赴任の仕事終わりでも作りやすい料理記事」を作成してください。',
    '',
    '写真から確認できる特徴を優先してください。写真だけでは確定できない材料・分量・調味料は断定しないでください。',
    '記事には次を含めてください。',
    '1. 検索されやすく、クリックしたくなるタイトル',
    '2. 料理名',
    '3. 実際に作った体験として自然な導入',
    '4. 材料',
    '5. 作り方',
    '6. 仕事終わり向けの時短・節約ポイント',
    '7. 失敗しにくくするポイント',
    '8. この料理に合うキッチン用品を自然に紹介する文章',
    '9. まとめ',
    '',
    '出力形式は必ず次の形式にしてください。',
    '1行目: TITLE: タイトル',
    '2行目: DISH_NAME: 料理名',
    '3行目以降: はてなブログへそのまま入れられるHTML本文',
    '',
    'AIが食べた・AIが作った等の表現は禁止。読者に自然に読まれる生活ブログの文章にしてください。'
  ].join('\n');

  var models = ['gemini-2.5-flash', 'gemini-2.5-flash-lite'];
  var lastError = '';

  for (var i = 0; i < models.length; i++) {
    try {
      var result = callGeminiCloud_(apiKey, models[i], prompt, imageBase64, mimeType || 'image/jpeg');
      if (result) return parseCloudArticle_(result);
    } catch (e) {
      lastError = e && e.message ? e.message : String(e);
      console.log('Gemini記事生成失敗 ' + models[i] + ': ' + lastError);
    }
  }

  throw new Error('Gemini記事生成に失敗しました: ' + lastError);
}

function callGeminiCloud_(apiKey, model, prompt, imageBase64, mimeType) {
  var url = 'https://generativelanguage.googleapis.com/v1beta/models/' + encodeURIComponent(model) + ':generateContent';
  var payload = {
    contents: [{
      parts: [
        { text: prompt },
        { inline_data: { mime_type: mimeType, data: imageBase64 } }
      ]
    }]
  };

  var response = UrlFetchApp.fetch(url + '?key=' + encodeURIComponent(apiKey), {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  var code = response.getResponseCode();
  var body = response.getContentText();
  if (code < 200 || code >= 300) throw new Error('Gemini API HTTP ' + code + '\n' + body);

  var data = JSON.parse(body);
  var text = data && data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts && data.candidates[0].content.parts[0] && data.candidates[0].content.parts[0].text;
  if (!text) throw new Error('Geminiから記事本文が返りませんでした。');
  return text.trim();
}

function parseCloudArticle_(text) {
  var lines = String(text).split(/\r?\n/);
  var title = '';
  var dishName = '';
  var bodyStart = 0;

  if (lines.length > 0 && /^TITLE\s*:/i.test(lines[0])) {
    title = lines[0].replace(/^TITLE\s*:/i, '').trim();
    bodyStart = 1;
  }
  if (lines.length > bodyStart && /^DISH_NAME\s*:/i.test(lines[bodyStart])) {
    dishName = lines[bodyStart].replace(/^DISH_NAME\s*:/i, '').trim();
    bodyStart++;
  }

  var body = lines.slice(bodyStart).join('\n').trim();
  if (!title) throw new Error('記事タイトルを取得できませんでした。');
  if (!dishName) dishName = title;
  if (!body) throw new Error('記事本文を取得できませんでした。');

  return { title: title, dish_name: dishName, body: body };
}

/**
 * Web API等から呼ぶ場合の安全なラッパー。
 * 既存doPost/doGetとは競合しない名前にしている。
 */
function cloudArticleGenerate(payload) {
  if (!payload || !payload.imageBase64) throw new Error('imageBase64 が必要です。');
  return generateArticleFromCloud_(payload.imageBase64, payload.mimeType || 'image/jpeg');
}
