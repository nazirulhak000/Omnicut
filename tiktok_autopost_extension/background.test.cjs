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
  ctx.dismissContinueToPostDialogIfPresent = async () => {};
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
      if (expression.includes('ImageUpload__root')) return {result: {value: false}};
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

test('cover upload counts as done when TikTok empties the input after reading the file', async () => {
  // Live 2026-11-10: TikTok clears input.files at once and swaps the button for a thumbnail.
  const ctx = worker();
  const calls = [];
  const send = async (method, params = {}) => {
    calls.push({method, params});
    if (method === 'Runtime.evaluate') {
      const expression = String(params.expression || '');
      if (expression.includes('dialogCandidates') && params.returnByValue === false) return {result: {objectId: 'cover-input'}};
      return {result: {value: true}};
    }
    if (method === 'Runtime.callFunctionOn') return {result: {value: {fileCount: 0}}};
    return {};
  };
  await ctx.OmniAutomation.uploadCover(send, 'D:/covers/demo_cover_3x4.jpg');
  assert.equal(calls.filter(call => call.method === 'DOM.setFileInputFiles').length, 1);
});

test('after a real post (tab left on Studio > Content) the next action brings that tab back to the upload page', async () => {
  // Live 2026-11-10: TikTok moves the tab to Content after posting; every later action failed with
  // "ไม่พบแท็บ ... หน้าอัปโหลด" and the batch skipped the remaining clips.
  const CONTENT = 'https://www.tiktok.com/tiktokstudio/content';
  const UPLOAD = 'https://www.tiktok.com/tiktokstudio/upload';
  let url = CONTENT;
  const updates = [];
  const ctx = worker({
    tabs: {
      query: async (q) => (q && q.active ? [] : [{id: 3, url, active: true}]),
      update: async (_id, props) => { updates.push(props.url); url = props.url; return {id: 3, url}; },
      get: async () => ({id: 3, url, status: 'complete'}),
    },
    debugger: {attach: async () => {}, detach: async () => {}, sendCommand: async () => ({result: {value: true}})},
  });
  ctx.focusTikTokTab = async (tab) => tab;
  const tab = await ctx.findUploadTab();
  assert.equal(tab.id, 3);
  assert.deepEqual(Array.from(updates), [UPLOAD]);

  // no Studio tab at all: still a clear error, nothing is navigated
  const none = worker({tabs: {query: async () => [], update: async () => { throw new Error('must not navigate'); }}});
  await assert.rejects(() => none.findUploadTab(), /ไม่พบแท็บ TikTok Studio/);

  // verify-post-content must not pre-navigate: it works from the Content tab as it is
  const noRecover = worker({tabs: {query: async (q) => (q && q.active ? [] : [{id: 3, url: CONTENT}]), update: async () => { throw new Error('must not navigate'); }}});
  await assert.rejects(() => noRecover.findUploadTab({recover: false}), /ไม่พบแท็บ TikTok Studio/);
  assert.equal((await noRecover.findAnyStudioTab()).id, 3);
});

// ---- draft mode: Save draft button, evidence = Content > Drafts, never the Post button ----
const DRAFTS_URL = 'https://www.tiktok.com/tiktokstudio/content?tab=draft';

function draftHarness({ job = {}, buttonPresent = true, urlAfterClick = DRAFTS_URL, pageText = 'Posts 219\nDrafts 1\nสุดยอดพัดลมตัวนี้ ลมแรงมาก\nNov 10, 2026, 12:05PM', pageUrl = DRAFTS_URL } = {}) {
  const ctx = worker();
  const log = { calls: [], expressions: [], receipts: [] };
  let clicked = false;
  ctx.fetchPendingJob = async () => ({ job_id: 'job-1', channel_id: 'main', caption: 'สุดยอดพัดลมตัวนี้ ลมแรงมาก', target_handle: '@mainuser', lease_expires_at: 9999999999, ...job });
  ctx.findUploadTab = async () => ({ id: 7, windowId: 3, url: UPLOAD_URL });
  ctx.waitForUploadComplete = async () => true;
  ctx.dismissLeaveConfirmDialogIfPresent = async () => false;
  ctx.guardPostingAction = async (_job, _send, _tab, opts) => { log.calls.push(opts && opts.beginPublish ? 'attempt' : 'check'); return '@mainuser'; };
  ctx.postingState = async () => ({});
  ctx.persistPostingState = async () => {};
  ctx.focusTikTokTab = async (tab) => tab;
  ctx.savePostingReceipt = async (_job, _source, outcome, proof) => { log.calls.push('receipt:' + outcome); log.receipts.push({ outcome, proof }); };
  ctx.openUploadPage = async () => { log.calls.push('upload-page'); };
  ctx.chrome.tabs = { get: async () => ({ id: 7, url: clicked ? urlAfterClick : UPLOAD_URL }) };
  ctx.chrome.debugger = {
    attach: async () => {}, detach: async () => {},
    sendCommand: async (_target, method, params = {}) => {
      if (method !== 'Runtime.evaluate') return {};
      const expression = String(params.expression || '');
      log.expressions.push(expression);
      if (expression.includes('window.innerWidth')) return { result: { value: { w: 1440, h: 900, dpr: 1, focus: true } } };
      if (expression.startsWith('Boolean(document.querySelector(')) return { result: { value: buttonPresent } };
      if (expression.includes('save_draft_button')) { clicked = true; log.calls.push('clicked'); return { result: { value: { success: true } } }; }
      if (expression.includes('location.href')) return { result: { value: { url: pageUrl, text: pageText } } };
      return { result: { value: true } };
    },
  };
  return { ctx, log };
}

test('runSaveDraftOnly saves a draft: one Save draft click, evidence = Drafts page + matching row, ack draft_saved', async () => {
  const { ctx, log } = draftHarness();
  const result = await ctx.runSaveDraftOnly();
  assert.equal(result.success, true);
  assert.equal(result.outcome, 'draft_saved');
  assert.equal(result.posted, false);
  assert.deepEqual(Array.from(log.calls), ['attempt', 'clicked', 'receipt:draft_saved', 'upload-page']);
  assert.equal(log.receipts[0].proof.kind, 'drafts_page_confirmed');
  assert.match(log.receipts[0].proof.confirmation_token, /^job-1:/);
  // it must never go near the Post button
  assert.ok(!log.expressions.some(e => e.includes('post_video_button')), 'Post button untouched');
});

test('runSaveDraftOnly refuses a job that carries a publish time (wrong mode) before touching the page', async () => {
  const { ctx, log } = draftHarness({ job: { schedule_date: '2026-11-12', schedule_time: '09:00' } });
  await assert.rejects(() => ctx.runSaveDraftOnly(), /ไม่ใช่งานแบบร่าง/);
  assert.deepEqual(Array.from(log.calls), []);
  assert.equal(log.expressions.length, 0);
});

test('runSaveDraftOnly with no Save draft button stops without clicking and without burning the attempt', async () => {
  const { ctx, log } = draftHarness({ buttonPresent: false });
  await assert.rejects(() => ctx.runSaveDraftOnly(), /Save draft/);
  assert.deepEqual(Array.from(log.calls), []); // no fence, no click, no receipt
  assert.ok(!log.expressions.some(e => e.includes('post_video_button')));
});

test('runSaveDraftOnly: TikTok never opens Drafts after the click -> not confirmed, receipt is confirmation_unknown', async () => {
  const { ctx, log } = draftHarness({ urlAfterClick: UPLOAD_URL });
  ctx.waitForDraftConfirmation = (send, tabId, caption) => ({ confirmed: false, reason: 'no-navigation' });
  await assert.rejects(() => ctx.runSaveDraftOnly(), /draft_not_confirmed.*ไม่พาไปหน้าแบบร่าง/);
  assert.deepEqual(Array.from(log.calls), ['attempt', 'clicked', 'receipt:confirmation_unknown']);
});

test('runSaveDraftOnly: Drafts page opens but no row matches the caption -> not confirmed (never ack draft_saved)', async () => {
  const { ctx, log } = draftHarness({ pageText: 'Posts 219\nDrafts 3\nคลิปอื่นทั้งหมด ไม่ตรงกัน\nNov 9, 2026' });
  ctx.waitForDraftConfirmation = async (send, tabId, caption) => {
    const evidence = await ctx.readDraftRowEvidence(send, caption);
    return evidence.rowVisible === false ? { confirmed: false, reason: 'draft-row-not-found', evidence } : { confirmed: true, evidence };
  };
  await assert.rejects(() => ctx.runSaveDraftOnly(), /draft_not_confirmed.*ไม่พบแถวแบบร่าง/);
  assert.ok(!log.calls.includes('receipt:draft_saved'));
  assert.ok(log.calls.includes('receipt:confirmation_unknown'));
});

