'use strict';

const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const statNames = {balanced:'Cân bằng',attack:'Sức đánh',hp:'HP',mp:'KI',def:'Giáp',off:'Tắt'};
const genderNames = ['Trái Đất','Namếc','Xayda'];
const statusNames = {running:'RUNNING',connecting:'CONNECTING',reconnecting:'RECONNECTING',stopped:'STOPPED',disconnected:'DISCONNECTED',error:'ERROR'};
let bots = [];
let selected = null;
let rendered = null;
let logVersion = null;
let createMode = 'single';
let view = 'manage';
let activeTab = 'overview';
let refreshing = false;

async function request(path, options = {}) {
  const response = await fetch(path, {headers:{'Content-Type':'application/json'}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

function showView(next) {
  view = next;
  $('nav-manage').classList.toggle('active', next === 'manage');
  $('nav-create').classList.toggle('active', next === 'create');
  $('create-view').hidden = next !== 'create';
  $('overview-view').hidden = next !== 'manage' || !selected;
  $('empty-view').hidden = next !== 'manage' || !!selected;
  if (next === 'manage' && selected) loadDetail();
}

function setCreateMode(mode) {
  createMode = mode;
  $('mode-single').classList.toggle('active', mode === 'single');
  $('mode-batch').classList.toggle('active', mode === 'batch');
  $('single-fields').hidden = mode !== 'single';
  $('batch-fields').hidden = mode !== 'batch';
  $('single-fields').querySelectorAll('input').forEach(input => input.disabled = mode !== 'single');
  $('batch-fields').querySelectorAll('input').forEach(input => input.disabled = mode !== 'batch');
  $('create-submit').textContent = mode === 'batch' ? '＋ Tạo và chạy hàng loạt' : '＋ Tạo và chạy bot';
  $('notice').textContent = '';
  previewBatch();
}

function previewBatch() {
  const form = $('create-form');
  const prefix = form.elements.username_prefix.value.trim() || 'abc';
  const first = Number(form.elements.start_number.value || 1);
  const count = Number(form.elements.count.value || 1);
  $('batch-preview').textContent = `Sẽ tự đặt nickname riêng cho từng bot (ví dụ: MiuMiu483, TuanAnh721); tài khoản: ${prefix}${first}` + (count > 1 ? ` → ${prefix}${first + count - 1}` : '');
}

function renderList() {
  $('bot-count').textContent = `(${bots.length})`;
  $('start-all').disabled = bots.length === 0 || bots.every(bot => ['running','connecting','reconnecting'].includes(bot.status));
  $('stop-all').disabled = bots.every(bot => ['stopped','disconnected','error'].includes(bot.status));
  $('delete-all').disabled = bots.length === 0;
  const list = $('bot-list');
  const scroll = list.scrollTop;
  const query = $('bot-search').value.trim().toLowerCase();
  const filtered = bots.filter(bot => [bot.name,bot.username,bot.character,bot.map_name,String(bot.map_id),bot.id].some(value => String(value ?? '').toLowerCase().includes(query)));
  list.innerHTML = filtered.length ? filtered.map(bot => `<button class="bot-row ${selected === bot.id ? 'active' : ''}" type="button" data-id="${esc(bot.id)}"><span class="dot ${esc(bot.status)}"></span><span class="row-text"><strong>${esc(bot.character || bot.name)} (ID: ${esc(bot.player_id || bot.id)})</strong><small>${esc(bot.name)} · ${esc(bot.action)}</small></span></button>`).join('') : `<div class="empty-small">${bots.length ? 'Không tìm thấy bot' : 'Chưa có bot'}</div>`;
  list.scrollTop = scroll;
}

function fill(id, value) { $(id).textContent = value ?? '—'; }
function mapLabel(bot) { return bot.map_id >= 0 ? `${bot.map_name || 'Map'} (ID: ${bot.map_id})` : '—'; }

function renderItems(container, items, location, running) {
  const entries = Object.values(items || {}).filter(item => Number(item.count) > 0);
  if (!entries.length) {
    container.textContent = location === 'bag' ? 'Chưa có vật phẩm trong túi' : location === 'worn' ? 'Chưa có trang bị đang mặc' : 'Chưa có vật phẩm trong rương';
    return;
  }
  container.innerHTML = entries.map(item => {
    const options = (item.options || []).map(option => option.label ?? `Chỉ số ${option.id}: ${option.param}`)
      .filter(Boolean).map(esc).join(' · ');
    const action = location === 'box'
      ? `<button class="button" data-item-action="take" data-location="box" data-item="${esc(item.id)}" ${running ? '' : 'disabled'}>Chuyển vào túi</button>${[0,1,2,3,4].includes(Number(item.type)) ? `<button class="button success" data-item-action="take_equip" data-location="box" data-item="${esc(item.id)}" ${running ? '' : 'disabled'}>Chuyển & mặc</button>` : `<button class="button success" data-item-action="take_use" data-location="box" data-item="${esc(item.id)}" ${running ? '' : 'disabled'}>Chuyển & dùng</button>`}<button class="button danger" data-item-action="take_throw" data-location="box" data-item="${esc(item.id)}" ${running ? '' : 'disabled'}>Chuyển & bỏ</button>`
      : location === 'worn'
        ? `<button class="button" data-item-action="unequip" data-location="worn" data-item="${esc(item.id)}" ${running ? '' : 'disabled'}>Tháo vào túi</button>`
      : `${[0,1,2,3,4].includes(Number(item.type)) ? `<button class="button success" data-item-action="equip" data-location="bag" data-item="${esc(item.id)}" ${running ? '' : 'disabled'}>Mặc</button>` : `<button class="button success" data-item-action="use" data-location="bag" data-item="${esc(item.id)}" ${running ? '' : 'disabled'}>Dùng</button>`}<button class="button danger" data-item-action="throw" data-location="bag" data-item="${esc(item.id)}" ${running ? '' : 'disabled'}>Bỏ</button>`;
    const iconId = Number(item.icon_id);
    const icon = Number.isSafeInteger(iconId) && iconId >= 0
      ? `<img class="item-icon" src="/assets/icon/${iconId}.png" alt="" loading="lazy" onerror="this.hidden=true">`
      : '';
    return `<article class="item-card">${icon}<strong>${esc(item.name || `Vật phẩm #${item.id}`)} <small>(ID: ${esc(item.id)}) × ${esc(item.count)}</small></strong><p>${esc(item.description || item.info || 'Không có mô tả')}</p>${options ? `<small>${options}</small>` : ''}<div class="item-actions">${action}</div></article>`;
  }).join('');
}

function showTab(tab) {
  activeTab = tab;
  document.querySelectorAll('[data-tab]').forEach(button => button.classList.toggle('active', button.dataset.tab === tab));
  $('summary-section').hidden = tab !== 'overview';
  $('logs-section').hidden = !['overview','logs'].includes(tab);
  for (const name of ['config','character','quest','trade']) $(`${name}-section`).hidden = tab !== name;
  $('main-panel')?.scrollTo?.({top:0});
}

function populateConfig(bot) {
  const form = $('config-form');
  for (const key of ['mode','gender','stat','heal_item','shop_map','shop_npc','shop_menu','shop_item','shop_min','shop_target','trade_partner']) {
    const value = key === 'gender' ? bot.create_gender : bot[key];
    form.elements[key].value = value ?? (key === 'stat' ? 'balanced' : 0);
  }
  $('trade-form').elements.trade_partner.value = bot.trade_partner || '';
  $('config-notice').textContent = '';
  $('trade-notice').textContent = '';
}

function renderDetail(bot) {
  const changedBot = rendered !== bot.id;
  if (changedBot) { rendered = bot.id; logVersion = null; $('event-log').scrollTop = 0; populateConfig(bot); showTab('overview'); }
  fill('detail-name', bot.name);
  const avatar = $('character-avatar');
  const avatarFallback = $('character-avatar-fallback');
  const avatarId = Number(bot.avatar_id);
  if (Number.isSafeInteger(avatarId) && avatarId >= 0) {
    const src = `/assets/icon/${avatarId}.png`;
    if (avatar.getAttribute('src') !== src) avatar.src = src;
    avatar.hidden = false;
    avatarFallback.hidden = true;
    avatar.onerror = () => { avatar.hidden = true; avatarFallback.hidden = false; };
  } else {
    avatar.hidden = true;
    avatarFallback.hidden = false;
    avatar.removeAttribute('src');
  }
  fill('detail-identity', `${bot.character || bot.name} (ID: ${bot.player_id || bot.id}) · bot ${bot.name}`);
  fill('detail-server', `${bot.host}:${bot.port}`);
  $('detail-status').textContent = statusNames[bot.status] || bot.status;
  $('detail-status').className = `status-pill ${bot.status}`;
  fill('detail-action', `${bot.character || bot.name}: ${bot.action}`);
  fill('detail-action-detail', bot.recovering
    ? `KI ${bot.mp}/${bot.max_mp} · Thể lực ${bot.stamina}/${bot.max_stamina} · Cây đậu ${bot.tree_peas >= 0 ? `${bot.tree_peas} hạt` : 'đang kiểm tra'}`
    : bot.character ? `Nhân vật ${bot.character} · Thể lực ${bot.stamina}/${bot.max_stamina} · ${bot.map_id >= 0 ? mapLabel(bot) : 'chưa vào map'}` : `Tài khoản ${bot.username}`);
  fill('activity-badge', bot.status === 'running' ? '● Đang hoạt động' : bot.status === 'connecting' ? '● Đang kết nối' : bot.status === 'reconnecting' ? '● Chờ kết nối lại' : bot.status === 'error' ? '● Có lỗi' : '● Đã dừng');
  $('activity-badge').className = `activity-badge ${bot.status}`;
  $('detail-error').hidden = !bot.error;
  fill('detail-error', bot.error);
  fill('stat-map', mapLabel(bot));
  fill('stat-hp', `${bot.hp} / ${bot.max_hp}`);
  fill('stat-mp', `${bot.mp} / ${bot.max_mp}`);
  fill('stat-stamina', `${bot.stamina} / ${bot.max_stamina}`);
  fill('stat-gold', Number(bot.gold).toLocaleString('vi-VN'));
  fill('stat-kills', bot.kills);
  fill('stat-picks', bot.picks);
  fill('stat-buys', bot.purchases);
  fill('stat-power', Number(bot.power || 0).toLocaleString('vi-VN'));
  fill('stat-potential', Number(bot.potential || 0).toLocaleString('vi-VN'));
  fill('info-name', bot.name);
  fill('info-account', bot.username);
  fill('info-host', bot.host);
  fill('info-port', bot.port);
  fill('info-stat', statNames[bot.stat] || bot.stat);
  fill('info-register', bot.auto_register ? 'Bật' : 'Tắt');
  fill('info-gender', genderNames[bot.player_id ? bot.gender : bot.create_gender] || '—');
  fill('info-task', bot.task_title || (bot.task ? `${bot.task} · bước ${bot.task_step + 1}` : 'Chưa có'));
  fill('character-name', bot.character || 'Chưa vào game');
  fill('character-power', Number(bot.power || 0).toLocaleString('vi-VN'));
  fill('character-potential', Number(bot.potential || 0).toLocaleString('vi-VN'));
  fill('character-damage', Number(bot.damage || 0).toLocaleString('vi-VN'));
  fill('character-defense', Number(bot.defense || 0).toLocaleString('vi-VN'));
  fill('character-location', bot.map_id >= 0 ? `${mapLabel(bot)} (${bot.x}, ${bot.y})` : 'Chưa vào map');
  renderItems($('character-worn'), bot.worn_details, 'worn', bot.status === 'running');
  renderItems($('character-bag'), bot.bag_details, 'bag', bot.status === 'running');
  renderItems($('character-box'), bot.box_details, 'box', bot.status === 'running');
  fill('item-notice', bot.item_feedback || '');
  fill('quest-name', bot.task || 'Chưa có nhiệm vụ');
  fill('quest-step', bot.task_title ? `Bước ${bot.task_step + 1}: ${bot.task_title}${bot.task_count ? ` · ${bot.task_count}` : ''}` : 'Chưa có bước nhiệm vụ');
  const powerGoal = /Đạt\s+([\d.,]+)\s+triệu\s+sức mạnh/i.exec(bot.task_title || '');
  if (bot.mode === 'farm') {
    $('quest-progress').hidden = true;
    fill('quest-hint', 'Chế độ chỉ đánh quái: bot tạm bỏ qua nhiệm vụ và chọn quái theo sức mạnh hiện tại.');
  } else if (powerGoal) {
    const target = Number(powerGoal[1].replace(',', '.')) * 1000000;
    $('quest-progress').hidden = false;
    $('quest-progress-bar').style.width = `${Math.min(100, (bot.power || 0) / target * 100)}%`;
    fill('quest-hint', `Sức mạnh: ${Number(bot.power || 0).toLocaleString('vi-VN')} / ${target.toLocaleString('vi-VN')}. Bot sẽ đổi bãi quái khi đủ sức đánh.`);
  } else if (/đi khám phá vật thể lạ/i.test(bot.task_title || '')) {
    $('quest-progress').hidden = true;
    fill('quest-hint', 'Bot ở vách núi trên hành tinh của nhân vật để tìm và nhặt vật thể nhiệm vụ; không chuyển sang hành tinh khác.');
  } else {
    $('quest-progress').hidden = true;
    fill('quest-hint', 'Bot ưu tiên quái của nhiệm vụ khi xác định được mục tiêu từ bước hiện tại.');
  }
  if (bot.mode === 'ai') {
    const goal = bot.ai_goal === 'farm' ? 'luyện sức mạnh' : 'làm nhiệm vụ';
    const stat = bot.ai_stat_focus || 'đang chọn';
    fill('quest-hint', `AI cục bộ: ${bot.ai_installed ? 'sẵn sàng' : 'chưa cài model'} · mục tiêu ${goal} · hướng cộng chỉ số ${stat}. ${$('quest-hint').textContent}`);
  }
  fill('log-path', bot.log_file);
  $('log-path').title = bot.log_file;
  document.querySelectorAll('[data-command="start"]').forEach(button => button.disabled = ['running','connecting','reconnecting'].includes(bot.status));
  document.querySelectorAll('[data-command="stop"]').forEach(button => button.disabled = ['stopped','disconnected','error'].includes(bot.status));
  document.querySelectorAll('[data-command="trade"]').forEach(button => button.disabled = bot.status !== 'running');
  $('skip-quest').disabled = bot.status !== 'running' || bot.task_step < 0;
  const currentLogVersion = `${bot.log_seq}:${bot.logs?.length || 0}`;
  if (logVersion !== currentLogVersion) {
    const log = $('event-log');
    const previousTop = log.scrollTop;
    const nearBottom = log.scrollHeight - log.clientHeight - previousTop < 35;
    log.innerHTML = bot.logs?.length ? bot.logs.map(entry => `<div class="entry ${esc(entry.level)}"><time>${esc(entry.time)}</time><span class="level">${entry.level === 'error' ? 'ERROR' : 'INFO'}</span><span class="message">${esc(entry.message)}</span></div>`).join('') : '<div class="empty-small">Chưa có log</div>';
    if (changedBot || ($('auto-scroll').checked && nearBottom)) log.scrollTop = log.scrollHeight;
    else log.scrollTop = previousTop;
    logVersion = currentLogVersion;
  }
}

async function loadDetail() {
  if (!selected || view !== 'manage') return;
  const requested = selected;
  try {
    const bot = await request(`/api/bots/${encodeURIComponent(requested)}`);
    if (selected === requested && view === 'manage') renderDetail(bot);
  } catch (error) {
    if (selected === requested) { selected = null; rendered = null; showView('manage'); }
  }
}

async function refresh() {
  if (refreshing) return;
  refreshing = true;
  try {
    bots = await request('/api/bots');
    if (selected && !bots.some(bot => bot.id === selected)) { selected = null; rendered = null; }
    renderList();
    $('overview-view').hidden = view !== 'manage' || !selected;
    $('empty-view').hidden = view !== 'manage' || !!selected;
    await loadDetail();
  } catch (error) { $('notice').textContent = `Mất kết nối Bot Manager: ${error.message}`; }
  finally { refreshing = false; }
}

async function command(action) {
  if (!selected) return;
  const bot = bots.find(item => item.id === selected);
  if (action === 'delete' && !confirm(`Xóa bot ${bot?.name || selected} khỏi danh sách đã lưu?`)) return;
  try {
    if (action === 'delete') {
      await request(`/api/bots/${selected}`, {method:'DELETE'});
      selected = null; rendered = null;
    } else {
      await request(`/api/bots/${selected}/${action}`, {method:'POST',body:'{}'});
    }
    await refresh();
  } catch (error) { alert(error.message); }
}

async function bulkCommand(action) {
  const button = $(action);
  if (action === 'delete-all' && !confirm(`Xóa toàn bộ ${bots.length} bot khỏi danh sách đã lưu và dừng bot đang chạy? Log cũ vẫn được giữ.`)) return;
  button.disabled = true;
  try {
    const result = await request(`/api/bots/${action}`, {method:'POST',body:'{}'});
    if (action === 'delete-all') {
      bots = []; selected = null; rendered = null; showView('manage');
      $('notice').textContent = `Đã xóa ${result.count} bot.`;
    } else {
      $('notice').textContent = action === 'start-all'
        ? `Đã xếp chạy ${result.count} bot, giãn cách 0,3 giây mỗi bot.`
        : `Đã gửi lệnh dừng ${result.count} bot.`;
    }
    await refresh();
  } catch (error) {
    $('notice').textContent = error.message;
    button.disabled = false;
  }
}

$('nav-manage').onclick = () => showView('manage');
$('nav-create').onclick = () => showView('create');
$('roster-create').onclick = () => showView('create');
$('empty-create').onclick = () => showView('create');
$('mode-single').onclick = () => setCreateMode('single');
$('mode-batch').onclick = () => setCreateMode('batch');
$('bot-search').oninput = renderList;
$('start-all').onclick = () => bulkCommand('start-all');
$('stop-all').onclick = () => bulkCommand('stop-all');
$('delete-all').onclick = () => bulkCommand('delete-all');
$('bot-list').onclick = event => {
  const row = event.target.closest('[data-id]');
  if (!row) return;
  selected = row.dataset.id;
  rendered = null;
  showView('manage');
  renderList();
};
$('overview-view').onclick = event => {
  const button = event.target.closest('[data-command]');
  if (button) command(button.dataset.command);
};
$('character-section').onclick = async event => {
  if (event.target.closest('#load-box')) {
    if (!selected) return;
    try {
      await request(`/api/bots/${selected}/box`, {method:'POST',body:'{}'});
      $('item-notice').textContent = 'Đã yêu cầu mở rương; vật phẩm sẽ xuất hiện khi server gửi dữ liệu.';
    } catch (error) { $('item-notice').textContent = error.message; }
    return;
  }
  const button = event.target.closest('[data-item-action]');
  if (!button || !selected) return;
  const action = button.dataset.itemAction;
  if (['throw','take_throw'].includes(action) && !confirm('Bỏ vật phẩm này?')) return;
  button.disabled = true;
  try {
    await request(`/api/bots/${selected}/item`, {method:'POST',body:JSON.stringify({
      action, location:button.dataset.location, item_id:Number(button.dataset.item)
    })});
    $('item-notice').textContent = ({take:'Đã yêu cầu chuyển vật phẩm vào túi.',use:'Đã gửi lệnh sử dụng vật phẩm.',throw:'Đã gửi lệnh bỏ vật phẩm.',take_use:'Sẽ chuyển vật phẩm vào túi rồi sử dụng.',take_throw:'Sẽ chuyển vật phẩm vào túi rồi bỏ.',take_equip:'Sẽ chuyển trang bị vào túi rồi mặc.',unequip:'Đã gửi lệnh tháo trang bị vào túi.',equip:'Đã gửi lệnh mặc trang bị.'})[action];
    setTimeout(loadDetail, 500);
  } catch (error) {
    $('item-notice').textContent = error.message;
    button.disabled = false;
  }
};
document.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => showTab(button.dataset.tab));
$('config-form').onsubmit = async event => {
  event.preventDefault();
  if (!selected) return;
  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
  const notice = $('config-notice');
  try {
    await request(`/api/bots/${selected}/config`, {method:'POST',body:JSON.stringify(payload)});
    notice.textContent = 'Đã lưu cấu hình'; notice.classList.remove('error');
    await refresh();
  } catch (error) { notice.textContent = error.message; notice.classList.add('error'); }
};
$('trade-form').onsubmit = async event => {
  event.preventDefault();
  if (!selected) return;
  const notice = $('trade-notice');
  try {
    await request(`/api/bots/${selected}/config`, {method:'POST',body:JSON.stringify({trade_partner:event.currentTarget.elements.trade_partner.value})});
    $('config-form').elements.trade_partner.value = event.currentTarget.elements.trade_partner.value;
    notice.textContent = 'Đã lưu đối tác'; notice.classList.remove('error');
    await refresh();
  } catch (error) { notice.textContent = error.message; notice.classList.add('error'); }
};
$('trade-invite').onclick = () => command('trade');
$('skip-quest').onclick = () => command('skip-quest');
$('auto-scroll').checked = localStorage.getItem('nro-bot-auto-scroll') !== 'false';
$('auto-scroll').onchange = event => localStorage.setItem('nro-bot-auto-scroll', String(event.target.checked));
['username_prefix','start_number','count'].forEach(name => $('create-form').elements[name].addEventListener('input', previewBatch));
$('create-form').onsubmit = async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());
  payload.auto_register = form.elements.auto_register.checked;
  const firstUsername = createMode === 'batch' ? `${payload.username_prefix}${payload.start_number}` : payload.username;
  $('notice').textContent = '';
  if (payload.auto_register && (firstUsername.length < 4 || firstUsername.length > 18 || payload.password.length < 5 || payload.password.length > 18)) {
    $('notice').textContent = 'Tự tạo tài khoản yêu cầu tên đăng nhập 4–18 và mật khẩu 5–18 ký tự.';
    return;
  }
  const submit = $('create-submit');
  submit.disabled = true;
  try {
    const result = await request(createMode === 'batch' ? '/api/bots/batch' : '/api/bots', {method:'POST',body:JSON.stringify(payload)});
    selected = createMode === 'batch' ? result[0]?.id : result.id;
    rendered = null;
    form.elements.password.value = '';
    showView('manage');
    await refresh();
  } catch (error) { $('notice').textContent = error.message; }
  finally { submit.disabled = false; }
};

setCreateMode('single');
showView('manage');
refresh();
setInterval(refresh, 1500);
