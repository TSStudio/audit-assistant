import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

const API_BASE =
    process.env.NODE_ENV === "development"
        ? "http://localhost:8000/api"
        : "/api";
const USER_TOKEN_COOKIE = "audit_user_token";
const MIN_GAP = 14;

const SEV_COLORS = {
    critical: "#f0817a",
    warn: "#f5c97a",
    error: "#f0817a",
    info: "#80b8f0",
};

const funMessages = [
    "正在用 AI 眼睛扫描页面…",
    "召唤多模态模型中…",
    "逐字逐句排查问题…",
    "核对图文一致性…",
    "汇总发现的所有线索…",
    "生成审计报告…",
];

function readCookie(name) {
    const all = document.cookie ? document.cookie.split(";") : [];
    for (const chunk of all) {
        const [k, ...rest] = chunk.trim().split("=");
        if (k === name) return decodeURIComponent(rest.join("="));
    }
    return "";
}

function randomToken() {
    const raw = Math.random().toString(36).slice(2) + Date.now().toString(36);
    return `u_${raw.slice(0, 24)}`;
}

function ensureUserToken() {
    const old = readCookie(USER_TOKEN_COOKIE);
    if (old) return old;
    const token = randomToken();
    document.cookie = `${USER_TOKEN_COOKIE}=${encodeURIComponent(token)}; path=/; max-age=31536000; samesite=lax`;
    return token;
}

const userToken = ensureUserToken();
const HISTORY_KEY = `audit_task_history_${userToken}`;

// ★ 真实今日计数 key，按自然日 + 用户 token 隔离
function todayKey() {
    return `audit_today_${new Date().toLocaleDateString("zh-CN")}_${userToken}`;
}

function apiFetch(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("X-User-Token", userToken);
    return fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
        credentials: "include",
    });
}

function deriveTitle(url) {
    try {
        const u = new URL(url);
        const seg =
            u.pathname.replace(/\/$/, "").split("/").filter(Boolean).pop() ||
            "";
        const dec = decodeURIComponent(seg)
            .replace(/[-_]/g, " ")
            .replace(/\.\w+$/, "");
        return dec
            ? `${dec} · ${u.hostname.replace(/^www\./, "")}`
            : u.hostname.replace(/^www\./, "");
    } catch {
        return url;
    }
}

function normalizeText(value) {
    return String(value || "").trim();
}

function isRealTitle(value) {
    const text = normalizeText(value);
    return !!text && !/^https?:\/\//i.test(text) && !/^upload:\/\//i.test(text);
}

function resolveBundleTitle(result) {
    const title = normalizeText(result?.title);
    return isRealTitle(title) ? title : "";
}

function parseChecklist(v) {
    return (v || "")
        .split(/\r?\n/)
        .map((s) => s.trim())
        .filter(Boolean);
}

function normalizeIssues(raw = []) {
    return raw.map((issue, idx) => {
        const n = issue ? { ...issue } : {};
        if (!n.id) n.id = `issue-${idx + 1}`;
        const ev =
            n.evidence && typeof n.evidence === "object"
                ? { ...n.evidence }
                : {};
        if (ev.text_block_id == null) delete ev.text_block_id;
        n.evidence = ev;
        n.manual = false;
        return n;
    });
}

