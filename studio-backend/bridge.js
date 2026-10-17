/* Adapter for the independently written web preview, not the DTMAX frontend. */
(async function () {
  'use strict';
  let token = '', health, fetching = false;
  const localSave = save, localRenderOther = renderOther, localSetMode = setMode;
  async function api(path, options = {}) {
    const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', 'X-Studio-Token': token, ...options.headers } });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || 'Backend HTTP ' + response.status);
    return body;
  }
  async function refresh() {
    if (fetching) return;
    fetching = true;
    try {
      const data = await api('/api/workspace');
      state.jobs = data.jobs; state.projects = data.projects; state.config = data.config; state.logs = data.logs;
      syncProjects();
      if (['dashboard', 'image', 'video'].includes(page)) { renderJobs(); renderStats(); }
      else if (page === 'library' || page === 'logs') renderOther();
    } finally { fetching = false; }
  }
  try {
    health = await api('/api/health');
    token = (await api('/api/session')).token;
    await refresh();
  } catch {
    toast('Không kết nối được backend mới. Hãy tải lại trang sau khi khởi chạy server.');
    $('#job-form').onsubmit = event => { event.preventDefault(); toast('Backend không sẵn sàng; chưa lưu tác vụ.'); };
    return;
  }
  document.title = 'Independent Studio · Backend mới';
  $('.brand strong').textContent = 'studio.';
  $('.pill').textContent = 'BACKEND MỚI · 0.1';
  $('.header-right .status').textContent = health.images_ready ? 'API ảnh đã cấu hình · Video chưa hỗ trợ' : 'Backend đang chạy · Chưa có API AI';
  $('.mini-panel p').textContent = 'Dự án và tác vụ được lưu bằng SQLite. Không dùng backend DTMAX.';
  $('.footer>span').textContent = 'Independent Studio · Giao diện thử nghiệm riêng, chưa tương thích giao diện DTMAX gốc';
  $('.footer>span:last-child').textContent = 'Lưu trên backend cục bộ';
  $('.profile>div:last-child').firstChild.textContent = state.config.studio;
  $('.profile .muted').textContent = 'Dữ liệu trên máy chạy backend';
  $('#quantity').max = '4';
  $('#reference').disabled = true;
  $('.upload').title = 'Adapter tạo ảnh hiện chưa hỗ trợ ảnh tham chiếu';
  $('#upload-label').textContent = 'Ảnh tham chiếu: chưa hỗ trợ ở backend mới';
  $('#reference').closest('.field').querySelector('.hint').textContent = 'Tính năng này chưa được gửi đến nhà cung cấp AI.';
  const notice = $('#job-form .notice');
  notice.textContent = 'Bản nháp được lưu vào SQLite. Dùng nút Gửi ở bảng để gọi API thật; có thể phát sinh phí. Video và ảnh tham chiếu chưa hỗ trợ. Tỉ lệ dự kiến không thay thế kích thước API bên dưới.';
  setMode = function (value) {
    localSetMode(value);
    $('#quality-label').textContent = 'Kích thước API';
    $('#quality').replaceChildren();
    for (const size of health.supported_sizes) { const o = el('option', size); o.value = size; $('#quality').append(o); }
    $('#quality').value = '1024x1024';
    $('#model').replaceChildren(el('option', health.images_ready ? health.model : 'Chưa cấu hình API ảnh'));
  };
  setMode(mode);
  renderStats = function () {
    const counts = [state.jobs.length, state.jobs.filter(j => j.kind === 'image').length,
      state.jobs.filter(j => j.status === 'succeeded').length, state.jobs.filter(j => ['queued', 'running', 'cancelling'].includes(j.status)).length];
    const labels = ['Tác vụ trên backend', 'Tác vụ hình ảnh', 'Đã hoàn thành', 'Đang chờ / xử lý'];
    $('#stats').replaceChildren();
    counts.forEach((n, i) => {
      const card = el('div', '', 'stat'), left = el('div'), right = el('div', '', 'stat-icon');
      left.append(el('div', labels[i], 'muted small'), el('span', String(n), 'number')); right.innerHTML = icon(['folder', 'image', 'spark', 'clock'][i]); card.append(left, right); $('#stats').append(card);
    });
  };
  const labels = { draft: 'Bản nháp', queued: 'Đang chờ', running: 'Đang tạo ảnh', cancelling: 'Đang chờ hủy', cancelled: 'Đã hủy', succeeded: 'Hoàn thành', failed: 'Thất bại' };
  async function act(id, action) {
    try {
      if (action === 'run' && !confirm('Gửi tác vụ đến API thật? Nhà cung cấp có thể tính phí, kể cả khi bạn yêu cầu hủy.')) return;
      await api('/api/jobs/' + encodeURIComponent(id) + (action === 'delete' ? '' : '/' + action), {
        method: action === 'delete' ? 'DELETE' : 'POST', ...(action === 'delete' ? {} : { body: '{}' })
      });
      await refresh(); toast(action === 'run' ? 'Đã gửi vào hàng đợi backend.' : action === 'cancel' ? 'Đã yêu cầu hủy; dịch vụ ngoài có thể vẫn tính phí.' : 'Đã xóa tác vụ.');
    } catch (error) { toast(error.message); }
  }
  renderJobs = function () {
    const q = $('#search').value.trim().toLowerCase(); const jobs = state.jobs.filter(j => j.prompt.toLowerCase().includes(q));
    $('#jobs').replaceChildren(); $('#job-count').textContent = state.jobs.length; $('#empty').classList.toggle('hidden', jobs.length > 0);
    if (!jobs.length) $('#empty').textContent = q ? 'Không tìm thấy tác vụ.' : 'Chưa có tác vụ trên backend. Thêm bản nháp để bắt đầu.';
    for (const job of jobs) {
      const row = el('tr'), prompt = el('td', job.prompt, 'prompt'); prompt.title = job.prompt + (job.error ? '\nLỗi: ' + job.error : '');
      const detail = el('td', (job.kind === 'image' ? 'Ảnh' : 'Video') + ' · ' + job.size), status = el('td'), label = el('span', labels[job.status] || job.status, 'job-status');
      status.append(label); if (job.error) { const error = el('div', job.error, 'hint'); error.style.maxWidth = '230px'; status.append(error); }
      const actions = el('td'); actions.style.whiteSpace = 'nowrap';
      if (['draft', 'failed', 'cancelled'].includes(job.status)) { const run = el('button', job.status === 'draft' ? 'Gửi' : 'Thử lại', 'btn'); run.type = 'button'; run.onclick = () => act(job.id, 'run'); actions.append(run); }
      if (['queued', 'running'].includes(job.status)) { const cancel = el('button', 'Hủy', 'btn'); cancel.type = 'button'; cancel.onclick = () => act(job.id, 'cancel'); actions.append(cancel); }
      if (!['queued', 'running', 'cancelling'].includes(job.status)) { const del = el('button', '', 'icon-btn'); del.type = 'button'; del.setAttribute('aria-label', 'Xóa tác vụ ' + job.prompt); del.innerHTML = icon('trash'); del.onclick = () => act(job.id, 'delete'); actions.append(del); }
      if (job.outputs.length) { const view = el('button', 'Xem ảnh', 'btn'); view.onclick = () => go('library'); actions.append(view); }
      row.append(prompt, detail, status, actions); $('#jobs').append(row);
    }
  };
  $('#job-form').onsubmit = async event => {
    event.preventDefault();
    try {
      await api('/api/jobs', { method: 'POST', body: JSON.stringify({ prompt: $('#prompt').value.trim(), quantity: Number($('#quantity').value),
        kind: mode, project: $('#project').value, ratio: $('#ratio').value, size: $('#quality').value, duration: $('#duration').value }) });
      await refresh(); toast('Đã lưu bản nháp trên backend. Chưa gọi API tạo ảnh/video.');
    } catch (error) { toast(error.message); }
  };
  $('#clear-jobs').onclick = async () => {
    const deletable = state.jobs.filter(j => !['queued', 'running', 'cancelling'].includes(j.status));
    if (!deletable.length) return toast('Không có tác vụ đã dừng để xóa.');
    if (!confirm('Xóa ' + deletable.length + ' tác vụ đã dừng và các ảnh của chúng?')) return;
    try { for (const j of deletable) await api('/api/jobs/' + j.id, { method: 'DELETE' }); await refresh(); toast('Đã xóa các tác vụ đã dừng.'); } catch (e) { toast(e.message); }
  };
  exportData = async function () {
    try {
      const workspace = await api('/api/workspace'), url = URL.createObjectURL(new Blob([JSON.stringify(workspace, null, 2)], { type: 'application/json' })), a = document.createElement('a');
      a.href = url; a.download = 'studio-backend-workspace.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); toast('Đã xuất metadata. Ảnh được lưu riêng trên backend.');
    } catch (error) { toast(error.message); }
  };
  $('#export').onclick = exportData;
  renderOther = function () {
    if (page === 'library') {
      $('#other-view').replaceChildren(); const gallery = el('div', '', 'gallery panel');
      for (const job of state.jobs) for (const output of job.outputs) {
        const card = el('div'), img = el('img'); img.src = output.url; img.alt = job.prompt; img.style.cssText = 'width:100%;border-radius:8px;aspect-ratio:1;object-fit:contain;background:#101119';
        const link = el('a', 'Tải ảnh', 'btn'); link.href = output.url; link.download = ''; card.append(img, el('p', job.prompt, 'small'), link); gallery.append(card);
      }
      if (!gallery.children.length) gallery.append(el('p', 'Chưa có ảnh từ API. Bản nháp không tạo kết quả giả.', 'empty'));
      $('#other-view').append(gallery); return;
    }
    localRenderOther();
    if (page !== 'settings') return;
    $('#other-view .notice').textContent = 'Backend độc lập đã kết nối. API ảnh: ' + (health.images_ready ? 'đã cấu hình (' + health.model + ').' : 'chưa cấu hình.') + ' Video và ảnh tham chiếu chưa hỗ trợ. Chỉ cấu hình khóa qua biến môi trường trên máy chủ; không nhập vào trình duyệt.';
    $('#other-view .muted.small').textContent = 'Xuất JSON chứa metadata. Chưa hỗ trợ nhập JSON vào backend; không thay thế cơ sở dữ liệu đang chạy.';
    const importer = $('#import'); importer.disabled = true; importer.previousElementSibling.style.display = 'none';
    $('#export-settings').onclick = exportData;
    $('#save-settings').onclick = async () => {
      try { const name = $('#studio-name').value.trim(); await api('/api/workspace', { method: 'PUT', body: JSON.stringify({ projects: state.projects, config: { studio: name } }) }); await refresh(); $('.profile>div:last-child').firstChild.textContent = name; toast('Đã lưu cấu hình trên backend.'); } catch (e) { toast(e.message); }
    };
    $('#add-project').onclick = async () => {
      const name = $('#new-project').value.trim(); if (!name || state.projects.includes(name)) return toast('Tên dự án trống hoặc đã tồn tại.');
      try { await api('/api/workspace', { method: 'PUT', body: JSON.stringify({ projects: [...state.projects, name], config: state.config }) }); await refresh(); $('#new-project').value = ''; toast('Đã thêm dự án trên backend.'); } catch (e) { toast(e.message); }
    };
  };
  // Form preferences remain local; canonical projects/jobs live exclusively in SQLite.
  save = localSave;
  renderJobs(); renderStats();
  setInterval(async () => { try { await refresh(); } catch { $('.header-right .status').textContent = 'Mất kết nối backend · Tải lại trang sau khi khởi động lại'; } }, 2000);
  toast('Đã kết nối backend mới. Không dùng binary hoặc máy chủ bản quyền DTMAX.');
})();
