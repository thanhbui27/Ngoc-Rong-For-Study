const animationStudio={selected:null,request:0,playing:false,start:0,last:-1,raf:0,cache:new Map(),busy:false};
const fileImage=path=>studioUrl('/api/asset-file',{path});
function stopExtended(){animationStudio.playing=false;cancelAnimationFrame(animationStudio.raf);$('animPlay').textContent='Phát';animationStudio.request++;}
window.addEventListener('clone-project-change',()=>{stopExtended();animationStudio.selected=null;animationStudio.cache.clear();$('animList').replaceChildren();$('animDetail').textContent='';$('visualLayers').replaceChildren();canvasEmpty($('animCanvas'));});
window.addEventListener('clone-data-updated',()=>{animationStudio.cache.clear();studio.imageCache.clear();studio.partCache.clear();});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stopExtended();});
const originalStudioTab=studioTab;
studioTab=function(name){if(name!=='animation')stopExtended();originalStudioTab(name);if(name==='animation')extendedCatalog();};

async function extendedCatalog(offset=0){
  const epoch=studio.epoch,kind=$('animKind').value,query=$('animSearch').value;
  if(!offset)$('animList').replaceChildren();else $('animList').querySelector('.load-more')?.remove();
  try{
    const result=await studioApi(studioUrl('/api/extended',{kind,query,offset}));
    if(epoch!==studio.epoch||kind!==$('animKind').value||query!==$('animSearch').value)return;
    $('animTotal').textContent=result.matches+' / '+result.total;
    for(const row of result.entries){const button=document.createElement('button');button.textContent='#'+row.id+' · '+row.name;button.onclick=()=>selectExtended(kind,row.id);$('animList').append(button);}
    if(result.has_more){const button=document.createElement('button');button.className='load-more';button.textContent='Tải thêm';button.onclick=()=>extendedCatalog(offset+result.entries.length);$('animList').append(button);}
    if(!result.entries.length&&!offset)$('animList').textContent='Chưa có dữ liệu. Dùng “Chỉ tải bổ sung animation” ở tab Clone.';
  }catch(error){if(epoch===studio.epoch)$('animNote').textContent=error.message;}
}
async function extendedDetail(kind,id,zoom){
  const key=kind+':'+id+':'+zoom;
  if(!animationStudio.cache.has(key)){
    const epoch=studio.epoch,value=await studioApi(studioUrl('/api/extended',{kind,id,zoom}));
    if(epoch!==studio.epoch)throw new Error('Đã đổi bản clone');
    animationStudio.cache.set(key,value);
  }
  return animationStudio.cache.get(key);
}
async function selectExtended(kind,id){
  stopExtended();const request=animationStudio.request,epoch=studio.epoch;
  try{
    const value=await extendedDetail(kind,id,Number($('animZoom').value));
    if(epoch!==studio.epoch||request!==animationStudio.request)return;
    animationStudio.selected=value;$('animFrame').value=0;$('animTitle').textContent=(value.name||kind)+' #'+id;
    const action=$('animAction');action.querySelectorAll('[data-native]').forEach(node=>node.remove());
    for(const key of Object.keys(value.actions||{})){const option=document.createElement('option');option.value=key;option.dataset.native='1';option.textContent='Dãy '+key;action.append(option);}
    $('animDetail').textContent=JSON.stringify({...value,effects:undefined,darts:undefined,arrows:undefined},null,2);await drawExtended();
  }catch(error){$('animNote').textContent=error.message;}
}
async function smallImage(ctx,id,x,y,scale,zoom,current,center=true,frame=null){
  for(const actual of [...new Set([zoom,4,3,2,1])]){
    const image=await loadImage(imageUrl(id,actual));if(!current())return '';
    if(!image)continue;
    if(image.width===1&&image.height===1)return 'PNG #'+id+' là ảnh 1×1';
    const w=frame?frame.width:image.width/actual,h=frame?frame.height:image.height/actual;
    const sourceY=frame?frame.index*h*actual:0;
    if(sourceY+h*actual>image.height||w*actual>image.width)return 'Sprite sheet #'+id+' vượt kích thước PNG';
    ctx.drawImage(image,0,sourceY,w*actual,h*actual,x-(center?w*scale/2:0),y-(center?h*scale/2:0),w*scale,h*scale);return '';
  }
  return 'Thiếu PNG #'+id;
}
async function drawAsset(ctx,value,tick,options){
  const {zoom,scale,current,x=150,y=150,action='default'}=options;
  if(!current())return '';
  const kind=value.render_kind||value.kind;
  if(value.missing)return 'Chưa tải animation '+kind+' #'+value.id;
  if(kind==='npc')return drawComposite(ctx.canvas,value,unityPoseForAction(action==='run'?'run':'stand',tick),zoom,current,scale);
  if(kind==='effect'){
    const frame=value.frames[tick%Math.max(1,value.frames.length)];
    return frame?smallImage(ctx,frame.image_id,x+frame.dx*scale,y+frame.dy*scale,scale,zoom,current):'Effect không có frame';
  }
  if(kind==='flag'){
    if(value.frame_paths?.length){
      const image=await loadImage(fileImage(value.frame_paths[tick%value.frame_paths.length]));if(!current())return '';
      if(!image)return 'Thiếu ảnh cờ tham chiếu';
      ctx.drawImage(image,x-image.width/value.zoom*scale/2,y-image.height/value.zoom*scale/2,image.width/value.zoom*scale,image.height/value.zoom*scale);return '';
    }
    const ids=value.image_ids||[];return ids.length?smallImage(ctx,ids[tick%ids.length],x,y,scale,zoom,current):'Cờ không có frame';
  }
  if(kind==='sheet'){
    const sequence=value.sequence||Array.from({length:value.count},(_,i)=>i),index=sequence[tick%sequence.length];
    if(value.image_path){
      const image=await loadImage(fileImage(value.image_path));if(!current())return '';
      if(!image)return 'Thiếu ảnh sprite sheet';const z=value.zoom,w=value.width,h=value.height;
      if((index+1)*h*z>image.height||w*z>image.width)return 'Kích thước sheet không khớp PNG tham chiếu';
      ctx.drawImage(image,0,index*h*z,w*z,h*z,x-w*scale/2,y-h*scale/2,w*scale,h*scale);return '';
    }
    return smallImage(ctx,Number(value.id),x,y,scale,zoom,current,true,{width:value.width,height:value.height,index});
  }
  if(kind==='dynamic'||kind==='mob'){
    const sequence=value.actions?.[action]||value.actions?.['0']||value.sequence?.filter(i=>i>=0)||[];
    const index=sequence.length?sequence[tick%sequence.length]:tick%Math.max(1,value.frames.length);
    const pieces=value.frames[index];if(!pieces)return 'Không có frame '+index;
    const image=await loadImage(fileImage(value.image_path));if(!current())return '';
    if(!image)return 'Thiếu atlas '+value.image_path;
    for(const piece of pieces){const sprite=value.sprites.find(s=>s.id===piece.sprite);if(!sprite)continue;
      const actual=value.zoom;ctx.drawImage(image,sprite.x*actual,sprite.y*actual,sprite.w*actual,sprite.h*actual,x+piece.dx*scale,y+piece.dy*scale,sprite.w*scale,sprite.h*scale);}
    return '';
  }
  if(kind==='sprite'||kind==='resource'){
    const image=await loadImage(fileImage(value.image_path));if(!current())return '';
    if(!image)return 'Thiếu ảnh '+value.image_path;
    const count=value.frame_count||1,actual=value.zoom,frameHeight=image.height/count;
    if(!Number.isInteger(frameHeight))return 'Số frame không chia hết chiều cao ảnh';
    const w=image.width/actual*scale,h=frameHeight/actual*scale;
    ctx.drawImage(image,0,(tick%count)*frameHeight,image.width,frameHeight,x-w/2,y-h,w,h);return '';
  }
  if(kind==='dart'||kind==='arrow'){
    const issues=[];
    if(kind==='dart'){
      for(let n=0;n<(value.tail_border||[]).length;n++)issues.push(await smallImage(ctx,value.tail_border[n],x-(n+1)*10*scale,y,scale,zoom,current));
      const border=value.head_border?.[tick%Math.max(1,value.head_border.length)];if(border?.length)issues.push(await smallImage(ctx,border[0],x,y,scale,zoom,current));
      for(let n=0;n<(value.tail||[]).length;n++)issues.push(await smallImage(ctx,value.tail[n],x-(n+1)*10*scale,y,scale,zoom,current));
      const head=value.head?.[tick%Math.max(1,value.head.length)];if(head?.length)issues.push(await smallImage(ctx,head[0],x,y,scale,zoom,current));
    }else if(value.image_ids?.length)issues.push(await smallImage(ctx,value.image_ids[0],x,y,scale,zoom,current));
    return issues.filter(Boolean).join(' · ')||'Dãy ảnh đầu/đuôi và viền theo hướng ngang; đường bay phụ thuộc mục tiêu trong game.';
  }
  if(kind==='skill'){
    const frames=action==='fly'?value.fly:value.stand;if(!frames.length)return 'Skill không có dãy này';
    const frame=frames[tick%frames.length],issues=[];
    issues.push(await drawComposite(ctx.canvas,{head:0,body:1,leg:2},frame.status,zoom,current,scale));
    for(let layer=0;layer<3;layer++){
      // Each skill stage starts a new effect at frame zero; old effects continue
      // until replaced (Char.updateSkill). Reconstruct that state for scrubbing.
      let stage=tick%frames.length,elapsed=0;
      while(stage>=0&&!frames[stage]['effect_'+layer]){stage--;elapsed++;}
      if(stage<0)continue;
      const start=frames[stage],effect=value.effects[start['effect_'+layer]-1];
      let dx=0,dy=0;for(let index=stage;index<=tick%frames.length;index++){dx=dx||frames[index]['effect_'+layer+'_dx'];dy=dy||frames[index]['effect_'+layer+'_dy'];}
      if(effect&&elapsed<effect.frames.length)issues.push(await drawAsset(ctx,{...effect,kind:'effect'},elapsed,{...options,x:150+dx*scale,y:190+dy*scale}));
    }
    const projectile=frame.arrow_id>=100?value.darts[frame.arrow_id-100]:frame.arrow_id>0?value.arrows[frame.arrow_id-1]:null;
    if(projectile)issues.push(await drawAsset(ctx,{...projectile,kind:frame.arrow_id>=100?'dart':'arrow'},tick,{...options,x:150+(frame.arrow_dx-(frame.arrow_id>=100?10:0))*scale,y:190+frame.arrow_dy*scale}));
    return issues.filter(Boolean).join(' · ');
  }
  return 'Chưa có renderer cho dữ liệu này';
}
async function drawExtended(){
  if(!animationStudio.selected)return;
  const request=++animationStudio.request,epoch=studio.epoch,current=()=>request===animationStudio.request&&epoch===studio.epoch;
  const canvas=document.createElement('canvas');canvas.width=300;canvas.height=240;const ctx=canvasEmpty(canvas);ctx.imageSmoothingEnabled=false;
  try{
    const note=await drawAsset(ctx,animationStudio.selected,Math.max(0,Number($('animFrame').value)||0),{zoom:Number($('animZoom').value),scale:Number($('animScale').value),current,x:150,y:170,action:$('animAction').value});
    if(current()){
      const visible=$('animCanvas').getContext('2d');visible.clearRect(0,0,300,240);visible.save();
      if($('animFlip').checked){visible.translate(300,0);visible.scale(-1,1);}visible.drawImage(canvas,0,0);visible.restore();
      $('animNote').textContent=(valueSource(animationStudio.selected))+(note||'Đang hiển thị frame '+$('animFrame').value+' từ dữ liệu đã tải.');
    }
  }catch(error){if(current())$('animNote').textContent=error.message;}
}
$('animKind').onchange=()=>{stopExtended();animationStudio.selected=null;canvasEmpty($('animCanvas'));$('animTitle').textContent='Chọn dữ liệu';extendedCatalog();};$('animFind').onclick=()=>extendedCatalog();
$('animSearch').onkeydown=e=>{if(e.key==='Enter')extendedCatalog();};
for(const id of ['animFrame','animAction','animScale','animFlip'])$(id).onchange=()=>{stopExtended();drawExtended();};
$('animZoom').onchange=()=>{if(animationStudio.selected)selectExtended(animationStudio.selected.kind,animationStudio.selected.id);};
$('animPlay').onclick=()=>{
  if(animationStudio.playing){stopExtended();return;}if(!animationStudio.selected)return;
  animationStudio.playing=true;animationStudio.start=performance.now();const initial=Number($('animFrame').value)||0;$('animPlay').textContent='Dừng';
  async function frame(now){if(!animationStudio.playing)return;const tick=initial+Math.floor((now-animationStudio.start)*Math.max(1,Math.min(50,Number($('animFps').value)||16))/1000);
    if(tick!==animationStudio.last){animationStudio.last=tick;$('animFrame').value=tick;try{await drawExtended();}catch(error){$('animNote').textContent=error.message;stopExtended();return;}}
    if(animationStudio.playing)animationStudio.raf=requestAnimationFrame(frame);
  }animationStudio.last=-1;animationStudio.raf=requestAnimationFrame(frame);
};

