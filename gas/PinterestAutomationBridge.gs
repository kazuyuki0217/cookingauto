/**
 * Pinterest自動投稿ブリッジ
 * GitHub Actionsから5件のPinデータを受け取り、既存のPinterest処理を実行する。
 * Cloud記事生成はGitHub Actionsの既存GEMINI_API_KEYを受け取り、Geminiへ渡す。
 *
 * セキュリティ:
 * - PINTEREST_AUTOMATION_SECRETはScript Propertiesに保存
 * - Pinterestアクセストークン/refresh tokenはGitHubへ渡さない
 * - 楽天API認証情報もScript Propertiesからのみ取得
 * - GEMINI_API_KEYはGitHub Actions SecretからHTTPSでCloud記事生成時だけ渡す
 */

function KAZU_PINTEREST_AUTOMATION_SECRET_() {
  var secret = KAZU_PROP_('PINTEREST_AUTOMATION_SECRET');
  if (!secret) throw new Error('PINTEREST_AUTOMATION_SECRETがScript Propertiesに未登録です。');
  return secret;
}

function KAZU_PINTEREST_AUTOMATION_JSON_(success, data) {
  var result = data || {};
  result.success = success;
  return ContentService
    .createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}

function KAZU_PINTEREST_EXISTING_PIN_KEYS_() {
  var boardId = KAZU_PROP_('PINTEREST_BOARD_ID');
  if (!boardId) return {};
  var seen = {};
  var bookmark = '';
  for (var page = 0; page < 10; page++) {
    var endpoint = '/boards/' + encodeURIComponent(boardId) + '/pins?page_size=100';
    if (bookmark) endpoint += '&bookmark=' + encodeURIComponent(bookmark);
    var data = KAZU_PIN_GET_(endpoint);
    var pins = data && Array.isArray(data.items) ? data.items : [];
    pins.forEach(function(pin) {
      var title = String(pin.title || '').trim();
      var link = String(pin.link || '').trim();
      if (title && link) seen[title + '\n' + link] = String(pin.id || '');
    });
    bookmark = String(data && data.bookmark ? data.bookmark : '').trim();
    if (!bookmark || pins.length === 0) break;
  }
  return seen;
}

