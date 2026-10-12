const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function worker(extraChrome = {}) {
  const context = vm.createContext({
    console, URL, setTimeout: (fn) => { fn(); },
    chrome: {
      sidePanel: { setPanelBehavior: async () => {} },
      runtime: { onMessage: { addListener() {} } },
      ...extraChrome,
    },
  });
  context.importScripts = (...files) => files.forEach(file =>
    vm.runInContext(fs.readFileSync(path.join(__dirname, file), 'utf8'), context));
  vm.runInContext(fs.readFileSync(path.join(__dirname, 'background.js'), 'utf8'), context);
  return context;
}

function durableWorker(saved = {}) {
  const clone = value => JSON.parse(JSON.stringify(value));
  return worker({storage:{local:{
    get: (_keys, callback) => callback(clone(saved)),
    set: (values, callback) => {Object.assign(saved, clone(values)); callback();},
  }}});
}

function protocolJob(overrides = {}) {
  return {job_id:'job-1', protocol_version:2, channel_id:'main', target_handle:'@mainuser', strict_mode:false,
    status:'claimed', lease_owner:'instance-1', lease_token:'token-1', revision:2, payload_hash:'frozen-hash',
    video_path:'canonical.mp4', caption:'server caption', hashtags:'#server', ...overrides};
}

async function seedJob(ctx, job = protocolJob()) {
  const state = await ctx.postingState();
  state.instanceId = job.lease_owner;
  state.channelId = job.channel_id;
  state.activeJob = job;
  await ctx.persistPostingState(state);
  return job;
}

test('account changing during attempt reply is checked in the actual click expression',async () => {
  const ctx=durableWorker();
  const job=await seedJob(ctx,protocolJob({lease_expires_at:Date.now()/1000+300}));
  let handle='@mainuser',clicks=0;
  const profile={getAttribute:()=>null,get textContent(){return handle;}};
  const button={closest:()=>null,scrollIntoView(){},click(){clicks+=1;}};
  const dom=vm.createContext({WeakMap,WeakSet,Date,window:{},MutationObserver:class {observe(){} disconnect(){}},
    document:{documentElement:{},querySelectorAll:selector=>selector.includes('profile-icon')?[profile]:[],querySelector:()=>button}});
  const send=async (_method,params) => {
    try {return {result:{value:vm.runInContext(params.expression,dom)}};}
    catch(error){return {exceptionDetails:{exception:{description:error.message}}};}
  };
  ctx.waitForUploadComplete=async()=>true;
  await assert.rejects(()=>ctx.clickPostButton(send,7,async()=>{handle='@wronguser';},job),/account_handle_mismatch/);
  assert.equal(clicks,0);
});

test('DOM observation rejects an old success notice and accepts only a fresh post-click notice',async () => {
  const ctx=worker(); ctx.chrome.tabs={get:async()=>({url:'https://www.tiktok.com/tiktokstudio/upload'})};
  const notice={textContent:'Posted successfully',checkVisibility:()=>true};
  let callback;
  const dom=vm.createContext({WeakMap,WeakSet,window:{},MutationObserver:class {constructor(fn){callback=fn;} observe(){} disconnect(){}},
    document:{documentElement:{},querySelectorAll:()=>[notice],querySelector:()=>({})}});
  const send=async (_method,params)=>({result:{value:vm.runInContext(params.expression,dom)}});
  await ctx.observePostConfirmation(send,'attempt-1');
  dom.window.__omnicutPostObservation.clicked=true;
  assert.equal((await ctx.waitForPostConfirmation(send,7,5,'attempt-1')).confirmed,false);
  callback([{addedNodes:[notice]}]);
  const confirmed=await ctx.waitForPostConfirmation(send,7,5,'attempt-1');
  assert.equal(confirmed.confirmed,true);
  assert.equal(confirmed.proof.confirmation_token,'attempt-1');
  assert.equal((await ctx.waitForPostConfirmation(send,7,5,'another-attempt')).confirmed,false);
});

test('release persists only after backend confirmation and recovers a lost response',async () => {
  const saved={},ctx=durableWorker(saved),job=await seedJob(ctx);
  let calls=0;
  ctx.postingRequest=async route=> {
    if(route.startsWith('/jobs/')) return {...job,status:calls?'cancelled':'claimed',revision:calls?3:2};
    calls+=1;
    if(calls===1) throw new Error('reply lost');
    return {...job,status:'cancelled',revision:3};
  };
  await assert.rejects(()=>ctx.releasePostingJob(),/reply lost/);
  assert.equal(saved.omnicutPostingProtocolV2.activeJob.job_id,'job-1');
  const restarted=durableWorker(saved); restarted.postingRequest=ctx.postingRequest;
  assert.equal((await restarted.releasePostingJob()).success,true);
  assert.equal(saved.omnicutPostingProtocolV2.activeJob,null);
  await restarted.selectPostingChannel('second');
});

test('protocol claim captures channel and rejects old singleton identity', async () => {
  const ctx = durableWorker({omnicutChannelId:'second'});
  const calls = [];
  ctx.postingRequest = async (route, channel, body) => {
    calls.push([route,channel,body]);
    if (route === '/capabilities') return {protocol_version:2,durable_jobs:true};
    if (route === '/pending') return protocolJob({channel_id:'second',status:'prepared'});
    return protocolJob({channel_id:'second',lease_owner:body.lease_owner});
  };
  const job = await ctx.fetchPendingJob();
  assert.equal(job.channel_id,'second');
  assert.deepEqual(calls.map(c => c[1]), ['second','second','second']);
  assert.equal((await ctx.postingState()).activeJob.job_id,'job-1');
  const old = durableWorker();
  old.postingRequest = async route => route === '/capabilities' ? {protocol_version:2,durable_jobs:true} : {video_path:'old.mp4'};
  await assert.rejects(() => old.fetchPendingJob(), /job\/channel identity/);
});