async function itemVisualLayers(ctx,layers,tick,zoom,scale,current,behind){
  const issues=[];
  for(const layer of layers.filter(layer=>!!layer.behind===behind)){
    try{
      const value=layer.kind==='sheet'?layer:await extendedDetail(layer.kind,layer.id,zoom);
      if(!current())return '';
      const frameTick=['sheet','sprite'].includes(value.render_kind||value.kind)?Math.floor(tick/3):tick;
      issues.push(valueSource(value)+await drawAsset(ctx,value,frameTick,{zoom,scale,current,x:150+layer.dx*scale,y:190+layer.dy*scale}));
    }catch(error){issues.push(error.message);}
  }return issues.filter(Boolean).join(' · ');
}
function renderVisualLayers(value){
  $('visualItem').value=value.id;$('visualLayers').replaceChildren();
  for(const [index,layer] of (value.visual_layers||[]).entries()){
    const button=document.createElement('button');button.className='record';button.textContent=layer.kind+' #'+layer.id+' · dx '+layer.dx+' dy '+layer.dy+' · Bấm để xóa';
    button.onclick=()=>persistVisualLayers(value.id,value.visual_layers.filter((_,i)=>i!==index));$('visualLayers').append(button);
  }
}
async function persistVisualLayers(id,layers){
  const epoch=studio.epoch,out=lastProject;
  try{await post('/api/item-visuals',{out,item_id:id,layers});if(epoch!==studio.epoch)return;if(studio.selectedCostume?.id===id){studio.selectedCostume.visual_layers=layers;renderVisualLayers(studio.selectedCostume);drawCurrentCostume();}$('visualNote').textContent='Đã lưu '+layers.length+' lớp cho item #'+id;}
  catch(error){$('visualNote').textContent=error.message;}
}
$('visualAdd').onclick=async()=>{
  try{
    const raw=$('visualItem').value;if(raw==='')throw new Error('Chọn item hoặc nhập Item ID trước');
    const id=Number(raw),item=await studioApi(studioUrl('/api/costume',{id}));let layer;
    if($('visualKind').value==='sheet')layer={kind:'sheet',id:$('visualImage').value,width:Number($('visualWidth').value),height:Number($('visualHeight').value),count:Number($('visualCount').value),sequence:$('visualSequence').value.split(',').map(x=>Number(x.trim()))};
    else{const value=animationStudio.selected;if(!value||!['effect','dynamic','flag','sprite','resource','reference'].includes(value.kind))throw new Error('Chọn effect, cờ, sprite hoặc resource');layer={kind:value.kind,id:String(value.id)};}
    Object.assign(layer,{dx:Number($('visualDx').value),dy:Number($('visualDy').value),behind:$('visualBehind').checked});await persistVisualLayers(id,[...(item.visual_layers||[]),layer]);
  }catch(error){$('visualNote').textContent=error.message;}
};
$('visualClear').onclick=()=>{if($('visualItem').value!=='')persistVisualLayers(Number($('visualItem').value),[]);};
$('extraLoad').onclick=async()=>{try{await post('/api/start',{...payload(),force:true,extra_only:true});await refresh();studioTab('clone');}catch(error){$('error').textContent=error.message;}};
function valueSource(value){return value.source_kind==='local-reference'?'Asset cục bộ từ '+value.source+' · ':'';}
$('importAssets').onclick=async()=>{try{const result=await post('/api/import-assets',{source:$('importSource').value});animationStudio.cache.clear();$('animKind').value='reference';await extendedCatalog();$('animNote').textContent='Đã nhập asset tham chiếu cục bộ: '+JSON.stringify(result.files)+' · '+result.errors.length+' lỗi. Không tự gắn các ID này vào item server.';}catch(error){$('animNote').textContent=error.message;}};

