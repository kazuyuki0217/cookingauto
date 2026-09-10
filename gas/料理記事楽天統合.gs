/*************************************************
 * 料理アフィリエイト自動化
 * 料理記事楽天統合.gs
 *
 * 目的
 * ・楽天認証情報をGitHubへ二重登録しない
 * ・GASに保存済みの楽天認証をそのまま利用
 * ・料理名から料理との親和性が高い商品を自動選定
 * ・ユーザー固有のaffiliateUrlを記事HTMLへ組み込む
 * ・既存のコード.gs / RakutenAffiliate.gsを変更しない
 *************************************************/

function KAZU_ARTICLE_ESCAPE_(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function KAZU_ARTICLE_PRODUCT_KEYWORDS_(dishName) {
  dishName = String(dishName || '').trim();
  var keywords = [];

  if (dishName) {
    keywords.push(dishName + ' フライパン');
    keywords.push(dishName + ' 調理器具');
  }

  keywords.push('26cm フライパン');
  keywords.push('キッチン用品 一人暮らし');

  return keywords;
}

function KAZU_ARTICLE_PRODUCT_SCORE_(item, dishName) {
  var name = String(item.itemName || '').toLowerCase();
  var dish = String(dishName || '').toLowerCase();
  var average = Number(item.reviewAverage || 0);
  var count = Number(item.reviewCount || 0);
  var score = average * 20 + Math.log(count + 1) * 8;

  if (name.indexOf('フライパン') !== -1) score += 25;
  if (name.indexOf('鍋') !== -1) score += 8;
  if (name.indexOf('包丁') !== -1) score += 5;
  if (dish && name.indexOf(dish) !== -1) score += 12;

  return score;
}

function KAZU_ARTICLE_PICK_PRODUCTS_(dishName, limit) {
  dishName = String(dishName || '').trim();
  limit = Number(limit || 3);

  if (!dishName) {
    throw new Error('料理名が指定されていません。');
  }

  var keywords = KAZU_ARTICLE_PRODUCT_KEYWORDS_(dishName);
  var map = {};

  keywords.forEach(function(keyword) {
    var result = RAKUTEN2_search(keyword);
    var items = result && result.items ? result.items : [];

    items.forEach(function(item) {
      var url = String(item.affiliateUrl || item.itemUrl || '').trim();
      if (!url) return;

      var key = String(item.itemCode || url);
      if (!map[key]) {
        map[key] = {
          itemName: item.itemName || '',
          itemPrice: item.itemPrice || '',
          itemUrl: item.itemUrl || '',
          affiliateUrl: url,
          shopName: item.shopName || '',
          imageUrl: item.imageUrl || '',
          reviewCount: Number(item.reviewCount || 0),
          reviewAverage: Number(item.reviewAverage || 0),
          score: KAZU_ARTICLE_PRODUCT_SCORE_(item, dishName)
        };
      }
    });
  });

  var products = Object.keys(map).map(function(key) {
    return map[key];
  });

  products.sort(function(a, b) {
    return b.score - a.score;
  });

  return products.slice(0, limit);
}

function KAZU_ARTICLE_CTA_(index) {
  var ctas = [
    '▶ 「これなら毎日使えそう」な調理道具を見てみる',
    '▶ この料理を作るなら気になるキッチン用品を見てみる',
    '▶ 一人暮らしの自炊に使いやすそうな道具を見てみる'
  ];
  return ctas[index % ctas.length];
}

function KAZU_ARTICLE_PRODUCTS_HTML_(products) {
  if (!products || !products.length) {
    throw new Error('記事に掲載できる楽天商品が見つかりませんでした。');
  }

  var html = '<section>\n<h2>この料理で気になったキッチン用品</h2>\n';
  html += '<p>料理を作っていると、「もう少しラクにできたら」と思う場面があります。今回の料理と相性がよく、自炊で使いやすそうなものを楽天市場から選びました。</p>\n';

  products.forEach(function(product, index) {
    html += '<div class="rakuten-affiliate-item">\n';
    html += '<p><strong>' + KAZU_ARTICLE_ESCAPE_(product.itemName) + '</strong></p>\n';
    if (product.itemPrice) {
      html += '<p>価格：' + KAZU_ARTICLE_ESCAPE_(String(product.itemPrice)) + '円</p>\n';
    }
    if (product.reviewAverage) {
      html += '<p>レビュー平均：' + KAZU_ARTICLE_ESCAPE_(String(product.reviewAverage)) + '（' + KAZU_ARTICLE_ESCAPE_(String(product.reviewCount)) + '件）</p>\n';
    }
    html += '<p><a href="' + KAZU_ARTICLE_ESCAPE_(product.affiliateUrl) + '">' + KAZU_ARTICLE_ESCAPE_(KAZU_ARTICLE_CTA_(index)) + '</a></p>\n';
    html += '</div>\n';
  });

  html += '</section>\n';
  return html;
}

function 料理記事楽天統合生成(dishName, title, body, imageUrl) {
  dishName = String(dishName || '').trim();
  title = String(title || ('51歳、単身赴任。仕事終わりに作る' + dishName)).trim();
  body = String(body || '').trim();
  imageUrl = String(imageUrl || '').trim();

  if (!dishName) throw new Error('料理名が必要です。');
  if (!body) throw new Error('記事本文が必要です。');
  if (!imageUrl) throw new Error('料理写真URLが必要です。完成記事には料理写真を必須にします。');

  var products = KAZU_ARTICLE_PICK_PRODUCTS_(dishName, 3);
  if (products.length === 0) throw new Error('楽天商品を3件選定できませんでした。');

  var html = '<article>\n';
  html += '<h1>' + KAZU_ARTICLE_ESCAPE_(title) + '</h1>\n';
  html += '<p><img src="' + KAZU_ARTICLE_ESCAPE_(imageUrl) + '" alt="' + KAZU_ARTICLE_ESCAPE_(dishName) + '" loading="lazy"></p>\n';
  html += body + '\n';
  html += KAZU_ARTICLE_PRODUCTS_HTML_(products);
  html += '</article>\n';

  PropertiesService.getScriptProperties().setProperty('COOKING_ARTICLE_HTML', html);
  PropertiesService.getScriptProperties().setProperty('COOKING_ARTICLE_LAST_DISH', dishName);
  PropertiesService.getScriptProperties().setProperty('COOKING_ARTICLE_LAST_UPDATED_AT', new Date().toISOString());

  return {
    success: true,
    dishName: dishName,
    title: title,
    productCount: products.length,
    products: products,
    html: html
  };
}

function 料理記事楽天統合テスト() {
  var props = PropertiesService.getScriptProperties();
  var dishName = props.getProperty('COOKING_TEST_DISH_NAME') || '豚の生姜焼き';
  var imageUrl = props.getProperty('COOKING_TEST_IMAGE_URL') || '';
  var body = props.getProperty('COOKING_TEST_BODY') || '<p>仕事終わりに、できるだけ手間を増やさずに作った一皿です。</p><p>焼いている間に立ち上る香りで、疲れていても食欲が戻ってきます。</p>';

  if (!imageUrl) {
    throw new Error('テスト用料理写真URLが未設定です。Script PropertiesのCOOKING_TEST_IMAGE_URLに公開画像URLを設定してください。');
  }

  var result = 料理記事楽天統合生成(
    dishName,
    '51歳、単身赴任。仕事終わりに作る' + dishName,
    body,
    imageUrl
  );

  Logger.log('料理記事楽天統合テスト成功');
  Logger.log('料理名: ' + result.dishName);
  Logger.log('楽天商品件数: ' + result.productCount);
  result.products.forEach(function(product, index) {
    Logger.log('商品' + (index + 1) + ': ' + product.itemName);
    Logger.log('アフィリエイトURL: ' + product.affiliateUrl);
  });

  return result;
}

function 料理記事楽天完成HTML取得() {
  var html = PropertiesService.getScriptProperties().getProperty('COOKING_ARTICLE_HTML');
  if (!html) throw new Error('完成HTMLがまだ生成されていません。「料理記事楽天統合テスト」または「料理記事楽天統合生成」を実行してください。');
  return html;
}
