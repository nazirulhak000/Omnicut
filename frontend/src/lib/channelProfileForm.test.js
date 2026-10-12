import test from 'node:test';
import assert from 'node:assert/strict';
import { captureProfile, profileForm, profileDirty, buildProfilePatch, buildDraftPayload, profileFailure } from './channelProfileForm.js';
import { createChannelRequestGuard } from './channelState.js';

const channel = {id:'main',revision:3,status:'active',display_name:'Main',handle:'@mainuser',watermark_text:'Main',posting_enabled:false};

test('profile payload belongs to captured owner/revision and excludes binding and identity edits', () => {
  const snapshot = captureProfile(channel,{channel_id:'main',generation:4});
  const form = {...profileForm(channel),handle:'https://www.tiktok.com/@NewUser',id:'second',account_binding:{status:'verified'}};
  assert.deepEqual(buildProfilePatch(snapshot,form,channel),{handle:'@newuser',expected_revision:3});
  assert.equal(snapshot.baseline.handle,'@mainuser');
  assert.equal(profileDirty(snapshot,form),true);
  assert.equal(buildProfilePatch(snapshot,profileForm(channel),channel),null);
});

test('stale channel, revision, A to B to A generation and archived form are rejected', () => {
  const snapshot = captureProfile(channel,{});
  for (const current of [{...channel,id:'second'},{...channel,revision:4}]) {
    assert.throws(()=>buildProfilePatch(snapshot,{...profileForm(channel),display_name:'New'},current),{code:'channel_profile_stale'});
  }
  assert.throws(()=>buildProfilePatch(snapshot,profileForm(channel),channel,false),{code:'channel_profile_stale'});
  const archived={...channel,status:'archived'};
  assert.throws(()=>buildProfilePatch(captureProfile(archived,{}),profileForm(archived),archived),{code:'channel_archived'});
});

test('capture preserves the runtime-issued opaque token identity and rejects an A B A return', () => {
  const guard=createChannelRequestGuard('main');
  const snapshot=captureProfile(channel,guard.capture());
  assert.equal(guard.isCurrent(snapshot.token),true);
  assert.deepEqual(buildProfilePatch(snapshot,{...profileForm(channel),display_name:'Updated'},channel,guard.isCurrent(snapshot.token)),{display_name:'Updated',expected_revision:3});
  guard.activate('second'); guard.activate('main');
  assert.throws(()=>buildProfilePatch(snapshot,profileForm(channel),channel,guard.isCurrent(snapshot.token)),{code:'channel_profile_stale'});
});

test('draft creation uses registry revision, forced posting off and no verification assertion', () => {
  const draft={...profileForm(),id:'second',display_name:'Second',handle:'@SecondUser',posting_enabled:true,account_binding:{status:'verified'}};
  const payload=buildDraftPayload(draft,9);
  assert.equal(payload.expected_registry_revision,9);
  assert.equal(payload.posting_enabled,false);
  assert.equal(payload.handle,'@seconduser');
  assert.equal('account_binding' in payload,false);
  assert.throws(()=>buildDraftPayload(draft,null),{code:'registry_revision_required'});
  assert.throws(()=>buildDraftPayload({...draft,id:'../main'},9),{code:'channel_scope_invalid'});
  assert.throws(()=>buildDraftPayload({...draft,display_name:' '},9),{code:'display_name_required'});
});

test('a server refresh establishes a clean baseline without overwriting local edits', () => {
  const old=captureProfile(channel,{}), edited={...profileForm(channel),display_name:'Edited'};
  assert.equal(profileDirty(old,edited),true);
  const updated={...channel,revision:4,display_name:'Edited'};
  assert.equal(profileDirty(captureProfile(updated,{}),profileForm(updated)),false);
});

test('structured backend validation becomes readable field text instead of a React object child', () => {
  const failure=profileFailure({response:{data:{detail:[{loc:['body','display_name'],msg:'Too long'}]}}});
  assert.equal(failure.message,'display_name: Too long');
  assert.equal(failure.field,'display_name');
  assert.equal(typeof profileFailure({response:{data:{detail:{unexpected:true}}}}).message,'string');
});
