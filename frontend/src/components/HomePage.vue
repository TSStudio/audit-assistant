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
                        {{
                            loading
                                ? "提交中..."
                                : taskId
                                  ? "重新提交"
                                  : "开始审计"
                        }}
                    </button>
                </div>
                <p v-if="error" class="error">{{ error }}</p>
                <p v-if="taskId" class="task-id">任务 ID：{{ taskId }}</p>
            </div>
            <div class="progress" v-if="status">
                <div class="bar" :style="{ width: progressWidth }"></div>
            </div>
            <p v-if="message" class="muted">{{ message }}</p>
        </div>

        <div class="card">
            <div class="card-head">
                <div>
                    <p class="eyebrow">步骤 2</p>
                    <h2>审计结果</h2>
                    <p class="muted">
                        左侧为页面截图，右侧为问题列表。悬停问题时，截图对应区域高亮。
                    </p>
                </div>
                <span class="pill">{{ issues.length }} 个问题</span>
            </div>

            <div v-if="!screenshotSrc && issues.length === 0" class="empty">
                <p>尚未生成问题列表。提交 URL 并等待审计完成即可查看结果。</p>
            </div>

            <div v-else class="result-grid">
                <div class="screenshot-pane">
                    <div v-if="screenshotSrc" class="screenshot-wrapper">
                        <img
                            ref="shotImg"
                            class="screenshot"
                            :src="screenshotSrc"
                            alt="页面截图"
                            @load="onShotLoad"
                        />
                        <div
                            v-for="issue in issues"
                            :key="`box-${issue.id}`"
                            v-show="boxForIssue(issue)"
                            class="overlay-box"
                            :class="{ active: hoverIssueId === issue.id }"
                            :style="boxStyle(issue)"
                        ></div>
                    </div>
                    <div v-else class="empty">暂无截图。</div>
                </div>

                <div
                    class="issues-pane"
                    :style="{ height: `${issuesPaneHeight}px` }"
                >
                    <template v-if="positionedIssues.length">
                        <div
                            v-for="item in positionedIssues"
                            :key="item.issue.id"
                            class="issue-item positioned"
                            :class="{ active: hoverIssueId === item.issue.id }"
                            :style="{ top: `${item.top}px` }"
                            :ref="(el) => setIssueRef(item.issue.id, el)"
                            @mouseenter="hoverIssueId = item.issue.id"
                            @mouseleave="hoverIssueId = null"
                        >
                            <div class="issue-top">
                                <span
                                    class="badge"
                                    :class="`sev-${item.issue.severity}`"
                                    >{{ item.issue.severity }}</span
                                >
                                <span class="type">{{ item.issue.type }}</span>
                                <span
                                    v-if="item.issue.confidence"
                                    class="confidence"
                                    >置信度
                                    {{ item.issue.confidence.toFixed(2) }}</span
                                >
                            </div>
                            <p v-if="item.issue.evidence?.quote" class="quote">
                                “{{ item.issue.evidence.quote }}”
                            </p>
                            <p
                                v-if="item.issue.recommendation"
                                class="recommend"
                            >
                                建议：{{ item.issue.recommendation }}
                            </p>
                            <div class="meta">
                                <span v-if="item.issue.evidence?.text_block_id"
                                    >文本段落：{{
                                        item.issue.evidence.text_block_id
                                    }}</span
                                >
                                <span v-if="item.issue.evidence?.image_id"
                                    >图片：{{
                                        item.issue.evidence.image_id
                                    }}</span
                                >
                                <span v-if="item.issue.evidence?.link_id"
                                    >链接：{{
                                        item.issue.evidence.link_id
                                    }}</span
                                >
                            </div>
                        </div>
                    </template>
                    <div v-else class="empty">暂无问题。</div>
                </div>
            </div>
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
const taskId = ref("");
const status = ref("");
const message = ref("");
const issues = ref([]);
const bundle = ref(null);
const targetProgress = ref(0);
const displayProgress = ref(0);
const loading = ref(false);
const error = ref("");
let pollTimer = null;
let easeTimer = null;
const hoverIssueId = ref(null);
const shotImg = ref(null);
const shotNatural = ref({ w: 1, h: 1 });
const shotDisplay = ref({ w: 1, h: 1 });
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
    if (displayProgress.value)
        return `${Math.min(displayProgress.value, 100)}%`;
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
    return `${apiOrigin.value}/captures/${name}`;
});

