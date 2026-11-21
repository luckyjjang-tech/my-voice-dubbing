// Language definitions with national flag emojis
const ALL_LANGUAGES = [
    { code: 'en', name: '영어', engName: 'English', flag: '🇺🇸' },
    { code: 'ja', name: '일본어', engName: 'Japanese', flag: '🇯🇵' },
    { code: 'zh', name: '중국어', engName: 'Chinese', flag: '🇨🇳' },
    { code: 'hi', name: '힌두어', engName: 'Hindi', flag: '🇮🇳' },
    { code: 'ar', name: '아랍어', engName: 'Arabic', flag: '🇸🇦' },
    { code: 'fr', name: '프랑스어', engName: 'French', flag: '🇫🇷' },
    { code: 'de', name: '독일어', engName: 'German', flag: '🇩🇪' },
    { code: 'es', name: '스페인어', engName: 'Spanish', flag: '🇪🇸' },
    { code: 'he', name: '히브리어', engName: 'Hebrew', flag: '🇮🇱' },
    { code: 'tr', name: '튀르키예어', engName: 'Turkish', flag: '🇹🇷' },
    { code: 'ms', name: '말레이어', engName: 'Malay', flag: '🇲🇾' },
];

let selectedLanguages = new Set(ALL_LANGUAGES.map(l => l.code));
let currentJobResult = null;
let currentActiveLang = 'en';

document.addEventListener('DOMContentLoaded', () => {
    initLanguageGrid();
    initSliders();
    initVideoInfoFetcher();
    initDubbingProcess();
});

// 1. Initialize 11 Target Languages Grid
function initLanguageGrid() {
    const grid = document.getElementById('langGrid');
    grid.innerHTML = '';

    ALL_LANGUAGES.forEach(lang => {
        const card = document.createElement('div');
        const isSelected = selectedLanguages.has(lang.code);
        card.id = `lang-card-${lang.code}`;
        card.className = `p-3.5 rounded-xl border cursor-pointer transition-all flex items-center justify-between select-none ${
            isSelected 
                ? 'bg-sky-950/40 border-sky-500/50 text-white shadow-md shadow-sky-500/10' 
                : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:border-slate-700'
        }`;

        card.innerHTML = `
            <div class="flex items-center space-x-2.5">
                <span class="text-xl">${lang.flag}</span>
                <div>
                    <div class="text-xs font-bold">${lang.name}</div>
                    <div class="text-[10px] text-slate-400">${lang.engName}</div>
                </div>
            </div>
            <i class="fa-solid fa-circle-check text-sm ${isSelected ? 'text-sky-400' : 'text-slate-700'}"></i>
        `;

        card.addEventListener('click', () => toggleLanguage(lang.code));
        grid.appendChild(card);
    });

    document.getElementById('selectAllBtn').addEventListener('click', () => {
        ALL_LANGUAGES.forEach(l => selectedLanguages.add(l.code));
        updateLanguageGridUI();
    });

    document.getElementById('deselectAllBtn').addEventListener('click', () => {
        selectedLanguages.clear();
        updateLanguageGridUI();
    });
}

function toggleLanguage(code) {
    if (selectedLanguages.has(code)) {
        selectedLanguages.delete(code);
    } else {
        selectedLanguages.add(code);
    }
    updateLanguageGridUI();
}

function updateLanguageGridUI() {
    ALL_LANGUAGES.forEach(lang => {
        const card = document.getElementById(`lang-card-${lang.code}`);
        const icon = card.querySelector('i');
        const isSelected = selectedLanguages.has(lang.code);

        if (isSelected) {
            card.className = 'p-3.5 rounded-xl border cursor-pointer transition-all flex items-center justify-between select-none bg-sky-950/40 border-sky-500/50 text-white shadow-md shadow-sky-500/10';
            icon.className = 'fa-solid fa-circle-check text-sm text-sky-400';
        } else {
            card.className = 'p-3.5 rounded-xl border cursor-pointer transition-all flex items-center justify-between select-none bg-slate-900/40 border-slate-800 text-slate-400 hover:border-slate-700';
            icon.className = 'fa-solid fa-circle-check text-sm text-slate-700';
        }
    });
}

// 2. Initialize Range Sliders
function initSliders() {
    const startInput = document.getElementById('voiceStartInput');
    const startVal = document.getElementById('voiceStartVal');
    const durInput = document.getElementById('voiceDurInput');
    const durVal = document.getElementById('voiceDurVal');

    startInput.addEventListener('input', (e) => startVal.textContent = e.target.value);
    durInput.addEventListener('input', (e) => durVal.textContent = e.target.value);
}

// 3. YouTube Info Fetcher
function initVideoInfoFetcher() {
    const btn = document.getElementById('fetchInfoBtn');
    const input = document.getElementById('youtubeUrl');
    const card = document.getElementById('videoInfoCard');

    btn.addEventListener('click', async () => {
        const url = input.value.trim();
        if (!url) {
            alert('유튜브 링크를 입력해주세요.');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i><span>조회 중...</span>`;

        try {
            const res = await fetch('/api/video-info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await res.json();

            if (data.success) {
                document.getElementById('videoThumb').src = data.thumbnail;
                document.getElementById('videoTitle').textContent = data.title;
                document.getElementById('videoUploader').querySelector('span').textContent = data.uploader;
                
                const mins = Math.floor(data.duration / 60);
                const secs = data.duration % 60;
                document.getElementById('videoDuration').textContent = `${mins}분 ${secs}초`;

                card.classList.remove('hidden');
            } else {
                alert(data.error || '영상 정보를 불러오지 못했습니다.');
            }
        } catch (err) {
            alert('영상 정보 조회 중 오류가 발생했습니다.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i><span>영상 정보 확인</span>`;
        }
    });
}