test('draft evidence helpers: URL, caption key and count are read from the Drafts page', async () => {
  const ctx = worker();
  assert.equal(ctx.isDraftsUrl('https://www.tiktok.com/tiktokstudio/content?tab=draft'), true);
  assert.equal(ctx.isDraftsUrl('https://www.tiktok.com/tiktokstudio/content'), false);
  assert.equal(ctx.isDraftsUrl('https://www.tiktok.com/tiktokstudio/upload?tab=draft'), false);
  assert.equal(ctx.draftCaptionKey('Hello, World! สวัสดี 123'), 'helloworldสวัสดี123'.slice(0, 14));
  const send = async () => ({ result: { value: { url: DRAFTS_URL, text: 'โพสต์ 219\nแบบร่าง 4\nแกะกล่องสุดคุ้ม ของแท้\nNov 10' } } });
  const hit = await ctx.readDraftRowEvidence(send, 'แกะกล่องสุดคุ้ม ของแท้ ราคาดี');
  assert.deepEqual(JSON.parse(JSON.stringify(hit)), { url: DRAFTS_URL, onDrafts: true, draftCount: 4, rowVisible: true });
  const miss = await ctx.readDraftRowEvidence(send, 'ข้อความอื่นที่ไม่มีในหน้า');
  assert.equal(miss.rowVisible, false);
  const noCaption = await ctx.readDraftRowEvidence(send, '');
  assert.equal(noCaption.rowVisible, null);
});

// ---- account check: read from the page twice per clip, fence-validate at every step ----
function accountReadHarness({ handle = '@mainuser' } = {}) {
  const saved = {};
  const ctx = durableWorker(saved);
  const routes = [];
  let reads = 0;
  let now = 1_000_000;
  ctx.Date = { now: () => now };
  ctx.postingRequest = async (route, _channel, body) => { routes.push(route); return { ...(await ctx.postingState()).activeJob, revision: 3 }; };
  const send = async () => { reads += 1; return { result: { value: { handles: [handle] } } }; };
  return { ctx, send, routes, saved, reads: () => reads, advance: (ms) => { now += ms; } };
}

test('account check: the page is read at the first step and before publishing, steps in between reuse the verified handle', async () => {
  const h = accountReadHarness();
  const job = await seedJob(h.ctx);
  await h.ctx.guardPostingAction(job, h.send, 7);                       // first guarded step: reads
  assert.equal(h.reads(), 1);
  for (let i = 0; i < 4; i += 1) await h.ctx.guardPostingAction(job, h.send, 7); // caption/product/cover/schedule: reuse
  assert.equal(h.reads(), 1);
  assert.deepEqual(Array.from(h.routes), ['/validate', '/validate', '/validate', '/validate', '/validate']); // fence still checked every step
  await h.ctx.guardPostingAction(job, h.send, 7, { beginPublish: true }); // right before the click: fresh read
  assert.equal(h.reads(), 2);
  assert.equal(h.routes.at(-1), '/attempt');
});

test('account check: before publishing the page is ALWAYS read again, and a switched account stops it', async () => {
  const h = accountReadHarness();
  const job = await seedJob(h.ctx);
  await h.ctx.guardPostingAction(job, h.send, 7);
  const switched = async () => ({ result: { value: { handles: ['@someoneelse'] } } });
  await assert.rejects(() => h.ctx.guardPostingAction(job, switched, 7, { beginPublish: true }), /account_handle_mismatch/);
  assert.ok(!h.routes.includes('/attempt'), 'no attempt is recorded for a wrong account');
});

test('account check: another job or an old verification is read again; an unreadable account is never cached', async () => {
  const h = accountReadHarness();
  const job = await seedJob(h.ctx);
  await h.ctx.guardPostingAction(job, h.send, 7);
  assert.equal(h.reads(), 1);
  h.advance(16 * 60 * 1000);                                             // verification too old
  await h.ctx.guardPostingAction(job, h.send, 7);
  assert.equal(h.reads(), 2);
  const other = protocolJob({ job_id: 'job-2' });
  await seedJob(h.ctx, other);
  await h.ctx.guardPostingAction(other, h.send, 7);                      // a different job never inherits the handle
  assert.equal(h.reads(), 3);
  const blank = accountReadHarness();
  const blankJob = await seedJob(blank.ctx);
  const nothing = async () => ({ result: { value: { handles: [] } } });
  await assert.rejects(() => blank.ctx.guardPostingAction(blankJob, nothing, 7), /source_account_required/);
  await assert.rejects(() => blank.ctx.guardPostingAction(blankJob, nothing, 7), /source_account_required/); // still reads, never reuses a failure
});

// ---- R1: no unintended live post, no force release, no invented success ----
const NLC = String.fromCharCode(10);
const btnProbe = (over = {}) => async () => ({ result: { value: { found: true, visible: true, text: 'Post', disabled: false, ...over } } });

test('R1 assertPublishReady: a draft job never reaches the Post button', async () => {
  const ctx = worker();
  await assert.rejects(() => ctx.assertPublishReady(btnProbe(), { intent: 'draft' }), /intent_mismatch.*แบบร่าง/);
});

test('R1 assertPublishReady: the page mode must match the intent (Schedule vs Post label)', async () => {
  const ctx = worker();
  const sched = { intent: 'schedule', schedule_date: '2026-11-12', schedule_time: '09:00' };
  await assert.rejects(() => ctx.assertPublishReady(btnProbe({ text: 'Post' }), sched), /intent_page_mismatch/);          // schedule step skipped -> would post LIVE
  await ctx.assertPublishReady(btnProbe({ text: 'Schedule' }), sched);
  await ctx.assertPublishReady(btnProbe({ text: 'กำหนดเวลา' }), sched);
  await assert.rejects(() => ctx.assertPublishReady(btnProbe({ text: 'Schedule' }), { intent: 'post_now' }), /intent_page_mismatch/);
  await ctx.assertPublishReady(btnProbe({ text: 'Post' }), { intent: 'post_now' });
  await ctx.assertPublishReady(btnProbe({ text: 'โพสต์' }), { intent: 'post_now' });
  // an old job without an intent is inferred from its schedule
  await assert.rejects(() => ctx.assertPublishReady(btnProbe({ text: 'Post' }), { schedule_date: '2026-11-12', schedule_time: '09:00' }), /intent_page_mismatch/);
  await ctx.assertPublishReady(btnProbe({ text: 'Post' }), {});
});

test('R1 assertPublishReady: missing/disabled button or a schedule intent without a schedule stops before the attempt', async () => {
  const ctx = worker();
  await assert.rejects(() => ctx.assertPublishReady(async () => ({ result: { value: { found: false } } }), { intent: 'post_now' }), /หาปุ่ม Post ไม่เจอ/);
  await assert.rejects(() => ctx.assertPublishReady(btnProbe({ disabled: true }), { intent: 'post_now' }), /ยังกดไม่ได้/);
  await assert.rejects(() => ctx.assertPublishReady(btnProbe({ visible: false }), { intent: 'post_now' }), /หาปุ่ม Post ไม่เจอ/);
  await assert.rejects(() => ctx.assertPublishReady(btnProbe({ text: 'Post' }), { intent: 'schedule' }), /ไม่มีวันเวลา/);
  await ctx.assertPublishReady(btnProbe(), null); // no job: nothing to check
});

test('R1 clickPostButton: an already-attempted job is refused before anything is touched; no draft button in the Post fallback', async () => {
  const ctx = worker();
  let touched = 0;
  const send = async () => { touched += 1; return {}; };
  await assert.rejects(() => ctx.clickPostButton(send, 7, async () => { touched += 1; }, { job_id: 'j', publish_attempted_at: 1700000000, status: 'publishing' }), /ห้ามกดโพสต์ซ้ำ/);
  await assert.rejects(() => ctx.clickPostButton(send, 7, async () => { touched += 1; }, { job_id: 'j', status: 'confirmation_unknown' }), /ห้ามกดโพสต์ซ้ำ/);
  assert.equal(touched, 0);
  const source = ctx.clickPostButton.toString();
  assert.ok(!/Save draft|Save to draft|บันทึกแบบร่าง/.test(source), 'the Post fallback must never include a draft button');
});

