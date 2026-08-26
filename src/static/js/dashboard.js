// MEDINTEL CLINICAL INTELLIGENCE DASHBOARD CONTROLLER

let activeRole = "Clinician";
let activeUserName = "Dr. Sarah Sterling";
let allPatientsData = [];
let riskChartInstance = null;
let trendChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
    initDashboard();
});

function getAuthHeaders() {
    return {
        "Content-Type": "application/json",
        "X-User-Role": activeRole,
        "X-User-Name": activeUserName
    };
}

function onRoleChange() {
    const sel = document.getElementById("roleSelect");
    activeRole = sel.value;
    if (activeRole === "Clinician") activeUserName = "Dr. Sarah Sterling";
    else if (activeRole === "Admin") activeUserName = "System Administrator";
    else activeUserName = "Data Science Analyst";

    console.log(`[Security] Active Role set to: ${activeRole}`);
    loadDashboardStats();
    loadPatients();
    loadAuditLogs();
}

function switchTab(tabId) {
    document.querySelectorAll(".nav-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));

    const btn = document.getElementById(`btn-tab-${tabId}`);
    if (btn) btn.classList.add("active");

    const pane = document.getElementById(`tab-${tabId}`);
    if (pane) pane.classList.add("active");

    if (tabId === 'dashboard') loadDashboardStats();
    if (tabId === 'patients') loadPatients();
    if (tabId === 'ml-models') loadMlMetrics();
    if (tabId === 'rag-assistant') loadRagDocuments();
    if (tabId === 'audit-logs') loadAuditLogs();
}

function initDashboard() {
    loadDashboardStats();
    loadPatients();
    loadRagDocuments();
}

// --- 1. DASHBOARD OVERVIEW & CHARTS ---
async function loadDashboardStats() {
    try {
        const res = await fetch("/api/dashboard/stats", { headers: getAuthHeaders() });
        const data = await res.json();

        document.getElementById("kpi-total-patients").innerText = data.total_patients.toLocaleString();
        document.getElementById("kpi-high-risk").innerText = data.high_risk_patients.toLocaleString();
        document.getElementById("kpi-readmissions").innerText = data.readmissions_count.toLocaleString();
        document.getElementById("sidebar-db-count").innerText = data.total_patients.toLocaleString();

        renderRiskDistributionChart(data.risk_distribution);
        renderDiseaseTrendChart(data.disease_risk_trends);
    } catch (err) {
        console.error("Error loading dashboard stats:", err);
    }
}

function renderRiskDistributionChart(riskData) {
    const ctx = document.getElementById("riskDistributionChart").getContext("2d");
    if (riskChartInstance) riskChartInstance.destroy();

    riskChartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Low Risk", "Moderate Risk", "High Risk"],
            datasets: [{
                data: [riskData.Low || 0, riskData.Moderate || 0, riskData.High || 0],
                backgroundColor: ["#059669", "#d97706", "#ef4444"],
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "bottom", labels: { font: { family: "Plus Jakarta Sans", weight: "600" } } }
            }
        }
    });
}

