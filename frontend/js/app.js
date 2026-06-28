const API = "http://localhost:8000/api";

// --- Auth state ---
let token = sessionStorage.getItem("token") || null;
let currentUser = null;
let currentCareerId = null;
let parsedSubjects = null;
let parsedFacultyName = "";

// --- Toast system ---
function toast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const t = document.createElement("div");
    t.className = `toast toast-${type}`;
    t.innerHTML = `<span>${message}</span><span class="toast-close">&times;</span>`;
    t.querySelector(".toast-close").onclick = () => t.remove();
    container.appendChild(t);
    setTimeout(() => {
        t.style.opacity = "0";
        t.style.transform = "translateX(40px)";
        t.style.transition = "all 0.3s";
        setTimeout(() => t.remove(), 300);
    }, 5000);
}

// --- API fetch with auth ---
async function apiFetch(url, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
    };
    const res = await fetch(`${API}${url}`, {
        ...options,
        headers,
    });
    if (res.status === 401 || res.status === 403) {
        sessionStorage.removeItem("token");
        token = null;
        currentUser = null;
        showAuth();
        throw new Error(res.status === 401 ? "Sesión expirada. Iniciá sesión de nuevo." : "No tenés permisos");
    }
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
    }
    return res.json();
}

function setLoading(btn, loading) {
    if (loading) {
        btn.disabled = true;
        btn.dataset.origText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner"></span>';
    } else {
        btn.disabled = false;
        btn.innerHTML = btn.dataset.origText || btn.innerHTML;
    }
}

// --- Auth UI ---
function showAuth() {
    document.getElementById("auth-screen").classList.remove("hidden");
    document.getElementById("main-app").classList.add("hidden");
    document.querySelectorAll(".auth-tab").forEach((t) => t.classList.remove("active"));
    document.querySelector('.auth-tab[data-auth="login"]').classList.add("active");
    document.getElementById("auth-login").classList.remove("hidden");
    document.getElementById("auth-register").classList.add("hidden");
}

function showApp() {
    document.getElementById("auth-screen").classList.add("hidden");
    document.getElementById("main-app").classList.remove("hidden");
    if (currentUser) {
        const badge = document.getElementById("user-badge");
        const roleText = currentUser.role === "admin" ? "admin" : "user";
        badge.innerHTML = `${currentUser.username} <span class="role-badge role-${currentUser.role}">${roleText}</span>`;
        badge.classList.remove("hidden");
        document.getElementById("btn-logout").classList.remove("hidden");
    }
}

async function tryRestoreSession() {
    if (!token) return false;
    try {
        const user = await apiFetch("/auth/me");
        currentUser = user;
        showApp();
        loadCareerList();
        return true;
    } catch {
        sessionStorage.removeItem("token");
        token = null;
        return false;
    }
}

// --- Auth tabs ---
document.querySelectorAll(".auth-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".auth-tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        const method = tab.dataset.auth;
        document.getElementById("auth-login").classList.toggle("hidden", method !== "login");
        document.getElementById("auth-register").classList.toggle("hidden", method !== "register");
    });
});

// --- Enter key navigation ---
document.getElementById("login-username").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        document.getElementById("login-password").focus();
    }
});
document.getElementById("login-password").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        document.getElementById("btn-login").click();
    }
});
document.getElementById("register-username").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        document.getElementById("register-password").focus();
    }
});
document.getElementById("register-password").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        document.getElementById("btn-register").click();
    }
});