test('R1 clickPostButton: leaving the form for Content is NOT proof of a post (recorded as unknown)', async () => {
  const { ctx, calls } = clickPostHarness({
    tabUrl: 'https://www.tiktok.com/tiktokstudio/content',
    onConfirmationEval: () => ({ result: { value: null } }),   // no toast was seen
  });
  const result = await ctx.runClickPostOnly();
  assert.equal(result.outcome, 'confirmation_unknown');
  assert.equal(result.posted, false);
  assert.equal(result.marked, false);
  assert.ok(calls.includes('unknown') && !calls.includes('mark'));
});

test('R1 dismissContinueToPostDialogIfPresent: only the button that matches the job intent, nothing without one', async () => {
  const ctx = worker();
  const expressions = [];
  const send = async (_m, params) => { expressions.push(String(params.expression)); return { result: { value: false } }; };
  assert.equal(await ctx.dismissContinueToPostDialogIfPresent(send, 50), false);                 // no intent: no click at all
  assert.equal(await ctx.dismissContinueToPostDialogIfPresent(send, 50, 'draft'), false);        // a draft never accepts a post dialog
  assert.equal(expressions.length, 0);
  await ctx.dismissContinueToPostDialogIfPresent(send, 50, 'post_now');
  assert.ok(expressions[0].includes('Post now') && !expressions[0].includes('Schedule now'));
  assert.ok(expressions[0].includes('postNowBtn && isContinueDialog'), 'the dialog text must be recognised');
  await ctx.dismissContinueToPostDialogIfPresent(send, 50, 'schedule');
  const last = expressions[expressions.length - 1];
  assert.ok(last.includes('Schedule now') && !last.includes('Post now'));
});

test('R1 release: there is no force; an attempted job is never released, a never-attempted claim is', async () => {
  const ctx = durableWorker({});
  const attempted = protocolJob({ status: 'publishing', publish_attempted_at: 1700000000 });
  await seedJob(ctx, attempted);
  const routes = [];
  ctx.postingRequest = async (route) => { routes.push(route); return { ...attempted }; };
  await assert.rejects(() => ctx.releasePostingJob({ force: true }), /ต้องตรวจผลเดิมก่อน/);
  assert.ok(!routes.includes('/release'), 'no /release call may be made for an attempted job');
  const claimedJob = protocolJob();
  const ctx2 = durableWorker({});
  await seedJob(ctx2, claimedJob);
  const routes2 = [];
  ctx2.postingRequest = async (route) => { routes2.push(route); return route === '/release' ? { ...claimedJob, status: 'cancelled' } : { ...claimedJob }; };
  const released = await ctx2.releasePostingJob({});
  assert.equal(released.status, 'cancelled');
  assert.ok(routes2.includes('/release'));
});

test('R1 park: if the backend cannot be asked, a possibly-attempted job is parked, never released on a stale copy', async () => {
  const ctx = durableWorker({});
  const job = protocolJob();                       // looks claimed locally, but the /attempt may have happened
  await seedJob(ctx, job);
  const routes = [];
  ctx.postingRequest = async (route) => { routes.push(route); throw new Error('backend down'); };
  const result = await ctx.parkPostingJob();
  assert.equal(result.parked, true);
  assert.ok(!routes.includes('/release') && !routes.includes('/clear'));
  // a job that was only prepared (never claimed) is simply cancelled via /clear
  const ctx2 = durableWorker({});
  const prepared = protocolJob({ status: 'prepared', lease_owner: null, lease_token: null });
  await seedJob(ctx2, prepared);
  const routes2 = [];
  ctx2.postingRequest = async (route) => { routes2.push(route); return { ...prepared }; };
  const res2 = await ctx2.parkPostingJob();
  assert.equal(res2.released, true);
  assert.ok(routes2.includes('/clear'));
});

test('R1 reconcileFromListPages: confirms only a row that matches the caption (and slot); never a made-up success', async () => {
  const ctx = worker();
  ctx.navigateAcceptingLeave = async () => true;
  ctx.chrome.tabs = { get: async () => ({ id: 7, url: 'https://www.tiktok.com/tiktokstudio/content' }) };
  const rowsText = (...rows) => ['Posts 219', 'Drafts 0', ...rows].join(NLC);
  const sendWith = (text) => async () => ({ result: { value: text } });
  const caption = 'ใช้จริงมาแล้วสามเดือนเต็ม พัดลมตัวนี้ดีมาก';
  const row = (badge, ...more) => ['00:28', caption, badge, 'Everyone', ...more].join(NLC);
  const sched = { job_id: 'j', intent: 'schedule', caption, schedule_date: '2026-11-10', schedule_time: '18:00', confirmation_token: 'tok' };
  const ok = await ctx.reconcileFromListPages(sendWith(rowsText(row('Nov 10, 6:00 PM (GMT+7) Bangkok'))), { id: 7 }, sched);
  assert.equal(ok.confirmed, true);
  assert.equal(ok.outcome, 'scheduled_on_platform');
  assert.equal(ok.proof.kind, 'content_page_reconciled');
  assert.match(ok.proof.notice, /caption and the slot 2026-11-10 18:00/);
  assert.equal(ok.proof.confirmation_token, 'tok');
  // right caption but another slot / no row / a view count equal to the day: not confirmed
  assert.equal((await ctx.reconcileFromListPages(sendWith(rowsText(row('Nov 12, 6:00 PM', '0', '10', '0'))), { id: 7 }, sched)).confirmed, false);
  assert.equal((await ctx.reconcileFromListPages(sendWith(rowsText()), { id: 7 }, sched)).confirmed, false);
  assert.equal((await ctx.reconcileFromListPages(sendWith(rowsText('00:28', 'คลิปอื่นทั้งหมด', 'Nov 10, 6:00 PM')), { id: 7 }, sched)).confirmed, false);
  // an immediate post: the row must carry a badge time close to the click, an older post with the same caption never confirms
  const attemptedAt = Date.parse('2026-11-10T11:00:00Z') / 1000;
  const RealDate = Date;
  const fixedNow = RealDate.parse('2026-11-10T11:02:00Z');
  ctx.Date = class extends RealDate { constructor(...args) { super(...(args.length ? args : [fixedNow])); } static now() { return fixedNow; } };
  const postNow = { job_id: 'j', intent: 'post_now', caption, publish_attempted_at: attemptedAt, confirmation_token: 'tok' };
  const fresh = await ctx.reconcileFromListPages(sendWith(rowsText(row('Nov 10, 6:01 PM (GMT+7) Bangkok'))), { id: 7 }, postNow);   // 11:01Z = 18:01 +07
  assert.equal(fresh.outcome, 'published');
  const stale = await ctx.reconcileFromListPages(sendWith(rowsText(row('Oct 2, 6:01 PM'))), { id: 7 }, postNow);
  assert.equal(stale.confirmed, false);
});

test('R1 reconcileFromListPages: a draft job is confirmed only by a matching row on the Drafts page', async () => {
  const ctx = worker();
  ctx.navigateAcceptingLeave = async () => true;
  const caption = 'แกะกล่องสุดคุ้ม ของแท้ ราคาดี';
  const draftsPage = (text) => async () => ({ result: { value: { url: 'https://www.tiktok.com/tiktokstudio/content?tab=draft', text } } });
  const job = { job_id: 'j', intent: 'draft', caption, confirmation_token: 'tok' };
  const yes = await ctx.reconcileFromListPages(draftsPage(['Drafts 1', caption].join(NLC)), { id: 7 }, job);
  assert.equal(yes.outcome, 'draft_saved');
  assert.equal(yes.proof.kind, 'drafts_page_confirmed');
  const no = await ctx.reconcileFromListPages(draftsPage(['Drafts 1', 'ข้อความของคลิปอื่น'].join(NLC)), { id: 7 }, job);
  assert.equal(no.confirmed, false);
});

test('R1 manual confirmation follows the job intent (was always "published")', async () => {
  for (const [intent, extra, expected] of [['draft', {}, 'draft_saved'], ['schedule', { schedule_date: '2026-11-12', schedule_time: '09:00' }, 'scheduled_on_platform'], ['post_now', {}, 'published']]) {
    const ctx = durableWorker({});
    const job = protocolJob({ status: 'confirmation_unknown', publish_attempted_at: 1700000000, attempted_source_account: '@mainuser', intent, ...extra });
    await seedJob(ctx, job);
    ctx.postingRequest = async () => ({ ...job });
    let body = null;
    ctx.retryPostingReceipt = async () => { body = (await ctx.postingState()).pendingReceipt?.body; return { success: true }; };
    await ctx.runReconcilePostingResult({ manual: true });
    assert.equal(body.outcome, expected, intent);
    assert.equal(body.proof.kind, 'manual_user_confirmation');
    assert.ok(body.proof.notice.length >= 8);
  }
});

