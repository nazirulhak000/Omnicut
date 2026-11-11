const {test}=require('node:test');
const assert=require('node:assert/strict');
const form=require('./prepare_form.js');
const guard=require('./post_guard.js');
const item={export_id:'e1',tiktok_caption:'Feature {value}',tiktok_hashtags:'#test'};
const values={caption:'Feature works well',hashtags:'#test',intent:'schedule',date:'2030-01-01',time:'12:00'};
const now=Date.parse('2026-11-12T00:00:00Z');
test('editing a blocked clip preserves the export and creates an explicit schedule snapshot',()=>{
  const result=form.build(item,values,guard,{export_id:'e1'},now);
  assert.equal(result.item.export_id,'e1');assert.equal(result.item.prepare_intent,'schedule');
  assert.equal(result.item.tiktok_caption,values.caption);assert.equal(item.tiktok_caption,'Feature {value}');
});
test('unresolved caption and missing or passed schedule never prepare',()=>{
  assert.equal(form.build(item,{...values,caption:'Feature {value}'},guard,{},now).code,'placeholder_in_caption');
  assert.equal(form.build(item,{...values,date:''},guard,{},now).code,'no_schedule');
  assert.equal(form.build(item,{...values,date:'2020-01-01'},guard,{},now).code,'slot_passed_or_too_close');
});
test('draft is explicit and strips stale schedule; posted or missing export remains blocked',()=>{
  const draft=form.build(item,{...values,intent:'draft'},guard,{},now).item;
  assert.equal(draft.schedule_date,'');assert.equal(draft.schedule_time,'');
  assert.equal(form.build(item,values,guard,{is_posted:true},now).code,'export_already_posted');
  assert.equal(form.build(item,values,guard,undefined,now).code,'export_missing');
  assert.ok(form.build(item,{...values,intent:'post_now'},guard,{},now).error);
});
test('the reported placeholder plus missing slot identifies all fields in one result',()=>{
  const result=form.validate(item,{...values,caption:'Review {product_name}',date:'',time:''},guard,{},now);
  assert.deepEqual(result.issues.map(i=>i.field),['Caption','Date','Time']);
  assert.match(result.issues[0].message,/\{product_name\}/);
  assert.deepEqual(form.validate(item,{...values,hashtags:'#{model}'},guard,{},now).issues.map(i=>i.field),['Tags']);
  assert.equal(form.validate(item,{...values,time:'12:03'},guard,{},now).issues[0].field,'Time');
  assert.ok(form.validate(item,values,guard,{},now).item);
});
test('only a known product name replaces its placeholder; no invented values',()=>{
  assert.equal(form.fillProductName('Review {product_name} {price}','MONSTER AC530'),'Review MONSTER AC530 {price}');
  assert.equal(form.fillProductName('Review {product_name}',''),'Review {product_name}');
  assert.equal(form.fillProductName('Review {product_name}','$& gadget'),'Review $& gadget');
});
function memory(){const data={};return {data,get:async key=>({[key]:data[key]}),set:async values=>Object.assign(data,structuredClone(values))};}
test('partial edits survive a new store instance and remain isolated by channel, export and queue',async()=>{
  const storage=memory();const scope={channelId:'main',clipId:'e1',queueId:'q1'};
  await form.createStore(storage,scope).save({...values,caption:'Review {product_name}',date:'',time:''});
  const restored=await form.createStore(storage,scope).load();
  assert.equal(restored.caption,'Review {product_name}');assert.equal(restored.date,'');
  for(const changed of [{channelId:'other'},{clipId:'e2'},{queueId:'q2'}])assert.equal(await form.createStore(storage,{...scope,...changed}).load(),null);
});
test('queued writes retain the newest edit and a failed save can be retried',async()=>{
  const storage=memory();const store=form.createStore(storage,{channelId:'main',clipId:'e1'});
  await Promise.all([store.save({...values,caption:'First edit'}),store.save({...values,caption:'Latest edit'})]);
  assert.equal((await store.load()).caption,'Latest edit');
  let fail=true;const realSet=storage.set;storage.set=async value=>{if(fail)throw Error('storage full');return realSet(value);};
  await assert.rejects(()=>store.save(values),/storage full/);fail=false;
  await store.save(values);assert.equal((await store.load()).caption,values.caption);
});
