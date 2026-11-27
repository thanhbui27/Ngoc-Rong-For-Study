const studio = {tab:'clone', poses:[], partCache:new Map(), selectedCostume:null, selectedPart:null, epoch:0};
window.addEventListener('clone-project-change',()=>{
  studio.epoch++;studio.partCache.clear();studio.selectedCostume=null;studio.selectedPart=null;
  for(const id of ['partList','costumeList','mapList','partFrames'])$(id).replaceChildren();
  for(const id of ['partTotal','costumeTotal','mapTotal','partMeta','mapMeta'])$(id).textContent='';
  $('partTitle').textContent='Chọn một part';$('costumeName').textContent='Chọn item';$('mapTitle').textContent='Chọn map';
  $('costumePreviewNote').textContent='Chọn item để xem ảnh hiện có.';$('costumeMessage').textContent='';
  $('costumeIcon').removeAttribute('src');
  for(const id of ['composeHead','composeBody','composeLeg','costumeHead','costumeBody','costumeLeg'])$(id).value='';
  canvasEmpty($('composeCanvas'));canvasEmpty($('costumeCanvas'));
  const map=$('mapCanvas');map.getContext('2d').clearRect(0,0,map.width,map.height);
});

async function studioApi(path){
  const response=await fetch(path,{cache:'no-store'});
  const value=await response.json();
  if(!response.ok)throw new Error(value.error||'Không đọc được dữ liệu');
  return value;
}
function studioUrl(path,params){return path+'?'+new URLSearchParams(params).toString();}
function studioMessage(id,message){$(id).textContent=message;}
function studioTab(name){
  studio.tab=name;
  document.querySelectorAll('.tabs button').forEach(button=>button.classList.toggle('active',button.dataset.tab===name));
  document.querySelectorAll('.tab-panel').forEach(panel=>panel.hidden=panel.id!=='tab-'+name);
  if(name==='parts')studioCatalog('part');
  if(name==='costumes')studioCatalog('costume');
  if(name==='maps')studioCatalog('map');
}
document.querySelectorAll('.tabs button').forEach(button=>button.onclick=()=>studioTab(button.dataset.tab));

const listConfig={part:['partSearch','partList','partTotal','partFind'],costume:['costumeSearch','costumeList','costumeTotal','costumeFind'],map:['mapSearch','mapList','mapTotal','mapFind']};
async function studioCatalog(kind,offset=0){
  const epoch=studio.epoch;
  const [searchId,listId,totalId]=listConfig[kind];
  const list=$(listId);
  if(offset===0)list.replaceChildren();
  else list.querySelector('.load-more')?.remove();
  try{
    const apiKind=kind==='part'&&$('partMode').value==='sets'?'sets':kind==='costume'?'visual':kind;
    const result=await studioApi(studioUrl('/api/catalog',{kind:apiKind,query:$(searchId).value.trim(),offset,category:$('visualCategory').value}));
    if(epoch!==studio.epoch)return;
    $(totalId).textContent=result.matches+' / '+result.total;
    for(const row of result.entries){
      const button=document.createElement('button');
      const label=document.createElement('span');
      label.textContent=apiKind==='sets'?'#'+row.head+' / #'+row.body+' / #'+row.leg:'#'+row.id+' · '+(kind==='part'?row.type_name:row.name);
      const meta=document.createElement('small');
      meta.textContent=apiKind==='sets'?'Bộ part liền kề · chưa gắn item':kind==='part'?row.frames+' frame · '+row.images+' ảnh':kind==='costume'?row.category+' · part template '+row.part_id+(row.mapped?' · map cục bộ':row.reference?' · map từ SQL đã đối chiếu':' · chưa map'):row.has_tiles?'Có tile':'Thiếu tile';
      button.append(label,meta);
      button.onclick=()=>{list.querySelectorAll('button').forEach(entry=>entry.classList.remove('selected'));button.classList.add('selected');
        if(apiKind==='sets'){$('composeHead').value=row.head;$('composeBody').value=row.body;$('composeLeg').value=row.leg;studioPart(row.head);drawCurrentParts();}
        else if(kind==='part')studioPart(row.id);
        if(kind==='costume')studioCostume(row.id);
        if(kind==='map')studioMap(row.id);};
      list.append(button);
    }
    if(result.has_more){const more=document.createElement('button');more.className='load-more';more.textContent='Tải thêm ('+(offset+result.entries.length)+' / '+result.matches+')';more.onclick=()=>studioCatalog(kind,offset+result.entries.length);list.append(more);}
    if(!result.entries.length&&offset===0)list.textContent='Không có kết quả.';
  }catch(error){if(epoch===studio.epoch){list.textContent=error.message;$(totalId).textContent='';}}
}
for(const [kind,[searchId,,,findId]] of Object.entries(listConfig)){
  $(findId).onclick=()=>studioCatalog(kind);
  $(searchId).onkeydown=event=>{if(event.key==='Enter')studioCatalog(kind);};
}
$('partMode').onchange=()=>studioCatalog('part');
$('visualCategory').onchange=()=>studioCatalog('costume');