const issuesPaneHeight = computed(() => {
    return Math.max(shotDisplay.value.h || 400, 400);
});

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
    bundle.value = null;
    targetProgress.value = 0;
    displayProgress.value = 0;
    error.value = "";
    issueHeights.value = {};
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
        // If target is 100, snap to completion
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
            body: JSON.stringify({ url: urlInput.value.trim() }),
        });
        if (!resp.ok) throw new Error(`提交失败：${resp.status}`);
        const data = await resp.json();
        taskId.value = data.task_id;
        status.value = data.status;
        message.value = data.message || "任务已创建，正在启动审计...";
        targetProgress.value = data.progress || 0;
        displayProgress.value = targetProgress.value;
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
        issues.value = data.issues || [];
        bundle.value = data.result || null;
        if (typeof data.progress === "number") {
            targetProgress.value = data.progress;
            if (targetProgress.value >= 100) {
                displayProgress.value = 100;
                stopEaseTimer();
            } else {
                startEaseTimer();
            }
        }

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

watch(issues, () => {
    issueHeights.value = {};
    nextTick(() => {
        // allow refs to re-register
    });
});

function setIssueRef(id, el) {
    if (!el) return;
    const height = el.getBoundingClientRect().height;
    const prev = issueHeights.value?.[id];
    // Avoid reactive churn that can cause update loops
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

function findBlock(issue) {
    const ev = issue?.evidence || {};
    if (!bundle.value?.text_blocks) return null;
    const blocks = bundle.value.text_blocks;

    if (ev.text_block_id) {
        const hit = blocks.find((b) => b.id === ev.text_block_id);
        if (hit) return hit;
    }

    if (ev.quote) {
        const hit = blocks.find((b) => b.text?.includes(ev.quote));
        if (hit) return hit;
    }
    return null;
}

function boxForIssue(issue) {
    const block = findBlock(issue);
    if (!block || !block.bbox) return null;
    return block.bbox;
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
    if (!issues.value?.length) return [];
    const scaleY = shotDisplay.value.h / (shotNatural.value.h || 1);
    const withPos = issues.value
        .map((issue) => {
            const block = findBlock(issue);
            const y = block?.bbox ? block.bbox.y * scaleY : null;
            const height = issueHeights.value?.[issue.id] || 120;
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
        let top;
        if (item.y === null) {
            top = cursor;
        } else {
            top = Math.max(item.y, cursor);
        }
        placed.push({ issue: item.issue, top, height: item.height });
        cursor = top + item.height + minIssueGap;
    }

    return placed;
});
</script>

<style scoped>
.panel {
    display: grid;
    grid-template-columns: 1fr;
    gap: 18px;
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

.empty {
    padding: 14px;
    border: 1px dashed rgba(255, 255, 255, 0.16);
    border-radius: 10px;
    color: #9ca3af;
}

.result-grid {
    display: grid;
    grid-template-columns: 1.3fr 1fr;
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
    height: 100%;
}

.screenshot {
    display: block;
    width: 100%;
    height: 100%;
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

.issues-pane {
    position: relative;
    overflow: hidden;
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

.issue-list {
    list-style: none;
    padding: 0;
    margin: 12px 0 0;
    display: grid;
    gap: 10px;
}

.issue-item {
    padding: 12px 14px;
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.06);
}

.issue-top {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
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

.quote {
    margin: 8px 0 4px;
    color: #cbd5e1;
    line-height: 1.5;
}

.recommend {
    margin: 0 0 6px;
    color: #c7d2fe;
}

.meta {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    color: #9ca3af;
    font-size: 12px;
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
}
</style>