function KAZU_RAKUTEN_BROWSER_PAGE_(keyword, hits) {
  var template = HtmlService.createTemplateFromFile('RakutenBrowserBridge');
  template.configJson = JSON.stringify({
    applicationId: KAZU_RAKUTEN_APP_ID_(),
    accessKey: KAZU_RAKUTEN_KEY_(),
    affiliateId: KAZU_RAKUTEN_AFFILIATE_ID_(),
    keyword: String(keyword || '').trim() || 'フライパン',
    hits: Math.max(1, Math.min(Number(hits || 10), 30))
  });
  return template.evaluate()
    .setTitle('楽天商品検索')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// WebアプリのdoGetはコード.gs側を正式な入口として使用する。
// このブリッジ側には同名doGetを置かず、Pinterest/Rakuten自動投稿の既存処理を保持する。
function KAZU_PINTEREST_AUTOMATION_DOGET_(e) {
  try {
    var params = e && e.parameter ? e.parameter : {};
    var service = String(params.service || '').trim();
    var secret = String(params.secret || '').trim();
    if (service === 'rakuten_browser') {
      var expectedBrowser = KAZU_PINTEREST_AUTOMATION_SECRET_();
      if (!secret || secret !== expectedBrowser) {
        return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error: '認証に失敗しました。'});
      }
      return KAZU_RAKUTEN_BROWSER_PAGE_(params.keyword, params.hits);
    }
    if (service === 'rakuten_key') {
      var expected = KAZU_PINTEREST_AUTOMATION_SECRET_();
      if (!secret || secret !== expected) {
        return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error: '認証に失敗しました。'});
      }
      return KAZU_PINTEREST_AUTOMATION_JSON_(true, {accessKey: KAZU_RAKUTEN_KEY_()});
    }
    return KAZU_PINTEREST_AUTOMATION_JSON_(true, {service: 'health', status: 'ok'});
  } catch (error) {
    return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
      error: String(error && error.message ? error.message : error)
    });
  }
}

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error:'POSTデータがありません。'});
    }
    var body;
    try {
      body = JSON.parse(e.postData.contents);
    } catch (parseError) {
      return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error:'JSON解析に失敗しました。'});
    }

    var expected = KAZU_PINTEREST_AUTOMATION_SECRET_();
    if (!body.secret || body.secret !== expected) {
      return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error:'認証に失敗しました。'});
    }

    // Cloud記事生成は既存の楽天・Pinterest処理より先に分岐する。
    if (body.service === 'cloud_article') {
      if (!body.imageBase64) {
        return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
          error: 'cloud_articleにはimageBase64が必要です。'
        });
      }
      if (!body.geminiApiKey) {
        return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
          error: 'GEMINI_API_KEYがCloud記事生成リクエストに渡されていません。'
        });
      }
      var article = cloudArticleGenerate({
        imageBase64: String(body.imageBase64),
        mimeType: String(body.mimeType || 'image/jpeg'),
        geminiApiKey: String(body.geminiApiKey)
      });
      return KAZU_PINTEREST_AUTOMATION_JSON_(true, {
        service: 'cloud_article',
        title: article.title,
        dish_name: article.dish_name,
        body: article.body
      });
    }

    if (body.service === 'rakuten') {
      return KAZU_RAKUTEN_AUTOMATION_(body);
    }

    // 5件を即時連続投稿せず、GASの時間主導トリガーで分散予約する。
    if (body.service === 'pinterest_schedule') {
      return KAZU_PINTEREST_SCHEDULE_(body.pins);
    }

    var pins = body.pins;
    if (!Array.isArray(pins) || pins.length !== 5) {
      return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
        error:'Pinterest投稿データは5件必要です。',
        count:Array.isArray(pins) ? pins.length : 0
      });
    }

    var existing = KAZU_PINTEREST_EXISTING_PIN_KEYS_();
    var results = [];
    for (var i = 0; i < pins.length; i++) {
      var pin = pins[i] || {};
      if (!pin.imageUrl || !pin.title || !pin.link) {
        return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
          error:'Pin ' + (i + 1) + ' にimageUrl/title/linkのいずれかがありません。'
        });
      }
      var title = String(pin.title);
      var link = String(pin.link);
      var key = title.trim() + '\n' + link.trim();
      var existingId = existing[key] || '';
      if (existingId) {
        results.push({index: i + 1, id: existingId, success: true, skipped: true, reason: '同一title+linkのPinが既に存在'});
        continue;
      }
      var result = PinterestPin作成(String(pin.imageUrl), title, String(pin.description || ''), link);
      results.push({index: i + 1, id: result && result.id ? String(result.id) : '', success: true, skipped: false});
      if (i < pins.length - 1) Utilities.sleep(1500);
    }
    return KAZU_PINTEREST_AUTOMATION_JSON_(true, {
      count: results.length,
      results: results,
      skippedCount: results.filter(function(item) { return item.skipped; }).length
    });
  } catch (error) {
    return KAZU_PINTEREST_AUTOMATION_JSON_(false, {
      error: String(error && error.message ? error.message : error)
    });
  }
}

function Pinterest自動投稿ブリッジ設定確認() {
  var props = PropertiesService.getScriptProperties().getProperties();
  return {
    automationSecret: props.PINTEREST_AUTOMATION_SECRET ? '登録済み' : '未登録',
    pinterestAccessToken: props.PINTEREST_ACCESS_TOKEN ? '登録済み' : '未登録',
    pinterestRefreshToken: props.PINTEREST_REFRESH_TOKEN ? '登録済み' : '未登録',
    pinterestBoardId: props.PINTEREST_BOARD_ID || '未登録'
  };
}