function bestZoom(frame,preferred){
  const choices=[preferred,4,3,2,1].filter((value,index,array)=>array.indexOf(value)===index);
  return choices.find(value=>frame.available[String(value)])||0;
}
function imageUrl(id,zoom){return studioUrl('/api/asset',{id,zoom});}
async function getPart(id){
  if(!studio.partCache.has(id)){
    const epoch=studio.epoch,value=await studioApi(studioUrl('/api/part',{id}));
    if(epoch!==studio.epoch)throw new Error('Đã đổi thư mục dự án');
    studio.partCache.set(id,value);
  }
  return studio.partCache.get(id);
}
async function studioPart(id){
  const epoch=studio.epoch;
  try{
    const value=await getPart(id);if(epoch!==studio.epoch)return;studio.selectedPart=value;
    $('partTitle').textContent='Part #'+id+' · '+value.type_name;
    $('partMeta').textContent=value.frames.length+' frame';
    if(value.type===0)$('composeHead').value=id;
    if(value.type===1)$('composeBody').value=id;
    if(value.type===2)$('composeLeg').value=id;
    renderPartFrames();
    drawCurrentParts();
  }catch(error){if(epoch===studio.epoch)studioMessage('partNote',error.message);}
}
function renderPartFrames(){
  const value=studio.selectedPart;if(!value)return;
  const zoom=Number($('partZoom').value),container=$('partFrames');container.replaceChildren();
  let missing=0;
  for(const frame of value.frames){
    const tile=document.createElement('div');tile.className='frame';
    const title=document.createElement('strong');title.textContent='Frame '+String(frame.index).padStart(2,'0');tile.append(title);
    const actual=bestZoom(frame,zoom);
    if(actual){const img=document.createElement('img');img.src=imageUrl(frame.image_id,actual);img.alt='Image '+frame.image_id;tile.append(img);}
    else{tile.classList.add('missing');const empty=document.createElement('em');empty.textContent='Thiếu PNG';tile.append(empty);missing++;}
    const caption=document.createElement('div');caption.textContent='Image #'+frame.image_id+' · dx '+frame.dx+' · dy '+frame.dy+(actual&&actual!==zoom?' · dùng x'+actual:'');tile.append(caption);
    container.append(tile);
  }
  studioMessage('partNote','Part #'+value.id+' có '+value.frames.length+' frame; '+missing+' frame thiếu PNG ở mọi mức zoom. Mỗi ô ghi Image ID và dx/dy gốc.');
}
$('partZoom').onchange=()=>{renderPartFrames();drawCurrentParts();};

function canvasEmpty(canvas){const ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);ctx.strokeStyle='#65809e66';ctx.beginPath();ctx.moveTo(45,190);ctx.lineTo(255,190);ctx.stroke();return ctx;}
function loadImage(url){return new Promise(resolve=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>resolve(null);img.src=url;});}
async function drawComposite(canvas,ids,poseIndex,preferred){
  const epoch=studio.epoch;
  const ctx=canvasEmpty(canvas),pose=studio.poses[poseIndex]||studio.poses[0];
  if(!pose)return 'Chưa tải được bảng dáng CharInfo.';
  const parts={};const issues=[];
  for(const [slot,id,kind] of [['head',ids.head,0],['body',ids.body,1],['leg',ids.leg,2]]){
    if(!Number.isInteger(id)||id<0){issues.push('Thiếu '+slot);continue;}
    try{const value=await getPart(id);if(epoch!==studio.epoch)return 'Đã đổi thư mục dự án';if(value.type!==kind){issues.push('Part '+slot+' #'+id+' sai loại');continue;}parts[slot]=value;}
    catch(error){issues.push(error.message);}
  }
  for(const [slot,poseSlot] of [['head',0],['leg',1],['body',2]]){
    const value=parts[slot];if(!value)continue;
    const [frameIndex,offsetX,offsetY]=pose[poseSlot];const frame=value.frames[frameIndex];
    if(!frame){issues.push(slot+' thiếu frame '+frameIndex);continue;}
    const zoom=bestZoom(frame,preferred);
    if(!zoom){issues.push('Thiếu PNG #'+frame.image_id+' ('+slot+')');continue;}
    const img=await loadImage(imageUrl(frame.image_id,zoom));
    if(epoch!==studio.epoch)return 'Đã đổi thư mục dự án';
    if(!img){issues.push('Không đọc được PNG #'+frame.image_id);continue;}
    const width=img.width/zoom,height=img.height/zoom;
    // Char.paintCharBody with cdir=1 uses transform=0 and anchor=0 (top-left).
    const x=150+offsetX+frame.dx,y=190-offsetY+frame.dy;
    ctx.imageSmoothingEnabled=false;ctx.drawImage(img,x,y,width,height);
    if(zoom!==preferred)issues.push('#'+frame.image_id+' dùng x'+zoom);
  }
  return issues.length?issues.join(' · '):'Đã ráp đủ đầu, thân, chân cho dáng '+poseIndex+'.';
}
function composeIds(prefix){return {head:Number($(prefix+'Head').value||-1),body:Number($(prefix+'Body').value||-1),leg:Number($(prefix+'Leg').value||-1)};}
async function drawCurrentParts(){
  const note=await drawComposite($('composeCanvas'),composeIds('compose'),Number($('composePose').value),Number($('partZoom').value));
  studioMessage('composeNote',note+' Preview dựa trên CharInfo; cần PNG đã tải để hiện ảnh.');
}
$('composeDraw').onclick=drawCurrentParts;
$('composePose').onchange=drawCurrentParts;

