<template>
    <section class="panel">
        <div class="card">
            <div class="card-head">
                <div>
                    <p class="eyebrow">步骤 1</p>
                    <h2>提交要审计的 URL</h2>
                    <p class="muted">
                        后端将抓取页面并调用文本与多模态模型完成审计。
                    </p>
                </div>
                <div class="status-chip" :class="statusClass">
                    {{ statusLabel }}
                </div>
            </div>
            <div class="form-row">
                <label for="urlInput">页面链接</label>
                <div class="input-group">
                    <input
                        id="urlInput"
                        v-model="urlInput"
                        type="url"
                        placeholder="https://example.com/article"
                        :disabled="loading"
                    />
                    <button
                        class="primary"
                        :disabled="loading || !urlInput"
                        @click="startAudit"
                    >
                        {{ loading ? "提交中..." : "开始审计" }}
                    </button>
                </div>
                <label for="checklistInput">审核清单（可选）</label>
                <textarea
                    id="checklistInput"
                    v-model="checklistInput"
                    class="checklist"
                    rows="3"
                    placeholder="每行一条，例如：
人名校对
日期一致性检查"
                    :disabled="loading"
                ></textarea>
                <p v-if="error" class="error">{{ error }}</p>
                <p v-if="taskId" class="task-id">任务 ID：{{ taskId }}</p>
            </div>
            <div class="progress" v-if="status">
                <div class="bar" :style="{ width: progressWidth }"></div>
            </div>
            <p v-if="message" class="muted">{{ message }}</p>
            <div class="task-actions" v-if="taskId">
                <button class="ghost" @click="rerunCurrent">
                    重新运行当前任务
                </button>
                <button
                    class="ghost danger"
                    v-if="taskHistory.length"
                    @click="clearHistory"
                >
                    清空历史记录
                </button>
            </div>
        </div>

        <div class="card">
            <div class="card-head">
                <div>
                    <p class="eyebrow">任务列表</p>
                    <h2>历史记录</h2>
                    <p class="muted">
                        使用浏览器本地存储保存任务记录。点击可查看进度与结果。
                    </p>
                </div>
                <span class="pill">{{ taskHistory.length }} 条</span>
            </div>
            <div v-if="!taskHistory.length" class="empty">
                <p>暂无历史任务。提交 URL 后会自动记录。</p>
            </div>
            <div v-else class="task-list">
                <div
                    v-for="item in taskHistory"
                    :key="item.task_id"
                    class="task-row"
                    :class="{ active: item.task_id === taskId }"
                >
                    <div class="task-main">
                        <div class="task-title">
                            <span class="task-url">{{ item.url }}</span>
                            <span class="task-status" :class="item.status">
                                {{ statusText(item.status) }}
                            </span>
                        </div>
                        <div class="task-meta">
                            <span>任务 ID：{{ item.task_id }}</span>
                            <span v-if="item.updated_at">
                                更新时间：{{ formatTime(item.updated_at) }}
                            </span>
                            <span v-if="item.progress != null">
                                进度：{{ item.progress }}%
                            </span>
                            <span v-if="item.checklist?.length">
                                清单：{{ formatChecklist(item.checklist) }}
                            </span>
                        </div>
                    </div>
                    <div class="task-actions">
                        <button class="ghost" @click="loadTask(item)">
                            查看
                        </button>
                        <button class="ghost" @click="rerunTask(item)">
                            重新运行
                        </button>
                        <button class="ghost danger" @click="removeTask(item)">
                            删除
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <div class="card" ref="resultCard">
            <div class="card-head">
                <div>
                    <p class="eyebrow">步骤 2</p>
                    <h2>审计结果与批注</h2>
                    <p class="muted">
                        支持驳回 AI 建议、手动画框并填写批注，最后导出 PDF。
                    </p>
                </div>
                <span class="pill">{{ displayIssues.length }} 个问题</span>
            </div>

            <div class="review-toolbar" v-if="screenshotSrc || displayIssues.length">
                <button class="ghost" :disabled="!customIssues.length" @click="clearCustomIssues">
                    清空手工批注
                </button>
            </div>

            <div class="summary-bar" v-if="displayIssues.length">
                <span>已保留 {{ decisionStats.kept }}</span>
                <span>已驳回 {{ decisionStats.rejected }}</span>
            </div>

            <div v-if="!screenshotSrc && displayIssues.length === 0" class="empty">
                <p>尚未生成问题列表。提交 URL 并等待审计完成即可查看结果。</p>
            </div>

            <div
                v-else
                ref="exportContainer"
                class="export-container"
                :class="{ 'export-mode': exportMode }"
            >
                <div class="export-head">
                    <h3>智慧审查报告</h3>
                    <p>URL：{{ urlInput || "(未填写)" }}</p>
                    <p>导出时间：{{ new Date().toLocaleString() }}</p>
                </div>

                <div class="result-grid">
                    <div class="screenshot-pane">
                        <div
                            v-if="screenshotSrc"
                            ref="shotWrapper"
                            class="screenshot-wrapper"
                            :class="{ drawing: drawingMode }"
                            @mousedown="beginDraw"
                            @mousemove="moveDraw"
                            @mouseup="endDraw"
                            @mouseleave="cancelDraw"
                        >
                            <img
                                ref="shotImg"
                                class="screenshot"
                                :src="screenshotSrc"
                                crossorigin="anonymous"
                                alt="页面截图"
                                @load="onShotLoad"
                            />
                            <div
                                v-for="issue in issuesWithBox"
                                :key="`box-${issue.id}`"
                                v-show="boxForIssue(issue)"
                                class="overlay-box"
                                :class="{
                                    active: hoverIssueId === issue.id,
                                    manual: issue.manual,
                                    rejected: isRejected(issue.id),
                                }"
                                :style="boxStyle(issue)"
                            ></div>
                            <div
                                v-if="drawingPreview"
                                class="overlay-box preview"
                                :style="drawingPreview"
                            ></div>
                        </div>
                        <div v-else class="empty">暂无截图。</div>
                    </div>

                    <div class="issues-pane" :style="{ height: `${issuesPaneRenderHeight}px` }">
                        <template v-if="positionedIssues.length">
                            <div
                                v-for="item in positionedIssues"
                                :key="item.issue.id"
                                class="issue-item positioned"
                                :class="{
                                    active: hoverIssueId === item.issue.id,
                                    rejected: isRejected(item.issue.id),
                                    manual: item.issue.manual,
                                }"
                                :style="{ top: `${item.top}px` }"
                                :ref="(el) => setIssueRef(item.issue.id, el)"
                                @mouseenter="hoverIssueId = item.issue.id"
                                @mouseleave="hoverIssueId = null"
                            >
                                <div class="issue-top">
                                    <span class="badge" :class="`sev-${item.issue.severity || 'info'}`">
                                        {{ item.issue.severity || "info" }}
                                    </span>
                                    <span class="type">{{ item.issue.type || "custom" }}</span>
                                    <span v-if="item.issue.confidence" class="confidence">
                                        置信度 {{ Number(item.issue.confidence).toFixed(2) }}
                                    </span>
                                    <span class="decision" :class="isRejected(item.issue.id) ? 'decision-rejected' : 'decision-kept'">
                                        {{ isRejected(item.issue.id) ? "已驳回" : "已保留" }}
                                    </span>
                                </div>

                                <div class="issue-controls">
                                    <button
                                        class="mini-btn reject"
                                        v-if="!isRejected(item.issue.id)"
                                        @click="rejectIssue(item.issue.id)"
                                        title="驳回该建议"
                                    >
                                        X 驳回
                                    </button>
                                    <button
                                        class="mini-btn"
                                        v-else
                                        @click="undoReject(item.issue.id)"
                                    >
                                        撤销
                                    </button>
                                    <button
                                        class="mini-btn danger"
                                        v-if="item.issue.manual"
                                        @click="removeCustomIssue(item.issue.id)"
                                    >
                                        删除批注
                                    </button>
                                </div>

                                <p v-if="item.issue.evidence?.quote" class="quote">
                                    “{{ item.issue.evidence.quote }}”
                                </p>
                                <p v-if="item.issue.recommendation" class="recommend">
                                    建议：{{ item.issue.recommendation }}
                                </p>

                                <template v-if="item.issue.manual">
                                    <label class="annotation-label">批注</label>
                                    <textarea
                                        class="annotation-input"
                                        :value="noteForIssue(item.issue.id)"
                                        placeholder="输入你的审校意见..."
                                        @input="updateNote(item.issue.id, $event.target.value)"
                                    ></textarea>
                                </template>

                                <div class="meta">
                                    <span v-if="item.issue.evidence?.text_block_id">
                                        文本段落：{{ item.issue.evidence.text_block_id }}
                                    </span>
                                    <span v-if="item.issue.evidence?.image_id">
                                        图片：{{ item.issue.evidence.image_id }}
                                    </span>
                                    <span v-if="item.issue.evidence?.link_id">
                                        链接：{{ item.issue.evidence.link_id }}
                                    </span>
                                    <span v-if="item.issue.manual">手工批注</span>
                                </div>
                            </div>
                        </template>
                        <div v-else class="empty">暂无问题。</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="floating-actions" v-if="screenshotSrc || displayIssues.length">
            <button
                class="fab fab-draw"
                :class="{ active: drawingMode }"
                :disabled="!screenshotSrc"
                @click="toggleDrawingMode"
            >
                {{ drawingMode ? "结束画框" : "新增批注画框" }}
            </button>
            <button
                class="fab fab-export"
                :disabled="exportingPdf || (!screenshotSrc && !displayIssues.length)"
                @click="exportPdf"
            >
                {{ exportingPdf ? "导出中..." : "导出 PDF" }}
            </button>
        </div>
    </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

