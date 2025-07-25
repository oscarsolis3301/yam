// Sticky Notes Module
// Handles sticky notes widget functionality including dragging, resizing, and CRUD operations

let notes = [];
let isDraggingSticky = false;
let stickyOffset = { x: 0, y: 0 };
let stickyInitial = { x: 0, y: 0 };
let resizing = false;
let searchQuery = '';

// --- Dragging ---
function initStickyDrag() {
  const widget = document.getElementById('stickyNotesWidget');
  const header = document.getElementById('stickyHeader');
  header.addEventListener('mousedown', (e) => {
    if (e.target.closest('.sticky-btn')) return;
    isDraggingSticky = true;
    const rect = widget.getBoundingClientRect();
    stickyOffset.x = e.clientX - rect.left;
    stickyOffset.y = e.clientY - rect.top;
    document.body.style.userSelect = 'none';
  });
  document.addEventListener('mousemove', (e) => {
    if (!isDraggingSticky) return;
    const x = e.clientX - stickyOffset.x;
    const y = e.clientY - stickyOffset.y;
    widget.style.left = x + 'px';
    widget.style.top = y + 'px';
    widget.style.right = 'auto';
  });
  document.addEventListener('mouseup', () => {
    isDraggingSticky = false;
    document.body.style.userSelect = '';
  });
}

// --- Resizing ---
document.getElementById('resizeNotesBtn').addEventListener('mousedown', function(e) {
  resizing = true;
  const widget = document.getElementById('stickyNotesWidget');
  widget.classList.add('resizing');
  let startX = e.clientX;
  let startY = e.clientY;
  let startWidth = widget.offsetWidth;
  let startHeight = widget.offsetHeight;
  function onMove(ev) {
    widget.style.width = Math.max(260, startWidth + (ev.clientX - startX)) + 'px';
    widget.style.height = Math.max(120, startHeight + (ev.clientY - startY)) + 'px';
  }
  function onUp() {
    resizing = false;
    widget.classList.remove('resizing');
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
  }
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
});

// --- Notes CRUD ---
function fetchNotes() {
  fetch('/api/notes')
    .then(res => res.json())
    .then(data => {
      notes = data;
      renderNotes();
    });
}

function renderNotes() {
  const notesList = document.getElementById('notesList');
  notesList.innerHTML = '';
  let filtered = notes.filter(note =>
    note.title.toLowerCase().includes(searchQuery) || note.content.toLowerCase().includes(searchQuery)
  );
  if (!filtered.length) {
    notesList.innerHTML = '<div style="color:#aaa;text-align:center;">No notes found.</div>';
    return;
  }
  // Pinned notes first
  filtered.sort((a, b) => (b.pinned || 0) - (a.pinned || 0));
  filtered.forEach(note => {
    const div = document.createElement('div');
    div.className = 'sticky-note-item';
    div.style.background = note.color || '#2c313a';
    div.innerHTML = `
      <div style="display:flex;align-items:center;gap:4px;">
        <button class="sticky-note-pin${note.pinned ? ' pinned' : ''}" title="Pin" onclick="togglePin(${note.id})"><i class="bi bi-pin-angle-fill"></i></button>
        <button class="sticky-note-collapse${note.collapsed ? ' collapsed' : ''}" title="Collapse" onclick="toggleCollapse(${note.id})"><i class="bi bi-chevron-${note.collapsed ? 'down' : 'up'}"></i></button>
        <button class="sticky-note-color" title="Color" onclick="showColorPicker(this, ${note.id})"><i class="bi bi-palette"></i></button>
        <button class="sticky-note-delete" title="Delete" onclick="deleteNote(${note.id})"><i class="bi bi-trash"></i></button>
        <span style="flex:1;"></span>
        <span id="autosave-${note.id}" style="font-size:0.9em;color:#8f8;opacity:0;transition:opacity 0.3s;">Saved</span>
      </div>
      <input class="sticky-note-title" value="${escapeHtml(note.title) || ''}" placeholder="Title..." onchange="updateNote(${note.id}, 'title', this.value)">
      <div class="sticky-color-picker" id="colorPicker-${note.id}" style="display:none;"></div>
      <div class="sticky-note-body" style="display:${note.collapsed ? 'none' : 'block'};">
        <textarea class="sticky-note-content" placeholder="Write a note..." onchange="updateNote(${note.id}, 'content', this.value)">${escapeHtml(note.content)}</textarea>
      </div>
    `;
    notesList.appendChild(div);
  });
}

function escapeHtml(text) {
  if (!text) return '';
  return text.replace(/[&<>"]|'/g, function(m) {
    return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m];
  });
}

function addNote() {
  fetch('/api/notes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'New Note', content: '', color: '#2c313a', pinned: false, collapsed: false })
  })
    .then(res => res.json())
    .then(note => {
      notes.push(note);
      renderNotes();
      showToast('Note created');
    });
}

function updateNote(id, field, value) {
  const note = notes.find(n => n.id === id);
  if (!note) return;
  note[field] = value;
  fetch(`/api/notes/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(note)
  }).then(() => {
    showAutoSave(id);
  });
}

function deleteNote(id) {
  if (!confirm('Delete this note?')) return;
  fetch(`/api/notes/${id}`, { method: 'DELETE' })
    .then(() => {
      notes = notes.filter(n => n.id !== id);
      renderNotes();
      showToast('Note deleted');
    });
}

function togglePin(id) {
  const note = notes.find(n => n.id === id);
  if (!note) return;
  note.pinned = !note.pinned;
  updateNote(id, 'pinned', note.pinned);
  renderNotes();
}

function toggleCollapse(id) {
  const note = notes.find(n => n.id === id);
  if (!note) return;
  note.collapsed = !note.collapsed;
  updateNote(id, 'collapsed', note.collapsed);
  renderNotes();
}

function showColorPicker(btn, id) {
  const picker = document.getElementById(`colorPicker-${id}`);
  if (!picker) return;
  picker.innerHTML = '';
  const colors = ['#2c313a','#ffd700','#ff6b6b','#6bcfff','#b2f296','#f8bbd0','#e1bee7','#d1c4e9','#c5cae9','#bbdefb','#b3e5fc','#b2ebf2','#b2dfdb','#c8e6c9','#dcedc8'];
  colors.forEach(color => {
    const dot = document.createElement('div');
    dot.className = 'sticky-color-dot' + (notes.find(n => n.id === id).color === color ? ' selected' : '');
    dot.style.background = color;
    dot.onclick = () => {
      updateNote(id, 'color', color);
      picker.style.display = 'none';
      renderNotes();
    };
    picker.appendChild(dot);
  });
  picker.style.display = picker.style.display === 'none' ? 'flex' : 'none';
}

function showAutoSave(id) {
  const el = document.getElementById(`autosave-${id}`);
  if (!el) return;
  el.style.opacity = 1;
  setTimeout(() => { el.style.opacity = 0; }, 1200);
}

function showToast(msg) {
  const toast = document.getElementById('stickyToast');
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 1800);
}

function filterNotes() {
  searchQuery = document.getElementById('stickySearch').value.toLowerCase();
  renderNotes();
}

// --- Minimize ---
document.getElementById('minimizeNotesBtn').onclick = function() {
  const widget = document.getElementById('stickyNotesWidget');
  widget.classList.toggle('minimized');
  if (!widget.classList.contains('minimized')) {
    widget.style.height = '540px';
    widget.style.minHeight = '180px';
  }
};

// --- Add Note ---
document.getElementById('addNoteBtn').onclick = addNote;

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
  fetchNotes();
  initStickyDrag();
}); 