async function studioCostume(id){
  const epoch=studio.epoch;
  try{
    const value=await studioApi(studioUrl('/api/costume',{id}));if(epoch!==studio.epoch)return;studio.selectedCostume=value;
    $('costumeName').textContent='#'+id+' · '+value.name;
    $('costumeMeta').textContent=value.category+' · type '+value.type+' · icon #'+value.icon_id+' · part template '+value.part_id;
    $('costumeIcon').src=imageUrl(value.icon_id,Number($('costumeZoom').value));
    $('costumeIcon').onerror=()=>{$('costumeIcon').onerror=null;$('costumeIcon').src=imageUrl(value.icon_id,1);};
    $('costumeSource').textContent=value.mapping?'Đang dùng mapping bro đã lưu trong bản clone.':value.reference_mapping?value.reference_kind==='mini_pet'?'Bộ mini pet từ mini_pet trong SQL seed cục bộ; tên, giới tính và từng frame part khớp bản clone. Không phải SQL tải từ server.':'Mapping từ cai_trang trong SQL seed cục bộ; ID/tên/icon/part và từng frame khớp bản clone. Không phải SQL tải từ server.':value.type===72?'Pet đi theo type 72 dùng icon hoặc sprite pet_follow riêng; packet item không chứa sprite follow.':value.template_part?'Item template chỉ trỏ part #'+value.part_id+' ('+value.template_part.type_name+'). Chưa có mapping đầy đủ từ server.':'Item template không có part hợp lệ. Chưa có mapping đầy đủ từ server.';
    const effective=value.mapping||value.reference_mapping;
    for(const key of ['head','body','leg']){
      const fromTemplate=key==='head'&&value.type===5&&value.template_part?.type===0?value.part_id:'';
      $('costume'+key[0].toUpperCase()+key.slice(1)).value=effective?.[key]??fromTemplate;
    }
    const canMap=[5,18,21].includes(value.type);
    for(const key of ['Head','Body','Leg'])$('costume'+key).disabled=!canMap;
    $('costumeSuggest').disabled=!canMap||!value.suggested;
    $('costumeSave').disabled=!canMap;
    $('costumeToPart').disabled=!canMap;
    studioMessage('costumeMessage',!canMap?'Item này chỉ preview icon; không dùng mapping part đầu/thân/chân.':value.suggested?'Gợi ý liền kề #'+value.suggested.head+' / #'+value.suggested.body+' / #'+value.suggested.leg+' (chưa xác minh là cùng item).':'Không có bộ part liền kề đúng loại để gợi ý.');
    drawCurrentCostume();
  }catch(error){if(epoch===studio.epoch)studioMessage('costumeMessage',error.message);}
}
async function drawCurrentCostume(){
  const selected=studio.selectedCostume;if(!selected)return;
  const epoch=studio.epoch,ids=composeIds('costume'),zoom=Number($('costumeZoom').value);
  if(![5,18,21].includes(selected.type)||Object.values(ids).every(id=>id<0)){
    const canvas=$('costumeCanvas'),ctx=canvasEmpty(canvas);
    const order=[zoom,4,3,2,1].filter((value,index,array)=>array.indexOf(value)===index);
    let found=false;
    for(const actual of order){
      const img=await loadImage(imageUrl(selected.icon_id,actual));
      if(epoch!==studio.epoch||studio.selectedCostume?.id!==selected.id)return;
      if(!img)continue;
      const scale=Math.min(150/(img.width/actual),150/(img.height/actual),4);
      const width=img.width/actual*scale,height=img.height/actual*scale;
      ctx.imageSmoothingEnabled=false;ctx.drawImage(img,(canvas.width-width)/2,(canvas.height-height)/2,width,height);
      studioMessage('costumePreviewNote','Chỉ có icon item #'+selected.icon_id+' (ảnh x'+actual+'). '+(selected.type===72?'Pet đi theo cần sprite pet_follow riêng để xem chuyển động.':'Chưa có mapping part đã xác minh cho item này.'));
      found=true;break;
    }
    if(!found)studioMessage('costumePreviewNote','Thiếu PNG icon #'+selected.icon_id+' ở mọi mức zoom.');
    return;
  }
  const displayIds={...ids},base=[];
  if(selected.type===5)for(const [slot,partId] of [['head',0],['body',1],['leg',2]])if(displayIds[slot]<0){displayIds[slot]=partId;base.push(slot+' #'+partId);}
  const note=await drawComposite($('costumeCanvas'),displayIds,Number($('costumePose').value),zoom);
  if(epoch===studio.epoch&&studio.selectedCostume?.id===selected.id){
    const complete=Object.values(ids).every(id=>id>=0);
    studioMessage('costumePreviewNote',(complete?'Preview bộ part: ':base.length?'Preview với part nền tham khảo ('+base.join(', ')+'): ':'Preview part hiện có: ')+note+(complete?'':base.length?' Các part nền không được lưu vào mapping cải trang.':' Bộ mini pet này chưa đủ mapping.'));
  }
}
$('costumeSuggest').onclick=()=>{const value=studio.selectedCostume?.suggested;if(!value)return;for(const key of ['head','body','leg'])$('costume'+key[0].toUpperCase()+key.slice(1)).value=value[key];drawCurrentCostume();};
$('costumeSave').onclick=async()=>{if(!studio.selectedCostume)return;try{const result=await post('/api/mapping',{item_id:studio.selectedCostume.id,mapping:composeIds('costume')});studio.selectedCostume.mapping=result.mapping;studioMessage('costumeMessage','Đã lưu '+result.path+' · chỉ là mapping cục bộ.');studioCatalog('costume');}catch(error){studioMessage('costumeMessage',error.message);}};
$('costumeToPart').onclick=()=>{for(const key of ['head','body','leg'])$('compose'+key[0].toUpperCase()+key.slice(1)).value=$('costume'+key[0].toUpperCase()+key.slice(1)).value;studioTab('parts');drawCurrentParts();};
$('costumePose').onchange=drawCurrentCostume;$('costumeZoom').onchange=()=>{if(studio.selectedCostume){$('costumeIcon').src=imageUrl(studio.selectedCostume.icon_id,Number($('costumeZoom').value));drawCurrentCostume();}};
for(const key of ['Head','Body','Leg'])$('costume'+key).onchange=drawCurrentCostume;