const API_BASE =
    process.env.NODE_ENV === "development"
        ? "http://localhost:8000/api"
        : "/api";

const urlInput = ref("");
const checklistInput = ref("");
const taskId = ref("");
const status = ref("");
const message = ref("");
const issues = ref([]);
const customIssues = ref([]);
const decisionMap = ref({});
const noteMap = ref({});
const bundle = ref(null);
const targetProgress = ref(0);
const displayProgress = ref(0);
const loading = ref(false);
const exportingPdf = ref(false);
const exportMode = ref(false);
const error = ref("");
let pollTimer = null;
let easeTimer = null;
const hoverIssueId = ref(null);
const taskHistory = ref([]);
const historyKey = "audit_task_history";

const shotImg = ref(null);
const shotWrapper = ref(null);
const exportContainer = ref(null);
const resultCard = ref(null);
const shotNatural = ref({ w: 1, h: 1 });
const shotDisplay = ref({ w: 1, h: 1 });

const drawingMode = ref(false);
const isDrawing = ref(false);
const drawStart = ref(null);
const drawCurrent = ref(null);

const minIssueGap = 14;
const issueHeights = ref({});

const statusLabel = computed(() => {
    if (!status.value) return "待开始";
    if (status.value === "running") return "运行中";
    if (status.value === "completed") return "已完成";
    if (status.value === "failed") return "失败";
    return status.value;
});