let mapTextureRequest=0;
async function drawMapTexture(value,selected=null){
  const epoch=studio.epoch,request=++mapTextureRequest;
  const current=()=>epoch===studio.epoch&&request===mapTextureRequest&&studio.selectedMap?.id===value.id;
  if(selected===null){
    const result=await studioApi(studioUrl('/api/extended',{kind:'tileset'}));if(!current())return;
    while(result.has_more){const next=await studioApi(studioUrl('/api/extended',{kind:'tileset',offset:result.entries.length}));if(!current())return;result.entries.push(...next.entries);result.has_more=next.has_more;}
    $('mapTileset').replaceChildren(new Option('Lưới màu',''));
    for(const row of result.entries)$('mapTileset').append(new Option(row.name,row.id));
    if(value.tileset&&!result.entries.some(row=>row.id===value.tileset))$('mapTileset').append(new Option(value.tileset,value.tileset));
    $('mapTileset').value=value.tileset||'';selected=value.tileset;
  }
  if(!value.tiles)return;
  if(!selected){
    const canvas=$('mapCanvas'),ctx=canvas.getContext('2d');canvas.width=value.width*5;canvas.height=value.height*5;
    for(let y=0;y<value.height;y++)for(let x=0;x<value.width;x++){const tile=value.tiles[y*value.width+x];ctx.fillStyle='hsl('+((tile*57)%360)+' 44% '+(tile===0?18:45)+'%)';ctx.fillRect(x*5,y*5,5,5);}
    $('mapNote').textContent='Lưới tile ID. Chọn tileset để xem texture.';return;
  }
  const data=await studioApi(studioUrl('/api/tileset',{path:selected}));if(!current())return;
  const tileImages=new Map();
  for(const tile of new Set(value.tiles)){
    if(!tile)continue;
    const path=data.strip||data.tiles?.[String(tile)];
    tileImages.set(tile,path?await loadImage(fileImage(path)):null);if(!current())return;
  }
  const canvas=$('mapCanvas'),ctx=canvas.getContext('2d'),size=12;canvas.width=value.width*size;canvas.height=value.height*size;ctx.imageSmoothingEnabled=false;let missing=0;
  for(let y=0;y<value.height;y++)for(let x=0;x<value.width;x++){
    const tile=value.tiles[y*value.width+x];if(!tile)continue;
    const image=tileImages.get(tile);
    if(!image){ctx.fillStyle='#ac3960';ctx.fillRect(x*size,y*size,size,size);missing++;continue;}
    const sourceSize=24*data.zoom,sourceY=data.strip?(tile-1)*sourceSize:0;
    if(sourceY+sourceSize>image.height){missing++;continue;}
    ctx.drawImage(image,0,sourceY,sourceSize,sourceSize,x*size,y*size,size,size);
  }
  $('mapNote').textContent='Tileset đã chọn: '+selected+' · '+missing+' ô thiếu texture. Packet tile không chứa liên kết tileset; lựa chọn này lưu riêng cho map. Hiệu ứng nước/nền động chưa có thông tin của phiên vào map.';
}
$('mapTileset').onchange=()=>{
  if(!studio.selectedMap)return;
  drawMapTexture(studio.selectedMap,$('mapTileset').value).catch(error=>$('mapNote').textContent=error.message);
};
$('mapTextureSave').onclick=async()=>{try{if(!studio.selectedMap)return;const id=studio.selectedMap.id;await post('/api/map-tileset',{map_id:id,tileset:$('mapTileset').value});$('mapNote').textContent='Đã lưu tileset cho map #'+id;}catch(error){$('mapNote').textContent=error.message;}};