test('account guard blocks known mismatch and secondary unknown before backend/action', async () => {
  for (const [job,handles] of [[protocolJob(),['@wronguser']], [protocolJob({channel_id:'second'}),[]], [protocolJob({strict_mode:true}),[]]]) {
    const ctx = durableWorker();
    await seedJob(ctx,job);
    ctx.postingRequest = async () => {throw new Error('must not reach backend');};
    await assert.rejects(() => ctx.guardPostingAction(job,async () => ({result:{value:{handles}}}),7), /account_handle_mismatch|source_account_required/);
    assert.equal((await ctx.postingState()).activeJob.status,'claimed');
  }
});

test('compat main unknown blocks before backend or upload', async () => {
  const ctx = durableWorker();
  const job = await seedJob(ctx);
  ctx.postingRequest = async () => {throw new Error('must not contact backend');};
  await assert.rejects(() => ctx.guardPostingAction(job,async () => ({result:{value:{handles:[]}}}),7), /source_account_required/);
  assert.equal(job.revision,2);
});

test('tab and captured channel fencing reject another upload target', async () => {
  const ctx = durableWorker();
  const job = await seedJob(ctx);
  const state = await ctx.postingState(); state.tabId = 7; await ctx.persistPostingState(state);
  const send = async () => {throw new Error('must not evaluate');};
  await assert.rejects(() => ctx.guardPostingAction(job,send,8), /tab ที่ผูกงาน/);
  state.channelId = 'second';
  await assert.rejects(() => ctx.guardPostingAction(job,send,7), /snapshot/);
});

test('durable attempt survives worker restart and blocks a second automatic click', async () => {
  const saved = {};
  const ctx = durableWorker(saved);
  const job = await seedJob(ctx);
  ctx.postingRequest = async (route,channel,body) => {
    assert.equal(route,'/attempt'); assert.equal(body.source_account,'@mainuser');
    return {...job,status:'publishing',revision:3};
  };
  await ctx.guardPostingAction(job,async () => ({result:{value:{handles:['@mainuser']}}}),7,{beginPublish:true});
  const restarted = durableWorker(saved);
  const recovered = await restarted.fetchPendingJob();
  assert.equal(recovered.status,'publishing');
  await assert.rejects(() => restarted.guardPostingAction(recovered,async () => {throw new Error('must not click');},7,{beginPublish:true}), /ห้ามกดโพสต์ซ้ำ/);
});

test('ack outage persists receipt; restarted worker retries receipt only, never publishes', async () => {
  const saved = {};
  const ctx = durableWorker(saved);
  const job = await seedJob(ctx,protocolJob({status:'publishing',revision:3}));
  ctx.postingRequest = async () => {throw new Error('offline');};
  await assert.rejects(() => ctx.savePostingReceipt(job,'@mainuser','published',{kind:'platform_success_notice',notice:'Posted successfully'}), /offline/);
  assert.equal(saved.omnicutPostingProtocolV2.pendingReceipt.body.job_id,'job-1');
  const restarted = durableWorker(saved);
  const requests = [];
  restarted.postingRequest = async (route,channel,body) => {
    requests.push(route); assert.equal(channel,'main'); assert.equal(body.payload_hash,'frozen-hash');
    return {...job,status:'published',effects_applied:true};
  };
  await assert.rejects(() => restarted.fetchPendingJob(), /ไม่ได้กดโพสต์ซ้ำ/);
  assert.deepEqual(requests,['/ack']);
  assert.equal(saved.omnicutPostingProtocolV2.pendingReceipt,null);
  assert.equal(saved.omnicutPostingProtocolV2.activeJob,null);
});

test('expired receipt lease uses reconciliation without obtaining a new claim', async () => {
  const ctx = durableWorker();
  const job = await seedJob(ctx,protocolJob({status:'publishing',revision:3}));
  const requests = [];
  ctx.postingRequest = async route => {
    requests.push(route);
    if (route === '/ack') throw new Error('posting_lease_expired');
    return {...job,status:'scheduled_on_platform'};
  };
  const result = await ctx.savePostingReceipt(job,'@mainuser','scheduled_on_platform',{kind:'platform_success_notice',notice:'Scheduled successfully'});
  assert.equal(result.outcome,'scheduled_on_platform');
  assert.deepEqual(requests,['/ack','/reconcile']);
});

test('pending receipt storage failure prevents acknowledgement', async () => {
  const ctx = durableWorker(); const job = await seedJob(ctx);
  ctx.postingStorageSet = async () => {throw new Error('storage failed');};
  ctx.postingRequest = async () => {throw new Error('must not send ack');};
  await assert.rejects(() => ctx.savePostingReceipt(job,'@mainuser','published',{}), /storage failed/);
});

test('channel selection is durable and refuses active or unknown jobs', async () => {
  const saved = {}; const ctx = durableWorker(saved);
  await ctx.selectPostingChannel('second');
  assert.equal((await durableWorker(saved).postingState()).channelId,'second');
  await seedJob(ctx,protocolJob({channel_id:'second',status:'confirmation_unknown'}));
  await assert.rejects(() => ctx.selectPostingChannel('main'), /posting_instance_busy/);
  await assert.rejects(() => ctx.clearPendingJob(), /ห้ามล้าง/);
});

test('final account capture and attempt happen after processing but before click', async () => {
  const ctx = worker(); const calls = [];
  ctx.waitForUploadComplete = async () => {calls.push('processed'); return true;};
  ctx.dismissLeaveConfirmDialogIfPresent = async () => {};
  ctx.waitForPostConfirmation = async () => ({confirmed:true,outcome:'published',proof:{kind:'platform_success_notice',notice:'Posted successfully'}});
  await ctx.clickPostButton(async () => {calls.push('click'); return {result:{value:{success:true}}};},7,async () => {calls.push('capture-account-and-attempt');});
  assert.deepEqual(calls,['processed','capture-account-and-attempt','click']);
});