const statusClass = computed(() => {
    if (status.value === "completed") return "ok";
    if (status.value === "running") return "warn";
    if (status.value === "failed") return "error";
    return "idle";
});

const progressWidth = computed(() => {
    if (status.value === "failed") return "100%";
    if (status.value === "completed") return "100%";
    if (displayProgress.value) {
        return `${Math.min(displayProgress.value, 100)}%`;
    }
    return "0%";
});

const apiOrigin = computed(() => {
    if (API_BASE.startsWith("http")) return API_BASE.replace(/\/api$/, "");
    return "";
});

const screenshotSrc = computed(() => {
    const file = bundle.value?.screenshots?.[0]?.filename;
    if (!file) return "";
    const name = file.split(/[/\\]/).pop();
    if (!name) return "";
    return `${apiOrigin.value}/api/captures/${name}`;
});

const displayIssues = computed(() => {
    return [...issues.value, ...customIssues.value];
});

const issuesForList = computed(() => {
    if (!exportMode.value) return displayIssues.value;
    return displayIssues.value.filter((issue) => !isRejected(issue.id));
});

const issuesWithBox = computed(() => {
    return displayIssues.value.filter(
        (issue) => boxForIssue(issue) && !isRejected(issue.id),
    );
});

const issuesPaneHeight = computed(() => {
    return Math.max(shotDisplay.value.h || 420, 420);
});

const positionedBottom = computed(() => {
    if (!positionedIssues.value.length) return 0;
    return positionedIssues.value.reduce((maxBottom, item) => {
        const bottom = item.top + item.height;
        return Math.max(maxBottom, bottom);
    }, 0);
});

const issuesPaneRenderHeight = computed(() => {
    if (!exportMode.value) return issuesPaneHeight.value;
    return Math.max(issuesPaneHeight.value, positionedBottom.value + 24);
});

const drawingPreview = computed(() => {
    if (!drawStart.value || !drawCurrent.value) return null;
    const x = Math.min(drawStart.value.x, drawCurrent.value.x);
    const y = Math.min(drawStart.value.y, drawCurrent.value.y);
    const width = Math.abs(drawCurrent.value.x - drawStart.value.x);
    const height = Math.abs(drawCurrent.value.y - drawStart.value.y);
    return {
        left: `${x}px`,
        top: `${y}px`,
        width: `${width}px`,
        height: `${height}px`,
    };
});

const decisionStats = computed(() => {
    let kept = 0;
    let rejected = 0;
    for (const issue of displayIssues.value) {
        if (isRejected(issue.id)) rejected += 1;
        else kept += 1;
    }
    return { kept, rejected };
});

function normalizeIssues(rawIssues) {
    if (!Array.isArray(rawIssues)) return [];
    return rawIssues.map((issue, idx) => {
        const normalized = issue ? { ...issue } : {};
        if (!normalized.id) normalized.id = `issue-${idx + 1}`;
        const evidence =
            normalized.evidence && typeof normalized.evidence === "object"
                ? { ...normalized.evidence }
                : {};
        if (evidence.text_block_id == null) delete evidence.text_block_id;
        normalized.evidence = evidence;
        normalized.manual = false;
        return normalized;
    });
}

function clearPolling() {
    if (pollTimer) {
        clearTimeout(pollTimer);
        pollTimer = null;
    }
}

function resetState() {
    clearPolling();
    taskId.value = "";
    status.value = "";
    message.value = "";
    issues.value = [];
    customIssues.value = [];
    decisionMap.value = {};
    noteMap.value = {};
    bundle.value = null;
    targetProgress.value = 0;
    displayProgress.value = 0;
    error.value = "";
    shotNatural.value = { w: 1, h: 1 };
    shotDisplay.value = { w: 1, h: 1 };
    hoverIssueId.value = null;
    issueHeights.value = {};
    drawingMode.value = false;
    isDrawing.value = false;
    drawStart.value = null;
    drawCurrent.value = null;
}

function stopEaseTimer() {
    if (easeTimer) {
        clearInterval(easeTimer);
        easeTimer = null;
    }
}

function startEaseTimer() {
    stopEaseTimer();
    easeTimer = setInterval(() => {
        if (targetProgress.value >= 100) {
            displayProgress.value = 100;
            stopEaseTimer();
            return;
        }
        const current = displayProgress.value;
        const target = targetProgress.value || 0;
        const next = current + (target - current) / 4;
        displayProgress.value = Math.min(next, 100);
    }, 1000);
}

