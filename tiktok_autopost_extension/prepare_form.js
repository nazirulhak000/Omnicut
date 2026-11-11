(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.OmniPrepareForm=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  function build(item,values,guard,record,now=Date.now(),exportsKnown=true){
    if(!['schedule','draft'].includes(values.intent))return {error:'กรุณาเลือกตั้งเวลาหรือบันทึกแบบร่าง'};
    const next={...item,tiktok_caption:values.caption.trim(),tiktok_hashtags:values.hashtags.trim(),
      prepare_intent:values.intent,schedule_date:values.intent==='schedule'?values.date:'',schedule_time:values.intent==='schedule'?values.time:''};
    const code=guard.clipSkipReason(next,record,now,{exportsKnown,ignoreSlot:values.intent==='draft',requireSchedule:values.intent==='schedule'});
    return code?{code}:{item:next};
  }
  function open(item,{guard,record,exportsKnown=true,reasons={}}){
    return new Promise(resolve=>{
      const dialog=document.createElement('dialog');
      dialog.className='app-dialog clip-setup-dialog';
      dialog.setAttribute('aria-labelledby','clipSetupTitle');
      dialog.innerHTML=`<form id="clipSetupForm"><h2 id="clipSetupTitle">เตรียมข้อมูลคลิป</h2>
        <p>แก้ข้อมูลให้ครบก่อนส่งเข้า TikTok ขั้นตอนนี้ยังไม่อัปโหลดหรือเผยแพร่</p>
        <label for="clipSetupCaption">คำอธิบายคลิป</label><textarea id="clipSetupCaption" rows="4" required></textarea>
        <label for="clipSetupTags">แฮชแท็ก</label><input id="clipSetupTags" type="text">
        <label for="clipSetupIntent">รูปแบบการเตรียม</label><select id="clipSetupIntent"><option value="schedule">ตั้งเวลาโพสต์</option><option value="draft">บันทึกเป็นแบบร่างบน TikTok</option></select>
        <div id="clipSetupSlot"><label for="clipSetupDate">วันที่โพสต์</label><input id="clipSetupDate" type="date"><label for="clipSetupTime">เวลาโพสต์</label><input id="clipSetupTime" type="time" step="300"><p>เลือกเวลาอย่างน้อย 15 นาทีข้างหน้า</p></div>
        <p id="clipSetupError" role="alert"></p><div class="row"><button id="clipSetupCancel" type="button">ยกเลิก</button><button class="btn-primary" type="submit">เตรียมคลิป</button></div></form>`;
      document.body.appendChild(dialog);
      const field=id=>dialog.querySelector('#clipSetup'+id);
      field('Caption').value=item.tiktok_caption||item.caption||'';
      field('Tags').value=item.tiktok_hashtags||item.hashtags||'';
      field('Date').value=item.schedule_date||'';field('Time').value=item.schedule_time||'';
      field('Intent').value=item.prepare_intent||'schedule';
      function sync(){const schedule=field('Intent').value==='schedule';field('Slot').hidden=!schedule;field('Date').required=schedule;field('Time').required=schedule;}
      field('Intent').addEventListener('change',sync);sync();
      function finish(value){dialog.close();dialog.remove();resolve(value);}
      field('Cancel').onclick=()=>finish(null);
      dialog.addEventListener('cancel',e=>{e.preventDefault();finish(null);});
      field('Form').addEventListener('submit',e=>{
        e.preventDefault();
        const result=build(item,{caption:field('Caption').value,hashtags:field('Tags').value,intent:field('Intent').value,date:field('Date').value,time:field('Time').value},guard,record,Date.now(),exportsKnown);
        if(!result.item){field('Error').textContent=result.error||reasons[result.code]||result.code;return;}
        finish(result.item);
      });
      dialog.showModal();field('Caption').focus();
    });
  }
  return {build,open};
});
