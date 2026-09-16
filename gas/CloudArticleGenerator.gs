/**
 * Cloud記事生成エンジン
 * Gemini APIキーは既存のGitHub Actions SecretからCloudArticleGeneratorへ渡す。
 * GAS Script Propertiesへの新規キー登録は不要。
 */

function cloudArticleGenerate(options) {
  options = options || {};
  var imageBase64 = String(options.imageBase64 || '');
  var mimeType = String(options.mimeType || 'image/jpeg');
  var apiKey = String(options.geminiApiKey || '').trim();

  if (!imageBase64) throw new Error('料理写真がありません。');
  if (!apiKey) throw new Error('GEMINI_API_KEYがCloud記事生成リクエストに渡されていません。');

  var prompt = [
    'あなたは日本語の料理記事編集者です。',
    '添付された料理写真を分析し、実際に写真から確認できる内容を中心に、自然な日本語の記事を作成してください。',
    '読者は仕事終わりに一人分の簡単・節約料理を作る人です。',
    '写真から確認できない材料や調理工程を事実として創作しないでください。',
    '記事本文には料理の感想、材料、作り方、時短・節約ポイントを含めてください。',
    'AIが料理を食べた・作ったという表現は禁止です。',
    '最初の行を TITLE: 記事タイトル、2行目を DISH_NAME: 料理名、その後に本文HTMLを出力してください。',
    'TITLE: と DISH_NAME: 以外の前置きやMarkdownコードブロックは不要です。'
  ].join('\n');

  var models = ['gemini-2.5-flash', 'gemini-2.5-flash-lite'];
  var lastError = '';

  for (var i = 0; i < models.length; i++) {
    try {
      var url = 'https://generativelanguage.googleapis.com/v1beta/models/' +
        encodeURIComponent(models[i]) + ':generateContent?key=' + encodeURIComponent(apiKey);

      var payload = {
        contents: [{
          parts: [
            { text: prompt },
            { inline_data: { mime_type: mimeType, data: imageBase64 } }
          ]
        }]
      };

      var response = UrlFetchApp.fetch(url, {
        method: 'post',
        contentType: 'application/json',
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      });

      var code = response.getResponseCode();
      var text = response.getContentText();
      if (code < 200 || code >= 300) {
        lastError = 'Gemini API HTTP ' + code + ': ' + text.slice(0, 500);
        continue;
      }

      var data = JSON.parse(text);
      var generated = data && data.candidates && data.candidates[0] &&
        data.candidates[0].content && data.candidates[0].content.parts &&
        data.candidates[0].content.parts[0] && data.candidates[0].content.parts[0].text;

      if (!generated) {
        lastError = 'Gemini APIから本文が返りませんでした。';
        continue;
      }

      var titleMatch = generated.match(/(?:^|\n)TITLE:\s*(.+)/i);
      var dishMatch = generated.match(/(?:^|\n)DISH_NAME:\s*(.+)/i);
      var title = titleMatch ? titleMatch[1].trim() : '今日の一人ごはん';
      var dishName = dishMatch ? dishMatch[1].trim() : title;
      var body = generated
        .replace(/(?:^|\n)TITLE:\s*.+/i, '')
        .replace(/(?:^|\n)DISH_NAME:\s*.+/i, '')
        .trim();

      return {
        title: title,
        dish_name: dishName,
        body: body
      };
    } catch (error) {
      lastError = String(error && error.message ? error.message : error);
    }
  }

  throw new Error('Gemini記事生成に失敗しました: ' + lastError);
}