function loadHistory() {
    try {
        const raw = localStorage.getItem(historyKey);
        const parsed = raw ? JSON.parse(raw) : [];
        taskHistory.value = Array.isArray(parsed) ? parsed : [];
    } catch (e) {
        taskHistory.value = [];
    }
}

function saveHistory(list) {
    taskHistory.value = list;
    localStorage.setItem(historyKey, JSON.stringify(list));
}

function upsertHistory(item) {
    const list = [...taskHistory.value];
    const index = list.findIndex((t) => t.task_id === item.task_id);
    if (index >= 0) {
        list[index] = { ...list[index], ...item };
    } else {
        list.unshift(item);
    }
    saveHistory(list.slice(0, 50));
}

function removeTask(item) {
    const list = taskHistory.value.filter((t) => t.task_id !== item.task_id);
    saveHistory(list);
}

function clearHistory() {
    saveHistory([]);
}

function formatTime(ts) {
    try {
        const date = new Date((ts || 0) * 1000);
        return date.toLocaleString();
    } catch (e) {
        return "";
    }
}

function statusText(value) {
    if (value === "running") return "运行中";
    if (value === "completed") return "已完成";
    if (value === "failed") return "失败";
    return value || "未知";
}

function parseChecklist(value) {
    return (value || "")
        .split(/\r?\n/)
        .map((item) => item.trim())
        .filter(Boolean);
}

function formatChecklist(list) {
    if (!Array.isArray(list) || list.length === 0) return "";
    const preview = list.slice(0, 3).join("、");
    return list.length > 3 ? `${preview}...` : preview;
}