// --- Login ---
document.getElementById("btn-login").addEventListener("click", async () => {
    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value;
    if (!username || !password) {
        toast("Completá usuario y contraseña", "warning");
        return;
    }
    setLoading(document.getElementById("btn-login"), true);
    try {
        const res = await fetch(`${API}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Error al iniciar sesión");
        }
        const data = await res.json();
        token = data.token;
        currentUser = { id: data.user_id, username: data.username, role: data.role };
        sessionStorage.setItem("token", token);
        document.getElementById("login-username").value = "";
        document.getElementById("login-password").value = "";
        showApp();
        loadCareerList();
        toast(`Bienvenido, ${data.username}`, "success");
    } catch (e) {
        toast("Error: " + e.message, "error");
    } finally {
        setLoading(document.getElementById("btn-login"), false);
    }
});

// --- Register ---
document.getElementById("btn-register").addEventListener("click", async () => {
    const username = document.getElementById("register-username").value.trim();
    const password = document.getElementById("register-password").value;
    if (!username || !password) {
        toast("Completá usuario y contraseña", "warning");
        return;
    }
    if (password.length < 4) {
        toast("La contraseña debe tener al menos 4 caracteres", "warning");
        return;
    }
    setLoading(document.getElementById("btn-register"), true);
    try {
        const res = await fetch(`${API}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Error al registrarse");
        }
        const data = await res.json();
        token = data.token;
        currentUser = { id: data.user_id, username: data.username, role: data.role };
        sessionStorage.setItem("token", token);
        document.getElementById("register-username").value = "";
        document.getElementById("register-password").value = "";
        showApp();
        loadCareerList();
        const msg = data.role === "admin" ? "Cuenta admin creada (primer usuario)" : "Cuenta creada correctamente";
        toast(msg, "success");
    } catch (e) {
        toast("Error: " + e.message, "error");
    } finally {
        setLoading(document.getElementById("btn-register"), false);
    }
});

// --- Logout ---
document.getElementById("btn-logout").addEventListener("click", () => {
    sessionStorage.removeItem("token");
    token = null;
    currentUser = null;
    currentCareerId = null;
    parsedSubjects = null;
    document.getElementById("step-upload").classList.add("hidden");
    document.getElementById("step-manage").classList.add("hidden");
    document.getElementById("step-progress").classList.add("hidden");
    showAuth();
    toast("Sesión cerrada", "info");
});

// --- DOM refs ---
const careerSelect = document.getElementById("career-select");
const btnLoadCareer = document.getElementById("btn-load-career");
const btnCreateCareer = document.getElementById("btn-create-career");
const careerNameInput = document.getElementById("career-name");
const careerSearch = document.getElementById("career-search");
const careerSearchEmpty = document.getElementById("career-search-empty");
const stepUpload = document.getElementById("step-upload");
const stepManage = document.getElementById("step-manage");
const stepProgress = document.getElementById("step-progress");

// --- State ---
let allCareers = [];

// Method tabs
const methodTabs = document.querySelectorAll(".method-tab");
const methodPanels = {
    pdf: document.getElementById("method-pdf"),
    text: document.getElementById("method-text"),
    manual: document.getElementById("method-manual"),
};

const pdfInput = document.getElementById("pdf-input");
const btnUploadPdf = document.getElementById("btn-upload-pdf");
const pdfStatus = document.getElementById("pdf-status");

const textInput = document.getElementById("text-input");
const btnParseText = document.getElementById("btn-parse-text");
const textStatus = document.getElementById("text-status");

const jsonInput = document.getElementById("json-input");
const btnUploadJson = document.getElementById("btn-upload-json");
const subjName = document.getElementById("subj-name");
const subjYear = document.getElementById("subj-year");
const subjSemester = document.getElementById("subj-semester");
const subjPrereqs = document.getElementById("subj-prereqs");
const btnAddSubject = document.getElementById("btn-add-subject");

const pdfPreviewSection = document.getElementById("pdf-preview-section");
const pdfPreviewTable = document.getElementById("pdf-preview-table");
const btnConfirmPdf = document.getElementById("btn-confirm-pdf");
const btnCancelPdf = document.getElementById("btn-cancel-pdf");

const subjectsContainer = document.getElementById("subjects-container");
const progressContainer = document.getElementById("progress-container");

// --- Method tabs ---
methodTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
        methodTabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        const method = tab.dataset.method;
        Object.entries(methodPanels).forEach(([key, panel]) => {
            panel.classList.toggle("hidden", key !== method);
        });
        pdfPreviewSection.classList.add("hidden");
        pdfStatus.innerHTML = "";
        textStatus.innerHTML = "";
    });
});

// --- Career management ---
function filterCareerList(query) {
    const q = query.toLowerCase().trim();
    careerSelect.innerHTML =
        '<option value="">Seleccionar carrera existente...</option>';
    const filtered = allCareers.filter((c) =>
        c.name.toLowerCase().includes(q) ||
        (c.faculty_name && c.faculty_name.toLowerCase().includes(q))
    );
    filtered.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.id;
        const faculty = c.faculty_name ? ` [${c.faculty_name}]` : "";
        opt.textContent = c.name + faculty;
        careerSelect.appendChild(opt);
    });
    careerSearchEmpty.classList.toggle("hidden", filtered.length > 0 || !query);
}

