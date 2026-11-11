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
