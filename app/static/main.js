const form = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const progressBar = document.getElementById('progressBar');
const progressBarFill = document.getElementById('progressBarFill');
const uploadStatus = document.getElementById('uploadStatus');
let jobId = null;

// Guarda a lista atual de highlights na página
let lastHighlights = [];
let hideBarTimeout = null;

form.addEventListener('submit', function(e) {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);

    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            progressBar.style.display = '';
            progressBarFill.style.width = percent + '%';
            progressBarFill.textContent = percent + '%';
            // Limpa timeout (se alguém resetar upload, timeout some)
            if (hideBarTimeout) clearTimeout(hideBarTimeout);
        }
    };

    xhr.onload = function() {
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            jobId = response.id;
            uploadStatus.innerHTML = '<b>Upload concluído! Processando...</b>';
            progressBarFill.textContent = '100%';
            progressBarFill.style.width = '100%';
            // Esconde barra de progresso depois de 5s
            hideBarTimeout = setTimeout(() => {
                progressBar.style.display = 'none';
            }, 5000);
            lastHighlights = []; // limpa highlights, pois começará novo job
            pollStatus();
        } else {
            uploadStatus.innerHTML = '<b style="color:red;">Erro ao enviar o arquivo.</b>';
        }
    };

    xhr.onerror = function() {
        uploadStatus.innerHTML = '<b style="color:red;">Erro ao enviar o arquivo.</b>';
    };

    progressBar.style.display = '';
    progressBarFill.style.width = '0%';
    progressBarFill.textContent = '0%';
    uploadStatus.innerHTML = '';

    if (hideBarTimeout) clearTimeout(hideBarTimeout);

    xhr.send(formData);
});

function pollStatus() {
    if (!jobId) return;
    fetch(`/status/${jobId}`)
        .then(res => res.json())
        .then(status => {
            uploadStatus.innerHTML = "<b>" + status.step + "</b>";

            // Progress bar lógica
            let corteMatch = null;
            if (
                status.step &&
                (corteMatch = status.step.match(/Cortando vídeo \((\d+)\/(\d+)\)/))
            ) {
                // Estamos cortando vídeos (ex: "Cortando vídeo (3/10)...")
                let atual = parseInt(corteMatch[1], 10);
                let total = parseInt(corteMatch[2], 10);
                let percent = Math.round((atual - 1) / total * 100);
                if (percent < 0) percent = 0;
                if (percent > 100) percent = 100;
                progressBar.style.display = '';
                progressBarFill.style.width = percent + '%';
                progressBarFill.textContent = percent + '%';
                if (hideBarTimeout) clearTimeout(hideBarTimeout);
            } else if (
                status.step &&
                status.step.startsWith("Upload")
            ) {
                // Upload ainda, não faz nada, deixa o onprogress cuidar
            } else {
                // Em outras etapas, oculta a barra
                progressBar.style.display = 'none';
            }

            // Verifica se a lista mudou (só re-renderiza se mudou)
            if (!arraysEqual(status.highlights || [], lastHighlights)) {
                renderHighlights(status.highlights || []);
                lastHighlights = [...(status.highlights || [])];
            }

            if (status.progress < 100 && status.step !== "Concluído") {
                setTimeout(pollStatus, 1500);
            } else {
                uploadStatus.innerHTML = "<b>Processamento concluído!</b>";
                setTimeout(() => window.location.reload(), 1200);
            }
        });
}

// Função para comparar arrays simples
function arraysEqual(a, b) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
        if (a[i] !== b[i]) return false;
    }
    return true;
}

// Renderiza os highlights
function renderHighlights(files) {
    const grid = document.querySelector("#highlightsGrid");
    if (!grid) return;
    grid.innerHTML = "";
    files.forEach(f => {
        grid.innerHTML += `
          <div class="bg-white rounded shadow p-3 flex flex-col items-center border w-full max-w-[560px]">
            <a class="text-blue-700 font-semibold underline break-all mb-2 text-center text-xs" href="/download/${f}" download>${f}</a>
            <video class="rounded w-full" style="max-width:540px" controls>
                <source src="/download/${f}" type="video/mp4">
                Seu navegador não suporta vídeo.
            </video>
          </div>
        `;
    });
}