async function loadCareerList() {
    try {
        allCareers = await apiFetch("/careers");
        filterCareerList(careerSearch.value);
    } catch (e) {
        toast("Error al cargar carreras: " + e.message, "error");
    }
}

careerSearch.addEventListener("input", () => {
    filterCareerList(careerSearch.value);
});

btnCreateCareer.addEventListener("click", async () => {
    const name = careerNameInput.value.trim();
    if (!name) {
        toast("Ingresá un nombre para la carrera", "warning");
        return;
    }
    setLoading(btnCreateCareer, true);
    try {
        const career = await apiFetch("/careers", {
            method: "POST",
            body: JSON.stringify({ name, faculty_name: "" }),
        });
        careerNameInput.value = "";
        await loadCareerList();
        currentCareerId = career.id;
        careerSelect.value = career.id;
        afterCareerLoaded(career);
        toast(`Carrera "${name}" creada`, "success");
    } catch (e) {
        toast("Error al crear carrera: " + e.message, "error");
    } finally {
        setLoading(btnCreateCareer, false);
    }
});

btnLoadCareer.addEventListener("click", async () => {
    const id = parseInt(careerSelect.value);
    if (!id) {
        toast("Seleccioná una carrera", "warning");
        return;
    }
    setLoading(btnLoadCareer, true);
    try {
        const career = await apiFetch(`/careers/${id}`);
        currentCareerId = id;
        afterCareerLoaded(career);
        toast(`Carrera "${career.name}" cargada`, "success");
    } catch (e) {
        toast("Error al cargar carrera: " + e.message, "error");
    } finally {
        setLoading(btnLoadCareer, false);
    }
});

function afterCareerLoaded(career) {
    stepUpload.classList.remove("hidden");
    stepManage.classList.remove("hidden");
    stepProgress.classList.remove("hidden");
    renderSubjects(career.subjects);
    renderProgress(currentCareerId);
}