function panelProtocolContext(authedFetch) {
  const code = fs.readFileSync(path.join(__dirname,'sidepanel.js'),'utf8');
  const ctx = vm.createContext({URL, authedFetch, withApiKeyParam:(url,key) => `${url}?api_key=${key}`});
  vm.runInContext("let activeChannelId='main'; let channelEpoch=0; let apiKey='secret';" +
    code.slice(code.indexOf('function panelChannelId'),code.indexOf('// The very first loadExports()')),ctx);
  return ctx;
}

test('sidepanel sends channel on requests and signed media URLs', async () => {
  const ctx = panelProtocolContext(async (url,key,options) => {
    assert.equal(key,'secret'); assert.equal(options.headers['X-OmniCut-Channel'],'second');
    return {json:async () => ({channel_id:'second'})};
  });
  vm.runInContext("activeChannelId='second';",ctx);
  assert.equal((await (await ctx.scopedPanelFetch('/api/exports')).json()).channel_id,'second');
  const media = new URL(ctx.scopedPanelMedia('http://127.0.0.1:8000/api/media/file.mp4'));
  assert.equal(media.searchParams.get('channel_id'),'second');
  assert.equal(media.searchParams.get('api_key'),'secret');
});

test('sidepanel refuses late A response after A to B to A and foreign response metadata', async () => {
  let resolve;
  const ctx = panelProtocolContext(() => new Promise(done => {resolve=done;}));
  const pending = ctx.scopedPanelFetch('/api/exports');
  vm.runInContext("activeChannelId='second'; channelEpoch++; activeChannelId='main'; channelEpoch++;",ctx);
  resolve({json:async () => ({})});
  await assert.rejects(() => pending,/ช่องเปลี่ยน/);
  const foreign = panelProtocolContext(async () => ({json:async () => ({channel_id:'second'})}));
  await assert.rejects(async () => (await foreign.scopedPanelFetch('/api/exports')).json(), /อีกช่อง/);
});

test('stats bridge captures account with rows and refuses ambiguous logged-in identities', () => {
  const code = fs.readFileSync(path.join(__dirname,'sidepanel.js'),'utf8');
  const start = code.indexOf('        const result = window.OmniCutStatsParser.parsePostsTable(document);');
  const end = code.indexOf('\n      },',start);
  const ctx = vm.createContext({window:{OmniCutStatsParser:{parsePostsTable:() => ({rows:[{title:'fixture'}]})}},
    document:{querySelectorAll:() => [{getAttribute:() => '/@MainUser'}]}});
  vm.runInContext('function captureStats(){' + code.slice(start,end) + '}',ctx);
  assert.equal(ctx.captureStats().source_account,'@mainuser');
  ctx.document.querySelectorAll = () => [{getAttribute:() => '/@MainUser'},{getAttribute:() => '/@OtherUser'}];
  assert.match(ctx.captureStats().error,/หลายบัญชี/);
  ctx.document.querySelectorAll = () => [];
  assert.equal(ctx.captureStats().source_account,null);
});

test('caption action uses immutable server snapshot instead of client override', async () => {
  const ctx = worker(); const job = protocolJob();
  ctx.fetchPendingJob = async () => job;
  ctx.findUploadTab = async () => ({id:7});
  ctx.chrome.debugger = {attach:async () => {},detach:async () => {}};
  ctx.cdp = () => async () => {};
  ctx.waitForCaptionEditor = async () => {};
  ctx.guardPostingAction = async received => {assert.equal(received,job);};
  ctx.typeCaption = async (_send,caption,hashtags) => {assert.equal(caption,'server caption'); assert.equal(hashtags,'#server');};
  await ctx.runTypeCaptionOnly({caption:'forged',hashtags:'#forged'});
});

test('expired prepublish claim safely renews and captures account again before attempting', async () => {
  const ctx = durableWorker(); const job = await seedJob(ctx); const calls=[]; let captures=0;
  ctx.postingRequest = async route => {
    calls.push(route);
    if (calls.length === 1) throw new Error('posting_lease_expired');
    if (route.startsWith('/jobs/')) return {...job,status:'claimed'};
    if (route === '/claim') return {...job,lease_token:'renewed',revision:3};
    return {...job,status:'publishing',revision:4};
  };
  await ctx.guardPostingAction(job,async () => {captures++; return {result:{value:{handles:['@mainuser']}}};},7,{beginPublish:true});
  assert.equal(captures,2);
  assert.equal(job.lease_token,'renewed');
  assert.deepEqual(calls,['/attempt','/jobs/job-1','/claim','/attempt']);
});

test('lost attempt reply revision conflict restores publishing state without retry click', async () => {
  const saved={}; const ctx=durableWorker(saved); const job=await seedJob(ctx); const calls=[];
  ctx.postingRequest = async route => {
    calls.push(route);
    if (route === '/attempt') throw new Error('revision_conflict');
    return {...job,status:'publishing',publish_attempted_at:123,revision:3};
  };
  await assert.rejects(() => ctx.guardPostingAction(job,async () => ({result:{value:{handles:['@mainuser']}}}),7,{beginPublish:true}), /posting_reconciliation_required/);
  assert.deepEqual(calls,['/attempt','/jobs/job-1']);
  assert.equal(saved.omnicutPostingProtocolV2.tabId,7);
  assert.equal(saved.omnicutPostingProtocolV2.activeJob.status,'publishing');
});

test('product search does not insert the ID a second time after setting its value', async () => {
  const ctx = worker();
  const calls = [];
  // Exercise the real orchestration with successful page responses; no TikTok requests.
  ctx.switchToShowcaseTab = async () => true;
  await ctx.attachProductLink(async (method, params) => {
    calls.push({ method, params });
    return { result: { value: { success: true } } };
  }, '1737088044189583209');
  assert.equal(calls.filter(c => c.method === 'Input.insertText').length, 0);
});

