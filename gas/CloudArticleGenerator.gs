/**
 * Gemini → Claude風 記事生成エンジン
 * Gemini APIキーは既存のGitHub Actions Secretから渡す。
 * Claude APIは使用しない。
 *
 * 方針:
 * Geminiを生成エンジンとして使い、Claude系の
 * 「生活感・読者への共感・自然なストーリー・押しつけない商品導線」
 * をプロンプト設計として取り込む。
 */

function cloudArticleGenerate(options) {
  options = options || {};
  var imageBase64 = String(options.imageBase64 || '');
  var mimeType = String(options.mimeType || 'image/jpeg');
  var apiKey = String(options.geminiApiKey || '').trim();

  if (!imageBase64) throw new Error('料理写真がありません。');
  if (!apiKey) throw new Error('GEMINI_API_KEYが記事生成リクエストに渡されていません。');

  var prompt = [
    'あなたは日本語の料理ブログ編集者兼コピーライターです。',
    '添付された料理写真を起点に、読者が「自分の生活に置き換えて」読み進められる自然なブログ記事を作成してください。',
    '',
    '【最重要：事実性】',
    '写真から確認できない材料・分量・調理工程・味・購入履歴などを事実として創作しないでください。',
    '写真だけでは断定できない内容は、一般的な提案として明確に表現してください。',
    'AIが料理を作った、食べた、感じたという一人称の体験を創作しないでください。',
    '',
    '【読者】',
    '仕事終わりに一人分の料理を作る人、一人暮らし・単身赴任で自炊する人です。',
    '料理上級者ではなく、「疲れていても作れそう」「これなら自分にもできそう」と感じる読者を想定してください。',
    '',
    '【文章設計：Claude風】',
    '単なるレシピ説明から始めず、仕事終わり・疲れ・食費・洗い物・料理の面倒さなど、読者が共感できる具体的な生活場面から自然に入ってください。',
    '短い文と長い文を混ぜ、説明が続きすぎない読みやすいリズムにしてください。',
    '「〜ですよね」「〜だったりします」のような自然な会話感は適度に使って構いませんが、多用しないでください。',
    '大げさな煽り、過剰なSEOキーワード、定型的なAI表現、「いかがでしたか？」は禁止です。',
    '料理の魅力だけでなく、「なぜ忙しい一人暮らしの人に役立つのか」を具体的に伝えてください。',
    '',
    '【読者の行動を考えた構成】',
    '読者は最初から商品を買うつもりで来ているとは限りません。',
    'まず料理そのものへの興味、次に「自分でもできそう」という安心、その後に「これなら少しラクになりそう」という必要性が生まれる順番を意識してください。',
    '商品を先に売ろうとせず、読者の小さな不便を文章の中で先に発見させてください。',
    'その不便を解決する道具が自然に思い浮かぶようにしてください。',
    '',
    '【記事構成】',
    '1. 強いタイトル：検索意図と読みたくなるフックを両立',
    '2. 共感を生む導入',
    '3. 料理の魅力・食卓でのイメージ',
    '4. 材料',
    '5. 作り方',
    '6. 時短・節約・洗い物などの実用ポイント',
    '7. 調理中に実際に困りやすいポイントと、それを減らす考え方',
    '8. まとめ',
    '',
    '【楽天アフィリエイト導線：最重要】',
    '記事末尾に「おすすめ商品一覧」「今回のおすすめ」「商品はこちら」などの広告コーナーを作らないでください。',
    '商品リンクは後工程で本文中へ自然に分散挿入します。',
    'そのため、調理器具が役立つ具体的な場面を本文の流れの中に自然に作ってください。',
    '例：肉を焼く→フライパンの扱いやすさ、材料を切る→包丁やまな板、残りを保存→保存容器、など。',
    '「おすすめです」「ぜひチェック」「楽天で見てみる」「購入はこちら」のような露骨なCTAを本文に作らないでください。',
    '読者が自分で「こういう道具があるとラクかも」と気づける文章を優先してください。',
    '',
    '【心理設計】',
    '使える心理要素は、共感、具体的な使用場面、損失回避、社会的証明、選択肢の少なさ、信頼性、自己投影です。',
    'ただし、嘘のレビュー数・人気・売り切れ・限定・値下げ・実体験は絶対に作らないでください。',
    '「買わせる」より「判断しやすくする」ことを優先してください。',
    '読者が商品ページへ進む理由は、商品そのものの宣伝ではなく、記事中で生まれた具体的な悩みや欲求と結び付けてください。',
    '',
    '【出力】',
    '最初の行を TITLE: 記事タイトル、2行目を DISH_NAME: 料理名、その後に本文HTMLを出力してください。',
    '本文はブログへそのまま渡せるHTMLにしてください。',
    'TITLE: と DISH_NAME: 以外の前置き、解説、Markdownコードブロックは不要です。'
  ].join('\n');

  var models = ['gemini-3.5-flash', 'gemini-3.5-flash-lite'];
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