function renderDiseaseTrendChart(trendData) {
    const ctx = document.getElementById("diseaseTrendChart").getContext("2d");
    if (trendChartInstance) trendChartInstance.destroy();

    trendChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: Object.keys(trendData),
            datasets: [{
                label: "Population Mean Risk Score (%)",
                data: Object.values(trendData),
                backgroundColor: ["#2563eb", "#ec4899", "#8b5cf6"],
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, max: 100, ticks: { font: { family: "Plus Jakarta Sans" } } }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// --- 2. PATIENT DIRECTORY & AI RISK ---
async function loadPatients() {
    try {
        const res = await fetch("/api/patients", { headers: getAuthHeaders() });
        const data = await res.json();
        allPatientsData = data.patients || [];
        filterPatients();
    } catch (err) {
        console.error("Error fetching patients:", err);
    }
}

function renderPatientsTable(patients) {
    const tbody = document.getElementById("patientsTableBody");
    tbody.innerHTML = "";

    patients.forEach(p => {
        const diabPred = p.predictions.find(pr => pr.model_name === "Diabetes Risk") || { risk_score: 0, risk_category: "LOW" };
        const cardPred = p.predictions.find(pr => pr.model_name === "Cardiac Risk") || { risk_score: 0, risk_category: "LOW" };
        const readPred = p.predictions.find(pr => pr.model_name === "Readmission Risk") || { risk_score: 0, risk_category: "LOW" };

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong style="font-family: var(--font-mono); color: #2563eb;">#${p.patient_id}</strong></td>
            <td><strong>${p.name}</strong></td>
            <td>${p.age} y/o (${p.gender})</td>
            <td><code>${p.blood_pressure_formatted}</code> mmHg</td>
            <td>${p.lab_results.glucose || '--'} mg/dL</td>
            <td>${p.lab_results.bmi || '--'}</td>
            <td><span class="badge ${diabPred.risk_category.toLowerCase()}"><i class="fa-solid fa-circle" style="font-size: 7px;"></i> ${diabPred.risk_score}%</span></td>
            <td><span class="badge ${cardPred.risk_category.toLowerCase()}"><i class="fa-solid fa-circle" style="font-size: 7px;"></i> ${cardPred.risk_score}%</span></td>
            <td><span class="badge ${readPred.risk_category.toLowerCase()}"><i class="fa-solid fa-circle" style="font-size: 7px;"></i> ${readPred.risk_score}%</span></td>
            <td>
                <button class="btn btn-outline" style="padding: 5px 10px; font-size: 11px;" onclick="viewPatientProfile('${p.patient_id}')"><i class="fa-solid fa-file-medical"></i> Profile</button>
                <button class="btn btn-accent" style="padding: 5px 10px; font-size: 11px;" onclick="explainPatientWithRag('${p.patient_id}')"><i class="fa-solid fa-robot"></i> RAG AI</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterPatients() {
    const searchVal = document.getElementById("patientSearchInput").value.toLowerCase();
    const riskVal = document.getElementById("riskFilterSelect").value;
    const sortVal = document.getElementById("patientSortSelect").value;

    let filtered = allPatientsData.filter(p => {
        const matchesSearch = p.patient_id.toLowerCase().includes(searchVal) || p.name.toLowerCase().includes(searchVal);
        const matchesRisk = (riskVal === "ALL") || (p.overall_risk === riskVal);
        return matchesSearch && matchesRisk;
    });

    if (sortVal === "age") filtered.sort((a, b) => b.age - a.age);
    else if (sortVal === "glucose") filtered.sort((a, b) => (b.lab_results.glucose || 0) - (a.lab_results.glucose || 0));
    else if (sortVal === "bp") filtered.sort((a, b) => b.blood_pressure_sys - a.blood_pressure_sys);

    renderPatientsTable(filtered);
}

async function viewPatientProfile(patientId) {
    const p = allPatientsData.find(pt => pt.patient_id === patientId);
    if (!p) return;

    const title = document.getElementById("modalPatientTitle");
    const body = document.getElementById("modalPatientBody");

    title.innerHTML = `<i class="fa-solid fa-id-card"></i> Clinical Profile — Patient #${p.patient_id} (${p.name})`;

    let predsHtml = "";
    p.predictions.forEach(pr => {
        const badgeColor = pr.risk_category === "HIGH" ? "high" : (pr.risk_category === "MODERATE" ? "moderate" : "low");
        predsHtml += `
            <div style="background: #f8fafc; padding: 14px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #e2e8f0; border-left: 4px solid ${pr.risk_category === 'HIGH' ? '#ef4444' : '#f59e0b'};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="font-size: 14px;">${pr.model_name}</strong>
                    <span class="badge ${badgeColor}">${pr.risk_score}% (${pr.risk_category})</span>
                </div>
                <div style="font-size: 12px; color: #64748b; margin-top: 8px;">
                    <strong>Contributing Clinical Drivers:</strong> ${pr.contributing_factors ? pr.contributing_factors.join(" • ") : 'None flagged'}
                </div>
            </div>
        `;
    });

    body.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px;">
            <div style="background: #fff; padding: 16px; border: 1px solid #e2e8f0; border-radius: 10px;">
                <h4 style="font-size: 14px; margin-bottom: 10px; color: #2563eb;"><i class="fa-solid fa-user"></i> Demographics & Vitals</h4>
                <ul style="list-style: none; font-size: 13px; line-height: 2.0; color: #334155;">
                    <li><strong>Age / Gender:</strong> ${p.age} years / ${p.gender}</li>
                    <li><strong>Blood Pressure:</strong> <code>${p.blood_pressure_formatted}</code> mmHg</li>
                    <li><strong>Height / Weight:</strong> ${p.height_cm} cm / ${p.weight_kg} kg</li>
                    <li><strong>BMI:</strong> ${p.lab_results.bmi} kg/m²</li>
                    <li><strong>Smoking Status:</strong> ${p.smoking_status}</li>
                    <li><strong>Physical Activity:</strong> ${p.physical_activity}</li>
                </ul>
            </div>

            <div style="background: #fff; padding: 16px; border: 1px solid #e2e8f0; border-radius: 10px;">
                <h4 style="font-size: 14px; margin-bottom: 10px; color: #0d9488;"><i class="fa-solid fa-flask"></i> Laboratory Panel</h4>
                <ul style="list-style: none; font-size: 13px; line-height: 2.0; color: #334155;">
                    <li><strong>Fasting Glucose:</strong> ${p.lab_results.glucose} mg/dL</li>
                    <li><strong>Hemoglobin A1c:</strong> ${p.lab_results.hemoglobin_a1c}%</li>
                    <li><strong>Total Cholesterol:</strong> ${p.lab_results.cholesterol} mg/dL</li>
                    <li><strong>LDL / HDL:</strong> ${p.lab_results.ldl} / ${p.lab_results.hdl} mg/dL</li>
                    <li><strong>Triglycerides:</strong> ${p.lab_results.triglycerides} mg/dL</li>
                    <li><strong>Serum Creatinine:</strong> ${p.lab_results.creatinine} mg/dL</li>
                </ul>
            </div>
        </div>

        <h4 style="font-size: 15px; margin-bottom: 12px; color: #0f172a;"><i class="fa-solid fa-brain"></i> AI Multi-Model Risk Stratification</h4>
        ${predsHtml}

        <div style="margin-top: 24px; text-align: right;">
            <button class="btn btn-accent" onclick="explainPatientWithRag('${p.patient_id}')"><i class="fa-solid fa-robot"></i> Generate RAG Clinical Decision Support</button>
        </div>
    `;

    document.getElementById("patientModal").classList.add("open");
}

function closePatientModal() {
    document.getElementById("patientModal").classList.remove("open");
}

async function explainPatientWithRag(patientId) {
    closePatientModal();
    switchTab("rag-assistant");

    const chatMsgs = document.getElementById("chatMessages");
    chatMsgs.innerHTML += `
        <div class="message user">
            <div class="avatar"><i class="fa-solid fa-user"></i></div>
            <div class="bubble">Generate a RAG clinical decision support synthesis for Patient #${patientId}.</div>
        </div>
        <div class="message assistant" id="temp-loading-msg">
            <div class="avatar"><i class="fa-solid fa-spinner fa-spin"></i></div>
            <div class="bubble">Searching clinical guidelines and synthesizing evidence-based explanation...</div>
        </div>
    `;
    chatMsgs.scrollTop = chatMsgs.scrollHeight;

    try {
        const res = await fetch("/api/rag/explain_patient", {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ patient_id: patientId })
        });
        const data = await res.json();

        document.getElementById("temp-loading-msg")?.remove();

        chatMsgs.innerHTML += `
            <div class="message assistant">
                <div class="avatar"><i class="fa-solid fa-user-doctor"></i></div>
                <div class="bubble" style="white-space: pre-line;">${data.explanation}</div>
            </div>
        `;
        chatMsgs.scrollTop = chatMsgs.scrollHeight;
    } catch (err) {
        console.error("RAG explanation error:", err);
    }
}

// --- 3. ML MODEL METRICS ---
async function loadMlMetrics() {
    const container = document.getElementById("mlMetricsContainer");
    container.innerHTML = `<p style="padding: 20px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading ML model performance metrics & feature importances...</p>`;

    try {
        const res = await fetch("/api/ml/metrics", { headers: getAuthHeaders() });
        const data = await res.json();

        let html = "";
        for (const [targetName, models] of Object.entries(data)) {
            const formattedName = targetName.replace("_", " ").toUpperCase();
            html += `<div class="ml-metrics-card">
                <h3 style="font-size: 16px; color: #0f172a; margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
                    <i class="fa-solid fa-bullseye" style="color: #2563eb;"></i> Predictive Target Task: ${formattedName}
                </h3>
                <div class="table-responsive">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Algorithm Architecture</th>
                                <th>Accuracy</th>
                                <th>Precision</th>
                                <th>Recall (Sensitivity)</th>
                                <th>F1-Score</th>
                                <th>ROC-AUC</th>
                            </tr>
                        </thead>
                        <tbody>`;

            for (const [mName, m] of Object.entries(models)) {
                html += `<tr>
                    <td><strong>${mName}</strong></td>
                    <td>${(m.accuracy * 100).toFixed(1)}%</td>
                    <td>${(m.precision * 100).toFixed(1)}%</td>
                    <td><strong style="color: #2563eb;">${(m.recall * 100).toFixed(1)}%</strong></td>
                    <td>${(m.f1_score * 100).toFixed(1)}%</td>
                    <td><span class="badge low">${m.roc_auc.toFixed(3)}</span></td>
                </tr>`;
            }
            html += `</tbody></table></div></div>`;
        }

        container.innerHTML = html;
    } catch (err) {
        console.error("Error loading ML metrics:", err);
    }
}

async function triggerMLRetrain() {
    alert("Retraining all Logistic Regression, Random Forest, and XGBoost models...");
    loadMlMetrics();
}

// --- 4. RAG CHAT & DOCUMENTS ---
async function loadRagDocuments() {
    try {
        const res = await fetch("/api/rag/documents", { headers: getAuthHeaders() });
        const data = await res.json();

        const docList = document.getElementById("documentsList");
        docList.innerHTML = "";
        document.getElementById("sidebar-rag-chunks").innerText = data.documents.reduce((acc, d) => acc + d.chunk_count, 0);

        data.documents.forEach(d => {
            docList.innerHTML += `
                <li class="doc-item">
                    <strong><i class="fa-solid fa-file-pdf" style="color: #ef4444;"></i> ${d.filename}</strong>
                    <div style="font-size: 11px; color: #64748b; margin-top: 4px;">
                        <span>${d.document_type}</span> • <span>${d.chunk_count} Chunks</span>
                    </div>
                </li>
            `;
        });
    } catch (err) {
        console.error("Error loading documents:", err);
    }
}

function setRagPrompt(text) {
    document.getElementById("ragInput").value = text;
    sendRagQuery();
}

function handleRagKeyPress(e) {
    if (e.key === "Enter") sendRagQuery();
}

async function sendRagQuery() {
    const input = document.getElementById("ragInput");
    const q = input.value.trim();
    if (!q) return;

    input.value = "";
    const chatMsgs = document.getElementById("chatMessages");
    chatMsgs.innerHTML += `
        <div class="message user">
            <div class="avatar"><i class="fa-solid fa-user"></i></div>
            <div class="bubble">${q}</div>
        </div>
        <div class="message assistant" id="rag-loading">
            <div class="avatar"><i class="fa-solid fa-spinner fa-spin"></i></div>
            <div class="bubble">Searching clinical vector index & retrieving guideline citations...</div>
        </div>
    `;
    chatMsgs.scrollTop = chatMsgs.scrollHeight;

    try {
        const res = await fetch("/api/rag/query", {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ question: q })
        });
        const data = await res.json();
        document.getElementById("rag-loading")?.remove();

        let citHtml = "";
        if (data.sources) {
            citHtml = `<div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid #cbd5e1; font-size: 11px; color: #475569;">
                <strong>Guideline Citations:</strong> ${data.sources.map(s => `<code>[${s.filename}]</code>`).join(", ")}
            </div>`;
        }

        chatMsgs.innerHTML += `
            <div class="message assistant">
                <div class="avatar"><i class="fa-solid fa-user-doctor"></i></div>
                <div class="bubble" style="white-space: pre-line;">${data.answer} ${citHtml}</div>
            </div>
        `;
        chatMsgs.scrollTop = chatMsgs.scrollHeight;
    } catch (err) {
        console.error("RAG Query Error:", err);
    }
}

function openDocUploadModal() {
    document.getElementById("uploadModal").classList.add("open");
}

function closeUploadModal() {
    document.getElementById("uploadModal").classList.remove("open");
}

async function submitNewDocument() {
    const filename = document.getElementById("docFilenameInput").value.trim();
    const doc_type = document.getElementById("docTypeSelect").value;
    const content = document.getElementById("docContentInput").value.trim();

    if (!filename || !content) {
        alert("Please provide filename and text content!");
        return;
    }

    try {
        const res = await fetch("/api/rag/documents", {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ filename, document_type: doc_type, content })
        });
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        closeUploadModal();
        alert(data.message);
        loadRagDocuments();
    } catch (err) {
        console.error("Upload error:", err);
    }
}

// --- 5. SQL EXPLORER ---
function loadPresetSql(presetKey) {
    executeSqlQuery(presetKey);
}

async function executeSqlQuery(presetKey = "") {
    const queryTxt = document.getElementById("sqlQueryText").value.trim();
    const payload = presetKey ? { preset_key: presetKey } : { query: queryTxt };

    const container = document.getElementById("sqlResultsContainer");
    container.innerHTML = `<p style="padding: 20px;"><i class="fa-solid fa-spinner fa-spin"></i> Executing SQL query against database engine...</p>`;

    try {
        const res = await fetch("/api/sql/query", {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.error) {
            container.innerHTML = `<div style="padding: 16px; background: #fee2e2; color: #dc2626; border-radius: 10px; border: 1px solid #fca5a5;"><strong>SQL Execution Error:</strong> ${data.error}</div>`;
            return;
        }

        document.getElementById("sqlQueryText").value = data.query;

        const result = data.result;
        let tableHtml = `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 13px; color: #64748b;">Returned <strong>${result.count}</strong> record rows</span>
        </div>`;

        tableHtml += `<div class="table-responsive"><table class="data-table"><thead><tr>`;
        result.columns.forEach(col => { tableHtml += `<th>${col}</th>`; });
        tableHtml += `</tr></thead><tbody>`;

        result.rows.forEach(r => {
            tableHtml += `<tr>`;
            result.columns.forEach(col => { tableHtml += `<td>${r[col] !== null ? r[col] : 'NULL'}</td>`; });
            tableHtml += `</tr>`;
        });
        tableHtml += `</tbody></table></div>`;

        container.innerHTML = tableHtml;
    } catch (err) {
        console.error("SQL Error:", err);
    }
}

// --- 6. AUDIT LOGS ---
async function loadAuditLogs() {
    try {
        const res = await fetch("/api/audit", { headers: getAuthHeaders() });
        const data = await res.json();

        const tbody = document.getElementById("auditLogsBody");
        tbody.innerHTML = "";

        data.logs.forEach(l => {
            tbody.innerHTML += `
                <tr>
                    <td style="font-family: var(--font-mono); font-size: 11.5px; color: #64748b;">${new Date(l.timestamp).toISOString()}</td>
                    <td><strong>${l.user_name}</strong></td>
                    <td><span class="badge low">${l.user_role}</span></td>
                    <td><code style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">${l.action}</code></td>
                    <td style="font-size: 12px;">${l.resource_accessed}</td>
                    <td style="font-family: var(--font-mono); font-size: 11.5px;">${l.ip_address}</td>
                </tr>
            `;
        });
    } catch (err) {
        console.error("Error loading audit logs:", err);
    }
}