async function startAudit() {
    if (!urlInput.value) {
        error.value = "请输入有效的 URL";
        return;
    }

    resetState();
    loading.value = true;
    try {
        const resp = await fetch(`${API_BASE}/audit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                url: urlInput.value.trim(),
                checklist: parseChecklist(checklistInput.value),
            }),
        });
        if (!resp.ok) throw new Error(`提交失败：${resp.status}`);
        const data = await resp.json();
        taskId.value = data.task_id;
        status.value = data.status;
        const msgFallback = "任务已创建，正在启动审计...";
        message.value = data.message || msgFallback;
        issues.value = normalizeIssues(data.issues || []);
        bundle.value = data.result || null;

        upsertHistory({
            task_id: data.task_id,
            url: urlInput.value.trim(),
            checklist: parseChecklist(checklistInput.value),
            status: data.status,
            progress: data.progress ?? 0,
            updated_at: Math.floor(Date.now() / 1000),
        });

        const initialProgress =
            typeof data.progress === "number"
                ? data.progress
                : data.status === "completed"
                  ? 100
                  : 0;
        targetProgress.value = initialProgress;
        displayProgress.value = initialProgress;

        if (data.status === "completed" || data.status === "failed") {
            stopEaseTimer();
            return;
        }

        startEaseTimer();
        pollStatus();
    } catch (e) {
        error.value = e?.message || "提交失败";
    } finally {
        loading.value = false;
    }
}

async function pollStatus() {
    if (!taskId.value) return;
    try {
        const resp = await fetch(`${API_BASE}/audit/${taskId.value}`);
        if (!resp.ok) throw new Error("查询失败");
        const data = await resp.json();
        status.value = data.status;
        message.value = data.message || "";
        issues.value = normalizeIssues(data.issues);
        bundle.value = data.result || null;
        if (Array.isArray(data.checklist)) {
            checklistInput.value = data.checklist.join("\n");
        }
        if (typeof data.progress === "number") {
            targetProgress.value = data.progress;
            if (targetProgress.value >= 100) {
                displayProgress.value = 100;
                stopEaseTimer();
            } else {
                startEaseTimer();
            }
        }

        upsertHistory({
            task_id: data.task_id,
            url: urlInput.value.trim(),
            checklist: Array.isArray(data.checklist)
                ? data.checklist
                : parseChecklist(checklistInput.value),
            status: data.status,
            progress: data.progress ?? targetProgress.value ?? 0,
            updated_at: Math.floor(Date.now() / 1000),
        });

        if (data.status === "completed" || data.status === "failed") {
            clearPolling();
            stopEaseTimer();
            return;
        }
        pollTimer = setTimeout(pollStatus, 1500);
    } catch (e) {
        error.value = e?.message || "查询失败";
        clearPolling();
        stopEaseTimer();
    }
}

onBeforeUnmount(() => {
    clearPolling();
    stopEaseTimer();
});

function loadTask(item) {
    if (!item?.task_id) return;
    resetState();
    urlInput.value = item.url || "";
    checklistInput.value = (item.checklist || []).join("\n");
    taskId.value = item.task_id;
    status.value = item.status || "";
    message.value = "正在加载任务状态...";
    issues.value = [];
    bundle.value = null;
    targetProgress.value = item.progress ?? 0;
    displayProgress.value = targetProgress.value;
    pollStatus();
}

function rerunTask(item) {
    if (!item?.url) return;
    urlInput.value = item.url;
    startAudit();
}

function rerunCurrent() {
    if (!urlInput.value) return;
    startAudit();
}

watch(
    issues,
    (list) => {
        const nextDecision = { ...decisionMap.value };
        for (const issue of list || []) {
            if (nextDecision[issue.id] == null) nextDecision[issue.id] = false;
        }
        decisionMap.value = nextDecision;
    },
    { immediate: true },
);

watch(displayIssues, () => {
    issueHeights.value = {};
    nextTick(() => {
        // allow refs to re-register
    });
});

function setIssueRef(id, el) {
    if (!el) return;
    const height = el.getBoundingClientRect().height;
    const prev = issueHeights.value?.[id];
    if (prev !== undefined && Math.abs(prev - height) < 0.5) return;
    issueHeights.value = {
        ...issueHeights.value,
        [id]: height,
    };
}

function onShotLoad(event) {
    const img = event.target;
    shotNatural.value = { w: img.naturalWidth || 1, h: img.naturalHeight || 1 };
    shotDisplay.value = { w: img.clientWidth || 1, h: img.clientHeight || 1 };
}

function isRejected(issueId) {
    return !!decisionMap.value?.[issueId];
}

function rejectIssue(issueId) {
    decisionMap.value = {
        ...decisionMap.value,
        [issueId]: true,
    };
}

function undoReject(issueId) {
    decisionMap.value = {
        ...decisionMap.value,
        [issueId]: false,
    };
}

function noteForIssue(issueId) {
    return noteMap.value?.[issueId] || "";
}

function updateNote(issueId, text) {
    noteMap.value = {
        ...noteMap.value,
        [issueId]: text,
    };
}

function removeCustomIssue(issueId) {
    customIssues.value = customIssues.value.filter((item) => item.id !== issueId);
    const nextDecisions = { ...decisionMap.value };
    const nextNotes = { ...noteMap.value };
    delete nextDecisions[issueId];
    delete nextNotes[issueId];
    decisionMap.value = nextDecisions;
    noteMap.value = nextNotes;
}

function clearCustomIssues() {
    const ids = new Set(customIssues.value.map((item) => item.id));
    customIssues.value = [];
    const nextDecisions = { ...decisionMap.value };
    const nextNotes = { ...noteMap.value };
    for (const id of ids) {
        delete nextDecisions[id];
        delete nextNotes[id];
    }
    decisionMap.value = nextDecisions;
    noteMap.value = nextNotes;
}

function toggleDrawingMode() {
    drawingMode.value = !drawingMode.value;
    isDrawing.value = false;
    drawStart.value = null;
    drawCurrent.value = null;
}

function localPointFromMouse(event) {
    if (!shotImg.value) return null;
    const rect = shotImg.value.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    const x = Math.max(0, Math.min(event.clientX - rect.left, rect.width));
    const y = Math.max(0, Math.min(event.clientY - rect.top, rect.height));
    return { x, y };
}

function beginDraw(event) {
    if (!drawingMode.value || !shotImg.value) return;
    if (shotNatural.value.w <= 1 || shotDisplay.value.w <= 1) return;
    event.preventDefault();
    const point = localPointFromMouse(event);
    if (!point) return;
    isDrawing.value = true;
    drawStart.value = point;
    drawCurrent.value = point;
}

function moveDraw(event) {
    if (!isDrawing.value) return;
    event.preventDefault();
    const point = localPointFromMouse(event);
    if (!point) return;
    drawCurrent.value = point;
}

function appendManualIssue(box) {
    const scaleX = shotNatural.value.w / (shotDisplay.value.w || 1);
    const scaleY = shotNatural.value.h / (shotDisplay.value.h || 1);
    const bbox = {
        x: Math.round(box.x * scaleX),
        y: Math.round(box.y * scaleY),
        width: Math.max(1, Math.round(box.width * scaleX)),
        height: Math.max(1, Math.round(box.height * scaleY)),
    };
    const id = `manual-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
    const issue = {
        id,
        type: "manual_note",
        severity: "info",
        evidence: {
            bbox,
            screenshot_id: bundle.value?.screenshots?.[0]?.id,
            quote: "",
        },
        recommendation: "",
        manual: true,
    };
    customIssues.value = [...customIssues.value, issue];
    undoReject(id);
    updateNote(id, "");
    hoverIssueId.value = id;
}

function endDraw(event) {
    if (event) event.preventDefault();
    if (!isDrawing.value || !drawStart.value || !drawCurrent.value) {
        isDrawing.value = false;
        drawStart.value = null;
        drawCurrent.value = null;
        return;
    }
    const x = Math.min(drawStart.value.x, drawCurrent.value.x);
    const y = Math.min(drawStart.value.y, drawCurrent.value.y);
    const width = Math.abs(drawCurrent.value.x - drawStart.value.x);
    const height = Math.abs(drawCurrent.value.y - drawStart.value.y);

    if (width >= 4 && height >= 4) {
        appendManualIssue({ x, y, width, height });
    }

    isDrawing.value = false;
    drawStart.value = null;
    drawCurrent.value = null;
}

function cancelDraw() {
    if (!isDrawing.value) return;
    endDraw();
}

loadHistory();

function boxForIssue(issue) {
    return issue?.evidence?.bbox || null;
}

function boxStyle(issue) {
    const bbox = boxForIssue(issue);
    if (!bbox) return {};
    const scaleX = shotDisplay.value.w / (shotNatural.value.w || 1);
    const scaleY = shotDisplay.value.h / (shotNatural.value.h || 1);
    return {
        left: `${bbox.x * scaleX}px`,
        top: `${bbox.y * scaleY}px`,
        width: `${bbox.width * scaleX}px`,
        height: `${bbox.height * scaleY}px`,
    };
}

const positionedIssues = computed(() => {
    if (!issuesForList.value?.length) return [];
    const scaleY = shotDisplay.value.h / (shotNatural.value.h || 1);
    const withPos = issuesForList.value
        .map((issue) => {
            const bbox = boxForIssue(issue);
            const y = bbox ? bbox.y * scaleY : null;
            const height = issueHeights.value?.[issue.id] || 205;
            return { issue, y, height };
        })
        .sort((a, b) => {
            if (a.y === null && b.y === null) return 0;
            if (a.y === null) return 1;
            if (b.y === null) return -1;
            return a.y - b.y;
        });

    let cursor = 0;
    const placed = [];
    for (const item of withPos) {
        const top = item.y === null ? cursor : Math.max(item.y, cursor);
        placed.push({ issue: item.issue, top, height: item.height });
        cursor = top + item.height + minIssueGap;
    }

    return placed;
});

async function exportPdf() {
    if (exportingPdf.value) return;
    if (!resultCard.value) {
        error.value = "未找到可导出的内容区域";
        return;
    }

    exportingPdf.value = true;
    error.value = "";
    exportMode.value = true;
    await nextTick();

        try {
            const html2canvas = await loadHtml2Canvas();
            const jsPDF = await loadJsPdf();

            const canvas = await html2canvas(resultCard.value, {
                scale: 2,
                useCORS: true,
                allowTaint: false,
                backgroundColor: "#0b1021",
                windowWidth: document.documentElement.scrollWidth,
                windowHeight: document.documentElement.scrollHeight,
                scrollX: 0,
                scrollY: -window.scrollY,
            });

            const imageData = canvas.toDataURL("image/png");
            const pdf = new jsPDF("p", "mm", "a4");
            const pageWidth = pdf.internal.pageSize.getWidth();
            const pageHeight = pdf.internal.pageSize.getHeight();
            const margin = 6;
            const imgWidth = pageWidth - margin * 2;
            const imgHeight = (canvas.height * imgWidth) / canvas.width;

            let remainHeight = imgHeight;
            let y = margin;

            pdf.addImage(imageData, "PNG", margin, y, imgWidth, imgHeight);
            remainHeight -= pageHeight - margin * 2;

            while (remainHeight > 0) {
                pdf.addPage();
                y = margin - (imgHeight - remainHeight);
                pdf.addImage(imageData, "PNG", margin, y, imgWidth, imgHeight);
                remainHeight -= pageHeight - margin * 2;
            }

            pdf.save(`audit-report-${Date.now()}.pdf`);
    } catch (e) {
        error.value = e?.message || "导出 PDF 失败";
    } finally {
        exportMode.value = false;
        exportingPdf.value = false;
    }
}

    async function loadScriptOnce(url) {
        if (typeof window === "undefined") return;
        const exists = Array.from(document.scripts).some((s) => s.src === url);
        if (exists) return;
        await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = url;
            script.async = true;
            script.onload = resolve;
            script.onerror = () => reject(new Error(`加载脚本失败: ${url}`));
            document.head.appendChild(script);
        });
    }

    async function loadHtml2Canvas() {
        if (window.html2canvas) return window.html2canvas;
        await loadScriptOnce("https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js");
        if (!window.html2canvas) {
            throw new Error("html2canvas 加载失败");
        }
        return window.html2canvas;
    }

    async function loadJsPdf() {
        const hasJsPdf = window.jspdf && window.jspdf.jsPDF;
        if (hasJsPdf) return window.jspdf.jsPDF;
        await loadScriptOnce("https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js");
        if (!window.jspdf || !window.jspdf.jsPDF) {
            throw new Error("jsPDF 加载失败");
        }
        return window.jspdf.jsPDF;
    }