test('caption script exceptions must propagate instead of reporting success', async () => {
  const ctx = worker();
  await assert.rejects(() => ctx.typeCaption(async () => ({
    exceptionDetails: { text: 'Execution context was destroyed' },
  }), 'caption'), /Execution context|แคปชัน|คำอธิบาย/);
});

test('preparation stops on product failure before cover and schedule', async () => {
  const ctx = worker();
  const called = [];
  ctx.fetchPendingJob = async () => ({caption:'review', tiktok_product_id:'123', schedule_date:'2026-10-12', schedule_time:'12:00'});
  ctx.runWaitForUploadOnly = async () => {};
  ctx.runTypeCaptionOnly = async () => { called.push('caption'); };
  ctx.runAttachProductOnly = async () => ({success:false, reason:'product not found'});
  ctx.runUploadCoverOnly = async () => { called.push('cover'); };
  ctx.runScheduleModeOnly = async () => { called.push('schedule'); };
  const result = await ctx.runPrepareDetails({scheduleMode:true});
  assert.equal(result.success, false);
  assert.equal(result.step, 'product');
  assert.deepEqual(Array.from(result.completed), ['caption']);
  assert.deepEqual(called, ['caption']);
});

test('preparation completes in order and never calls publication', async () => {
  const ctx = worker();
  const called = [];
  ctx.fetchPendingJob = async () => ({caption:'review', tiktok_product_id:'123', schedule_date:'2026-10-12', schedule_time:'12:00'});
  ctx.runWaitForUploadOnly = async () => {};
  ctx.runTypeCaptionOnly = async () => { called.push('caption'); };
  ctx.runAttachProductOnly = async () => { called.push('product'); return {success:true}; };
  ctx.runUploadCoverOnly = async () => { called.push('cover'); return {success:true}; };
  ctx.runScheduleModeOnly = async () => { called.push('schedule'); return {success:true}; };
  ctx.runClickPostOnly = async () => { throw new Error('must not post'); };
  const result = await ctx.runPrepareDetails({scheduleMode:true});
  assert.equal(result.success, true);
  assert.deepEqual(called, ['caption', 'product', 'schedule', 'cover']);
});

test('preparation waits for the real upload to finish before doing anything else', async () => {
  // Regression: the "ทำต่อหลังอัปโหลด" shortcut becomes clickable as soon as
  // step 1 hands the file to TikTok's page, which is well before the upload
  // actually finishes -- confirmed live at 26% progress. Without this wait,
  // caption/product/cover all raced the real upload and TikTok's own
  // product-search endpoint refused results ("การตรวจสอบจะเริ่มได้หลังจาก
  // อัปโหลดไฟล์แล้วเท่านั้น").
  const ctx = worker();
  const called = [];
  ctx.fetchPendingJob = async () => ({caption:'review', tiktok_product_id:'123', schedule_date:'2026-10-12', schedule_time:'12:00'});
  ctx.runWaitForUploadOnly = async () => { called.push('wait-for-upload'); };
  ctx.runTypeCaptionOnly = async () => { called.push('caption'); };
  ctx.runAttachProductOnly = async () => { called.push('product'); return {success:true}; };
  ctx.runUploadCoverOnly = async () => { called.push('cover'); return {success:true}; };
  ctx.runScheduleModeOnly = async () => { called.push('schedule'); return {success:true}; };
  const result = await ctx.runPrepareDetails({scheduleMode:true});
  assert.equal(result.success, true);
  assert.deepEqual(called, ['wait-for-upload', 'caption', 'product', 'schedule', 'cover']);
});

test('preparation stops immediately if the upload never finishes, before touching caption/product/cover', async () => {
  const ctx = worker();
  const called = [];
  ctx.fetchPendingJob = async () => ({caption:'review', tiktok_product_id:'123', schedule_date:'2026-10-12', schedule_time:'12:00'});
  ctx.runWaitForUploadOnly = async () => { throw new Error('TikTok ยังอัปโหลดวิดีโอไม่เสร็จ -- รอสักครู่แล้วลองใหม่'); };
  ctx.runTypeCaptionOnly = async () => { called.push('caption'); };
  ctx.runAttachProductOnly = async () => { called.push('product'); return {success:true}; };
  ctx.runUploadCoverOnly = async () => { called.push('cover'); return {success:true}; };
  const result = await ctx.runPrepareDetails({scheduleMode:false});
  assert.equal(result.success, false);
  assert.match(result.error, /ยังอัปโหลดวิดีโอไม่เสร็จ/);
  assert.deepEqual(called, []);
  assert.deepEqual(Array.from(result.completed), []);
});

test('cover is rejected before any page interaction when missing', async () => {
  const ctx = worker();
  await assert.rejects(() => ctx.OmniAutomation.uploadCover(() => {
    throw new Error('must not touch page');
  }, null), /ยังไม่มีปก/);
});