export default function useHomePageLogic() {
    const slowModeEnabled = false;
    const tab = ref("submit");
    const showMotivation = ref(true);
    const inputMode = ref("url");
    const auditSpeed = ref("fast");
    const urlInput = ref("");
    const selectedFile = ref(null);
    const fileInputRef = ref(null);
    const referenceFiles = ref([]);
    const referenceFileInputRef = ref(null);
    const checklistInput = ref("");
    const newChecklistName = ref("");
    const checklistKbs = ref([]);
    const referenceKbs = ref([]);
    const selectedChecklistKbIds = ref([]);
    const selectedReferenceKbIds = ref([]);
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
    const hoverIssueId = ref(null);
    const taskHistory = ref([]);
    const currentSourceMeta = ref({
        source_type: "url",
        source_label: "",
        url: "",
        file_name: "",
        article_title: "",
    });

    // ★ 真实今日计数：从 localStorage 读取当日数值
    const todayCount = ref(
        parseInt(localStorage.getItem(todayKey()) || "0", 10),
    );

    const toastMsg = ref("");
    const shotImg = ref(null);
    const shotWrapper = ref(null);
    const shotNatural = ref({ w: 1, h: 1 });
    const shotDisplay = ref({ w: 1, h: 1 });
    const drawingMode = ref(false);
    const isDrawing = ref(false);
    const drawStart = ref(null);
    const drawCurrent = ref(null);
    const issueHeights = ref({});

    let pollTimer = null;
    let easeTimer = null;
    let toastTimer = null;
    let issueMeasureFrame = 0;

    const issueElements = new Map();
    const issueResizeObserver =
        typeof ResizeObserver === "undefined"
            ? null
            : new ResizeObserver((entries) => {
                  for (const entry of entries) {
                      const id = entry.target?.dataset?.id;
                      if (!id) continue;
                      queueIssueHeightMeasure(id, entry.target);
                  }
              });

    // ★ resetState 回调机制，供外部（如 collabVm）注册
    const _resetCallbacks = [];
    function onReset(cb) {
        _resetCallbacks.push(cb);
    }

    const achievements = ref([
        {
            id: 1,
            icon: "⚡",
            name: "审校先锋",
            color: "amber",
            unlocked: false,
            goal: "首次审计",
        },
        {
            id: 2,
            icon: "🔥",
            name: "连续 7 天",
            color: "green",
            unlocked: false,
            goal: "完成 3 篇",
        },
        {
            id: 3,
            icon: "🏆",
            name: "审校达人",
            color: "blue",
            unlocked: false,
            goal: "完成 5 篇",
        },
        {
            id: 4,
            icon: "💎",
            name: "精英审校",
            color: "gray",
            unlocked: false,
            goal: "完成 10 篇",
        },
    ]);

    // ★ 根据 todayCount 实时解锁成就
    function refreshAchievements() {
        const n = todayCount.value;
        achievements.value = achievements.value.map((a, i) => {
            const thresholds = [1, 3, 5, 10];
            return { ...a, unlocked: n >= thresholds[i] };
        });
    }

    const displayIssues = computed(() => [
        ...issues.value,
        ...customIssues.value,
    ]);

    const tabLabel = computed(
        () =>
            ({ submit: "新建审计", result: "审计结果", history: "历史记录" })[
                tab.value
            ] || "",
    );

    const statusLabel = computed(
        () =>
            ({ running: "审计中…", completed: "已完成", failed: "失败" })[
                status.value
            ] || "待开始",
    );

    const pillClass = computed(
        () =>
            ({ running: "pill-run", completed: "pill-ok", failed: "pill-err" })[
                status.value
            ] || "pill-idle",
    );

    const progressWidth = computed(() => {
        if (status.value === "completed" || status.value === "failed")
            return "100%";
        return `${Math.min(displayProgress.value, 100)}%`;
    });

    const selectedFileName = computed(() => selectedFile.value?.name || "");

    const referenceFileNamesText = computed(() => {
        const n = referenceFiles.value.length;
        if (!n) return "未选择附加资料";
        return n === 1 ? referenceFiles.value[0].name : `已选择 ${n} 个文件`;
    });

    const apiOrigin = computed(() =>
        API_BASE.startsWith("http") ? API_BASE.replace(/\/api$/, "") : "",
    );

    const screenshotSrc = computed(() => {
        const file = bundle.value?.screenshots?.[0]?.filename;
        if (!file) return "";
        const norm = String(file).replace(/\\/g, "/");
        const idx = norm.lastIndexOf("/captures/");
        const rel =
            idx >= 0
                ? norm.slice(idx + "/captures/".length)
                : norm.split("/").pop() || "";
        const enc = rel
            .split("/")
            .filter(Boolean)
            .map((s) => encodeURIComponent(s))
            .join("/");
        return enc ? `${apiOrigin.value}/api/captures/${enc}` : "";
    });

    const issuesForList = computed(() =>
        exportMode.value
            ? displayIssues.value.filter((i) => !isRejected(i.id))
            : displayIssues.value,
    );

    const issuesWithBox = computed(() =>
        displayIssues.value.filter(
            (i) => i.evidence?.bbox && !isRejected(i.id),
        ),
    );

    const issuesPaneH = computed(() =>
        Math.max(shotDisplay.value.h || 420, 420),
    );

    const motIcon = computed(() => {
        if (tab.value === "history") return "📈";
        if (tab.value === "result" && displayIssues.value.length) return "🎯";
        return "🌟";
    });

    const decisionStats = computed(() => {
        let kept = 0,
            rejected = 0;
        for (const i of displayIssues.value)
            isRejected(i.id) ? rejected++ : kept++;
        return { kept, rejected };
    });

    const allResolved = computed(
        () =>
            displayIssues.value.length > 0 &&
            displayIssues.value.every((i) => isRejected(i.id)),
    );

    const motTitle = computed(() => {
        if (tab.value === "history") return "本周已审 12 篇，进步明显！";
        if (tab.value === "result" && displayIssues.value.length)
            return `发现 ${displayIssues.value.length} 个问题，做得很好！`;
        return todayCount.value === 0
            ? "开始今天的第一次审计吧！"
            : `今日已完成 ${todayCount.value} 篇，继续保持！`;
    });

    const motSub = computed(() => {
        if (tab.value === "history")
            return "平均每篇发现 2.4 个问题，比上周减少 30%。";
        if (tab.value === "result" && displayIssues.value.length)
            return `你已驳回 ${decisionStats.value.rejected} 条 AI 建议，保持判断力。`;
        const next = achievements.value.find((a) => !a.unlocked);
        return next
            ? `再完成更多篇可解锁「${next.name}」成就。`
            : "所有成就已解锁，厉害了！";
    });

    const positionedIssues = computed(() => {
        if (!issuesForList.value?.length) return [];
        const sy = shotDisplay.value.h / (shotNatural.value.h || 1);
        const withPos = issuesForList.value
            .map((issue) => {
                const bbox = issue?.evidence?.bbox;
                return {
                    issue,
                    y: bbox ? bbox.y * sy : null,
                    height: issueHeights.value?.[issue.id] || 205,
                };
            })
            .sort((a, b) => {
                if (a.y === null && b.y === null) return 0;
                if (a.y === null) return 1;
                if (b.y === null) return -1;
                return a.y - b.y;
            });
        let cursor = 0;
        return withPos.map((it) => {
            const top = it.y === null ? cursor : Math.max(it.y, cursor);
            cursor = top + it.height + MIN_GAP;
            return { issue: it.issue, top, height: it.height };
        });
    });

    const positionedBottom = computed(() =>
        positionedIssues.value.reduce(
            (m, it) => Math.max(m, it.top + it.height),
            0,
        ),
    );

    const issuesPaneRenderHeight = computed(() =>
        exportMode.value
            ? Math.max(issuesPaneH.value, positionedBottom.value + 24)
            : issuesPaneH.value,
    );

    const drawingPreview = computed(() => {
        if (!drawStart.value || !drawCurrent.value) return null;
        const x = Math.min(drawStart.value.x, drawCurrent.value.x);
        const y = Math.min(drawStart.value.y, drawCurrent.value.y);
        return {
            left: `${x}px`,
            top: `${y}px`,
            width: `${Math.abs(drawCurrent.value.x - drawStart.value.x)}px`,
            height: `${Math.abs(drawCurrent.value.y - drawStart.value.y)}px`,
        };
    });

    const donutSegments = computed(() => {
        const total = displayIssues.value.length;
        if (!total) return [];
        const counts = {};
        for (const i of displayIssues.value) {
            const k = i.severity || "info";
            counts[k] = (counts[k] || 0) + 1;
        }
        const circ = 2 * Math.PI * 24;
        let offset = 0;
        return Object.entries(counts).map(([sev, cnt]) => {
            const frac = cnt / total;
            const dash = frac * circ - 1;
            const seg = {
                label: sev,
                count: cnt,
                color: SEV_COLORS[sev] || "#b0aca6",
                dash,
                gap: circ - dash,
                offset: -90 + offset * 360,
            };
            offset += frac;
            return seg;
        });
    });

    const compareDiff = computed(() => {
        const completed = taskHistory.value.filter(
            (t) => t.status === "completed" && t.issueCount != null,
        );
        if (completed.length < 2) return 0;
        return (completed[0].issueCount || 0) - (completed[1].issueCount || 0);
    });

    const compareGood = computed(() => compareDiff.value <= 0);

    const currentSourceLabel = computed(() =>
        historyTitle(currentSourceMeta.value),
    );

    function historyTitle(item) {
        if (!item) return "未命名任务";
        const derived = item.url ? deriveTitle(item.url) : "";
        const articleTitle = isRealTitle(item.article_title)
            ? normalizeText(item.article_title)
            : "";
        if (articleTitle) return articleTitle;
        const storedTitle = isRealTitle(item.title)
            ? normalizeText(item.title)
            : "";
        if (storedTitle && storedTitle !== derived) return storedTitle;
        if (item.source_type === "file") {
            if (item.file_name) return `[文件] ${item.file_name}`;
            if (isRealTitle(item.source_label))
                return normalizeText(item.source_label);
        }
        if (
            isRealTitle(item.source_label) &&
            !/^https?:\/\//i.test(item.source_label)
        )
            return normalizeText(item.source_label);
        return derived || "未命名任务";
    }

    function buildHistoryItem(
        task_id,
        sourceMeta,
        data,
        checklist,
        issueCount,
    ) {
        const article_title =
            resolveBundleTitle(data?.result) ||
            normalizeText(sourceMeta?.article_title);
        const item = {
            task_id,
            url: sourceMeta.url,
            article_title,
            source_type: sourceMeta.source_type,
            source_label: sourceMeta.source_label,
            file_name: sourceMeta.file_name,
            checklist,
            status: data.status,
            progress: data.progress ?? 0,
            updated_at: Math.floor(Date.now() / 1000),
        };
        if (issueCount != null) item.issueCount = issueCount;
        item.title = historyTitle(item);
        return item;
    }

    function loadHistory() {
        try {
            const parsed = JSON.parse(
                localStorage.getItem(HISTORY_KEY) || "[]",
            );
            taskHistory.value = Array.isArray(parsed)
                ? parsed.map((item) => ({
                      ...(item || {}),
                      title: historyTitle(item || {}),
                  }))
                : [];
        } catch {
            taskHistory.value = [];
        }
    }

    function saveHistory(list) {
        taskHistory.value = list;
        localStorage.setItem(HISTORY_KEY, JSON.stringify(list));
    }

    function upsertHistory(item) {
        const list = [...taskHistory.value];
        const i = list.findIndex((t) => t.task_id === item.task_id);
        if (i >= 0) list[i] = { ...list[i], ...item };
        else list.unshift(item);
        saveHistory(list.slice(0, 50));
    }

    function removeTask(item) {
        saveHistory(
            taskHistory.value.filter((t) => t.task_id !== item.task_id),
        );
    }

    function clearHistory() {
        saveHistory([]);
    }

    function dotColor(s) {
        return (
            {
                running: "#d97706",
                llm_vlm_working: "#d97706",
                llm_done_vlm_working: "#c97a00",
                llm_working_vlm_done: "#b7791f",
                llm_vlm_done: "#2d9e5f",
                completed: "#2d9e5f",
                failed: "#dc2626",
            }[s] || "#b0aca6"
        );
    }

    function statusText(s) {
        return (
            {
                running: "运行中",
                llm_vlm_working: "LLM/VLM 并行审核中",
                llm_done_vlm_working: "LLM完成，VLM进行中",
                llm_working_vlm_done: "VLM完成，LLM进行中",
                llm_vlm_done: "LLM/VLM审核完成",
                completed: "已完成",
                failed: "失败",
            }[s] ||
            s ||
            "未知"
        );
    }

    function fmtTime(ts) {
        if (!ts) return "";
        return new Date(ts * 1000).toLocaleString("zh-CN", {
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    function formatChecklist(list) {
        if (!list?.length) return "";
        const p = list.slice(0, 3).join("、");
        return list.length > 3 ? `${p}…` : p;
    }

    function showToast(msg) {
        toastMsg.value = msg;
        if (toastTimer) clearTimeout(toastTimer);
        toastTimer = setTimeout(() => {
            toastMsg.value = "";
        }, 2600);
    }

    function stopEase() {
        if (easeTimer) {
            clearInterval(easeTimer);
            easeTimer = null;
        }
    }

    function startEase() {
        stopEase();
        easeTimer = setInterval(() => {
            if (targetProgress.value >= 100) {
                displayProgress.value = 100;
                stopEase();
                return;
            }
            displayProgress.value +=
                (targetProgress.value - displayProgress.value) / 4;
        }, 800);
    }

    function stopPoll() {
        if (pollTimer) {
            clearTimeout(pollTimer);
            pollTimer = null;
        }
    }

    function resetState() {
        stopPoll();
        stopEase();
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
        // ★ 通知外部（collabVm）重置协作状态
        for (const cb of _resetCallbacks) cb();
    }

    function switchMode(mode) {
        if (loading.value) return;
        inputMode.value = mode;
        error.value = "";
        if (mode === "url") {
            selectedFile.value = null;
            if (fileInputRef.value) fileInputRef.value.value = "";
        }
    }

    function onFileChange(e) {
        selectedFile.value = e?.target?.files?.[0] || null;
    }
    function onReferenceFilesChange(e) {
        referenceFiles.value = Array.from(e?.target?.files || []);
    }

    async function loadKnowledgeBases() {
        const [clResp, refResp] = await Promise.all([
            apiFetch("/kb/checklists"),
            apiFetch("/kb/references"),
        ]);
        if (clResp.ok) {
            const data = await clResp.json();
            checklistKbs.value = Array.isArray(data.items) ? data.items : [];
        }
        if (refResp.ok) {
            const data = await refResp.json();
            referenceKbs.value = Array.isArray(data.items) ? data.items : [];
        }
    }

    async function saveChecklistToKb() {
        try {
            const items = parseChecklist(checklistInput.value);
            if (!items.length) {
                error.value = "清单为空，无法保存";
                return;
            }
            const resp = await apiFetch("/kb/checklists", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: (newChecklistName.value || "未命名清单").trim(),
                    items,
                }),
            });
            if (!resp.ok) {
                throw new Error(
                    (await resp.text()) || `保存清单失败：${resp.status}`,
                );
            }
            const created = await resp.json();
            checklistKbs.value = [created, ...checklistKbs.value];
            selectedChecklistKbIds.value = [
                created.kb_id,
                ...selectedChecklistKbIds.value,
            ];
            newChecklistName.value = "";
            showToast("清单已保存到知识库");
        } catch (e) {
            error.value = e?.message || "保存清单失败";
        }
    }

    async function saveReferencesToKb() {
        try {
            if (!referenceFiles.value.length) {
                error.value = "请先选择附加资料文件";
                return;
            }
            const fd = new FormData();
            for (const f of referenceFiles.value) fd.append("files", f);
            const resp = await apiFetch("/kb/references/upload", {
                method: "POST",
                body: fd,
            });
            if (!resp.ok)
                throw new Error(
                    (await resp.text()) || `保存附加资料失败：${resp.status}`,
                );
            const data = await resp.json();
            const created = Array.isArray(data.items) ? data.items : [];
            if (created.length) {
                referenceKbs.value = [...created, ...referenceKbs.value];
                selectedReferenceKbIds.value = [
                    ...new Set([
                        ...created.map((i) => i.kb_id),
                        ...selectedReferenceKbIds.value,
                    ]),
                ];
            }
            referenceFiles.value = [];
            if (referenceFileInputRef.value)
                referenceFileInputRef.value.value = "";
            showToast("附加资料已保存到知识库");
        } catch (e) {
            error.value = e?.message || "保存附加资料失败";
            throw e;
        }
    }

    async function renameChecklistKb(item) {
        try {
            const name = window.prompt(
                "请输入新的清单名称",
                String(item?.name || "").trim(),
            );
            if (name == null) return;
            const trimmed = name.trim();
            if (!trimmed) {
                error.value = "名称不能为空";
                return;
            }
            const resp = await apiFetch(`/kb/checklists/${item.kb_id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: trimmed }),
            });
            if (!resp.ok) throw new Error(`改名失败：${resp.status}`);
            const updated = await resp.json();
            checklistKbs.value = checklistKbs.value.map((v) =>
                v.kb_id === updated.kb_id ? updated : v,
            );
            showToast("清单知识库已改名");
        } catch (e) {
            error.value = e?.message || "清单改名失败";
        }
    }

    async function deleteChecklistKb(item) {
        try {
            if (!window.confirm(`确认删除清单知识库"${item?.name || ""}"？`))
                return;
            const resp = await apiFetch(`/kb/checklists/${item.kb_id}`, {
                method: "DELETE",
            });
            if (!resp.ok) throw new Error(`删除失败：${resp.status}`);
            checklistKbs.value = checklistKbs.value.filter(
                (v) => v.kb_id !== item.kb_id,
            );
            selectedChecklistKbIds.value = selectedChecklistKbIds.value.filter(
                (id) => id !== item.kb_id,
            );
            showToast("清单知识库已删除");
        } catch (e) {
            error.value = e?.message || "清单删除失败";
        }
    }

    async function renameReferenceKb(item) {
        try {
            const name = window.prompt(
                "请输入新的资料库名称",
                String(item?.name || "").trim(),
            );
            if (name == null) return;
            const trimmed = name.trim();
            if (!trimmed) {
                error.value = "名称不能为空";
                return;
            }
            const resp = await apiFetch(`/kb/references/${item.kb_id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: trimmed }),
            });
            if (!resp.ok) throw new Error(`改名失败：${resp.status}`);
            const updated = await resp.json();
            referenceKbs.value = referenceKbs.value.map((v) =>
                v.kb_id === updated.kb_id ? updated : v,
            );
            showToast("附加资料知识库已改名");
        } catch (e) {
            error.value = e?.message || "资料库改名失败";
        }
    }

    async function deleteReferenceKb(item) {
        try {
            if (!window.confirm(`确认删除资料库"${item?.name || ""}"？`))
                return;
            const resp = await apiFetch(`/kb/references/${item.kb_id}`, {
                method: "DELETE",
            });
            if (!resp.ok) throw new Error(`删除失败：${resp.status}`);
            referenceKbs.value = referenceKbs.value.filter(
                (v) => v.kb_id !== item.kb_id,
            );
            selectedReferenceKbIds.value = selectedReferenceKbIds.value.filter(
                (id) => id !== item.kb_id,
            );
            showToast("附加资料知识库已删除");
        } catch (e) {
            error.value = e?.message || "资料库删除失败";
        }
    }

    // ★ 真实计数：审计完成时 +1 并写入 localStorage
    function incrementTodayCount() {
        todayCount.value++;
        localStorage.setItem(todayKey(), String(todayCount.value));
        refreshAchievements();
    }

    async function startAudit() {
        let sourceMeta;
        if (inputMode.value === "url") {
            if (!urlInput.value.trim()) {
                error.value = "请输入有效的 URL";
                return;
            }
            sourceMeta = {
                source_type: "url",
                source_label: urlInput.value.trim(),
                url: urlInput.value.trim(),
                file_name: "",
                article_title: "",
            };
        } else {
            if (!selectedFile.value) {
                error.value = "请先选择要上传的文件";
                return;
            }
            sourceMeta = {
                source_type: "file",
                source_label: `[上传] ${selectedFile.value.name}`,
                url: "",
                file_name: selectedFile.value.name,
                article_title: "",
            };
        }
        resetState();
        loading.value = true;
        try {
            if (referenceFiles.value.length) await saveReferencesToKb();
            const cl = parseChecklist(checklistInput.value);
            const selectedChecklistIds = [...selectedChecklistKbIds.value];
            const selectedReferenceIds = [...selectedReferenceKbIds.value];
            let resp;
            if (inputMode.value === "url") {
                const fd = new FormData();
                fd.append("url", urlInput.value.trim());
                fd.append("checklist", JSON.stringify(cl));
                fd.append(
                    "fast_mode",
                    String(!slowModeEnabled || auditSpeed.value === "fast"),
                );
                fd.append(
                    "selected_checklist_ids",
                    JSON.stringify(selectedChecklistIds),
                );
                fd.append(
                    "selected_reference_ids",
                    JSON.stringify(selectedReferenceIds),
                );
                resp = await apiFetch("/audit/url", {
                    method: "POST",
                    body: fd,
                });
            } else {
                const fd = new FormData();
                fd.append("file", selectedFile.value);
                fd.append("checklist", JSON.stringify(cl));
                fd.append(
                    "fast_mode",
                    String(!slowModeEnabled || auditSpeed.value === "fast"),
                );
                fd.append(
                    "selected_checklist_ids",
                    JSON.stringify(selectedChecklistIds),
                );
                fd.append(
                    "selected_reference_ids",
                    JSON.stringify(selectedReferenceIds),
                );
                resp = await apiFetch("/audit/upload", {
                    method: "POST",
                    body: fd,
                });
            }
            if (!resp.ok) throw new Error(`提交失败：${resp.status}`);
            const data = await resp.json();
            taskId.value = data.task_id;
            status.value = data.status;
            message.value = funMessages[0];
            issues.value = normalizeIssues(data.issues || []);
            bundle.value = data.result || null;
            currentSourceMeta.value = {
                ...sourceMeta,
                article_title: resolveBundleTitle(data.result),
            };
            upsertHistory(
                buildHistoryItem(
                    data.task_id,
                    currentSourceMeta.value,
                    data,
                    cl,
                ),
            );
            const p =
                typeof data.progress === "number"
                    ? data.progress
                    : data.status === "completed"
                      ? 100
                      : 0;
            targetProgress.value = p;
            displayProgress.value = p;
            tab.value = "submit";
            if (data.status !== "completed" && data.status !== "failed") {
                startEase();
                schedulePoll(data.task_id);
            }
        } catch (e) {
            error.value = e?.message || "提交失败";
        } finally {
            loading.value = false;
        }
    }

    function schedulePoll(id) {
        pollTimer = setTimeout(() => doPoll(id), 1500);
    }

    async function doPoll(id) {
        try {
            const resp = await apiFetch(`/audit/${id}`);
            if (!resp.ok) throw new Error("查询失败");
            const data = await resp.json();
            status.value = data.status;
            issues.value = normalizeIssues(data.issues);
            bundle.value = data.result || null;
            if (Array.isArray(data.checklist))
                checklistInput.value = data.checklist.join("\n");
            if (typeof data.progress === "number")
                targetProgress.value = data.progress;
            const articleTitle = resolveBundleTitle(data.result);
            if (
                articleTitle &&
                articleTitle !== currentSourceMeta.value.article_title
            )
                currentSourceMeta.value = {
                    ...currentSourceMeta.value,
                    article_title: articleTitle,
                };
            const idx = Math.min(
                Math.floor(data.progress / 18),
                funMessages.length - 1,
            );
            message.value =
                data.status === "completed"
                    ? `审计完成，发现 ${data.issues?.length || 0} 个问题！`
                    : funMessages[idx];
            upsertHistory(
                buildHistoryItem(
                    id,
                    currentSourceMeta.value,
                    data,
                    data.checklist || parseChecklist(checklistInput.value),
                    (data.issues || []).length,
                ),
            );
            if (data.status === "completed" || data.status === "failed") {
                targetProgress.value = 100;
                displayProgress.value = 100;
                stopPoll();
                stopEase();
                if (data.status === "completed") {
                    // ★ 真实计数：每次审计完成 +1
                    incrementTodayCount();
                    showToast(
                        `审计完成！发现 ${data.issues?.length || 0} 个问题`,
                    );
                    tab.value = "result";
                }
            } else schedulePoll(id);
        } catch (e) {
            error.value = e?.message || "查询失败";
            stopPoll();
            stopEase();
        }
    }

    function loadTask(item) {
        if (!item?.task_id) return;
        resetState();
        currentSourceMeta.value = {
            source_type: item.source_type || "url",
            source_label: item.source_label || item.url || "",
            url: item.url || "",
            file_name: item.file_name || "",
            article_title: item.article_title || "",
        };
        inputMode.value = item.source_type === "file" ? "file" : "url";
        urlInput.value = item.url || "";
        selectedFile.value = null;
        if (fileInputRef.value) fileInputRef.value.value = "";
        if (referenceFileInputRef.value) referenceFileInputRef.value.value = "";
        referenceFiles.value = [];
        checklistInput.value = (item.checklist || []).join("\n");
        taskId.value = item.task_id;
        status.value = item.status || "";
        message.value = "正在加载任务状态…";
        targetProgress.value = item.progress ?? 0;
        displayProgress.value = targetProgress.value;
        tab.value = "result";
        schedulePoll(item.task_id);
    }

    function rerunTask(item) {
        if (item?.source_type && item.source_type !== "url") {
            error.value = "上传任务无法直接重跑，请重新选择文件后提交。";
            return;
        }
        if (!item?.url) return;
        switchMode("url");
        urlInput.value = item.url;
        tab.value = "submit";
        nextTick(startAudit);
    }

    const isRejected = (id) => !!decisionMap.value?.[id];
    const rejectIssue = (id) => {
        decisionMap.value = { ...decisionMap.value, [id]: true };
        showToast("已驳回，你的判断已记录");
    };
    const undoReject = (id) => {
        decisionMap.value = { ...decisionMap.value, [id]: false };
        showToast("已撤销驳回");
    };
    const noteForIssue = (id) => noteMap.value?.[id] || "";
    const updateNote = (id, t) => {
        noteMap.value = { ...noteMap.value, [id]: t };
    };

    function removeCustomIssue(id) {
        customIssues.value = customIssues.value.filter((i) => i.id !== id);
        const nd = { ...decisionMap.value },
            nn = { ...noteMap.value };
        delete nd[id];
        delete nn[id];
        decisionMap.value = nd;
        noteMap.value = nn;
    }

    function clearCustomIssues() {
        const ids = new Set(customIssues.value.map((i) => i.id));
        customIssues.value = [];
        const nd = { ...decisionMap.value },
            nn = { ...noteMap.value };
        for (const id of ids) {
            delete nd[id];
            delete nn[id];
        }
        decisionMap.value = nd;
        noteMap.value = nn;
    }

    function toggleDrawingMode() {
        drawingMode.value = !drawingMode.value;
        isDrawing.value = false;
        drawStart.value = null;
        drawCurrent.value = null;
    }

    function localPoint(e) {
        if (!shotImg.value) return null;
        const r = shotImg.value.getBoundingClientRect();
        if (!r.width || !r.height) return null;
        return {
            x: Math.max(0, Math.min(e.clientX - r.left, r.width)),
            y: Math.max(0, Math.min(e.clientY - r.top, r.height)),
        };
    }

    function beginDraw(e) {
        if (!drawingMode.value || !shotImg.value || shotNatural.value.w <= 1)
            return;
        e.preventDefault();
        const p = localPoint(e);
        if (!p) return;
        isDrawing.value = true;
        drawStart.value = p;
        drawCurrent.value = p;
    }

    function moveDraw(e) {
        if (!isDrawing.value) return;
        e.preventDefault();
        const p = localPoint(e);
        if (p) drawCurrent.value = p;
    }

    function endDraw(e) {
        if (e) e.preventDefault();
        if (!isDrawing.value || !drawStart.value || !drawCurrent.value) {
            isDrawing.value = false;
            drawStart.value = null;
            drawCurrent.value = null;
            return;
        }
        const x = Math.min(drawStart.value.x, drawCurrent.value.x);
        const y = Math.min(drawStart.value.y, drawCurrent.value.y);
        const w = Math.abs(drawCurrent.value.x - drawStart.value.x);
        const h = Math.abs(drawCurrent.value.y - drawStart.value.y);
        if (w >= 4 && h >= 4) appendManualIssue({ x, y, width: w, height: h });
        isDrawing.value = false;
        drawStart.value = null;
        drawCurrent.value = null;
    }

    function cancelDraw() {
        if (isDrawing.value) endDraw();
    }

    function appendManualIssue(box) {
        const sx = shotNatural.value.w / (shotDisplay.value.w || 1);
        const sy = shotNatural.value.h / (shotDisplay.value.h || 1);
        const bbox = {
            x: Math.round(box.x * sx),
            y: Math.round(box.y * sy),
            width: Math.max(1, Math.round(box.width * sx)),
            height: Math.max(1, Math.round(box.height * sy)),
        };
        const id = `manual-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
        customIssues.value = [
            ...customIssues.value,
            {
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
            },
        ];
        undoReject(id);
        updateNote(id, "");
        hoverIssueId.value = id;
        showToast("手工批注已添加，可在卡片中填写内容");
    }

    function onShotLoad(e) {
        const img = e.target;
        shotNatural.value = {
            w: img.naturalWidth || 1,
            h: img.naturalHeight || 1,
        };
        shotDisplay.value = {
            w: img.clientWidth || 1,
            h: img.clientHeight || 1,
        };
    }

    function boxStyle(issue) {
        const bbox = issue?.evidence?.bbox;
        if (!bbox) return {};
        const wrapperRect = shotWrapper.value?.getBoundingClientRect();
        const imageRect = shotImg.value?.getBoundingClientRect();
        const offsetX =
            imageRect && wrapperRect ? imageRect.left - wrapperRect.left : 0;
        const offsetY =
            imageRect && wrapperRect ? imageRect.top - wrapperRect.top : 0;
        const sx = shotDisplay.value.w / (shotNatural.value.w || 1);
        const sy = shotDisplay.value.h / (shotNatural.value.h || 1);
        return {
            left: `${offsetX + bbox.x * sx}px`,
            top: `${offsetY + bbox.y * sy}px`,
            width: `${bbox.width * sx}px`,
            height: `${bbox.height * sy}px`,
        };
    }

    function flushIssueHeightMeasure(id, el) {
        if (!el?.isConnected) return;
        const h = el.getBoundingClientRect().height;
        if (!Number.isFinite(h) || h <= 0) return;
        if (Math.abs((issueHeights.value[id] || 0) - h) < 0.5) return;
        issueHeights.value = { ...issueHeights.value, [id]: h };
    }

    function queueIssueHeightMeasure(id, el) {
        if (!id || !el) return;
        if (issueMeasureFrame) cancelAnimationFrame(issueMeasureFrame);
        issueMeasureFrame = requestAnimationFrame(() => {
            issueMeasureFrame = 0;
            flushIssueHeightMeasure(id, el);
        });
    }

    function setIssueRef(id, el) {
        const prev = issueElements.get(id);
        if (prev && prev !== el) {
            issueResizeObserver?.unobserve(prev);
        }
        if (!el) {
            issueElements.delete(id);
            return;
        }
        issueElements.set(id, el);
        issueResizeObserver?.observe(el);
        queueIssueHeightMeasure(id, el);
    }

    async function loadLib(url, path) {
        const parts = path.split(".");
        let v = window;
        if (!window[parts[0]]) {
            await new Promise((res, rej) => {
                if (Array.from(document.scripts).some((s) => s.src === url)) {
                    res();
                    return;
                }
                const s = document.createElement("script");
                s.src = url;
                s.async = true;
                s.onload = res;
                s.onerror = () => rej(new Error(`加载失败: ${url}`));
                document.head.appendChild(s);
            });
        }
        for (const p of parts) v = v?.[p];
        if (!v) throw new Error(`${path} 加载失败`);
        return v;
    }

    async function exportPdf() {
        if (exportingPdf.value) return;
        exportingPdf.value = true;
        exportMode.value = true;
        error.value = "";
        await nextTick();
        await new Promise((resolve) => requestAnimationFrame(resolve));
        await new Promise((resolve) => requestAnimationFrame(resolve));
        try {
            const h2c = await loadLib(
                "https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js",
                "html2canvas",
            );
            const jPDF = await loadLib(
                "https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js",
                "jspdf.jsPDF",
            );
            const el =
                document.querySelector(".result-wrap") ||
                document.querySelector(".left-panel");
            if (!el) throw new Error("未找到可导出的内容区域");
            const canvas = await h2c(el, {
                scale: 2,
                useCORS: true,
                allowTaint: false,
                backgroundColor: "#fff",
            });
            const img = canvas.toDataURL("image/png");
            const pdf = new jPDF("p", "mm", "a4");
            const pw = pdf.internal.pageSize.getWidth(),
                ph = pdf.internal.pageSize.getHeight(),
                m = 6;
            const iw = pw - m * 2,
                ih = (canvas.height * iw) / canvas.width;
            let rem = ih;
            pdf.addImage(img, "PNG", m, m, iw, ih);
            rem -= ph - m * 2;
            while (rem > 0) {
                pdf.addPage();
                pdf.addImage(img, "PNG", m, m - (ih - rem), iw, ih);
                rem -= ph - m * 2;
            }
            pdf.save(`audit-report-${Date.now()}.pdf`);
            showToast("PDF 已导出，太棒了！");
        } catch (e) {
            error.value = e?.message || "导出 PDF 失败";
        } finally {
            exportMode.value = false;
            exportingPdf.value = false;
        }
    }

    // ★ 键盘快捷键：J/K/↑↓ 切换，空格 驳回
    function onKeyDown(e) {
        if (tab.value !== "result") return;
        const tag = document.activeElement?.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA") return;
        const ids = positionedIssues.value.map((it) => it.issue.id);
        if (!ids.length) return;
        const cur = hoverIssueId.value;
        const idx = ids.indexOf(cur);
        if (e.key === "j" || e.key === "ArrowDown") {
            e.preventDefault();
            hoverIssueId.value = ids[Math.min(idx + 1, ids.length - 1)];
        } else if (e.key === "k" || e.key === "ArrowUp") {
            e.preventDefault();
            hoverIssueId.value = ids[Math.max(idx - 1, 0)];
        } else if (e.key === " " && cur) {
            e.preventDefault();
            isRejected(cur) ? undoReject(cur) : rejectIssue(cur);
        }
    }

    watch(displayIssues, () => {
        issueHeights.value = {};
        nextTick(() => {
            for (const [id, el] of issueElements.entries()) {
                queueIssueHeightMeasure(id, el);
            }
        });
    });

    // ★ 注册键盘监听，卸载时移除
    window.addEventListener("keydown", onKeyDown);
    onBeforeUnmount(() => {
        stopPoll();
        stopEase();
        if (issueMeasureFrame) cancelAnimationFrame(issueMeasureFrame);
        issueResizeObserver?.disconnect();
        issueElements.clear();
        window.removeEventListener("keydown", onKeyDown);
    });

    // 初始化
    refreshAchievements();
    loadHistory();
    loadKnowledgeBases().catch((e) => {
        error.value = e?.message || "加载知识库失败";
    });

    return {
        achievements,
        allResolved,
        auditSpeed,
        slowModeEnabled,
        beginDraw,
        boxStyle,
        cancelDraw,
        checklistInput,
        checklistKbs,
        clearCustomIssues,
        clearHistory,
        compareDiff,
        compareGood,
        currentSourceLabel,
        customIssues,
        decisionStats,
        deleteChecklistKb,
        deleteReferenceKb,
        displayIssues,
        displayProgress,
        doPoll,
        dotColor,
        donutSegments,
        drawingMode,
        drawingPreview,
        endDraw,
        error,
        exportMode,
        exportPdf,
        exportingPdf,
        fileInputRef,
        fmtTime,
        formatChecklist,
        hoverIssueId,
        inputMode,
        isRejected,
        issuesPaneRenderHeight,
        issuesWithBox,
        loadTask,
        loading,
        message,
        motIcon,
        motSub,
        motTitle,
        moveDraw,
        newChecklistName,
        noteForIssue,
        onFileChange,
        onReferenceFilesChange,
        onReset, // ★ 新增：供 HomePage.vue 注册 collabVm.resetCollab
        onShotLoad,
        pillClass,
        positionedIssues,
        progressWidth,
        referenceFileInputRef,
        referenceFileNamesText,
        referenceFiles,
        referenceKbs,
        rejectIssue,
        removeCustomIssue,
        removeTask,
        renameChecklistKb,
        renameReferenceKb,
        rerunTask,
        saveChecklistToKb,
        saveReferencesToKb,
        screenshotSrc,
        selectedChecklistKbIds,
        selectedFile,
        selectedFileName,
        selectedReferenceKbIds,
        setIssueRef,
        shotImg,
        shotWrapper,
        showMotivation,
        showToast, // ★ 新增：供 useCollabLogic 使用
        startAudit,
        status,
        statusLabel,
        statusText,
        switchMode,
        tab,
        tabLabel,
        targetProgress,
        taskHistory,
        taskId,
        toastMsg,
        todayCount, // ★ 真实计数
        toggleDrawingMode,
        undoReject,
        updateNote,
        urlInput,
    };
}