async function studioMap(id){
  const epoch=studio.epoch;
  try{
    const value=await studioApi(studioUrl('/api/map',{id}));
    if(epoch!==studio.epoch)return;
    $('mapTitle').textContent='#'+id+' · '+value.name;
    $('mapMeta').textContent=value.has_tiles?value.width+' × '+value.height+' tile':'Thiếu packet tile';
    const canvas=$('mapCanvas'),ctx=canvas.getContext('2d');
    if(value.tiles){
      canvas.width=value.width*5;canvas.height=value.height*5;
      for(let y=0;y<value.height;y++)for(let x=0;x<value.width;x++){
        const tile=value.tiles[y*value.width+x];ctx.fillStyle='hsl('+((tile*57)%360)+' 44% '+(tile===0?18:45)+'%)';ctx.fillRect(x*5,y*5,5,5);
      }
      studioMessage('mapNote',value.unique_tiles+' tile ID khác nhau · '+value.trailing_bytes+' byte phụ. Màu chỉ phân biệt ID, không phải texture trong game.');
    }else{canvas.width=640;canvas.height=320;ctx.clearRect(0,0,640,320);studioMessage('mapNote',value.error||'Server chưa trả tile của map này.');}
  }catch(error){if(epoch===studio.epoch)studioMessage('mapNote',error.message);}
}

studioApi('/api/poses').then(value=>{
  studio.poses=value.poses;
  for(const select of [$('composePose'),$('costumePose')])for(let index=0;index<studio.poses.length;index++){
    const option=document.createElement('option');option.value=String(index);option.textContent='Dáng '+String(index).padStart(2,'0');select.append(option);
  }
}).catch(error=>studioMessage('composeNote',error.message));