test('cover upload dispatches input and change events after CDP sets the hidden file input', async () => {
  const ctx = worker();
  const calls = [];
  let filesSet = false;
  const send = async (method, params = {}) => {
    calls.push({method, params});
    if (method === 'Runtime.evaluate') {
      const expression = String(params.expression || '');
      if (expression.includes('dialogCandidates') && !params.returnByValue) {
        return {result: {objectId: 'cover-input'}};
      }
      if (expression.includes('input.files.length') && expression.includes('preview')) {
        return {result: {value: filesSet}};
      }
      return {result: {value: true}};
    }
    if (method === 'DOM.getDocument') return {root: {nodeId: 1}};
    if (method === 'DOM.querySelectorAll') return {nodeIds: [7]};
    if (method === 'DOM.resolveNode') return {object: {objectId: 'cover-input'}};
    if (method === 'Runtime.callFunctionOn') {
      return {result: {value: {fileCount: filesSet ? 1 : 0}}};
    }
    if (method === 'DOM.setFileInputFiles') {
      filesSet = true;
      return {};
    }
    return {};
  };

  await ctx.OmniAutomation.uploadCover(send, 'D:/covers/demo_cover_3x4.jpg');
  const notifyCall = calls.find(call => call.method === 'Runtime.callFunctionOn');
  const eventExpression = String(notifyCall?.params.functionDeclaration || '');
  assert.ok(eventExpression, 'must notify React about the selected cover');
  assert.match(eventExpression, /dispatchEvent\(new Event\('input'/);
  assert.match(eventExpression, /dispatchEvent\(new Event\('change'/);
});

test('cover upload resolves the DOM node directly when Runtime.requestNode cannot resolve TikTok input', async () => {
  const ctx = worker();
  const calls = [];
  let filesSet = false;
  const send = async (method, params = {}) => {
    calls.push({method, params});
    if (method === 'Runtime.evaluate') {
      const expression = String(params.expression || '');
      if (expression.includes('input.files.length') && expression.includes('preview')) {
        return {result: {value: filesSet}};
      }
      return {result: {value: true}};
    }
    if (method === 'DOM.getDocument') return {root: {nodeId: 1}};
    if (method === 'DOM.querySelectorAll') return {nodeIds: [13]};
    if (method === 'DOM.resolveNode') return {object: {objectId: 'cover-input'}};
    if (method === 'Runtime.callFunctionOn') {
      return {result: {value: {fileCount: filesSet ? 1 : 0}}};
    }
    if (method === 'DOM.setFileInputFiles') {
      filesSet = true;
      return {};
    }
    if (method === 'DOM.requestNode') return {};
    return {};
  };

  await ctx.OmniAutomation.uploadCover(send, 'D:/covers/demo_cover_3x4.jpg');
  assert.equal(calls.some(call => call.method === 'DOM.requestNode'), false);
  const setFileCall = calls.find(call => call.method === 'DOM.setFileInputFiles');
  assert.equal(setFileCall.params.nodeId, 13);
  assert.equal(Array.from(setFileCall.params.files)[0], 'D:/covers/demo_cover_3x4.jpg');
  assert.ok(calls.some(call => call.method === 'DOM.resolveNode'));
  const notifyCall = calls.find(call => call.method === 'Runtime.callFunctionOn');
  assert.match(notifyCall.params.functionDeclaration, /dispatchEvent\(new Event\('change'/);
});

test('cover upload sets the exact Cover Studio input object returned by the scoped query', async () => {
  const ctx = worker();
  const calls = [];
  let filesSet = false;
  const send = async (method, params = {}) => {
    calls.push({method, params});
    if (method === 'Runtime.evaluate') {
      const expression = String(params.expression || '');
      if (expression.includes('dialogCandidates') && params.returnByValue === false) {
        return {result: {objectId: 'exact-cover-input'}};
      }
      return {result: {value: filesSet || true}};
    }
    if (method === 'DOM.setFileInputFiles') {
      filesSet = true;
      return {};
    }
    if (method === 'Runtime.callFunctionOn') {
      return {result: {value: {fileCount: filesSet ? 1 : 0}}};
    }
    if (method === 'Runtime.releaseObject') return {};
    return {};
  };

  await ctx.OmniAutomation.uploadCover(send, 'D:/covers/demo_cover_3x4.jpg');
  const setFileCall = calls.find(call => call.method === 'DOM.setFileInputFiles');
  assert.equal(setFileCall.params.objectId, 'exact-cover-input');
  assert.equal('nodeId' in setFileCall.params, false);
  assert.ok(calls.some(call => call.method === 'Runtime.callFunctionOn'));
});

test('cover upload retries once when TikTok replaces the hidden input during file assignment', async () => {
  const ctx = worker();
  const calls = [];
  let targetNumber = 0;
  let notifyNumber = 0;
  const send = async (method, params = {}) => {
    calls.push({method, params});
    if (method === 'Runtime.evaluate') {
      const expression = String(params.expression || '');
      if (expression.includes('dialogCandidates') && params.returnByValue === false) {
        targetNumber += 1;
        return {result: {objectId: targetNumber === 1 ? 'stale-cover-input' : 'replacement-cover-input'}};
      }
      return {result: {value: true}};
    }
    if (method === 'DOM.setFileInputFiles') return {};
    if (method === 'Runtime.callFunctionOn') {
      notifyNumber += 1;
      return {result: {value: {fileCount: notifyNumber === 1 ? 0 : 1}}};
    }
    return {};
  };

  await ctx.OmniAutomation.uploadCover(send, 'D:/covers/demo_cover_3x4.jpg');
  const setCalls = calls.filter(call => call.method === 'DOM.setFileInputFiles');
  assert.deepEqual(setCalls.map(call => call.params.objectId), [
    'stale-cover-input',
    'replacement-cover-input',
  ]);
});

test('schedule time follows TikTok five-minute increments', () => {
  const ctx = worker();
  assert.equal(ctx.normalizeScheduleTime('16:08'), '16:10');
  assert.equal(ctx.normalizeScheduleTime('23:58'), '00:00');
  assert.equal(ctx.normalizeScheduleTime('09:35'), '09:35');
  assert.equal(ctx.normalizeScheduleTime('24:00'), '');
});

test('schedule waits for TikTok time-picker animation to settle on the exact value', async () => {
  const ctx = worker();
  const snapshots = [
    ['2026-09-26', '19:20'],
    ['2026-09-26', '19:10'],
    ['2026-09-26', '19:00'],
  ];
  let attempts = 0;
  const sendEval = async () => {
    const value = snapshots[Math.min(attempts, snapshots.length - 1)];
    attempts += 1;
    return {result: {value}};
  };

  const result = await ctx.waitForScheduleValues(sendEval, '2026-09-26', '19:00', 1000);

  assert.equal(result.success, true);
  assert.equal(attempts, 3);
  assert.deepEqual(Array.from(result.shown), ['2026-09-26', '19:00']);
});

test('background.js does not contain invalid numeric ID selectors like #1 or #2', () => {
  const code = fs.readFileSync(path.join(__dirname, 'background.js'), 'utf8');
  const invalidIdMatch = code.match(/querySelector(?:All)?\s*\(\s*['"`][^'"`]*#[0-9]/);
  assert.equal(invalidIdMatch, null, `Found invalid numeric ID selector: ${invalidIdMatch?.[0]}`);
});

test('live DOM contracts for the reported TikTok screens stay in the worker', () => {
  const code = fs.readFileSync(path.join(__dirname, 'background.js'), 'utf8');
  const automation = fs.readFileSync(path.join(__dirname, 'automation.js'), 'utf8');
  const panel = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  assert.match(code, /TUXRadioStandalone-input/);
  assert.match(code, /cartName/);
  assert.match(code, /scheduleDate/);
  assert.match(code, /tiktok-timepicker-option-text/);
  assert.match(code, /pickerOpen/);
  assert.match(code, /scrollIntoView\(\{block:'center'\}\)/g);
  assert.match(code, /calendar-wrapper.*span\.day\.valid/);
  assert.match(code, /calendar-wrapper/);
  assert.match(code, /span\.day\.valid/);
  const scheduleFn = code.slice(code.indexOf('async function switchToScheduleMode'), code.indexOf('async function setScheduleDateTime'));
  assert.match(scheduleFn, /input\[type="radio"\]\[value="schedule"\]/);
  assert.doesNotMatch(scheduleFn, /const TARGETS = \['ตั้งเวลา'/);
  const showcaseFn = code.slice(code.indexOf('async function switchToShowcaseTab'), code.indexOf('async function attachProductLink'));
  assert.doesNotMatch(showcaseFn, /dispatchEvent\(new MouseEvent/);
  assert.match(automation, /ImageUpload__uploadArea/);
  assert.match(automation, /DOM\.setFileInputFiles/);
  assert.match(automation, /CoverEditor__root/);
  assert.match(automation, /cover-editor-container/);
  assert.match(automation, /Input\.dispatchMouseEvent/);
  assert.match(automation, /editTarget/);
  assert.match(automation, /closest\('button, \[role="button"\]'\)/);
  assert.match(code, /ขั้น 5: เปิด\/อัปโหลด\/บันทึกปกไม่สำเร็จ/);
  assert.match(automation, /หน้าต่าง Cover Studio ยังไม่ปิด/);
  assert.match(automation, /attempt < 3/);
  assert.match(code, /savePostingReceipt/);
  assert.match(code, /marked: published/);
  assert.match(panel, /await openTikTokUploadTab\(\)/);
  assert.match(panel, /scheduleDateInput/);
  assert.match(panel, /scheduleTimeInput/);
  assert.match(panel, /product_name: item\.product_name/);
  assert.match(panel, /activeClip\.cover_path \|\| ''/);
  assert.match(panel, /SCHEDULE_LEAD_MINUTES = 15/);
  assert.match(panel, /minute \+= 5/);
  assert.match(panel, /classList\.add\('completed'\)/);
  const searchStep = code.slice(code.indexOf('// Step 4: Type Product ID'), code.indexOf('const searchVal'));
  assert.match(searchStep, /const search = root\.querySelector/);
  assert.doesNotMatch(searchStep, /const search = document\.querySelector/);
  assert.match(searchStep, /productContainers\.at\(-1\)/);
});

test('extension sidepanel exposes the stats-sync button in its own Tools tab', () => {
  const sideHtml = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  const sideJs = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  // Stats sync lives in its own tab, not buried in the post checklist.
  assert.match(sideHtml, /id="tabBtnTools"/);
  assert.match(sideHtml, /id="panelTools"/);
  assert.match(sideHtml, /id="syncStatsBtn"/);
  assert.match(sideHtml, /ซิงก์สถิติ/);
  assert.match(sideHtml, /src="stats_parser\.js"/);
  const checklistSection = sideHtml.slice(sideHtml.indexOf('id="panelChecklist"'), sideHtml.indexOf('id="panelTools"'));
  assert.doesNotMatch(checklistSection, /syncStatsBtn/);
  // Wiring: tab switch + result is read from the injected execution.
  assert.match(sideJs, /const result = injected\?\.\[0\]\?\.result;/);
  assert.match(sideJs, /tabBtnTools\.addEventListener/);
  assert.match(sideJs, /\/api\/tiktok-stats\/import/);
  assert.match(sideJs, /parsePostsTable/);
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'manifest.json'), 'utf8'));
  assert.ok(manifest.permissions.includes('scripting'));
});

test('stats sync accepts the real Studio posts page and stamps a visible build tag', () => {
  const sideHtml = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  const sideJs = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'manifest.json'), 'utf8'));
  // Build identity: chrome://extensions + the Tools tab both prove the fresh
  // code is running, so stale cached sidepanel.js (the ghost "จำกัดโดเมน"
  // banner that never existed in this repo) can be caught by the user's eyes.
  assert.equal(manifest.version, '0.2.0');
  assert.match(sideHtml, /id="buildTag"/);
  assert.match(sideJs, /getManifest/);
  // The strict domain banner must never come back: resolution is a loose
  // tiktok.com check with a page-side location.href fallback and an error
  // that reports the URL actually seen.
  assert.doesNotMatch(sideJs, /จำกัดโดเมน/);
  assert.match(sideJs, /resolveTikTokTab/);
  assert.match(sideJs, /tiktokHrefOf/);
  assert.match(sideJs, /func: \(\) => location\.href/);
});

test('extension UI exposes single consolidated TikTok upload opener and complies with clean UI standard', () => {
  const sideHtml = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  const sideJs = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  const popupHtml = fs.readFileSync(path.join(__dirname, 'popup.html'), 'utf8');
  const popupJs = fs.readFileSync(path.join(__dirname, 'popup.js'), 'utf8');

  // Verify single global header opener exists in sidepanel and single opener in popup
  assert.match(sideHtml, /id="headerOpenTikTokBtn"/);
  assert.match(popupHtml, /id="popupOpenTikTokBtn"/);

  // Verify redundant buttons were removed (User requested exactly one single spot)
  assert.doesNotMatch(sideHtml, /id="listOpenTikTokBtn"/);
  assert.doesNotMatch(sideHtml, /id="openTikTokBtn"/);
  assert.doesNotMatch(sideJs, /listOpenTikTokBtn/);
  assert.doesNotMatch(sideJs, /openTikTokBtn/);

  // Verify listeners and URL opener in JS
  assert.match(sideJs, /headerOpenTikTokBtn/);
  assert.match(sideJs, /tiktok\.com\/tiktokstudio\/upload/);
  assert.match(popupJs, /popupOpenTikTokBtn/);
  assert.match(popupJs, /tiktok\.com\/tiktokstudio\/upload/);

  // Verify clean UI standard: no emojis in button texts
  assert.doesNotMatch(sideHtml, /<button[^>]*>[^<]*[\u{1F300}-\u{1F9FF}][^<]*<\/button>/u);
  assert.doesNotMatch(popupHtml, /<button[^>]*>[^<]*[\u{1F300}-\u{1F9FF}][^<]*<\/button>/u);
});

test('extension UI exposes dynamic backend health status and bilingual upload status check', () => {
  const sideHtml = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  const sideJs = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  const autoJs = fs.readFileSync(path.join(__dirname, 'automation.js'), 'utf8');
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'manifest.json'), 'utf8'));

  // Header status pill elements
  assert.match(sideHtml, /id="headerStatusPill"/);
  assert.match(sideHtml, /id="headerStatusDot"/);
  assert.match(sideHtml, /id="headerStatusText"/);
  assert.match(sideJs, /updateHeaderBackendStatus/);

  // Manifest includes both 127.0.0.1 and localhost
  assert.ok(manifest.host_permissions.includes('http://127.0.0.1:8000/*'));
  assert.ok(manifest.host_permissions.includes('http://localhost:8000/*'));

  // Bilingual upload check
  assert.match(autoJs, /text\.includes\('อัปโหลดแล้ว'\) \|\| text\.toLowerCase\(\)\.includes\('uploaded'\)/);
});


test('confirmed publication persists a job-scoped receipt before local effects', async () => {
  const ctx = worker();
  const calls = [];
  const job = {job_id:'job-1', export_id:'exp-1'};
  ctx.chrome.debugger = {attach: async () => {}, detach: async () => {}};
  ctx.fetchPendingJob = async () => job;
  ctx.findUploadTab = async () => ({id:7});
  ctx.cdp = () => async () => {};
  ctx.guardPostingAction = async () => { calls.push('attempt'); return '@mainuser'; };
  ctx.clickPostButton = async (_send, _tab, beforeClick) => {
    await beforeClick(); calls.push('click');
    return {outcome:'published', proof:{kind:'platform_success_notice', notice:'Posted successfully'}};
  };
  ctx.savePostingReceipt = async (saved, source, outcome) => {
    assert.equal(saved, job); assert.equal(source, '@mainuser'); assert.equal(outcome, 'published');
    calls.push('receipt');
  };
  ctx.openUploadPage = async () => { calls.push('upload-page'); };
  const result = await ctx.runClickPostOnly();
  assert.equal(result.marked, true);
  assert.deepEqual(calls, ['attempt','click','receipt','upload-page']);
});

// --- post confirmation: only a POSITIVE signal counts as posted ---------------

const UPLOAD_URL = 'https://www.tiktok.com/tiktokstudio/upload?from=webapp';
const editorGoneEval = async () => ({ result: { value: { done: true, failed: false, reason: 'editor-gone' } } });
const stillEditingEval = async () => ({ result: { value: { done: false } } });

test('background registers a chrome.debugger.onDetach listener that records detaches per tab', () => {
  let listener = null;
  const context = worker({ debugger: { onDetach: { addListener: (fn) => { listener = fn; } } } });
  assert.equal(typeof listener, 'function');
  const before = Date.now();
  listener({ tabId: 5 }, 'canceled_by_user');
  assert.equal(context.getDebuggerDetach(5, before).reason, 'canceled_by_user');
  assert.equal(context.getDebuggerDetach(6, before), null);
  assert.equal(context.getDebuggerDetach(5, Date.now() + 1000), null);
});

test('decidePostConfirmation: only a positive platform notice confirms', () => {
  const ctx = worker();
  const d = (o) => ctx.decidePostConfirmation(o);
  assert.equal(d({ tabUrl: 'https://www.tiktok.com/tiktokstudio/content' }).outcome, 'pending');
  assert.equal(d({evalValue:{platform_outcome:'published', notice:'Posted successfully'}}).outcome, 'confirmed');
  assert.equal(d({ tabUrl: UPLOAD_URL }).outcome, 'pending');
  assert.equal(d({ tabUrl: UPLOAD_URL, evalThrew: true }).outcome, 'pending');
  assert.equal(d({ tabUrl: UPLOAD_URL, evalValue: { done: true, failed: false } }).outcome, 'pending');
  assert.equal(d({ tabUrl: 'about:blank' }).outcome, 'pending');
  assert.equal(d({ tabUrl: 'https://www.tiktok.com/login' }).outcome, 'pending');
  assert.equal(d({ tabUrl: 'https://evil.example/tiktok.com' }).outcome, 'pending');
  assert.equal(d({ tabMissing: true }).reason, 'tab-gone-unverified');
  assert.equal(d({ tabUrl: UPLOAD_URL, evalValue: { done: true, failed: true, message: 'x' } }).outcome, 'failed');
  assert.equal(d({ tabUrl: UPLOAD_URL, detach: { reason: 'canceled_by_user' } }).reason, 'debugger-detached');
  // A user cancel never counts as success, even if the URL looks like it moved on.
  assert.equal(d({ tabUrl: 'https://www.tiktok.com/tiktokstudio/content', detach: { reason: 'canceled_by_user' } }).outcome, 'unconfirmed');
});

test('waitForPostConfirmation: debugger detached during the wait is unconfirmed', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => ({ url: UPLOAD_URL }) };
  const send = async () => {
    ctx.recordDebuggerDetach({ tabId: 7 }, 'canceled_by_user');
    throw new Error('Debugger is not attached to the tab with id: 7.');
  };
  const res = await ctx.waitForPostConfirmation(send, 7, 5000);
  assert.equal(res.confirmed, false);
  assert.equal(res.reason, 'debugger-detached');
  assert.equal(res.detachReason, 'canceled_by_user');
});