/* ================= Pinterest 5件分散予約投稿 ================= */
function KAZU_PINTEREST_SCHEDULE_(pins) {
  if (!Array.isArray(pins) || pins.length !== 5) return KAZU_PINTEREST_AUTOMATION_JSON_(false, {error:'Pinterest予約投稿データは5件必要です。',count:Array.isArray(pins)?pins.length:0});
  var existing=KAZU_PINTEREST_EXISTING_PIN_KEYS_();
  var targets=['07:00','11:30','15:00','18:30','21:30'];
  var jstNow=new Date(new Date().getTime()+9*60*60*1000);
  var y=jstNow.getUTCFullYear(), m=jstNow.getUTCMonth(), d=jstNow.getUTCDate()+1;
  var queue=[];
  for(var i=0;i<5;i++){
    var pin=pins[i]||{};
    if(!pin.imageUrl||!pin.title||!pin.link) return KAZU_PINTEREST_AUTOMATION_JSON_(false,{error:'Pin '+(i+1)+' にimageUrl/title/linkのいずれかがありません。'});
    var key=String(pin.title).trim()+'\\n'+String(pin.link).trim();
    var parts=targets[i].split(':');
    var scheduledAt=new Date(Date.UTC(y,m,d,Number(parts[0])-9,Number(parts[1]),0,0));
    queue.push({index:i+1,pin:pin,scheduledAt:scheduledAt.toISOString(),status:existing[key]?'success':'pending',id:existing[key]||'',attempts:0});
  }
  var props=PropertiesService.getScriptProperties();
  props.setProperty('PINTEREST_SCHEDULE_QUEUE',JSON.stringify({createdAt:new Date().toISOString(),queue:queue,successCount:queue.filter(function(x){return x.status==='success';}).length}));
  ScriptApp.getProjectTriggers().forEach(function(t){if(t.getHandlerFunction()==='KAZU_PINTEREST_SCHEDULE_WORKER_') ScriptApp.deleteTrigger(t);});
  queue.forEach(function(item){if(item.status==='pending') ScriptApp.newTrigger('KAZU_PINTEREST_SCHEDULE_WORKER_').timeBased().at(new Date(item.scheduledAt)).create();});
  return KAZU_PINTEREST_AUTOMATION_JSON_(true,{service:'pinterest_schedule',count:5,scheduledCount:queue.filter(function(x){return x.status==='pending';}).length,schedule:targets,scheduledFor:y+'-'+('0'+(m+1)).slice(-2)+'-'+('0'+d).slice(-2)});
}
function KAZU_PINTEREST_SCHEDULE_WORKER_(){
  var lock=LockService.getScriptLock(); if(!lock.tryLock(30000)) return;
  try{
    var props=PropertiesService.getScriptProperties(),raw=props.getProperty('PINTEREST_SCHEDULE_QUEUE'); if(!raw)return;
    var data=JSON.parse(raw),queue=data.queue||[],now=Date.now(),target=null;
    for(var i=0;i<queue.length;i++){if(queue[i].status==='pending'&&new Date(queue[i].scheduledAt).getTime()<=now+10*60*1000){target=queue[i];break;}}
    if(!target)return;
    target.attempts=Number(target.attempts||0)+1;
    try{
      var existing=KAZU_PINTEREST_EXISTING_PIN_KEYS_(),key=String(target.pin.title).trim()+'\\n'+String(target.pin.link).trim();
      if(existing[key]){target.id=existing[key];target.status='success';}
      else{var result=PinterestPin作成(String(target.pin.imageUrl),String(target.pin.title),String(target.pin.description||''),String(target.pin.link));target.id=result&&result.id?String(result.id):'';target.status=target.id?'success':'pending';}
      target.completedAt=new Date().toISOString();
    }catch(error){target.status='pending';target.lastError=String(error&&error.message?error.message:error);ScriptApp.newTrigger('KAZU_PINTEREST_SCHEDULE_WORKER_').timeBased().at(new Date(Date.now()+10*60*1000)).create();}
    data.queue=queue;data.updatedAt=new Date().toISOString();data.successCount=queue.filter(function(x){return x.status==='success';}).length;props.setProperty('PINTEREST_SCHEDULE_QUEUE',JSON.stringify(data));
  }finally{lock.releaseLock();}
}
function Pinterest5件予約状態(){var raw=PropertiesService.getScriptProperties().getProperty('PINTEREST_SCHEDULE_QUEUE');if(!raw)return{success:false,count:0,message:'予約データなし'};try{var data=JSON.parse(raw);return{success:true,count:(data.queue||[]).length,successCount:data.successCount||0,queue:data.queue||[],createdAt:data.createdAt||'',updatedAt:data.updatedAt||''};}catch(e){return{success:false,count:0,message:'予約データJSONエラー'};}}