// 4. Start Dubbing & Real-time Progress Polling
function initDubbingProcess() {
    const startBtn = document.getElementById('startDubbingBtn');
    const urlInput = document.getElementById('youtubeUrl');
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const stepTitle = document.getElementById('currentStepTitle');
    const logsTerminal = document.getElementById('logsTerminal');

    startBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            alert('유튜브 링크를 입력해주세요.');
            urlInput.focus();
            return;
        }

        if (selectedLanguages.size === 0) {
            alert('최소 1개 이상의 언어를 선택해주세요.');
            return;
        }

        const voiceStart = parseFloat(document.getElementById('voiceStartInput').value);
        const voiceDur = parseFloat(document.getElementById('voiceDurInput').value);

        startBtn.disabled = true;
        startBtn.classList.add('opacity-50', 'cursor-not-allowed');
        progressSection.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        logsTerminal.innerHTML = '<div class="text-sky-400">[시작] 더빙 작업 요청을 전송합니다...</div>';
        progressBar.style.width = '5%';
        progressPercent.textContent = '5%';

        try {
            const res = await fetch('/api/start-dubbing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    target_langs: Array.from(selectedLanguages),
                    voice_start: voiceStart,
                    voice_duration: voiceDur
                })
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || '작업 시작 실패');
            }

            const { job_id } = await res.json();
            pollJobStatus(job_id);

        } catch (err) {
            alert(`오류: ${err.message}`);
            startBtn.disabled = false;
            startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            progressSection.classList.add('hidden');
        }
    });

    async function pollJobStatus(jobId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/job-status/${jobId}`);
                if (!res.ok) return;

                const job = await res.json();
                
                // Update Progress UI
                const pct = Math.max(job.progress, 5);
                progressBar.style.width = `${pct}%`;
                progressPercent.textContent = `${Math.round(pct)}%`;
                stepTitle.textContent = job.status_text;

                // Update Logs Terminal
                if (job.logs && job.logs.length > 0) {
                    logsTerminal.innerHTML = job.logs.map(log => `<div>${log}</div>`).join('');
                    logsTerminal.scrollTop = logsTerminal.scrollHeight;
                }

                if (job.state === 'completed') {
                    clearInterval(interval);
                    startBtn.disabled = false;
                    startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                    renderResults(job.result);
                } else if (job.state === 'failed') {
                    clearInterval(interval);
                    startBtn.disabled = false;
                    startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                    alert(`작업 실패: ${job.error}`);
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 1200);
    }
}

// 5. Render Final Results
function renderResults(result) {
    if (!result) return;
    currentJobResult = result;

    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');

    // Smooth transition
    progressSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');

    // 1. Download ZIP button
    const zipBtn = document.getElementById('downloadAllZipBtn');
    zipBtn.href = result.zip_url;

    // 2. My Voice Sample Audio
    const voiceAudio = document.getElementById('voiceSampleAudio');
    voiceAudio.src = result.voice_sample_url;

    // 3. Korean SRT
    const koSrtBtn = document.getElementById('downloadKoSrt');
    koSrtBtn.href = result.subtitles_ko_url;

    // 4. STT Subtitles Table
    const tableBody = document.getElementById('sttTableBody');
    tableBody.innerHTML = '';
    (result.segments || []).forEach(seg => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-900/60 transition';
        tr.innerHTML = `
            <td class="py-2.5 px-3 text-center text-slate-500 font-mono">${seg.id}</td>
            <td class="py-2.5 px-3 text-sky-400 font-mono font-medium">${seg.start}s ~ ${seg.end}s</td>
            <td class="py-2.5 px-3 text-slate-200">${seg.text}</td>
        `;
        tableBody.appendChild(tr);
    });

    // 5. Build Language Tabs
    const tabsContainer = document.getElementById('resultTabs');
    tabsContainer.innerHTML = '';
    
    const availableLangs = Object.keys(result.languages || {});
    if (availableLangs.length === 0) return;

    availableLangs.forEach((langCode, index) => {
        const langInfo = ALL_LANGUAGES.find(l => l.code === langCode) || { name: langCode, flag: '🌐' };
        const tabBtn = document.createElement('button');
        tabBtn.className = `px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1.5 ${
            index === 0
                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/20'
                : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
        }`;
        tabBtn.innerHTML = `<span>${langInfo.flag}</span><span>${langInfo.name}</span>`;
        tabBtn.addEventListener('click', () => switchLanguageTab(langCode, tabBtn));
        tabsContainer.appendChild(tabBtn);
    });

    // Select first tab
    switchLanguageTab(availableLangs[0], tabsContainer.children[0]);
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function switchLanguageTab(langCode, activeBtn) {
    if (!currentJobResult || !currentJobResult.languages[langCode]) return;
    currentActiveLang = langCode;

    // Highlight button
    const tabsContainer = document.getElementById('resultTabs');
    Array.from(tabsContainer.children).forEach(btn => {
        btn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1.5 bg-slate-900 text-slate-400 hover:text-white border border-slate-800';
    });
    activeBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1.5 bg-sky-500 text-white shadow-md shadow-sky-500/20';

    const langData = currentJobResult.languages[langCode];

    // Audio
    const audioEl = document.getElementById('activeLangAudio');
    audioEl.src = langData.audio_url;
    document.getElementById('downloadLangAudio').href = langData.audio_url;

    // Script text
    document.getElementById('activeLangText').textContent = langData.translated_text || '';

    // Video
    const videoEl = document.getElementById('activeLangVideo');
    if (langData.video_url) {
        videoEl.src = langData.video_url;
        videoEl.parentElement.classList.remove('hidden');
        document.getElementById('downloadLangVideo').href = langData.video_url;
    } else {
        videoEl.parentElement.classList.add('hidden');
    }
}