test('waitForPostConfirmation: editor gone but URL still /upload is not confirmed', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => ({ url: UPLOAD_URL }) };
  const res = await ctx.waitForPostConfirmation(editorGoneEval, 7, 50);
  assert.equal(res.confirmed, false);
  assert.equal(res.timedOut, true);
  assert.equal(res.editorGone, true);
});

test('waitForPostConfirmation: evaluate always throwing with URL on /upload is not confirmed', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => ({ url: UPLOAD_URL }) };
  const res = await ctx.waitForPostConfirmation(async () => { throw new Error('Execution context was destroyed'); }, 7, 50);
  assert.equal(res.confirmed, false);
  assert.equal(res.timedOut, true);
});

test('waitForPostConfirmation: tab removed without a positive signal is not confirmed', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => { throw new Error('No tab with id: 7.'); } };
  const res = await ctx.waitForPostConfirmation(async () => { throw new Error('gone'); }, 7, 5000);
  assert.equal(res.confirmed, false);
  assert.equal(res.reason, 'tab-gone-unverified');
});

test('waitForPostConfirmation: navigation cannot confirm, explicit scheduling notice can', async () => {
  const ctx = worker();
  ctx.chrome.tabs = {get:async () => ({url:'https://www.tiktok.com/tiktokstudio/content'})};
  assert.equal((await ctx.waitForPostConfirmation(stillEditingEval, 7, 15)).confirmed, false);
  assert.equal((await ctx.waitForPostConfirmation(async () => {throw new Error('context destroyed');}, 7, 15)).confirmed, false);
  const res = await ctx.waitForPostConfirmation(async () => ({result:{value:{platform_outcome:'scheduled_on_platform', notice:'Scheduled successfully'}}}), 7, 100);
  assert.equal(res.confirmed, true);
  assert.equal(res.outcome, 'scheduled_on_platform');
  assert.equal(res.proof.kind, 'platform_success_notice');
});