// --- PDF upload ---
btnUploadPdf.addEventListener("click", async () => {
    if (!currentCareerId) {
        toast("Primero seleccioná o creá una carrera", "warning");
        return;
    }
    const file = pdfInput.files[0];
    if (!file) {
        toast("Seleccioná un archivo PDF", "warning");
        return;
    }

    setLoading(btnUploadPdf, true);
    pdfStatus.innerHTML = '<div class="alert alert-info">Procesando PDF...</div>';

    const formData = new FormData();
    formData.append("file", file);

    try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const res = await fetch(`${API}/parse-pdf`, {
            method: "POST",
            headers,
            body: formData,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Error ${res.status}`);
        }
        const data = await res.json();
        parsedSubjects = data.subjects;
        parsedFacultyName = data.faculty_name || "";

        if (!parsedSubjects || parsedSubjects.length === 0) {
            let html = '<div class="alert alert-warning">';
            html += "<strong>No se pudieron detectar materias.</strong> El formato del PDF puede no ser compatible.";
            html += " Probá con la opción <strong>Texto</strong> o <strong>Manual</strong>.";
            html += "</div>";
            if (data.raw_text) {
                html += `<button class="raw-text-toggle" onclick="this.nextElementSibling.classList.toggle('hidden')">Ver texto extraído del PDF</button>`;
                html += `<pre class="raw-text-block hidden">${escapeHtml(data.raw_text)}</pre>`;
            }
            pdfStatus.innerHTML = html;
            pdfPreviewSection.classList.add("hidden");
            return;
        }

        pdfStatus.innerHTML = `<div class="alert alert-success"><strong>${parsedSubjects.length} materias detectadas.</strong> Revisá y confirmá abajo.</div>`;
        renderPdfPreview(parsedSubjects);
        pdfPreviewSection.classList.remove("hidden");
        toast(`${parsedSubjects.length} materias detectadas en el PDF`, "success");
    } catch (e) {
        pdfStatus.innerHTML = `<div class="alert alert-error"><strong>Error:</strong> ${e.message}</div>`;
        toast("Error al procesar PDF: " + e.message, "error");
    } finally {
        setLoading(btnUploadPdf, false);
    }
});

// --- Text parse ---
btnParseText.addEventListener("click", async () => {
    if (!currentCareerId) {
        toast("Primero seleccioná o creá una carrera", "warning");
        return;
    }
    const text = textInput.value.trim();
    if (!text) {
        toast("Pegá el texto del plan de estudios", "warning");
        return;
    }

    setLoading(btnParseText, true);
    textStatus.innerHTML = '<div class="alert alert-info">Procesando texto...</div>';

    try {
        const data = await apiFetch("/parse-text", {
            method: "POST",
            body: JSON.stringify({ text }),
        });
        parsedSubjects = data.subjects;
        parsedFacultyName = data.faculty_name || "";

        if (!parsedSubjects || parsedSubjects.length === 0) {
            textStatus.innerHTML = '<div class="alert alert-warning"><strong>No se pudieron detectar materias.</strong> Revisá que el texto tenga el formato correcto.</div>';
            pdfPreviewSection.classList.add("hidden");
            return;
        }

        textStatus.innerHTML = `<div class="alert alert-success"><strong>${parsedSubjects.length} materias detectadas.</strong> Revisá y confirmá abajo.</div>`;
        renderPdfPreview(parsedSubjects);
        pdfPreviewSection.classList.remove("hidden");
        toast(`${parsedSubjects.length} materias detectadas del texto`, "success");
    } catch (e) {
        textStatus.innerHTML = `<div class="alert alert-error"><strong>Error:</strong> ${e.message}</div>`;
        toast("Error al parsear texto: " + e.message, "error");
    } finally {
        setLoading(btnParseText, false);
    }
});

// --- Preview ---
function renderPdfPreview(subjects) {
    let html = `<table class="preview-table">
        <thead><tr>
            <th>Materia</th>
            <th style="width:60px">Año</th>
            <th style="width:70px">Sem.</th>
            <th>Correlativas</th>
        </tr></thead><tbody>`;
    subjects.forEach((s, i) => {
        html += `<tr>
            <td><input type="text" class="name-input" data-idx="${i}" value="${escapeHtml(s.name)}"></td>
            <td><input type="number" class="year-input" data-idx="${i}" value="${s.year}" min="1"></td>
            <td><input type="number" class="sem-input" data-idx="${i}" value="${s.semester}" min="1" max="2"></td>
            <td><input type="text" class="prereq-input" data-idx="${i}" value="${escapeHtml((s.prerequisites || []).join(", "))}"></td>
        </tr>`;
    });
    html += "</tbody></table>";
    pdfPreviewTable.innerHTML = html;
}

function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
}

function getEditedParsedSubjects() {
    return parsedSubjects.map((s, i) => {
        const nameInput = document.querySelector(`.name-input[data-idx="${i}"]`);
        const yearInput = document.querySelector(`.year-input[data-idx="${i}"]`);
        const semInput = document.querySelector(`.sem-input[data-idx="${i}"]`);
        const prereqInput = document.querySelector(`.prereq-input[data-idx="${i}"]`);
        return {
            name: nameInput ? nameInput.value.trim() : s.name,
            year: yearInput ? parseInt(yearInput.value) || s.year : s.year,
            semester: semInput ? parseInt(semInput.value) || s.semester : s.semester,
            prerequisites: prereqInput
                ? prereqInput.value.split(",").map((p) => p.trim()).filter(Boolean)
                : s.prerequisites,
        };
    });
}

btnConfirmPdf.addEventListener("click", async () => {
    if (!currentCareerId) return;
    const subjects = getEditedParsedSubjects();
    if (subjects.length === 0) {
        toast("No hay materias para guardar", "warning");
        return;
    }

    setLoading(btnConfirmPdf, true);
    try {
        const career = await apiFetch(`/careers/${currentCareerId}/subjects`, {
            method: "POST",
            body: JSON.stringify({ name: "", faculty_name: parsedFacultyName, subjects }),
        });
        parsedSubjects = null;
        parsedFacultyName = "";
        pdfPreviewSection.classList.add("hidden");
        pdfStatus.innerHTML = `<div class="alert alert-success"><strong>${subjects.length} materias guardadas correctamente.</strong></div>`;
        textStatus.innerHTML = "";
        pdfInput.value = "";
        textInput.value = "";
        afterCareerLoaded(career);
        toast(`${subjects.length} materias guardadas`, "success");
    } catch (e) {
        toast("Error al guardar: " + e.message, "error");
    } finally {
        setLoading(btnConfirmPdf, false);
    }
});

btnCancelPdf.addEventListener("click", () => {
    parsedSubjects = null;
    parsedFacultyName = "";
    pdfPreviewSection.classList.add("hidden");
    pdfStatus.innerHTML = "";
    textStatus.innerHTML = "";
});

// --- JSON upload ---
btnUploadJson.addEventListener("click", async () => {
    if (!currentCareerId) {
        toast("Primero seleccioná o creá una carrera", "warning");
        return;
    }
    let data;
    try {
        data = JSON.parse(jsonInput.value);
    } catch {
        toast("JSON inválido. Revisá el formato.", "error");
        return;
    }
    if (!Array.isArray(data)) {
        toast("El JSON debe ser un array de materias", "error");
        return;
    }

    setLoading(btnUploadJson, true);
    try {
        const career = await apiFetch(`/careers/${currentCareerId}/subjects`, {
            method: "POST",
            body: JSON.stringify({ name: "", faculty_name: "", subjects: data }),
        });
        jsonInput.value = "";
        afterCareerLoaded(career);
        toast(`${data.length} materias cargadas desde JSON`, "success");
    } catch (e) {
        toast("Error al cargar JSON: " + e.message, "error");
    } finally {
        setLoading(btnUploadJson, false);
    }
});

// --- Manual subject ---
btnAddSubject.addEventListener("click", async () => {
    if (!currentCareerId) {
        toast("Primero seleccioná o creá una carrera", "warning");
        return;
    }
    const name = subjName.value.trim();
    const year = parseInt(subjYear.value);
    const semester = parseInt(subjSemester.value);
    if (!name || !year || !semester) {
        toast("Completá nombre, año y semestre", "warning");
        return;
    }

    const prereqs = subjPrereqs.value
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

    setLoading(btnAddSubject, true);
    try {
        const career = await apiFetch(`/careers/${currentCareerId}/subjects`, {
            method: "POST",
            body: JSON.stringify({
                name: "",
                subjects: [{ name, year, semester, prerequisites: prereqs }],
            }),
        });
        subjName.value = "";
        subjYear.value = "";
        subjSemester.value = "";
        subjPrereqs.value = "";
        afterCareerLoaded(career);
        toast(`"${name}" agregada`, "success");
    } catch (e) {
        toast("Error al agregar materia: " + e.message, "error");
    } finally {
        setLoading(btnAddSubject, false);
    }
});

// --- Prerequisite availability ---
function computeAvailability(subjects) {
    const statusMap = {};
    subjects.forEach((s) => { statusMap[s.name] = s.status; });

    const result = [];
    for (const s of subjects) {
        const blockedBy = s.prerequisites.filter(
            (pr) => statusMap[pr] !== "aprobado" && statusMap[pr] !== "promocionado"
        );
        result.push({ ...s, available: blockedBy.length === 0, blockedBy });
    }
    return result;
}

// --- Render subjects ---
function renderSubjects(subjects) {
    if (!subjects || subjects.length === 0) {
        subjectsContainer.innerHTML =
            '<p class="help">No hay materias cargadas aún. Usá la sección de arriba para cargar el plan de estudios.</p>';
        return;
    }

    const enriched = computeAvailability(subjects);

    const byYear = {};
    enriched.forEach((s) => {
        const key = `Año ${s.year}`;
        if (!byYear[key]) byYear[key] = [];
        byYear[key].push(s);
    });

    const statusLabels = {
        no_cursada: "No cursada",
        cursando: "Cursando",
        regular: "Regular",
        aprobado: "Aprobado",
        promocionado: "Promocionado",
    };

    let html = "";
    for (const [year, subs] of Object.entries(byYear)) {
        html += `<div class="year-section"><h3>${year}</h3><div class="subjects-grid">`;
        subs.forEach((s) => {
            const prereqText =
                s.prerequisites.length > 0
                    ? `📎 ${s.prerequisites.join(", ")}`
                    : "Sin correlativas";
            const locked = !s.available && s.status === "no_cursada";
            const lockIcon = locked ? '<span class="lock-icon" title="Correlativas pendientes">🔒</span>' : "";
            const disabled = locked ? "disabled" : "";
            const blockedHint =
                !s.available && s.status === "no_cursada"
                    ? `<div class="blocked-hint">Requiere: ${s.blockedBy.join(", ")}</div>`
                    : "";

            html += `
                <div class="subject-card ${s.status} ${locked ? "locked" : ""}" data-id="${s.id}">
                    <div class="name">${lockIcon} ${escapeHtml(s.name)}</div>
                    <div class="meta">${year} · Semestre ${s.semester}</div>
                    <div class="prereqs">${prereqText}</div>
                    ${blockedHint}
                    <select class="status-select" data-id="${s.id}" ${disabled}>
                        ${Object.entries(statusLabels)
                            .map(([val, label]) =>
                                `<option value="${val}" ${s.status === val ? "selected" : ""}>${label}</option>`
                            )
                            .join("")}
                    </select>
                </div>`;
        });
        html += "</div></div>";
    }
    subjectsContainer.innerHTML = html;

    document.querySelectorAll(".status-select").forEach((sel) => {
        sel.addEventListener("change", async (e) => {
            const id = parseInt(e.target.dataset.id);
            const status = e.target.value;
            const card = e.target.closest(".subject-card");

            if (card.classList.contains("locked") && status !== "no_cursada") {
                const name = card.querySelector(".name").textContent.trim();
                if (!confirm(`"${name}" tiene correlativas pendientes. ¿Estás seguro de que querés cambiar su estado?`)) {
                    e.target.value = "no_cursada";
                    return;
                }
            }

            card.className = `subject-card ${status}`;
            try {
                await apiFetch(`/subjects/${id}`, {
                    method: "PUT",
                    body: JSON.stringify({ status }),
                });
                const career = await apiFetch(`/careers/${currentCareerId}`);
                renderProgress(currentCareerId);
                renderSubjects(career.subjects);
            } catch (err) {
                toast("Error al actualizar estado: " + err.message, "error");
            }
        });
    });
}

// --- Render progress ---
async function renderProgress(careerId) {
    if (!careerId) {
        progressContainer.innerHTML = "";
        return;
    }
    try {
        const p = await apiFetch(`/careers/${careerId}/progress`);
        const barWidth = Math.max(p.progress_percentage, 4);

        let html = `
            <div class="progress-stats">
                <div class="stat-card promocionado">
                    <div class="number">${p.promocionado}</div>
                    <div class="label">Promocionado</div>
                </div>
                <div class="stat-card aprobado">
                    <div class="number">${p.aprobado}</div>
                    <div class="label">Aprobado</div>
                </div>
                <div class="stat-card regular">
                    <div class="number">${p.regular}</div>
                    <div class="label">Regular</div>
                </div>
                <div class="stat-card cursando">
                    <div class="number">${p.cursando}</div>
                    <div class="label">Cursando</div>
                </div>
                <div class="stat-card no_cursada">
                    <div class="number">${p.no_cursada}</div>
                    <div class="label">No cursada</div>
                </div>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar-fill" style="width: ${barWidth}%"></div>
                <div class="progress-bar-text">${p.progress_percentage}%</div>
            </div>
            <div class="progress-summary">
                ${p.aprobado + p.promocionado} de ${p.total_subjects} materias aprobadas
            </div>
            <hr>
            <h3>Avance por año</h3>`;

        for (const [year, data] of Object.entries(p.subjects_by_year)) {
            const pct =
                data.total > 0
                    ? Math.round((data.aprobadas / data.total) * 100)
                    : 0;
            const w = Math.max(pct, 4);
            html += `
                <div class="year-section">
                    <h4>Año ${year}</h4>
                    <div class="year-bar-container">
                        <div class="year-bar-fill" style="width: ${w}%"></div>
                        <div class="year-bar-text">${data.aprobadas}/${data.total} (${pct}%)</div>
                    </div>
                </div>`;
        }

        progressContainer.innerHTML = html;
    } catch (e) {
        progressContainer.innerHTML = `<div class="alert alert-error">Error al cargar progreso: ${e.message}</div>`;
    }
}

// --- Init ---
(async function init() {
    const restored = await tryRestoreSession();
    if (!restored) {
        showAuth();
    }
})();