test('schedule time follows TikTok five-minute increments', () => {
  const ctx = worker();
  assert.equal(ctx.normalizeScheduleTime('16:08'), '16:10');
  assert.equal(ctx.normalizeScheduleTime('23:58'), '23:55');
  assert.equal(ctx.normalizeScheduleTime('10:58'), '11:00');
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
  assert.equal(manifest.version, '0.8.0');
  assert.equal(manifest.content_scripts, undefined, 'no legacy content script');
  for (const gone of ['batch_runner.js', 'batch_runner.test.cjs', 'content_script.js', 'popup.html', 'popup.js']) assert.ok(!fs.existsSync(path.join(__dirname, gone)), gone + ' must stay deleted');
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

  // Verify single global header opener exists in sidepanel and the old popup is gone
  assert.match(sideHtml, /id="headerOpenTikTokBtn"/);

  // Verify redundant buttons were removed (User requested exactly one single spot)
  assert.doesNotMatch(sideHtml, /id="listOpenTikTokBtn"/);
  assert.doesNotMatch(sideHtml, /id="openTikTokBtn"/);
  assert.doesNotMatch(sideJs, /listOpenTikTokBtn/);
  assert.doesNotMatch(sideJs, /openTikTokBtn/);

  // Verify listeners and URL opener in JS
  assert.match(sideJs, /headerOpenTikTokBtn/);
  assert.match(sideJs, /tiktok\.com\/tiktokstudio\/upload/);

  // Verify clean UI standard: no emojis in button texts
  assert.doesNotMatch(sideHtml, /<button[^>]*>[^<]*[\u{1F300}-\u{1F9FF}][^<]*<\/button>/u);
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

test('TikTok Studio Quota Detector and Batch Size Cap are fully wired into sidepanel and background', () => {
  const sideHtml = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  const sideJs = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  const bgJs = fs.readFileSync(path.join(__dirname, 'background.js'), 'utf8');

  // Background action registered
  assert.match(bgJs, /'detect-tiktok-quota':/);
  assert.match(bgJs, /function runDetectTikTokQuota/);

  // Sidepanel UI elements wired
  assert.match(sideHtml, /id="batchQuotaCard"/);
  assert.match(sideHtml, /id="btnCheckQuota"/);
  assert.match(sideHtml, /id="quotaScheduleValue"/);
  assert.match(sideHtml, /id="quotaDraftValue"/);
  assert.match(sideHtml, /id="batchLimitSelect"/);
  assert.match(sideHtml, /id="batchCappedCount"/);

  // Sidepanel script logic wired
  assert.match(sideJs, /checkTikTokQuota/);
  assert.match(sideJs, /getEffectiveBatchLimit/);
  assert.match(sideJs, /updateBatchCountDisplay/);
  assert.match(sideJs, /slicedClips/);
  assert.match(sideHtml, /<script src="quota_detector\.js"><\/script>/);
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
    sendCommand: async (_target, method, params = {}) => {
      if (method !== 'Runtime.evaluate') return {};
      // The pre-attempt readiness probe (page mode + enabled primary button) is answered like a healthy "Post now" page.
      if (String(params.expression || '').includes('{found: false}')) return { result: { value: { found: true, visible: true, text: 'Post', disabled: false } } };
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

test('waitForPostConfirmation: matches standard Thai TikTok Studio toasts immediately', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => ({ url: UPLOAD_URL }) };

  const thaiCases = [
    { notice: 'วิดีโอถูกกำหนดเวลาแล้ว', expectedOutcome: 'scheduled_on_platform' },
    { notice: 'กำหนดเวลาโพสต์แล้ว', expectedOutcome: 'scheduled_on_platform' },
    { notice: 'วิดีโอของคุณได้รับการกำหนดเวลาแล้ว', expectedOutcome: 'scheduled_on_platform' },
    { notice: 'วิดีโอถูกโพสต์แล้ว', expectedOutcome: 'published' },
    { notice: 'วิดีโอของคุณได้รับการเผยแพร่แล้ว', expectedOutcome: 'published' },
  ];

  for (const tc of thaiCases) {
    const send = async () => ({
      result: {
        value: {
          platform_outcome: tc.expectedOutcome,
          notice: tc.notice,
        }
      }
    });
    const res = await ctx.waitForPostConfirmation(send, 7, 500);
    assert.equal(res.confirmed, true, `Notice "${tc.notice}" must be confirmed`);
    assert.equal(res.outcome, tc.expectedOutcome);
    assert.equal(res.proof.notice, tc.notice);
  }
});

test('waitForPostConfirmation: fast-path breaks quickly when tab navigated to /content', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => ({ url: 'https://www.tiktok.com/tiktokstudio/content' }) };
  const send = async () => ({ result: { value: { done: false } } });

  const start = Date.now();
  const res = await ctx.waitForPostConfirmation(send, 7, 10_000);
  const elapsed = Date.now() - start;

  // Must break within ~1 second rather than stalling for the full 10,000ms timeout
  assert.equal(res.confirmed, false);
  assert.ok(elapsed < 2000, `Expected elapsed < 2000ms on /content navigation fast-path, got ${elapsed}ms`);
});


test('B1: wait-for-upload-only resolves a success object so the side panel can continue', async () => {
  const calls = [];
  const ctx = worker({debugger: {
    attach: async () => { calls.push('attach'); },
    detach: async () => { calls.push('detach'); },
    sendCommand: async (_target, method) => method === 'Runtime.evaluate' ? {result:{value:true}} : {},
  }});
  ctx.findUploadTab = async () => ({id: 7});
  const result = await ctx.runWaitForUploadOnly();
  assert.equal(result?.success, true);
  assert.deepEqual(calls, ['attach', 'detach']);
});

test('B1: wait-for-upload-only failure still detaches and rejects with the TikTok message', async () => {
  const calls = [];
  const ctx = worker({debugger: {
    attach: async () => { calls.push('attach'); },
    detach: async () => { calls.push('detach'); },
    sendCommand: async () => ({exceptionDetails: {text: 'boom'}}),
  }});
  ctx.findUploadTab = async () => ({id: 7});
  await assert.rejects(() => ctx.runWaitForUploadOnly(), /boom/);
  assert.deepEqual(calls, ['attach', 'detach']);
});

test('B3: a percent sign typed in the caption is not mistaken for upload progress', async () => {
  const ctx = worker();
  ctx.sleep = async () => {};
  const editor = {innerText: 'พัดลมพกพา ลด 50% วันนี้ #fan'};
  const makeDom = (bodyText) => vm.createContext({document: {
    body: {innerText: bodyText},
    querySelectorAll: (sel) => sel.includes('contenteditable') ? [editor] : [],
  }});
  const sendFor = (dom) => async (_m, params) => ({result: {value: vm.runInContext(params.expression, dom)}});
  const done = await ctx.waitForUploadComplete(sendFor(makeDom('อัปโหลดแล้ว\nพัดลมพกพา ลด 50% วันนี้ #fan\nโพสต์')), 50);
  assert.equal(done, true);
  const uploading = await ctx.waitForUploadComplete(sendFor(makeDom('42%\nพัดลมพกพา ลด 50% วันนี้ #fan')), 1);
  assert.equal(uploading, false);
});

test('B4: batch park never cancels an attempted job (no duplicate post) and frees the worker', async () => {
  const saved = {}, ctx = durableWorker(saved);
  const job = await seedJob(ctx, protocolJob({status: 'confirmation_unknown', publish_attempted_at: 1}));
  const routes = [];
  ctx.postingRequest = async (route) => { routes.push(route); if (route.startsWith('/jobs/')) return {...job}; throw new Error('unexpected ' + route); };
  const res = await ctx.releasePostingJob({park: true});
  assert.equal(res.parked, true);
  assert.ok(!routes.includes('/release'));
  assert.equal(saved.omnicutPostingProtocolV2.activeJob, null);
  assert.equal(saved.omnicutPostingProtocolV2.unresolvedJobs[0].job_id, 'job-1');
  await ctx.selectPostingChannel('main');
});

test('B4: batch park releases a claimed job that was never attempted', async () => {
  const saved = {}, ctx = durableWorker(saved);
  const job = await seedJob(ctx);
  const bodies = [];
  ctx.postingRequest = async (route, _ch, body) => {
    if (route.startsWith('/jobs/')) return {...job};
    if (route === '/release') { bodies.push(body); return {...job, status: 'cancelled', revision: 3}; }
    throw new Error('unexpected ' + route);
  };
  const res = await ctx.releasePostingJob({park: true});
  assert.equal(res.success, true);
  assert.equal(bodies.length, 1);
  assert.equal(saved.omnicutPostingProtocolV2.activeJob, null);
});

test('B4: batch park retries a stuck receipt and keeps it if the backend still fails', async () => {
  const saved = {}, ctx = durableWorker(saved);
  const job = await seedJob(ctx, protocolJob({status: 'publishing', publish_attempted_at: 1}));
  const state = await ctx.postingState();
  state.pendingReceipt = {channelId: 'main', body: {job_id: job.job_id, outcome: 'published'}, reconcile: false};
  await ctx.persistPostingState(state);
  let acks = 0;
  ctx.postingRequest = async (route) => { if (route === '/ack') { acks += 1; throw new Error('backend down'); } return {...job}; };
  await assert.rejects(() => ctx.releasePostingJob({park: true}), /posting_receipt_unsent/);
  assert.equal(acks, 3);
  assert.ok(saved.omnicutPostingProtocolV2.pendingReceipt);
});

test('B4: batch park succeeds once a stuck receipt goes through on retry', async () => {
  const saved = {}, ctx = durableWorker(saved);
  const job = await seedJob(ctx, protocolJob({status: 'publishing', publish_attempted_at: 1}));
  const state = await ctx.postingState();
  state.pendingReceipt = {channelId: 'main', body: {job_id: job.job_id, outcome: 'published'}, reconcile: false};
  await ctx.persistPostingState(state);
  let acks = 0;
  ctx.postingRequest = async (route) => {
    if (route === '/ack') { acks += 1; if (acks < 2) throw new Error('blip'); return {...job, status: 'published'}; }
    return {...job, status: 'published'};
  };
  const res = await ctx.releasePostingJob({park: true});
  assert.equal(res.success, true);
  assert.equal(saved.omnicutPostingProtocolV2.pendingReceipt, null);
  assert.equal(saved.omnicutPostingProtocolV2.activeJob, null);
});

test('B5: side panel batch never force-cancels backend jobs directly', () => {
  const panel = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  assert.ok(!panel.includes('tiktok-autopost/release'), 'raw /release from the panel can cancel an attempted job');
  const batchStart = panel.indexOf('const batchActions = {');
  const batchEnd = panel.indexOf('const orchestratorModule', batchStart);
  const batchBlock = panel.slice(batchStart, batchEnd);
  assert.ok(!/release-posting-job',\s*force:\s*true/.test(batchBlock), 'batch must park, not force-release');
});

test('stray TikTok Content tab does not replace the real post click for an unattempted job', async () => {
  const ctx = worker({tabs: {query: async () => [{id: 3, url: 'https://www.tiktok.com/tiktokstudio/content'}]}});
  let reconciled = 0;
  ctx.fetchPendingJob = async () => protocolJob();
  ctx.runReconcilePostingResult = async () => { reconciled += 1; return {outcome: 'published'}; };
  ctx.findUploadTab = async () => { throw new Error('went-to-upload-tab'); };
  await assert.rejects(() => ctx.runClickPostOnly(), /went-to-upload-tab/);
  assert.equal(reconciled, 0);
});

test('Content tab after a real click reconciles instead of clicking again', async () => {
  const ctx = worker({tabs: {query: async () => [{id: 3, url: 'https://www.tiktok.com/tiktokstudio/content'}]}});
  ctx.fetchPendingJob = async () => protocolJob({status: 'confirmation_unknown', publish_attempted_at: 1});
  ctx.runReconcilePostingResult = async () => ({outcome: 'published'});
  ctx.findUploadTab = async () => { throw new Error('must not click again'); };
  const res = await ctx.runClickPostOnly();
  assert.equal(res.posted, true);
});

test('schedule window rejects past or too-close slots and accepts a future one', () => {
  const ctx = worker();
  const now = new Date('2026-11-09T10:00:00').getTime();
  assert.match(ctx.scheduleWindowProblem('2026-11-09', '09:00', now), /ผ่านไปแล้ว/);
  assert.match(ctx.scheduleWindowProblem('2026-11-09', '10:10', now), /15 นาที/);
  assert.equal(ctx.scheduleWindowProblem('2026-11-09', '10:30', now), '');
  assert.equal(ctx.scheduleWindowProblem('', '', now), '');
});

test('account read waits for the Studio header instead of failing on the first empty read', async () => {
  const ctx = worker();
  let calls = 0;
  const send = async () => ({result: {value: {handles: ++calls < 4 ? [] : ['@mainuser']}}});
  assert.equal(await ctx.readStudioAccount(send), '@mainuser');
  assert.equal(calls, 4);
  const never = async () => ({result: {value: {handles: []}}});
  assert.equal(await ctx.readStudioAccount(never, 3), null);
});

test('a scheduled job is never reported as published just because TikTok toasts "Video published"', () => {
  const ctx = worker();
  const toast = {confirmed: true, outcome: 'published', proof: {kind: 'platform_success_notice', notice: 'Video published'}};
  assert.equal(ctx.withScheduledOutcome(toast, {schedule_date: '2026-11-10', schedule_time: '07:00'}).outcome, 'scheduled_on_platform');
  assert.equal(ctx.withScheduledOutcome(toast, {}).outcome, 'published');
  assert.equal(ctx.withScheduledOutcome({confirmed: false}, {schedule_date: 'x', schedule_time: 'y'}).confirmed, false);
});

test('cover fallback closes the Edit cover modal before reporting success', async () => {
  const ctx = worker();
  let dismissed = 0;
  ctx.fetchPendingJob = async () => ({caption: 'review', hashtags: '#x', tiktok_product_id: '123'});
  ctx.runWaitForUploadOnly = async () => ({success: true});
  ctx.runTypeCaptionOnly = async () => ({success: true});
  ctx.runAttachProductOnly = async () => ({success: true});
  ctx.runUploadCoverOnly = async () => { throw new Error('ไม่พบ node ของช่องอัปโหลดปก'); };
  ctx.runDismissCoverModal = async () => { dismissed += 1; return true; };
  const ok = await ctx.runPrepareDetails({coverFallback: true, coverPath: 'c.jpg'});
  assert.equal(ok.success, true);
  assert.equal(ok.coverFallbackUsed, true);
  assert.equal(ok.coverModalClosed, true);
  assert.equal(dismissed, 1);
  const strict = await ctx.runPrepareDetails({coverFallback: false, coverPath: 'c.jpg'});
  assert.equal(strict.success, false);
  assert.equal(strict.step, 'cover');
  assert.equal(dismissed, 1);
});

test('window guard enlarges a small normal window once and leaves maximized/large windows alone', async () => {
  const updates = [];
  const mk = win => worker({windows: {get: async () => win, update: async (id, props) => { updates.push([id, props]); }}});
  assert.equal(await mk({state: 'normal', width: 900, height: 700}).ensureWorkableWindow({windowId: 7}), true);
  assert.equal(JSON.stringify(updates[0]), JSON.stringify([7, {state: 'normal', width: 1440, height: 960}]));
  updates.length = 0;
  assert.equal(await mk({state: 'normal', width: 1500, height: 900}).ensureWorkableWindow({windowId: 7}), false);
  assert.equal(await mk({state: 'maximized', width: 1000, height: 600}).ensureWorkableWindow({windowId: 7}), false);
  assert.equal(await worker().ensureWorkableWindow({windowId: 7}), false); // no windows API (conductor host)
  assert.equal(updates.length, 0);
});

test('upload resets a leftover (non-fresh) page once and then finds the file input', async () => {
  let attached = 0, detached = 0, resets = 0, inputChecks = 0, setFiles = 0;
  const ctx = worker({debugger: {
    attach: async () => { attached += 1; },
    detach: async () => { detached += 1; },
    sendCommand: async (_t, method) => {
      if (method === 'DOM.getDocument') return {root: {nodeId: 1}};
      if (method === 'DOM.querySelectorAll') { inputChecks += 1; return {nodeIds: inputChecks <= 1 ? [] : [42]}; }
      if (method === 'DOM.setFileInputFiles') { setFiles += 1; return {}; }
      return {};
    },
  }});
  ctx.fetchPendingJob = async () => ({job_id: 'j', video_path: 'C:/v.mp4'});
  ctx.findUploadTab = async () => ({id: 7, url: 'https://www.tiktok.com/tiktokstudio/upload'});
  ctx.attachDebuggerWithCleanTabFallback = async tab => { attached += 1; return tab; };
  ctx.findFileInputNodeId = (() => { const real = ctx.findFileInputNodeId; let n = 0; return async send => { n += 1; if (n === 1) throw new Error('ไม่พบ <input type="file">'); return 42; }; })();
  ctx.cleanResetUploadTab = async () => { resets += 1; return {success: true}; };
  ctx.guardPostingAction = async () => 'acct';
  ctx.setFileInput = async () => { setFiles += 1; };
  const res = await ctx.runUploadFileOnly();
  assert.equal(res.success, true);
  assert.equal(res.resetFirst, true);
  assert.equal(resets, 1);
  assert.equal(setFiles, 1);
});

test('verify-post-content finds the row (after reload retries) and always returns to the upload page', async () => {
  const nl = String.fromCharCode(10);
  const rowText = ['00:35', 'เล่นเกมนานแค่ไหนเครื่องก็ไม่ร้อน HOYAUP พัดลมระบายความร้อน', 'Nov 10, 7:00 AM (GMT+7) Bangkok', 'Everyone'].join(nl) + nl;
  const urls = [];
  let evaluations = 0;
  const ctx = worker({
    tabs: {update: async (_id, props) => { urls.push(props.url); return {id: 7}; }, get: async () => ({id: 7, url: 'https://www.tiktok.com/tiktokstudio/upload'}), query: async () => []},
    debugger: {
      attach: async () => {}, detach: async () => {},
      sendCommand: async (_t, method, params) => {
        if (method !== 'Runtime.evaluate') return {};
        if (/BeforeUnloadEvent/.test(params.expression)) return {result: {value: true}}; // prompt disarm, not a page read
        if (/scrollTop/.test(params.expression)) return {result: {value: 0}};   // the list does not scroll in this fake
        evaluations += 1;
        // first two page loads still show the old list, the third shows the new row
        const loads = urls.filter(u => u.endsWith('/content')).length;
        return {result: {value: loads < 3 ? ['00:25', 'อย่างอื่น', 'Pinned'].join(nl) + nl : rowText}};
      },
    },
  });
  ctx.findUploadTab = async () => ({id: 7, url: 'https://www.tiktok.com/tiktokstudio/upload'});
  const found = await ctx.runVerifyPostOnContent({caption: 'เล่นเกมนานแค่ไหนเครื่องก็ไม่ร้อน HOYAUP พัดลม', scheduleDate: '2026-11-10', scheduleTime: '07:00'});
  assert.equal(found.verified, true);
  assert.equal(urls[urls.length - 1], 'https://www.tiktok.com/tiktokstudio/upload');
  assert.ok(urls.filter(u => u.endsWith('/content')).length >= 3, 'reloaded until the list caught up');

  evaluations = 0;
  urls.length = 0;
  const missing = await ctx.runVerifyPostOnContent({caption: 'คลิปที่ไม่เคยโพสต์เลยสักครั้ง', attempts: 2});
  assert.equal(missing.verified, false);
  assert.equal(missing.reason, 'row_not_found');
  assert.equal(urls[urls.length - 1], 'https://www.tiktok.com/tiktokstudio/upload');
});

test('leaving the upload page first disarms its beforeunload prompt, then navigates normally', async () => {
  const commands = [];
  const urls = [];
  let detached = 0;
  // the worker harness fakes setTimeout as 'run now'; give withTimeout a real timer for this test
  const realWithTimeout = (p, ms, label) => Promise.race([Promise.resolve(p), new Promise((_, rej) => setTimeout(() => rej(new Error(label || 'timeout')), ms))]);
  const ctx = worker({
    tabs: {update: async (_id, props) => { urls.push(props.url); return {id: 7}; }},
    debugger: {
      attach: async () => {}, detach: async () => { detached += 1; },
      sendCommand: async (_target, method, params) => { commands.push([method, params && params.expression]); return {result: {value: true}}; },
    },
  });
  ctx.withTimeout = realWithTimeout;
  assert.equal(await ctx.navigateAcceptingLeave(7, 'https://www.tiktok.com/tiktokstudio/upload'), true);
  const evaluate = commands.find(c => c[0] === 'Runtime.evaluate');
  assert.ok(evaluate && /BeforeUnloadEvent/.test(evaluate[1]) && /preventDefault/.test(evaluate[1]) && /returnValue/.test(evaluate[1]), 'prompt disarmed before leaving');
  assert.deepEqual(Array.from(urls), ['https://www.tiktok.com/tiktokstudio/upload']);
  assert.equal(detached, 1);
  assert.ok(!commands.some(c => c[0] === 'Page.navigate'), 'no hanging debugger navigation');

  // debugger unavailable (DevTools open ...): still navigates, reports not-neutralized, never throws
  const fallbackUrls = [];
  const fallback = worker({
    tabs: {update: async (_id, props) => { fallbackUrls.push(props.url); }},
    debugger: {attach: async () => { throw new Error('Cannot attach to this target'); }, detach: async () => {}, sendCommand: async () => ({})},
  });
  assert.equal(await fallback.navigateAcceptingLeave(7, 'https://x.test/'), false);
  assert.deepEqual(Array.from(fallbackUrls), ['https://x.test/']);

  // a hung page (debugger never answers) must not hang the reset: bounded by a timeout
  const hung = worker({
    tabs: {update: async () => ({id: 7})},
    debugger: {attach: async () => {}, detach: async () => {}, sendCommand: () => new Promise(() => {})},
  });
  hung.withTimeout = (p, ms, label) => realWithTimeout(p, 50, label);
  const started = Date.now();
  assert.equal(await Promise.race([hung.navigateAcceptingLeave(7, 'https://x.test/'), new Promise(r => setTimeout(() => r('HUNG'), 8000))]), false);
  assert.ok(Date.now() - started < 8000);
});

function identityPage(ctx, hrefs) {
  ctx.document = {
    querySelectorAll: () => hrefs.map(h => ({ getAttribute: () => h, textContent: h })),
    getElementById: () => null,
  };
}

test('R2 studioIdentityAtClick: nothing readable and nothing verified stops (the intended handle is never trusted)', () => {
  const ctx = worker();
  identityPage(ctx, []);
  assert.throws(() => ctx.studioIdentityAtClick('@main', null), /source_account_required/);
  assert.throws(() => ctx.studioIdentityAtClick(null, undefined), /source_account_required/);
});

test('R2 studioIdentityAtClick: falls back only to the handle verified through the avatar menu, and it must equal the target', () => {
  const ctx = worker();
  identityPage(ctx, []);
  assert.equal(ctx.studioIdentityAtClick('@main', '@main'), '@main');
  assert.throws(() => ctx.studioIdentityAtClick('@main', '@other'), /account_handle_mismatch/);
  identityPage(ctx, ['/@main']);
  assert.equal(ctx.studioIdentityAtClick('@main', '@main'), '@main');
  assert.throws(() => ctx.studioIdentityAtClick('@main', '@other'), /account_handle_mismatch/);   // page and verified disagree
  identityPage(ctx, ['/@other']);
  assert.throws(() => ctx.studioIdentityAtClick('@main', '@main'), /account_handle_mismatch/);
  identityPage(ctx, ['/@main', '/@other']);
  assert.throws(() => ctx.studioIdentityAtClick('@main', '@main'), /source_account_required/);        // two accounts visible
});

test('R2 typeCaption never types price text, placeholders or oversize text', async () => {
  const ctx = worker();
  const send = async () => { throw new Error('must not reach the page'); };
  await assert.rejects(() => ctx.typeCaption(send, 'ราคา 199 บาท', '#a'), /content_blocked.*price_in_caption/);
  await assert.rejects(() => ctx.typeCaption(send, '{product_name}', ''), /content_blocked.*placeholder_in_caption/);
  await assert.rejects(() => ctx.typeCaption(send, 'ก'.repeat(4001), ''), /content_blocked.*caption_too_long/);
});

test('R3 panel wiring: one run at a time, no legacy runner, manual prepare guarded, honest end state', () => {
  const side = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  const html = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  assert.doesNotMatch(html, /batch_runner\.js/);
  assert.match(html, /run_lock\.js/);
  assert.doesNotMatch(side, /OmniBatchRunner/);
  assert.doesNotMatch(side, /createBatchRunner/);
  // the starting flag is set before the first await of the click handler
  const handler = side.slice(side.indexOf("batchStartBtn?.addEventListener('click'"));
  assert.ok(handler.indexOf('batchStarting = true') > 0 && handler.indexOf('batchStarting = true') < handler.indexOf('await'));
  assert.match(side, /beforeunload/);
  assert.match(side, /OmniRunLock\.acquire/);
  assert.match(side, /requiredActions:/);
  assert.match(side, /runnerModule\.finalVerdict\(summary\)/);
  // the manual prepare route runs the same content/status guard as the batch
  const manual = side.slice(side.indexOf('async function prepareClip(item)'), side.indexOf('async function prepareClip(item)') + 900);
  assert.match(manual, /clipSkipReason/);
  // worker answers carry postAttempted so the orchestrator can tell "unknown" from "failed"
  const bg = fs.readFileSync(path.join(__dirname, 'background.js'), 'utf8');
  assert.match(bg, /postAttempted/);
});

test('R4 quota counting never walks the tab away while a job is in flight; click steps never recover a Studio tab', async () => {
  const ctx = worker();
  ctx.runDetectQuotaFromTab = async () => ({ success: true });
  ctx.postingState = async () => ({ activeJob: { job_id: 'j' } });
  ctx.runCountScheduledOnContent = async () => { throw new Error('must not navigate'); };
  const result = await ctx.runDetectTikTokQuota({ allowNavigate: true });
  assert.equal(result.countSkipped, 'active_job');
  const bg = fs.readFileSync(path.join(__dirname, 'background.js'), 'utf8');
  assert.match(bg, /NO_TAB_RECOVERY_ACTIONS = new Set\(\[[^\]]*'click-post-only'[^\]]*'save-draft-only'/);
  assert.match(bg, /findUploadTab\(\{recover: !NO_TAB_RECOVERY_ACTIONS\.has\(message\.action\)\}\)/);
});

test('R5 notifyAttention raises a notification and a badge; clearAttention removes the badge', async () => {
  const ctx = worker();
  const seen = { badge: [], created: [] };
  ctx.chrome.action = { setBadgeText: async (o) => seen.badge.push(o.text), setBadgeBackgroundColor: async () => {} };
  ctx.chrome.notifications = { create: async (id, opts) => { seen.created.push({ id, ...opts }); } };
  const r = await ctx.notifyAttention({ title: 'ต้องตรวจ', message: 'คลิปยืนยันผลไม่ได้' });
  assert.equal(r.notified, true);
  assert.deepEqual(seen.badge, ['!']);
  assert.equal(seen.created[0].requireInteraction, true);
  assert.equal(seen.created[0].message, 'คลิปยืนยันผลไม่ได้');
  await ctx.clearAttention();
  assert.deepEqual(seen.badge, ['!', '']);
  // a browser without the API must not break the run
  const bare = worker();
  bare.chrome.action = undefined; bare.chrome.notifications = undefined;
  assert.equal((await bare.notifyAttention({})).notified, false);
});

test('R5 preflight and evidence are read-only probes: no tab means a clear failure, never a recovery or a click', async () => {
  const ctx = worker();
  let recovered = false;
  ctx.chrome.runtime.getManifest = () => ({ version: 'test' });
  ctx.findUploadTab = async (opts) => { recovered = Boolean(opts?.recover); throw new Error('ไม่พบแท็บ TikTok Studio'); };
  const pre = await ctx.runPreflight();
  assert.equal(pre.success, false);
  assert.match(pre.error, /ไม่พบแท็บ/);
  assert.equal(recovered, false, 'the probe must not navigate a Studio tab to the upload page');
  const ev = await ctx.runCaptureEvidence();
  assert.equal(ev.found, false);
  const bg = fs.readFileSync(path.join(__dirname, 'background.js'), 'utf8');
  assert.match(bg, /'run-preflight': \(\) => runPreflight\(\)/);
  assert.match(bg, /'capture-evidence'/);
});

test('R5 panel wiring: preflight before the confirm dialog, history of every log line, evidence, attention notice', () => {
  const side = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  const html = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  for (const file of ['limits.js', 'preflight.js', 'run_history.js', 'run_lock.js']) assert.match(html, new RegExp(`<script src="${file.replace('.', '\.')}"></script>`));
  assert.ok(html.indexOf('limits.js') < html.indexOf('post_guard.js') && html.indexOf('limits.js') < html.indexOf('batch_orchestrator.js'), 'limits.js loads first');
  assert.match(html, /id="batchPreflightBtn"/);
  assert.match(html, /id="batchHistoryBtn"/);
  const handler = side.slice(side.indexOf('async function runBatchFromPanel('));
  assert.ok(handler.indexOf('runPreflightAndReport(') > 0 && handler.indexOf('runPreflightAndReport(') < handler.indexOf('askConfirm('), 'preflight runs before the confirm dialog');
  assert.match(handler, /if \(!readiness\.ok\)/);
  assert.match(side, /activeRecorder\?\.log\(kind, msg\)/);
  assert.match(side, /captureEvidence: async/);
  assert.match(side, /notifyAttentionIfNeeded\(/);
  assert.match(side, /activeRecorder\?\.setJob\(prepared\.job_id/);
  // clean-UI rule: the new buttons start with a verb and carry no icon
  assert.doesNotMatch(html, /id="batchPreflightBtn"[^>]*>\s*<svg/);
});

// ---- publish from draft ----
function publishDraftHarness({ job, pick = { ok: true, count: 1 }, editor, switched = { success: true } }) {
  const ctx = worker();
  const seen = { switched: null, nowEval: 0, clicked: 0, navigated: [], detached: 0 };
  ctx.fetchPendingJob = async () => job;
  ctx.findUploadTab = async () => ({ id: 7, url: 'https://www.tiktok.com/tiktokstudio/upload' });
  ctx.navigateAcceptingLeave = async (_id, url) => { seen.navigated.push(url); };
  ctx.sleep = async () => {};
  ctx.ensureWorkableViewport = async () => null;
  ctx.guardPostingAction = async () => '@main';
  ctx.switchToScheduleMode = async (_send, args) => { seen.switched = args; return switched; };
  ctx.chrome.debugger = {
    attach: async () => {}, detach: async () => { seen.detached += 1; },
    sendCommand: async (_t, method, params) => {
      if (method !== 'Runtime.evaluate') return {};
      const expression = String(params.expression);
      if (expression.includes('components_DraftRowLayout_FlexRow')) return { result: { value: pick } };
      if (expression.includes('post_video_button')) return { result: { value: editor } };
      if (expression.includes("labels = ['Now'")) { seen.nowEval += 1; return { result: { value: { ok: true } } }; }
      return { result: { value: {} } };
    },
  };
  return { ctx, seen };
}
const draftJob = (over = {}) => ({ job_id: 'j1', intent: 'publish_draft', status: 'claimed', caption: 'บอกลาสมาร์ตวอทช์หนักๆ อัปเกรดชีวิต', schedule_date: '2030-01-02', schedule_time: '09:00', ...over });
const goodEditor = (ctx) => ({ url: 'https://www.tiktok.com/tiktokstudio/upload?from=creator_center&draft_id=1&open_editor=0', hasPost: true, caption: ctx.OmniPostGuard.captionKey('บอกลาสมาร์ตวอทช์หนักๆ อัปเกรดชีวิต') });

test('publish_draft behaves like schedule / post_now for the button label, outcome and dismissal rules', () => {
  const ctx = worker();
  assert.equal(ctx.jobIntent({ intent: 'publish_draft', schedule_date: '2030-01-02', schedule_time: '09:00' }), 'schedule');
  assert.equal(ctx.jobIntent({ intent: 'publish_draft' }), 'post_now');
  assert.equal(ctx.jobIntent({ intent: 'draft' }), 'draft');
});

test('open-draft-for-publish: a scheduled publication opens the matching draft, checks its caption and sets the slot', async () => {
  const probe = worker();
  const { ctx, seen } = publishDraftHarness({ job: draftJob(), editor: goodEditor(probe) });
  ctx.OmniPostGuard = probe.OmniPostGuard;
  const result = await ctx.runOpenDraftForPublish();
  assert.equal(result.success, true);
  assert.equal(result.mode, 'schedule');
  assert.deepEqual(seen.navigated, ['https://www.tiktok.com/tiktokstudio/content?tab=draft']);
  assert.deepEqual({ date: seen.switched.date, time: seen.switched.time }, { date: '2030-01-02', time: '09:00' });
  assert.equal(seen.detached, 1);
});

test('open-draft-for-publish: an immediate publication keeps/sets "Now" and never touches the schedule', async () => {
  const probe = worker();
  const { ctx, seen } = publishDraftHarness({ job: draftJob({ schedule_date: null, schedule_time: null }), editor: goodEditor(probe) });
  const result = await ctx.runOpenDraftForPublish();
  assert.equal(result.mode, 'now');
  assert.equal(seen.nowEval, 1);
  assert.equal(seen.switched, null);
});

test('open-draft-for-publish refuses: wrong job kind, already attempted, no/ambiguous draft, different caption, unset slot', async () => {
  const probe = worker();
  const editor = goodEditor(probe);
  await assert.rejects(() => publishDraftHarness({ job: draftJob({ intent: 'draft' }), editor }).ctx.runOpenDraftForPublish(), /intent_mismatch/);
  await assert.rejects(() => publishDraftHarness({ job: draftJob({ publish_attempted_at: 1700000000, status: 'publishing' }), editor }).ctx.runOpenDraftForPublish(), /posting_reconciliation_required/);
  await assert.rejects(() => publishDraftHarness({ job: draftJob({ caption: 'สั้น' }), editor }).ctx.runOpenDraftForPublish(), /สั้นเกินกว่า/);
  await assert.rejects(() => publishDraftHarness({ job: draftJob(), pick: { ok: false, count: 0 }, editor }).ctx.runOpenDraftForPublish(), /draft_not_found/);
  await assert.rejects(() => publishDraftHarness({ job: draftJob(), pick: { ok: false, count: 2 }, editor }).ctx.runOpenDraftForPublish(), /draft_ambiguous/);
  await assert.rejects(() => publishDraftHarness({ job: draftJob(), editor: { ...editor, caption: 'caption-ของคลิปอื่นทั้งหมด' } }).ctx.runOpenDraftForPublish(), /draft_mismatch/);
  const noSlot = publishDraftHarness({ job: draftJob(), editor, switched: { success: false, reason: 'schedule_toggle_not_confirmed' } });
  await assert.rejects(() => noSlot.ctx.runOpenDraftForPublish(), /schedule_not_set/);
  assert.equal(noSlot.seen.detached, 1, 'the debugger is always detached');
});

test('open-draft-for-publish never presses Post or Save draft (source scan) and is wired as an action', () => {
  const bg = fs.readFileSync(path.join(__dirname, 'background.js'), 'utf8');
  const fn = bg.slice(bg.indexOf('async function runOpenDraftForPublish()'), bg.indexOf('let actionRunning = false;'));
  assert.doesNotMatch(fn, /post_video_button"\]\)\.click|save_draft_button|\.click\(\);\s*\/\/ post/i);
  assert.doesNotMatch(fn, /clickPostButton|runClickPostOnly|savePostingReceipt/);
  assert.match(bg, /'open-draft-for-publish': \(\) => runOpenDraftForPublish\(\)/);
});

test('publish-from-draft panel wiring: drafts are cards in the main list, ticked and run like any clip', () => {
  const side = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  const html = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  assert.doesNotMatch(html, /id="draftPublishPanel"/, 'no separate box any more');
  assert.match(html, /data-filter="draft"/);
  assert.match(html, /id="filterCountDraft"/);
  // draft rows of the queue become clips of the list
  assert.match(side, /'awaiting_post', 'failed', 'draft_on_platform'\]\.includes\(item\.status\)/);
  // the card says what it is, lets the slot be changed, and posts live only through its own confirmed run
  assert.match(side, /แบบร่างอยู่บน TikTok · จะเผยแพร่/);
  assert.match(side, /btn\.addEventListener\('click', \(\) => startDraftPublish\(item, \{ now: true \}\)\)/);
  assert.match(side, /เผยแพร่สดทันที ไม่ใช่การตั้งเวลา/);
  // an unticked whole-queue run never publishes a draft by itself
  assert.match(side, /matchesQuery: \(c\) => !c\.is_draft && /);
  // a draft is never part of a draft-only run, and still needs a valid slot otherwise
  assert.match(side, /draft_in_draft_mode/);
  assert.match(side, /function blockCodeFor\(/);
  // a draft is never re-uploaded or re-filled; the worker opens it instead
  assert.match(side, /if \(clip\?\.publish_draft\) return panelWorkerRequest\(\{ action: 'open-draft-for-publish' \}\)/);
  assert.match(side, /if \(clip\?\.publish_draft\) return \{ success: true, skipped: 'draft' \}/);
  assert.match(side, /clip\.publish_draft && clip\.publish_now \? \{ confirm_live: true \}/);
  const start = side.slice(side.indexOf('async function startDraftPublish('));
  assert.match(start, /batchStarting = true/);
  assert.match(start, /runBatchFromPanel\(\{ clips: \[clip\]/);
});

test('collectContentRows walks a virtualized list: a row far below the first screen is found (post-now rows sit after all scheduled ones)', async () => {
  const ctx = worker();
  const nl2 = String.fromCharCode(10);
  const all = Array.from({length: 40}, (_, i) => ['00:30', `caption-${i}-ของคลิปที่ ${i}`, i === 33 ? 'Nov 10, 8:15 PM' : `Nov ${20 - (i % 9)}, 10:15 AM (GMT+7) Bangkok`, 'Everyone'].join(nl2) + nl2);
  let top = 0;                                    // first visible row index; the page keeps only 8 rows
  const send = async (_method, params) => {
    const expression = String(params.expression);
    if (/scrollTop/.test(expression)) {
      if (top >= all.length - 8) return {result: {value: 0}};
      top = Math.min(all.length - 8, top + 6);
      return {result: {value: 500}};
    }
    return {result: {value: 'Posts 227' + nl2 + all.slice(top, top + 8).join('')}};
  };
  const noMatch = await ctx.collectContentRows(send, {});
  assert.equal(noMatch.rows.length, 40, 'every row was collected exactly once');
  top = 0;
  const hit = await ctx.collectContentRows(send, {match: (row) => row.includes('caption-33-')});
  assert.ok(hit.found && hit.found.includes('Nov 10, 8:15 PM'));
  assert.ok(hit.rows.length < 40, 'it stops as soon as the row is found');
  top = 0;
  const bounded = await ctx.collectContentRows(send, {maxSteps: 2});
  assert.ok(bounded.rows.length <= 20, 'the scan is bounded');
});

test('draft card layout: caption, then date | time in two equal columns, time styled like date, full-width action', () => {
  const html = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  const side = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  assert.match(html, /\.draft-slot-controls \{ display: grid; grid-template-columns: 1fr 1fr;/);
  assert.match(html, /\.draft-slot-label \{ grid-column: 1 \/ -1;/);
  assert.match(html, /input\[type="date"\], input\[type="time"\], select \{/, 'the time box shares the field style of the date box');
  assert.match(html, /\.draft-slot-controls input \{[^}]*height: 40px/, 'touch-friendly field height');
  assert.match(side, /label\.className = 'draft-slot-label'/);
  assert.match(side, /btn\.className = 'btn-primary draft-now'/);
});

test('overdue clips: filter chip, one bulk button with a preview dialog, and the slot editor persists to the queue', () => {
  const side = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  const html = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  assert.match(html, /data-filter="overdue"/);
  assert.match(html, /id="filterCountOverdue"/);
  assert.match(html, /id="rescheduleOverdueBtn"/);
  assert.match(side, /currentStatusFilter === 'overdue'/);
  // bulk: preview first (nothing written), explicit confirmation, then commit; drafts are not touched
  const bulk = side.slice(side.indexOf("rescheduleOverdueBtn?.addEventListener('click'"));
  assert.ok(bulk.indexOf('reschedule-overdue/preview') > 0 && bulk.indexOf('reschedule-overdue/preview') < bulk.indexOf('askConfirm('));
  assert.ok(bulk.indexOf('askConfirm(') < bulk.indexOf('/api/schedule-queue/reschedule-overdue`'));
  assert.match(bulk, /แบบร่างไม่ถูกแตะ/);
  // the draft card's time fields save to the scheduler's row (one source of truth) instead of only changing the card
  assert.match(side, /method: 'PATCH'[\s\S]{0,200}scheduled_at: `\$\{dateIn\.value\}T\$\{timeIn\.value\}:00\+07:00`/);
  assert.match(side, /timeIn\.step = 300/);
});