test('waitForPostConfirmation: TikTok rejection toast is reported verbatim', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => ({ url: UPLOAD_URL }) };
  const send = async () => ({ result: { value: { done: true, failed: true, message: 'กรุณาเลือกหมวดหมู่' } } });
  const res = await ctx.waitForPostConfirmation(send, 7, 5000);
  assert.equal(res.confirmed, false);
  assert.equal(res.message, 'กรุณาเลือกหมวดหมู่');
});

function clickPostHarness({ tabUrl, onConfirmationEval }) {
  const ctx = worker();
  const calls = [];
  ctx.fetchPendingJob = async () => ({ video_path: 'clip.mp4', export_id: 'exp-1' });
  ctx.findUploadTab = async () => ({ id: 7, windowId: 3, url: UPLOAD_URL });
  ctx.waitForUploadComplete = async () => true;
  ctx.dismissLeaveConfirmDialogIfPresent = async () => false;
  ctx.chrome.tabs = { get: async () => ({ url: tabUrl }) };
  ctx.chrome.debugger = {
    attach: async () => {},
    detach: async () => {},
    sendCommand: async (_target, method) => {
      if (method !== 'Runtime.evaluate') return {};
      // First evaluate = the click; later ones = confirmation polls.
      if (!calls.includes('clicked')) {
        calls.push('clicked');
        return { result: { value: { success: true, method: 'direct' } } };
      }
      return onConfirmationEval(ctx);
    },
  };
  ctx.guardPostingAction = async () => '@mainuser';
  ctx.observePostConfirmation = async () => {};
  ctx.postingState = async () => ({});
  ctx.persistPostingState = async () => {};
  ctx.savePostingReceipt = async (_job, _source, outcome) => { calls.push(outcome === 'published' ? 'mark' : 'unknown'); };
  ctx.openUploadPage = async () => { calls.push('upload-page'); };
  return { ctx, calls };
}

test('runClickPostOnly does not call mark-posted when the debugger is detached during confirmation', async () => {
  const { ctx, calls } = clickPostHarness({
    tabUrl: UPLOAD_URL,
    onConfirmationEval: (c) => {
      c.recordDebuggerDetach({ tabId: 7 }, 'canceled_by_user');
      throw new Error('Debugger is not attached to the tab with id: 7.');
    },
  });
  await assert.rejects(() => ctx.runClickPostOnly(), /post_not_confirmed.*ตัดการเชื่อมต่อ/);
  assert.deepEqual(calls, ['clicked', 'unknown']);
});

test('runClickPostOnly marks posted only on an explicit publication notice', async () => {
  const { ctx, calls } = clickPostHarness({
    tabUrl: 'https://www.tiktok.com/tiktokstudio/content',
    onConfirmationEval: () => ({ result: { value: { platform_outcome:'published', notice:'Posted successfully' } } }),
  });
  const result = await ctx.runClickPostOnly();
  assert.equal(result.marked, true);
  assert.deepEqual(calls, ['clicked', 'mark', 'upload-page']);
});