</script>

<style scoped>
.panel {
    display: grid;
    grid-template-columns: 1fr;
    gap: 18px;
    padding-bottom: 108px;
}

.card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 20px 22px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35);
}

.card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
}

.eyebrow {
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 12px;
    color: #a5b4fc;
}

h2 {
    margin: 4px 0 4px;
    font-size: 20px;
    color: #f9fafb;
}

h3 {
    margin: 0;
    font-size: 16px;
}

.muted {
    margin: 0;
    color: #9ca3af;
    font-size: 14px;
}

.form-row {
    margin-top: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

label {
    font-size: 14px;
    color: #d1d5db;
}

.input-group {
    display: flex;
    gap: 10px;
}

input[type="url"] {
    flex: 1;
    padding: 12px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    background: rgba(15, 23, 42, 0.7);
    color: #e5e7eb;
    outline: none;
}

.checklist {
    padding: 12px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    background: rgba(15, 23, 42, 0.7);
    color: #e5e7eb;
    outline: none;
    resize: vertical;
    min-height: 80px;
}

input:disabled {
    opacity: 0.6;
}

button.primary {
    padding: 12px 16px;
    background: linear-gradient(135deg, #6366f1, #22d3ee);
    color: #0b0f1a;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    cursor: pointer;
    min-width: 120px;
}

button.primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.error {
    color: #f87171;
    margin: 0;
}

.task-id {
    color: #a5b4fc;
    font-size: 13px;
    margin: 0;
}

.status-chip {
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.status-chip.idle {
    color: #9ca3af;
}

.status-chip.warn {
    color: #facc15;
    background: rgba(250, 204, 21, 0.12);
}

.status-chip.ok {
    color: #34d399;
    background: rgba(52, 211, 153, 0.12);
}

.status-chip.error {
    color: #f87171;
    background: rgba(248, 113, 113, 0.12);
}

.progress {
    margin-top: 8px;
    height: 6px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    overflow: hidden;
}

.bar {
    height: 100%;
    background: linear-gradient(90deg, #22d3ee, #6366f1);
    transition: width 0.4s ease;
}

.card .pill {
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.08);
    color: #e5e7eb;
    font-size: 13px;
}

.task-list {
    margin-top: 12px;
    display: grid;
    gap: 12px;
}

.task-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 14px;
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.06);
}

.task-row.active {
    border-color: rgba(99, 102, 241, 0.7);
    box-shadow: 0 8px 18px rgba(0, 0, 0, 0.35);
}

.task-main {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
}

.task-title {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.task-url {
    font-weight: 600;
    color: #e5e7eb;
    word-break: break-all;
}

.task-status {
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
}

.task-status.running {
    background: rgba(250, 204, 21, 0.15);
    color: #facc15;
}

.task-status.completed {
    background: rgba(52, 211, 153, 0.15);
    color: #34d399;
}

.task-status.failed {
    background: rgba(248, 113, 113, 0.18);
    color: #f87171;
}

.task-meta {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    color: #9ca3af;
    font-size: 12px;
}

.task-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.ghost {
    padding: 6px 12px;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    background: transparent;
    color: #cbd5f5;
    cursor: pointer;
}

.ghost.active {
    border-color: rgba(52, 211, 153, 0.8);
    color: #34d399;
    background: rgba(52, 211, 153, 0.12);
}

.ghost.danger {
    color: #f87171;
    border-color: rgba(248, 113, 113, 0.4);
}

.empty {
    padding: 14px;
    border: 1px dashed rgba(255, 255, 255, 0.16);
    border-radius: 10px;
    color: #9ca3af;
}

.review-toolbar {
    margin-top: 14px;
    margin-bottom: 10px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.floating-actions {
    position: fixed;
    left: 50%;
    bottom: 18px;
    transform: translateX(-50%);
    z-index: 90;
    display: flex;
    gap: 12px;
    padding: 9px;
    border-radius: 999px;
    border: 1px solid rgba(203, 213, 225, 0.22);
    background:
        linear-gradient(
            135deg,
            rgba(2, 6, 23, 0.9) 0%,
            rgba(15, 23, 42, 0.88) 45%,
            rgba(30, 41, 59, 0.86) 100%
        ),
        radial-gradient(
            circle at 10% 0%,
            rgba(255, 255, 255, 0.22),
            transparent 45%
        );
    box-shadow:
        0 20px 44px rgba(2, 6, 23, 0.55),
        inset 0 1px 0 rgba(255, 255, 255, 0.18);
    backdrop-filter: blur(14px) saturate(115%);
}

.fab {
    position: relative;
    overflow: hidden;
    border: none;
    border-radius: 999px;
    padding: 11px 18px;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.02em;
    cursor: pointer;
    color: #f8fafc;
    transition:
        transform 0.25s ease,
        box-shadow 0.25s ease,
        opacity 0.2s ease,
        filter 0.25s ease;
}

.fab::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
        105deg,
        rgba(255, 255, 255, 0.24) 0%,
        rgba(255, 255, 255, 0.07) 42%,
        rgba(255, 255, 255, 0) 70%
    );
    pointer-events: none;
}

.fab:hover {
    transform: translateY(-2px);
    filter: saturate(115%);
}

.fab:disabled {
    opacity: 0.55;
    cursor: not-allowed;
}

.fab-draw {
    background: linear-gradient(135deg, #0f766e 0%, #0ea5a8 48%, #22d3ee 100%);
    box-shadow:
        0 10px 22px rgba(15, 118, 110, 0.42),
        inset 0 0 0 1px rgba(255, 255, 255, 0.2);
}

.fab-draw.active {
    background: linear-gradient(135deg, #047857 0%, #10b981 55%, #34d399 100%);
    box-shadow:
        0 12px 24px rgba(4, 120, 87, 0.46),
        inset 0 0 0 1px rgba(255, 255, 255, 0.24);
}

.fab-export {
    background: linear-gradient(135deg, #b45309 0%, #d97706 45%, #f59e0b 100%);
    box-shadow:
        0 10px 22px rgba(180, 83, 9, 0.44),
        inset 0 0 0 1px rgba(255, 255, 255, 0.22);
}

.summary-bar {
    margin-bottom: 10px;
    display: flex;
    gap: 14px;
    color: #c7d2fe;
    font-size: 13px;
}

.export-container {
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(2, 6, 23, 0.4);
    padding: 12px;
}

.export-head {
    margin-bottom: 10px;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(15, 23, 42, 0.65);
}

.export-head p {
    margin: 4px 0 0;
    color: #cbd5e1;
    font-size: 12px;
    word-break: break-all;
}

.result-grid {
    display: grid;
    grid-template-columns: 1.25fr 1fr;
    gap: 14px;
    min-height: 360px;
}

.screenshot-pane {
    position: relative;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    overflow: hidden;
    min-height: 320px;
}

.screenshot-wrapper {
    position: relative;
    width: 100%;
    user-select: none;
}

.screenshot-wrapper.drawing {
    cursor: crosshair;
}

.screenshot {
    display: block;
    width: 100%;
    height: auto;
    object-fit: contain;
    background: #0b1021;
}

.overlay-box {
    position: absolute;
    border: 2px solid rgba(34, 211, 238, 0.7);
    background: rgba(34, 211, 238, 0.15);
    pointer-events: none;
    transition:
        border-color 0.2s ease,
        background 0.2s ease,
        box-shadow 0.2s ease;
}

.overlay-box.active {
    border-color: rgba(99, 102, 241, 1);
    background: rgba(99, 102, 241, 0.3);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.35);
}

.overlay-box.manual {
    border-color: rgba(16, 185, 129, 0.95);
    background: rgba(16, 185, 129, 0.15);
}

.overlay-box.rejected {
    border-color: rgba(248, 113, 113, 0.7);
    background: rgba(248, 113, 113, 0.16);
}

.overlay-box.preview {
    border-style: dashed;
    border-color: rgba(16, 185, 129, 0.95);
    background: rgba(16, 185, 129, 0.18);
}

.issues-pane {
    position: relative;
    overflow-x: hidden;
    overflow-y: auto;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 6px 4px;
    background: rgba(255, 255, 255, 0.02);
}

.issue-item.positioned {
    position: absolute;
    left: 0;
    right: 0;
    margin: 0;
}

.issue-item.positioned.active {
    border-color: rgba(99, 102, 241, 0.7);
    box-shadow: 0 8px 18px rgba(0, 0, 0, 0.35);
}

.issue-item {
    padding: 12px 14px;
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.06);
}

.issue-item.rejected {
    opacity: 0.7;
    border-color: rgba(248, 113, 113, 0.45);
}

.issue-item.manual {
    border-color: rgba(52, 211, 153, 0.45);
}

.issue-top {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.issue-controls {
    margin-top: 8px;
    margin-bottom: 8px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.mini-btn {
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: rgba(15, 23, 42, 0.8);
    color: #e2e8f0;
    padding: 4px 10px;
    font-size: 12px;
    cursor: pointer;
}

.mini-btn.active {
    border-color: rgba(16, 185, 129, 0.85);
    color: #6ee7b7;
}

.mini-btn.reject.active {
    border-color: rgba(248, 113, 113, 0.8);
    color: #fda4af;
}

.mini-btn.danger {
    border-color: rgba(248, 113, 113, 0.45);
    color: #f87171;
}

.badge {
    padding: 4px 8px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
}

.badge.sev-warn {
    background: rgba(250, 204, 21, 0.15);
    color: #facc15;
}

.badge.sev-critical {
    background: rgba(248, 113, 113, 0.18);
    color: #f87171;
}

.badge.sev-info {
    background: rgba(59, 130, 246, 0.15);
    color: #93c5fd;
}

.type {
    color: #e5e7eb;
    font-weight: 600;
}

.confidence {
    color: #9ca3af;
    font-size: 13px;
}

.decision {
    margin-left: auto;
    padding: 4px 8px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
}

.decision-pending {
    background: rgba(59, 130, 246, 0.18);
    color: #93c5fd;
}

.decision-accepted {
    background: rgba(16, 185, 129, 0.2);
    color: #6ee7b7;
}

.decision-rejected {
    background: rgba(248, 113, 113, 0.2);
    color: #fda4af;
}

.quote {
    margin: 8px 0 4px;
    color: #cbd5e1;
    line-height: 1.5;
}

.recommend {
    margin: 0 0 6px;
    color: #c7d2fe;
}

.annotation-label {
    display: block;
    margin: 8px 0 4px;
    font-size: 12px;
    color: #a5b4fc;
}

.annotation-input {
    width: 100%;
    min-height: 58px;
    border-radius: 8px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: rgba(15, 23, 42, 0.65);
    color: #f8fafc;
    padding: 8px;
    resize: vertical;
    font-size: 13px;
}

.meta {
    margin-top: 8px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    color: #9ca3af;
    font-size: 12px;
}

.export-mode .issues-pane {
    overflow: visible;
}

@media (max-width: 720px) {
    .input-group {
        flex-direction: column;
    }

    button.primary {
        width: 100%;
    }

    .result-grid {
        grid-template-columns: 1fr;
    }

    .issues-pane {
        max-height: none;
    }

    .task-row {
        flex-direction: column;
        align-items: stretch;
    }

    .task-actions {
        justify-content: flex-start;
    }

    .decision {
        margin-left: 0;
    }

    .floating-actions {
        width: calc(100vw - 24px);
        left: 12px;
        bottom: 12px;
        transform: none;
        justify-content: space-between;
        border-radius: 14px;
        padding: 8px;
    }

    .fab {
        flex: 1;
        text-align: center;
        padding: 10px 12px;
        font-size: 12px;
    }
}
</style>
