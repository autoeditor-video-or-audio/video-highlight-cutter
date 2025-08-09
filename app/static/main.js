const fileInput = document.getElementById('fileInput');
const fileNameSpan = document.getElementById('file-name');
const videoPreview = document.getElementById('videoPreview');
const dropZone = document.getElementById('dropZone');
const sendBtn = document.getElementById('sendBtn');

const dhPromptSelect = document.getElementById('dhPromptSelect');
const useDhCustom = document.getElementById('useDhCustom');
const dhCustomText = document.getElementById('dhCustomText');
const viewPromptBtn = document.getElementById('viewPromptBtn');
const progressBar = document.getElementById('progressBar');
const progressBarFill = document.getElementById('progressBarFill');
const uploadStatus = document.getElementById('uploadStatus');

let jobId = null;
let lastHighlights = [];

// Drag & Drop
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('bg-blueglow', 'text-navy');
});
dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('bg-blueglow', 'text-navy');
});
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('bg-blueglow', 'text-navy');
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    handleFile(fileInput.files[0]);
  }
});
fileInput.addEventListener('change', () => {
  if (fileInput.files.length) handleFile(fileInput.files[0]);
});

function handleFile(file) {
  if (!file.name.endsWith('.mp4')) {
    alert('Somente arquivos .mp4 são permitidos');
    return;
  }
  fileNameSpan.textContent = file.name;
  videoPreview.src = URL.createObjectURL(file);
  videoPreview.classList.remove('hidden');
  checkFormReady();
}

// Carregar prompts
async function loadPrompts() {
  const res = await fetch('/api/prompts/detect_highlight');
  const data = await res.json();
  dhPromptSelect.innerHTML = '';
  if (!data.items?.length) {
    dhPromptSelect.innerHTML = '<option value="">Nenhum prompt</option>';
    return;
  }
  data.items.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.name;
    opt.textContent = p.label || p.name;
    dhPromptSelect.appendChild(opt);
  });
  checkFormReady();
}
loadPrompts();

function checkFormReady() {
  if (fileInput.files.length > 0 && (dhPromptSelect.value || (useDhCustom.checked && dhCustomText.value.trim()))) {
    sendBtn.disabled = false;
    sendBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  } else {
    sendBtn.disabled = true;
    sendBtn.classList.add('opacity-50', 'cursor-not-allowed');
  }
}

dhPromptSelect.addEventListener('change', checkFormReady);
useDhCustom.addEventListener('change', () => {
  dhCustomText.style.display = useDhCustom.checked ? 'block' : 'none';
  checkFormReady();
});
dhCustomText.addEventListener('input', checkFormReady);

viewPromptBtn.addEventListener('click', async () => {
  const name = dhPromptSelect.value;
  if (!name) return;
  const res = await fetch(`/api/prompts/detect_highlight/${encodeURIComponent(name)}`);
  const data = await res.json();
  if (data?.content) {
    dhCustomText.value = data.content;
    dhCustomText.style.display = 'block';
    useDhCustom.checked = true;
    checkFormReady();
  }
});

// Upload
document.getElementById('uploadForm').addEventListener('submit', (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append('file', file);
  if (useDhCustom.checked && dhCustomText.value.trim()) {
    formData.append('prompt_text', dhCustomText.value.trim());
  } else {
    formData.append('prompt_name', dhPromptSelect.value);
  }

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/upload', true);

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const percent = Math.round((e.loaded / e.total) * 100);
      progressBar.classList.remove('hidden');
      progressBarFill.style.width = percent + '%';
      progressBarFill.textContent = percent + '%';
    }
  };

  xhr.onload = () => {
    if (xhr.status === 200) {
      const response = JSON.parse(xhr.responseText);
      jobId = response.id;
      uploadStatus.innerHTML = '<b>Upload concluído! Processando...</b>';
      progressBarFill.style.width = '100%';
      progressBarFill.textContent = '100%';
      pollStatus();
    } else {
      uploadStatus.innerHTML = '<b style="color:red;">Erro no upload</b>';
    }
  };
  xhr.send(formData);
});

function pollStatus() {
  if (!jobId) return;
  fetch(`/status/${jobId}`)
    .then(res => res.json())
    .then(status => {
      uploadStatus.innerHTML = `<b>${status.step}</b>`;

      if (status.progress > 0 && status.progress <= 100) {
        progressBar.classList.remove('hidden');
        progressBarFill.style.width = status.progress + '%';
        progressBarFill.textContent = status.progress + '%';
      }

      if (JSON.stringify(status.highlights) !== JSON.stringify(lastHighlights)) {
        renderHighlights(status.highlights);
        lastHighlights = status.highlights;
      }

      if (status.progress < 100 && status.step !== "Concluído") {
        setTimeout(pollStatus, 1500);
      } else {
        uploadStatus.innerHTML = "<b>Processamento concluído!</b>";
        setTimeout(() => window.location.reload(), 1200);
      }
    });
}

function renderHighlights(files) {
  const grid = document.getElementById('highlightsGrid');
  grid.innerHTML = '';
  files.forEach(f => {
    grid.innerHTML += `
      <div class="relative border-2 border-darkborder bg-darkcontainer rounded-xl p-4 flex flex-col items-center w-full">
        <a class="text-blue-400 font-semibold underline hover:text-blueglow block text-center break-all text-sm mb-2"
          href="/download/${f}" download>${f}</a>
        <video class="w-full rounded" style="aspect-ratio: 16 / 9; height:auto;" controls>
          <source src="/download/${f}" type="video/mp4">
        </video>
      </div>
    `;
  });
}
