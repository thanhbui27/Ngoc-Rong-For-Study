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
  const name = form.elements.name_prefix.value.trim() || 'bot';
  const first = Number(form.elements.start_number.value || 1);
  const count = Number(form.elements.count.value || 1);
  $('batch-preview').textContent = `Sẽ tạo ${count} bot: ${name} ${first} → ${prefix}${first}` + (count > 1 ? `, …, ${name} ${first + count - 1} → ${prefix}${first + count - 1}` : '');
}

function renderList() {
  $('bot-count').textContent = `(${bots.length})`;
  const list = $('bot-list');
  const scroll = list.scrollTop;
  const query = $('bot-search').value.trim().toLowerCase();
  const filtered = bots.filter(bot => [bot.name,bot.username,bot.character,bot.map_name,String(bot.map_id),bot.id].some(value => String(value ?? '').toLowerCase().includes(query)));
  list.innerHTML = filtered.length ? filtered.map(bot => `<button class="bot-row ${selected === bot.id ? 'active' : ''}" type="button" data-id="${esc(bot.id)}"><span class="dot ${esc(bot.status)}"></span><span class="row-text"><strong>${esc(bot.name)}</strong><small>${esc(bot.action)}</small></span></button>`).join('') : `<div class="empty-small">${bots.length ? 'Không tìm thấy bot' : 'Chưa có bot'}</div>`;
  list.scrollTop = scroll;
}

function fill(id, value) { $(id).textContent = value ?? '—'; }

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
  for (const key of ['gender','stat','heal_item','shop_map','shop_npc','shop_menu','shop_item','shop_min','shop_target','trade_partner']) {
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
  fill('detail-identity', `ID: ${bot.player_id || bot.id}${bot.character ? ` · ${bot.character}` : ''}`);
  fill('detail-server', `${bot.host}:${bot.port}`);
  $('detail-status').textContent = statusNames[bot.status] || bot.status;
  $('detail-status').className = `status-pill ${bot.status}`;
  fill('detail-action', `${bot.character || bot.name}: ${bot.action}`);
  fill('detail-action-detail', bot.recovering
    ? `KI ${bot.mp}/${bot.max_mp} · Cây đậu ${bot.tree_peas >= 0 ? `${bot.tree_peas} hạt` : 'đang kiểm tra'}`
    : bot.character ? `Nhân vật ${bot.character} · ${bot.map_name || 'chưa vào map'}` : `Tài khoản ${bot.username}`);
  fill('activity-badge', bot.status === 'running' ? '● Đang hoạt động' : bot.status === 'connecting' ? '● Đang kết nối' : bot.status === 'reconnecting' ? '● Chờ kết nối lại' : bot.status === 'error' ? '● Có lỗi' : '● Đã dừng');
  $('activity-badge').className = `activity-badge ${bot.status}`;
  $('detail-error').hidden = !bot.error;
  fill('detail-error', bot.error);
  fill('stat-map', bot.map_id >= 0 ? `${bot.map_id} · ${bot.map_name}` : '—');
  fill('stat-hp', `${bot.hp} / ${bot.max_hp}`);
  fill('stat-mp', `${bot.mp} / ${bot.max_mp}`);
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
  fill('character-location', bot.map_id >= 0 ? `${bot.map_id} · ${bot.map_name} (${bot.x}, ${bot.y})` : 'Chưa vào map');
  const bag = Object.entries(bot.bag || {}).filter(([,count]) => Number(count) > 0);
  $('character-bag').innerHTML = bag.length ? bag.map(([id,count]) => `<span>Item #${esc(id)} × ${esc(count)}</span>`).join('') : 'Chưa có vật phẩm';
  fill('quest-name', bot.task || 'Chưa có nhiệm vụ');
  fill('quest-step', bot.task_title ? `Bước ${bot.task_step + 1}: ${bot.task_title}${bot.task_count ? ` · ${bot.task_count}` : ''}` : 'Chưa có bước nhiệm vụ');
  const powerGoal = /Đạt\s+([\d.,]+)\s+triệu\s+sức mạnh/i.exec(bot.task_title || '');
  if (powerGoal) {
    const target = Number(powerGoal[1].replace(',', '.')) * 1000000;
    $('quest-progress').hidden = false;
    $('quest-progress-bar').style.width = `${Math.min(100, (bot.power || 0) / target * 100)}%`;
    fill('quest-hint', `Sức mạnh: ${Number(bot.power || 0).toLocaleString('vi-VN')} / ${target.toLocaleString('vi-VN')}. Bot sẽ đổi bãi quái khi đủ sức đánh.`);
  } else {
    $('quest-progress').hidden = true;
    fill('quest-hint', 'Bot ưu tiên quái của nhiệm vụ khi xác định được mục tiêu từ bước hiện tại.');
  }
  fill('log-path', bot.log_file);
  $('log-path').title = bot.log_file;
  document.querySelectorAll('[data-command="start"]').forEach(button => button.disabled = ['running','connecting','reconnecting'].includes(bot.status));
  document.querySelectorAll('[data-command="stop"]').forEach(button => button.disabled = ['stopped','disconnected','error'].includes(bot.status));
  document.querySelectorAll('[data-command="trade"]').forEach(button => button.disabled = bot.status !== 'running');
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

$('nav-manage').onclick = () => showView('manage');
$('nav-create').onclick = () => showView('create');
$('roster-create').onclick = () => showView('create');
$('empty-create').onclick = () => showView('create');
$('mode-single').onclick = () => setCreateMode('single');
$('mode-batch').onclick = () => setCreateMode('batch');
$('bot-search').oninput = renderList;
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
$('auto-scroll').checked = localStorage.getItem('nro-bot-auto-scroll') !== 'false';
$('auto-scroll').onchange = event => localStorage.setItem('nro-bot-auto-scroll', String(event.target.checked));
['name_prefix','username_prefix','start_number','count'].forEach(name => $('create-form').elements[name].addEventListener('input', previewBatch));
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
