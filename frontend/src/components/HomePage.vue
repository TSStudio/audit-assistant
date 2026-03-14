<template>
    <div class="shell">
        <!-- ══ sidebar ══════════════════════════════════════════════════════════ -->
        <aside class="sidebar">
            <div class="logo">
                <div class="logo-mark">A</div>
                <div>
                    <div class="logo-text">Audit Assistant</div>
                    <div class="logo-sub">AI 内容审校</div>
                </div>
            </div>
            <div class="rule" />

            <nav class="nav-wrap">
                <p class="nav-label">工作台</p>
                <button
                    class="nav-item"
                    :class="{ active: tab === 'submit' }"
                    @click="tab = 'submit'"
                >
                    <SvgPlus /> 新建审计
                </button>
                <button
                    class="nav-item"
                    :class="{ active: tab === 'history' }"
                    @click="tab = 'history'"
                >
                    <SvgClock /> 历史记录
                    <span class="nav-count">{{ taskHistory.length }}</span>
                </button>
                <button
                    class="nav-item"
                    :class="{ active: tab === 'result' }"
                    @click="tab = 'result'"
                >
                    <SvgDoc /> 审计结果
                    <span class="nav-count">{{
                        displayIssues.length || "—"
                    }}</span>
                </button>
            </nav>

            <div class="rule" />

            <div class="recent-wrap">
                <p class="nav-label">最近记录</p>
                <div class="recent-list">
                    <button
                        v-for="item in taskHistory.slice(0, 7)"
                        :key="item.task_id"
                        class="recent-item"
                        :class="{ active: item.task_id === taskId }"
                        @click="loadTask(item)"
                    >
                        <span
                            class="dot"
                            :style="{ background: dotColor(item.status) }"
                        />
                        <div class="recent-body">
                            <span class="recent-title">{{
                                item.title || item.source_label || item.url
                            }}</span>
                            <span class="recent-time">{{
                                fmtTime(item.updated_at)
                            }}</span>
                        </div>
                    </button>
                </div>
            </div>
        </aside>

        <!-- ══ main ══════════════════════════════════════════════════════════════ -->
        <div class="main">
            <!-- topbar -->
            <header class="topbar">
                <button class="hamburger" @click="sidebarOpen = !sidebarOpen">
                    <SvgMenu />
                </button>
                <div class="tab-strip">
                    <button
                        class="tstrip-btn"
                        :class="{ active: tab === 'submit' }"
                        @click="tab = 'submit'"
                    >
                        新建
                    </button>
                    <button
                        class="tstrip-btn"
                        :class="{ active: tab === 'history' }"
                        @click="tab = 'history'"
                    >
                        历史
                    </button>
                    <button
                        class="tstrip-btn"
                        :class="{ active: tab === 'result' }"
                        @click="tab = 'result'"
                    >
                        结果
                    </button>
                </div>
                <span
                    v-if="status"
                    class="status-pill"
                    :class="statusClass"
                    style="margin-left: auto"
                    >{{ statusLabel }}</span
                >
            </header>

            <div class="content">
                <!-- ── submit panel ───────────────────────────────────────────────── -->
                <div v-show="tab === 'submit'" class="panel">
                    <p class="eyebrow">新建审计</p>
                    <h2>提交待审计内容</h2>
                    <p class="sub">
                        支持 URL 或上传 txt / docx / pdf /
                        图片，后端按类型走不同流程。
                    </p>

                    <!-- mode switch -->
                    <div class="mode-switch">
                        <button
                            class="mode-btn"
                            :class="{ active: inputMode === 'url' }"
                            :disabled="loading"
                            @click="switchMode('url')"
                        >
                            URL
                        </button>
                        <button
                            class="mode-btn"
                            :class="{ active: inputMode === 'file' }"
                            :disabled="loading"
                            @click="switchMode('file')"
                        >
                            文件上传
                        </button>
                    </div>

                    <div class="form-col">
                        <template v-if="inputMode === 'url'">
                            <label class="form-label">页面链接</label>
                            <div class="input-row">
                                <input
                                    v-model="urlInput"
                                    type="url"
                                    class="text-input"
                                    placeholder="https://example.com/article"
                                    :disabled="loading"
                                    @keydown.enter="startAudit"
                                />
                            </div>
                        </template>
                        <template v-else>
                            <label class="form-label">上传文件</label>
                            <div class="file-row">
                                <label class="file-pick-btn">
                                    选择文件
                                    <input
                                        ref="fileInputRef"
                                        type="file"
                                        accept=".txt,.docx,.pdf,image/*"
                                        :disabled="loading"
                                        style="display: none"
                                        @change="onFileChange"
                                    />
                                </label>
                                <span class="file-name-hint">{{
                                    selectedFileName || "未选择文件"
                                }}</span>
                            </div>
                        </template>

                        <div class="input-row" style="margin-top: 4px">
                            <button
                                class="primary-btn"
                                :disabled="loading || !canStartAudit"
                                @click="startAudit"
                            >
                                {{ loading ? "提交中…" : "开始审计" }}
                            </button>
                        </div>

                        <div class="mode-switch" style="margin-top: 2px">
                            <button
                                class="mode-btn"
                                :class="{ active: fastMode }"
                                :disabled="loading"
                                @click="fastMode = true"
                            >
                                Fast Mode（关闭 Thinking）
                            </button>
                            <button
                                class="mode-btn"
                                :class="{ active: !fastMode }"
                                :disabled="loading"
                                @click="fastMode = false"
                            >
                                Slow Mode（开启 Thinking）
                            </button>
                        </div>

                        <label class="form-label"
                            >审核清单知识库
                            <span class="hint-text"
                                >（用户独立，可复用）</span
                            ></label
                        >
                        <textarea
                            v-model="checklistInput"
                            class="textarea-input"
                            rows="3"
                            :disabled="loading"
                            placeholder="输入清单条目（每行一条），可保存到知识库"
                        />
                        <div class="input-row" style="margin-top: 6px">
                            <input
                                v-model="newChecklistName"
                                type="text"
                                class="text-input"
                                placeholder="清单名称（可选）"
                                :disabled="loading"
                            />
                            <button
                                class="ghost-btn"
                                :disabled="
                                    loading ||
                                    !parseChecklist(checklistInput).length
                                "
                                @click="saveChecklistLibrary"
                            >
                                保存到清单库
                            </button>
                        </div>
                        <div
                            v-if="checklistLibrary.length"
                            class="library-list"
                        >
                            <div
                                v-for="item in checklistLibrary"
                                :key="item.checklist_id"
                                class="library-item"
                            >
                                <input
                                    type="checkbox"
                                    :value="item.checklist_id"
                                    :checked="
                                        selectedChecklistIds.includes(
                                            item.checklist_id,
                                        )
                                    "
                                    @change="
                                        toggleChecklistSelection(
                                            item.checklist_id,
                                            $event.target.checked,
                                        )
                                    "
                                />
                                <input
                                    v-if="
                                        ckEditState[item.checklist_id]?.editing
                                    "
                                    class="lib-edit-input"
                                    :value="ckEditState[item.checklist_id].name"
                                    @input="
                                        ckEditState[item.checklist_id].name =
                                            $event.target.value
                                    "
                                    @keydown.enter="commitRenameCk(item)"
                                    @keydown.esc="
                                        ckEditState[item.checklist_id].editing =
                                            false
                                    "
                                />
                                <span v-else class="lib-name"
                                    >{{ item.name }}（{{
                                        item.items?.length || 0
                                    }}条）</span
                                >
                                <div class="lib-actions">
                                    <button
                                        v-if="
                                            !ckEditState[item.checklist_id]
                                                ?.editing
                                        "
                                        class="lib-btn"
                                        title="重命名"
                                        @click.stop="startRenameCk(item)"
                                    >
                                        ✎
                                    </button>
                                    <button
                                        v-else
                                        class="lib-btn ok"
                                        title="确认"
                                        @click.stop="commitRenameCk(item)"
                                    >
                                        ✓
                                    </button>
                                    <button
                                        class="lib-btn del"
                                        title="删除"
                                        @click.stop="deleteCkItem(item)"
                                    >
                                        ✕
                                    </button>
                                </div>
                            </div>
                        </div>
                        <p v-else class="hint-text">
                            暂无清单库，先保存一份即可复用。
                        </p>

                        <label class="form-label"
                            >附加资料知识库
                            <span class="hint-text"
                                >（用户独立，可复用）</span
                            ></label
                        >
                        <div class="file-row">
                            <label class="file-pick-btn">
                                选择文件
                                <input
                                    ref="referenceFileInputRef"
                                    type="file"
                                    accept=".txt,.docx,.pdf"
                                    multiple
                                    :disabled="loading || uploading"
                                    style="display: none"
                                    @change="onReferenceFilesSelect"
                                />
                            </label>
                        </div>
                        <div v-if="pendingRefFiles.length" class="pending-list">
                            <p class="pending-hint">可修改名称后上传：</p>
                            <div
                                v-for="(p, i) in pendingRefFiles"
                                :key="i"
                                class="pending-item"
                            >
                                <span class="pending-orig">{{
                                    p.file.name
                                }}</span>
                                <input
                                    class="lib-edit-input"
                                    v-model="p.customName"
                                    placeholder="自定义名称"
                                />
                            </div>
                            <div class="pending-actions">
                                <button
                                    class="ghost-btn"
                                    @click="pendingRefFiles = []"
                                >
                                    取消
                                </button>
                                <button
                                    class="primary-btn"
                                    :disabled="uploading"
                                    @click="uploadPendingFiles"
                                >
                                    {{ uploading ? "上传中…" : "确认上传" }}
                                </button>
                            </div>
                        </div>
                        <div
                            v-if="referenceLibrary.length"
                            class="library-list"
                            style="margin-top: 8px"
                        >
                            <div
                                v-for="item in referenceLibrary"
                                :key="item.reference_id"
                                class="library-item"
                            >
                                <input
                                    type="checkbox"
                                    :value="item.reference_id"
                                    :checked="
                                        selectedReferenceIds.includes(
                                            item.reference_id,
                                        )
                                    "
                                    @change="
                                        toggleReferenceSelection(
                                            item.reference_id,
                                            $event.target.checked,
                                        )
                                    "
                                />
                                <input
                                    v-if="
                                        refEditState[item.reference_id]?.editing
                                    "
                                    class="lib-edit-input"
                                    :value="
                                        refEditState[item.reference_id].name
                                    "
                                    @input="
                                        refEditState[item.reference_id].name =
                                            $event.target.value
                                    "
                                    @keydown.enter="commitRenameRef(item)"
                                    @keydown.esc="
                                        refEditState[
                                            item.reference_id
                                        ].editing = false
                                    "
                                />
                                <span v-else class="lib-name">{{
                                    item.name
                                }}</span>
                                <div class="lib-actions">
                                    <button
                                        v-if="
                                            !refEditState[item.reference_id]
                                                ?.editing
                                        "
                                        class="lib-btn"
                                        title="重命名"
                                        @click.stop="startRenameRef(item)"
                                    >
                                        ✎
                                    </button>
                                    <button
                                        v-else
                                        class="lib-btn ok"
                                        title="确认"
                                        @click.stop="commitRenameRef(item)"
                                    >
                                        ✓
                                    </button>
                                    <button
                                        class="lib-btn del"
                                        title="删除"
                                        @click.stop="deleteRefItem(item)"
                                    >
                                        ✕
                                    </button>
                                </div>
                            </div>
                        </div>
                        <p v-else class="hint-text">
                            暂无资料库，先上传文件即可后续直接选择。
                        </p>

                        <div v-if="error" class="error-banner">
                            ⚠ {{ error }}
                        </div>
                        <p v-if="taskId" class="task-id-note">
                            任务 {{ taskId }}
                        </p>
                    </div>

                    <div v-if="status" class="progress-wrap">
                        <div class="progress-bg">
                            <div
                                class="progress-fill"
                                :class="statusClass"
                                :style="{ width: progressWidth }"
                            />
                        </div>
                    </div>
                    <p v-if="message" class="sub" style="margin-top: 6px">
                        {{ message }}
                    </p>

                    <div
                        v-if="taskId"
                        class="action-row"
                        style="margin-top: 12px"
                    >
                        <button class="ghost-btn" @click="rerunCurrent">
                            重新运行
                        </button>
                        <button
                            v-if="taskHistory.length"
                            class="ghost-btn danger"
                            @click="clearHistory"
                        >
                            清空历史
                        </button>
                    </div>
                </div>

                <!-- ── history panel ──────────────────────────────────────────────── -->
                <div v-show="tab === 'history'" class="panel">
                    <div class="panel-head">
                        <div>
                            <p class="eyebrow">历史记录</p>
                            <h2>所有审计任务</h2>
                        </div>
                        <button
                            v-if="taskHistory.length"
                            class="ghost-btn danger"
                            @click="clearHistory"
                        >
                            清空全部
                        </button>
                    </div>

                    <div v-if="!taskHistory.length" class="empty-state">
                        <SvgClock
                            style="width: 28px; height: 28px; color: #bbb"
                        />
                        <p>暂无历史记录，提交后自动保存。</p>
                    </div>

                    <div v-else class="hist-list">
                        <div
                            v-for="item in taskHistory"
                            :key="item.task_id"
                            class="hist-row"
                            :class="{ active: item.task_id === taskId }"
                        >
                            <span
                                class="dot"
                                :style="{
                                    background: dotColor(item.status),
                                    marginTop: '5px',
                                    flexShrink: 0,
                                }"
                            />
                            <div class="hist-body">
                                <div class="hist-title">
                                    {{
                                        item.title ||
                                        item.source_label ||
                                        item.url
                                    }}
                                </div>
                                <div class="hist-meta">
                                    <span
                                        class="mini-pill"
                                        :class="item.status"
                                        >{{ statusText(item.status) }}</span
                                    >
                                    <span
                                        v-if="
                                            item.issueCount != null &&
                                            item.status === 'completed'
                                        "
                                        >{{ item.issueCount }} 个问题</span
                                    >
                                    <span
                                        v-if="
                                            item.progress != null &&
                                            item.status === 'running'
                                        "
                                        >{{ item.progress }}%</span
                                    >
                                    <span class="meta-time">{{
                                        fmtTime(item.updated_at)
                                    }}</span>
                                </div>
                                <div
                                    v-if="item.checklist?.length"
                                    class="hist-checklist"
                                >
                                    清单：{{ formatChecklist(item.checklist) }}
                                </div>
                            </div>
                            <div class="hist-actions">
                                <button
                                    class="ghost-btn sm"
                                    @click="loadTask(item)"
                                >
                                    查看
                                </button>
                                <button
                                    class="ghost-btn sm"
                                    @click="rerunTask(item)"
                                >
                                    重跑
                                </button>
                                <button
                                    class="ghost-btn sm danger"
                                    @click="removeTask(item)"
                                >
                                    删除
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ── result panel ───────────────────────────────────────────────── -->
                <div v-show="tab === 'result'" class="panel" ref="resultCard">
                    <div class="panel-head">
                        <div>
                            <p class="eyebrow">审计结果</p>
                            <h2>审计结果与批注</h2>
                            <p class="sub">
                                支持驳回 AI 建议、手动画框并填写批注，最后导出
                                PDF。
                            </p>
                        </div>
                        <div
                            style="
                                display: flex;
                                align-items: center;
                                gap: 8px;
                                flex-shrink: 0;
                            "
                        >
                            <span class="count-chip"
                                >{{ displayIssues.length }} 个问题</span
                            >
                            <span
                                v-if="status"
                                class="status-pill"
                                :class="statusClass"
                                >{{ statusLabel }}</span
                            >
                        </div>
                    </div>

                    <div
                        v-if="status === 'running'"
                        class="progress-wrap"
                        style="margin-bottom: 14px"
                    >
                        <div class="progress-bg">
                            <div
                                class="progress-fill"
                                :class="statusClass"
                                :style="{ width: progressWidth }"
                            />
                        </div>
                        <p v-if="message" class="sub" style="margin-top: 5px">
                            {{ message }}
                        </p>
                    </div>

                    <div
                        v-if="screenshotSrc || displayIssues.length"
                        class="review-bar"
                    >
                        <div class="summary-chips">
                            <span class="chip green"
                                >已保留 {{ decisionStats.kept }}</span
                            >
                            <span class="chip red"
                                >已驳回 {{ decisionStats.rejected }}</span
                            >
                        </div>
                        <button
                            class="ghost-btn sm"
                            :disabled="!customIssues.length"
                            @click="clearCustomIssues"
                        >
                            清空手工批注
                        </button>
                    </div>

                    <div
                        v-if="!screenshotSrc && !displayIssues.length"
                        class="empty-state"
                    >
                        <SvgDoc
                            style="width: 28px; height: 28px; color: #bbb"
                        />
                        <p>尚无结果，提交后等待审计完成即可查看。</p>
                    </div>

                    <div
                        v-else
                        ref="exportContainer"
                        :class="['export-wrap', { 'export-mode': exportMode }]"
                    >
                        <!-- export header (only visible in export mode) -->
                        <div class="export-head">
                            <h3>智慧审查报告</h3>
                            <p>来源：{{ currentSourceLabel }}</p>
                            <p>导出时间：{{ new Date().toLocaleString() }}</p>
                        </div>

                        <div class="result-grid">
                            <!-- screenshot -->
                            <div class="shot-pane">
                                <div
                                    v-if="screenshotSrc"
                                    ref="shotWrapper"
                                    class="shot-wrapper"
                                    :class="{ drawing: drawingMode }"
                                    @mousedown="beginDraw"
                                    @mousemove="moveDraw"
                                    @mouseup="endDraw"
                                    @mouseleave="cancelDraw"
                                >
                                    <img
                                        ref="shotImg"
                                        class="shot-img"
                                        :src="screenshotSrc"
                                        crossorigin="anonymous"
                                        alt="页面截图"
                                        @load="onShotLoad"
                                    />
                                    <div
                                        v-for="issue in issuesWithBox"
                                        :key="`box-${issue.id}`"
                                        class="overlay-box"
                                        :class="{
                                            active: hoverIssueId === issue.id,
                                            manual: issue.manual,
                                            rejected: isRejected(issue.id),
                                        }"
                                        :style="boxStyle(issue)"
                                    />
                                    <div
                                        v-if="drawingPreview"
                                        class="overlay-box preview"
                                        :style="drawingPreview"
                                    />
                                </div>
                                <div
                                    v-else
                                    class="empty-state"
                                    style="min-height: 160px"
                                >
                                    <SvgImage
                                        style="
                                            width: 28px;
                                            height: 28px;
                                            color: #bbb;
                                        "
                                    />
                                    <p>截图在后端完成后显示</p>
                                </div>
                            </div>

                            <!-- issues -->
                            <div
                                class="issues-pane"
                                :style="{
                                    height: issuesPaneRenderHeight + 'px',
                                }"
                            >
                                <template v-if="positionedIssues.length">
                                    <div
                                        v-for="item in positionedIssues"
                                        :key="item.issue.id"
                                        class="issue-card"
                                        :class="{
                                            active:
                                                hoverIssueId === item.issue.id,
                                            rejected: isRejected(item.issue.id),
                                            manual: item.issue.manual,
                                        }"
                                        :style="{ top: item.top + 'px' }"
                                        :ref="
                                            (el) =>
                                                setIssueRef(item.issue.id, el)
                                        "
                                        @mouseenter="
                                            hoverIssueId = item.issue.id
                                        "
                                        @mouseleave="hoverIssueId = null"
                                    >
                                        <div class="issue-top">
                                            <span
                                                class="sev-badge"
                                                :class="`sev-${item.issue.severity || 'info'}`"
                                            >
                                                {{
                                                    item.issue.severity ||
                                                    "info"
                                                }}
                                            </span>
                                            <span class="issue-type">{{
                                                item.issue.type || "custom"
                                            }}</span>
                                            <span
                                                v-if="item.issue.confidence"
                                                class="issue-conf"
                                            >
                                                置信度
                                                {{
                                                    Number(
                                                        item.issue.confidence,
                                                    ).toFixed(2)
                                                }}
                                            </span>
                                            <span
                                                class="decision-tag"
                                                :class="
                                                    isRejected(item.issue.id)
                                                        ? 'rej'
                                                        : 'kept'
                                                "
                                            >
                                                {{
                                                    isRejected(item.issue.id)
                                                        ? "已驳回"
                                                        : "已保留"
                                                }}
                                            </span>
                                        </div>

                                        <div class="issue-btns">
                                            <button
                                                v-if="
                                                    !isRejected(item.issue.id)
                                                "
                                                class="mini-btn reject"
                                                @click="
                                                    rejectIssue(item.issue.id)
                                                "
                                            >
                                                驳回
                                            </button>
                                            <button
                                                v-else
                                                class="mini-btn"
                                                @click="
                                                    undoReject(item.issue.id)
                                                "
                                            >
                                                撤销
                                            </button>
                                            <button
                                                v-if="item.issue.manual"
                                                class="mini-btn danger"
                                                @click="
                                                    removeCustomIssue(
                                                        item.issue.id,
                                                    )
                                                "
                                            >
                                                删除批注
                                            </button>
                                        </div>

                                        <p
                                            v-if="item.issue.evidence?.quote"
                                            class="issue-quote"
                                        >
                                            "{{ item.issue.evidence.quote }}"
                                        </p>
                                        <p
                                            v-if="item.issue.recommendation"
                                            class="issue-rec"
                                        >
                                            建议：{{
                                                item.issue.recommendation
                                            }}
                                        </p>

                                        <template v-if="item.issue.manual">
                                            <label class="ann-label"
                                                >批注</label
                                            >
                                            <textarea
                                                class="ann-input"
                                                :value="
                                                    noteForIssue(item.issue.id)
                                                "
                                                placeholder="输入你的审校意见…"
                                                @input="
                                                    updateNote(
                                                        item.issue.id,
                                                        $event.target.value,
                                                    )
                                                "
                                            />
                                        </template>

                                        <div class="issue-meta">
                                            <span
                                                v-if="
                                                    item.issue.evidence
                                                        ?.text_block_id
                                                "
                                                >段落：{{
                                                    item.issue.evidence
                                                        .text_block_id
                                                }}</span
                                            >
                                            <span
                                                v-if="
                                                    item.issue.evidence
                                                        ?.image_id
                                                "
                                                >图片：{{
                                                    item.issue.evidence.image_id
                                                }}</span
                                            >
                                            <span
                                                v-if="
                                                    item.issue.evidence?.link_id
                                                "
                                                >链接：{{
                                                    item.issue.evidence.link_id
                                                }}</span
                                            >
                                            <span v-if="item.issue.manual"
                                                >手工批注</span
                                            >
                                        </div>
                                    </div>
                                </template>
                                <div
                                    v-else
                                    class="empty-state"
                                    style="min-height: 120px"
                                >
                                    <p>暂无问题</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <!-- /content -->
        </div>
        <!-- /main -->

        <!-- ══ mobile sidebar overlay ══════════════════════════════════════════ -->
        <transition name="fade">
            <div
                v-if="sidebarOpen"
                class="sidebar-overlay"
                @click="sidebarOpen = false"
            />
        </transition>
        <aside class="sidebar sidebar-mobile" :class="{ open: sidebarOpen }">
            <div class="logo" style="padding: 16px 14px 12px">
                <div class="logo-mark">A</div>
                <div>
                    <div class="logo-text">Audit Assistant</div>
                    <div class="logo-sub">AI 内容审校</div>
                </div>
                <button class="close-btn" @click="sidebarOpen = false">
                    ✕
                </button>
            </div>
            <div class="rule" />
            <nav class="nav-wrap">
                <button
                    class="nav-item"
                    :class="{ active: tab === 'submit' }"
                    @click="
                        tab = 'submit';
                        sidebarOpen = false;
                    "
                >
                    <SvgPlus />新建审计
                </button>
                <button
                    class="nav-item"
                    :class="{ active: tab === 'history' }"
                    @click="
                        tab = 'history';
                        sidebarOpen = false;
                    "
                >
                    <SvgClock />历史记录
                </button>
                <button
                    class="nav-item"
                    :class="{ active: tab === 'result' }"
                    @click="
                        tab = 'result';
                        sidebarOpen = false;
                    "
                >
                    <SvgDoc />审计结果
                </button>
            </nav>
        </aside>

        <!-- ══ floating action bar ══════════════════════════════════════════════ -->
        <div
            class="fab-bar"
            v-if="tab === 'result' && (screenshotSrc || displayIssues.length)"
        >
            <button
                class="fab"
                :class="{ 'fab-draw-active': drawingMode }"
                :disabled="!screenshotSrc"
                @click="toggleDrawingMode"
            >
                {{ drawingMode ? "结束画框" : "新增批注画框" }}
            </button>
            <button
                class="fab fab-export"
                :disabled="
                    exportingPdf || (!screenshotSrc && !displayIssues.length)
                "
                @click="exportPdf"
            >
                {{ exportingPdf ? "导出中…" : "导出 PDF" }}
            </button>
        </div>
    </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

// ── inline SVG icons ──────────────────────────────────────────────────────────
const SvgPlus = {
    template: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.2"/><path d="M8 5v6M5 8h6" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>`,
};
const SvgClock = {
    template: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.2"/><path d="M8 5v3l2 2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>`,
};
const SvgDoc = {
    template: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.2"/><path d="M5 8h6M5 5h4M5 11h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>`,
};
const SvgMenu = {
    template: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>`,
};
const SvgImage = {
    template: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none"><rect x="2" y="2" width="24" height="24" rx="4" stroke="currentColor" stroke-width="1.2"/><circle cx="10" cy="10" r="3" stroke="currentColor" stroke-width="1.2"/><path d="M3 20l6-6 4 4 4-5 8 7" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
};

// ── config ────────────────────────────────────────────────────────────────────
const API_BASE =
    process.env.NODE_ENV === "development"
        ? "http://localhost:8000/api"
        : "/api";
const MIN_GAP = 14;

// ── state ─────────────────────────────────────────────────────────────────────
const tab = ref("submit");
const sidebarOpen = ref(false);
const inputMode = ref("url");
const urlInput = ref("");
const selectedFile = ref(null);
const fileInputRef = ref(null);
const referenceFiles = ref([]);
const referenceFileInputRef = ref(null);
const checklistInput = ref("");
const newChecklistName = ref("");
const checklistLibrary = ref([]);
const referenceLibrary = ref([]);
const selectedChecklistIds = ref([]);
const selectedReferenceIds = ref([]);
const userToken = ref("");
const pendingRefFiles = ref([]);
const uploading = ref(false);
const refEditState = ref({});
const ckEditState = ref({});
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
const fastMode = ref(false);
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
});

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
const issueHeights = ref({});

let pollTimer = null;
let easeTimer = null;

// ── status helpers ────────────────────────────────────────────────────────────
const statusLabel = computed(
    () =>
        ({
            running: "运行中",
            llm_vlm_working: "LLM/VLM并发中",
            llm_done_vlm_working: "LLM完成，VLM处理中",
            llm_working_vlm_done: "VLM完成，LLM处理中",
            llm_vlm_done: "LLM/VLM已完成",
            completed: "已完成",
            failed: "失败",
        })[status.value] || "待开始",
);
const statusClass = computed(
    () =>
        ({
            completed: "ok",
            running: "warn",
            llm_vlm_working: "warn",
            llm_done_vlm_working: "warn",
            llm_working_vlm_done: "warn",
            llm_vlm_done: "warn",
            failed: "err",
        })[status.value] || "idle",
);
const progressWidth = computed(() => {
    if (status.value === "failed" || status.value === "completed")
        return "100%";
    return `${Math.min(displayProgress.value, 100)}%`;
});
const dotColor = (s) =>
    ({
        running: "#BA7517",
        llm_vlm_working: "#BA7517",
        llm_done_vlm_working: "#BA7517",
        llm_working_vlm_done: "#BA7517",
        llm_vlm_done: "#BA7517",
        completed: "#639922",
        failed: "#E24B4A",
    })[s] || "#B4B2A9";
const statusText = (s) =>
    ({
        running: "运行中",
        llm_vlm_working: "LLM/VLM并发中",
        llm_done_vlm_working: "LLM完成，VLM处理中",
        llm_working_vlm_done: "VLM完成，LLM处理中",
        llm_vlm_done: "LLM/VLM已完成",
        completed: "已完成",
        failed: "失败",
    })[s] ||
    s ||
    "未知";
const fmtTime = (ts) => {
    if (!ts) return "";
    return new Date(ts * 1000).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
};

// ── computed ──────────────────────────────────────────────────────────────────
const selectedFileName = computed(() => selectedFile.value?.name || "");
const referenceFileNamesText = computed(() => {
    const n = referenceFiles.value.length;
    if (!n) return "未选择附加资料";
    return n === 1 ? referenceFiles.value[0].name : `已选择 ${n} 个文件`;
});
const canStartAudit = computed(() =>
    inputMode.value === "url" ? !!urlInput.value.trim() : !!selectedFile.value,
);
const currentSourceLabel = computed(() => {
    const e = currentSourceMeta.value?.source_label;
    if (e) return e;
    if (inputMode.value === "url") return urlInput.value || "(未填写)";
    return selectedFileName.value || "(未选择文件)";
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
const displayIssues = computed(() => [...issues.value, ...customIssues.value]);
const issuesForList = computed(() =>
    exportMode.value
        ? displayIssues.value.filter((i) => !isRejected(i.id))
        : displayIssues.value,
);
const issuesWithBox = computed(() =>
    displayIssues.value.filter((i) => boxForIssue(i) && !isRejected(i.id)),
);
const issuesPaneH = computed(() => Math.max(shotDisplay.value.h || 420, 420));
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
const decisionStats = computed(() => {
    let kept = 0,
        rejected = 0;
    for (const i of displayIssues.value) isRejected(i.id) ? rejected++ : kept++;
    return { kept, rejected };
});

// ── history ───────────────────────────────────────────────────────────────────
function deriveTitle(url) {
    try {
        const u = new URL(url);
        const seg =
            u.pathname.replace(/\/$/, "").split("/").filter(Boolean).pop() ||
            "";
        const dec = decodeURIComponent(seg)
            .replace(/[-_]/g, " ")
            .replace(/\.\w+$/, "");
        const host = u.hostname.replace(/^www\./, "");
        return dec ? `${dec} · ${host}` : host;
    } catch {
        return url;
    }
}

function randomToken() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `u_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function readCookie(name) {
    const pairs = document.cookie ? document.cookie.split(";") : [];
    const key = `${name}=`;
    for (const p of pairs) {
        const v = p.trim();
        if (v.startsWith(key)) return decodeURIComponent(v.slice(key.length));
    }
    return "";
}

function ensureUserToken() {
    const fromCookie = readCookie("audit_user");
    if (fromCookie) return fromCookie;
    const created = randomToken();
    document.cookie = `audit_user=${encodeURIComponent(created)}; path=/; max-age=${60 * 60 * 24 * 365}`;
    return created;
}

function historyKey() {
    return `audit_task_history:${userToken.value || "anon"}`;
}

function authHeaders() {
    return userToken.value ? { "X-User-Token": userToken.value } : {};
}

function loadHistory() {
    try {
        const r = localStorage.getItem(historyKey());
        taskHistory.value = r ? JSON.parse(r) : [];
    } catch {
        taskHistory.value = [];
    }
}
function saveHistory(list) {
    taskHistory.value = list;
    localStorage.setItem(historyKey(), JSON.stringify(list));
}
function upsertHistory(item) {
    const list = [...taskHistory.value];
    const i = list.findIndex((t) => t.task_id === item.task_id);
    if (i >= 0) list[i] = { ...list[i], ...item };
    else list.unshift(item);
    saveHistory(list.slice(0, 50));
}
function removeTask(item) {
    saveHistory(taskHistory.value.filter((t) => t.task_id !== item.task_id));
}
function clearHistory() {
    saveHistory([]);
}

function parseChecklist(v) {
    return (v || "")
        .split(/\r?\n/)
        .map((s) => s.trim())
        .filter(Boolean);
}
function formatChecklist(list) {
    if (!list?.length) return "";
    const p = list.slice(0, 3).join("、");
    return list.length > 3 ? `${p}…` : p;
}

// ── normalise ─────────────────────────────────────────────────────────────────
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

// ── polling / ease ────────────────────────────────────────────────────────────
function stopPoll() {
    if (pollTimer) {
        clearTimeout(pollTimer);
        pollTimer = null;
    }
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
        const d = targetProgress.value - displayProgress.value;
        displayProgress.value = Math.min(displayProgress.value + d / 4, 100);
    }, 800);
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

function toggleChecklistSelection(id, checked) {
    if (checked) {
        if (!selectedChecklistIds.value.includes(id))
            selectedChecklistIds.value = [...selectedChecklistIds.value, id];
        return;
    }
    selectedChecklistIds.value = selectedChecklistIds.value.filter(
        (v) => v !== id,
    );
}

function toggleReferenceSelection(id, checked) {
    if (checked) {
        if (!selectedReferenceIds.value.includes(id))
            selectedReferenceIds.value = [...selectedReferenceIds.value, id];
        return;
    }
    selectedReferenceIds.value = selectedReferenceIds.value.filter(
        (v) => v !== id,
    );
}

async function fetchLibraries() {
    if (!userToken.value) return;
    try {
        const [ckResp, refResp] = await Promise.all([
            fetch(`${API_BASE}/kb/checklists`, { headers: authHeaders() }),
            fetch(`${API_BASE}/kb/references`, { headers: authHeaders() }),
        ]);
        checklistLibrary.value = ckResp.ok ? await ckResp.json() : [];
        referenceLibrary.value = refResp.ok ? await refResp.json() : [];
    } catch {
        checklistLibrary.value = [];
        referenceLibrary.value = [];
    }
}

async function saveChecklistLibrary() {
    try {
        const items = parseChecklist(checklistInput.value);
        if (!items.length) return;
        const fd = new FormData();
        fd.append("name", newChecklistName.value.trim());
        fd.append("items", JSON.stringify(items));
        const resp = await fetch(`${API_BASE}/kb/checklists`, {
            method: "POST",
            headers: authHeaders(),
            body: fd,
        });
        if (!resp.ok) throw new Error(`清单保存失败：${resp.status}`);
        const row = await resp.json();
        checklistLibrary.value = [
            row,
            ...checklistLibrary.value.filter(
                (i) => i.checklist_id !== row.checklist_id,
            ),
        ];
        if (!selectedChecklistIds.value.includes(row.checklist_id)) {
            selectedChecklistIds.value = [
                ...selectedChecklistIds.value,
                row.checklist_id,
            ];
        }
        newChecklistName.value = "";
    } catch (e) {
        error.value = e?.message || "清单保存失败";
    }
}

async function onReferenceFilesChangeAndUpload(e) {
    onReferenceFilesSelect(e);
}

function onReferenceFilesSelect(e) {
    const files = Array.from(e?.target?.files || []);
    if (!files.length) return;
    referenceFiles.value = files;
    pendingRefFiles.value = files.map((f) => ({
        file: f,
        customName: f.name.replace(/\.[^.]+$/, ""),
    }));
    // reset input so same files can be re-selected
    if (referenceFileInputRef.value) referenceFileInputRef.value.value = "";
}

async function uploadPendingFiles() {
    if (!pendingRefFiles.value.length) return;
    try {
        uploading.value = true;
        const fd = new FormData();
        const names = pendingRefFiles.value.map(
            (p) => (p.customName || "").trim() || p.file.name,
        );
        for (const p of pendingRefFiles.value) fd.append("files", p.file);
        fd.append("names", JSON.stringify(names));
        const resp = await fetch(`${API_BASE}/kb/references`, {
            method: "POST",
            headers: authHeaders(),
            body: fd,
        });
        if (!resp.ok) throw new Error(`资料上传失败：${resp.status}`);
        const rows = await resp.json();
        if (Array.isArray(rows) && rows.length) {
            const old = referenceLibrary.value.filter(
                (r) => !rows.some((n) => n.reference_id === r.reference_id),
            );
            referenceLibrary.value = [...rows, ...old];
            const ids = rows.map((r) => r.reference_id);
            selectedReferenceIds.value = Array.from(
                new Set([...selectedReferenceIds.value, ...ids]),
            );
        }
        pendingRefFiles.value = [];
    } catch (e) {
        error.value = e?.message || "资料上传失败";
    } finally {
        uploading.value = false;
    }
}

function startRenameRef(item) {
    refEditState.value = {
        ...refEditState.value,
        [item.reference_id]: { editing: true, name: item.name },
    };
}

async function commitRenameRef(item) {
    const state = refEditState.value[item.reference_id];
    if (!state) return;
    const newName = (state.name || "").trim();
    if (!newName || newName === item.name) {
        refEditState.value = {
            ...refEditState.value,
            [item.reference_id]: { ...state, editing: false },
        };
        return;
    }
    try {
        const resp = await fetch(
            `${API_BASE}/kb/references/${item.reference_id}`,
            {
                method: "PATCH",
                headers: {
                    ...authHeaders(),
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ name: newName }),
            },
        );
        if (!resp.ok) throw new Error("重命名失败");
        const updated = await resp.json();
        referenceLibrary.value = referenceLibrary.value.map((r) =>
            r.reference_id === item.reference_id ? updated : r,
        );
        refEditState.value = {
            ...refEditState.value,
            [item.reference_id]: { editing: false, name: newName },
        };
    } catch (e) {
        error.value = e?.message || "重命名失败";
    }
}

async function deleteRefItem(item) {
    try {
        const resp = await fetch(
            `${API_BASE}/kb/references/${item.reference_id}`,
            { method: "DELETE", headers: authHeaders() },
        );
        if (!resp.ok) throw new Error("删除失败");
        referenceLibrary.value = referenceLibrary.value.filter(
            (r) => r.reference_id !== item.reference_id,
        );
        selectedReferenceIds.value = selectedReferenceIds.value.filter(
            (id) => id !== item.reference_id,
        );
        const ns = { ...refEditState.value };
        delete ns[item.reference_id];
        refEditState.value = ns;
    } catch (e) {
        error.value = e?.message || "删除失败";
    }
}

function startRenameCk(item) {
    ckEditState.value = {
        ...ckEditState.value,
        [item.checklist_id]: { editing: true, name: item.name },
    };
}

async function commitRenameCk(item) {
    const state = ckEditState.value[item.checklist_id];
    if (!state) return;
    const newName = (state.name || "").trim();
    if (!newName || newName === item.name) {
        ckEditState.value = {
            ...ckEditState.value,
            [item.checklist_id]: { ...state, editing: false },
        };
        return;
    }
    try {
        const resp = await fetch(
            `${API_BASE}/kb/checklists/${item.checklist_id}`,
            {
                method: "PATCH",
                headers: {
                    ...authHeaders(),
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ name: newName }),
            },
        );
        if (!resp.ok) throw new Error("重命名失败");
        const updated = await resp.json();
        checklistLibrary.value = checklistLibrary.value.map((c) =>
            c.checklist_id === item.checklist_id ? updated : c,
        );
        ckEditState.value = {
            ...ckEditState.value,
            [item.checklist_id]: { editing: false, name: newName },
        };
    } catch (e) {
        error.value = e?.message || "重命名失败";
    }
}

async function deleteCkItem(item) {
    try {
        const resp = await fetch(
            `${API_BASE}/kb/checklists/${item.checklist_id}`,
            { method: "DELETE", headers: authHeaders() },
        );
        if (!resp.ok) throw new Error("删除失败");
        checklistLibrary.value = checklistLibrary.value.filter(
            (c) => c.checklist_id !== item.checklist_id,
        );
        selectedChecklistIds.value = selectedChecklistIds.value.filter(
            (id) => id !== item.checklist_id,
        );
        const ns = { ...ckEditState.value };
        delete ns[item.checklist_id];
        ckEditState.value = ns;
    } catch (e) {
        error.value = e?.message || "删除失败";
    }
}

// ── audit ─────────────────────────────────────────────────────────────────────
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
        };
    }

    resetState();
    loading.value = true;
    try {
        const cl = parseChecklist(checklistInput.value);
        let resp;
        if (inputMode.value === "url") {
            const fd = new FormData();
            fd.append("url", urlInput.value.trim());
            fd.append("checklist", JSON.stringify(cl));
            fd.append("fast_mode", String(fastMode.value));
            fd.append(
                "checklist_ids",
                JSON.stringify(selectedChecklistIds.value),
            );
            fd.append(
                "reference_ids",
                JSON.stringify(selectedReferenceIds.value),
            );
            resp = await fetch(`${API_BASE}/audit/url`, {
                method: "POST",
                headers: authHeaders(),
                body: fd,
            });
        } else {
            const fd = new FormData();
            fd.append("file", selectedFile.value);
            fd.append("checklist", JSON.stringify(cl));
            fd.append("fast_mode", String(fastMode.value));
            fd.append(
                "checklist_ids",
                JSON.stringify(selectedChecklistIds.value),
            );
            fd.append(
                "reference_ids",
                JSON.stringify(selectedReferenceIds.value),
            );
            resp = await fetch(`${API_BASE}/audit/upload`, {
                method: "POST",
                headers: authHeaders(),
                body: fd,
            });
        }
        if (!resp.ok) throw new Error(`提交失败：${resp.status}`);
        const data = await resp.json();

        taskId.value = data.task_id;
        status.value = data.status;
        message.value = data.message || "任务已创建，正在启动审计…";
        issues.value = normalizeIssues(data.issues || []);
        bundle.value = data.result || null;
        currentSourceMeta.value = sourceMeta;

        const title =
            sourceMeta.source_type === "url"
                ? deriveTitle(sourceMeta.url)
                : `[文件] ${sourceMeta.file_name}`;
        upsertHistory({
            task_id: data.task_id,
            url: sourceMeta.url,
            title,
            source_type: sourceMeta.source_type,
            source_label: sourceMeta.source_label,
            file_name: sourceMeta.file_name,
            checklist: cl,
            status: data.status,
            progress: data.progress ?? 0,
            updated_at: Math.floor(Date.now() / 1000),
        });

        const p =
            typeof data.progress === "number"
                ? data.progress
                : data.status === "completed"
                  ? 100
                  : 0;
        targetProgress.value = p;
        displayProgress.value = p;

        tab.value = "result";
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
        const resp = await fetch(`${API_BASE}/audit/${id}`, {
            headers: authHeaders(),
        });
        if (!resp.ok) throw new Error("查询失败");
        const data = await resp.json();

        status.value = data.status;
        message.value = data.message || "";
        issues.value = normalizeIssues(data.issues);
        bundle.value = data.result || null;
        if (Array.isArray(data.checklist))
            checklistInput.value = data.checklist.join("\n");
        if (typeof data.progress === "number") {
            targetProgress.value = data.progress;
            if (data.progress >= 100) {
                displayProgress.value = 100;
                stopEase();
            } else startEase();
        }

        const title =
            currentSourceMeta.value.source_type === "url"
                ? deriveTitle(currentSourceMeta.value.url)
                : `[文件] ${currentSourceMeta.value.file_name}`;
        upsertHistory({
            task_id: data.task_id,
            url: currentSourceMeta.value.url,
            title,
            source_type: currentSourceMeta.value.source_type,
            source_label: currentSourceMeta.value.source_label,
            file_name: currentSourceMeta.value.file_name,
            checklist: Array.isArray(data.checklist)
                ? data.checklist
                : parseChecklist(checklistInput.value),
            status: data.status,
            progress: data.progress ?? targetProgress.value ?? 0,
            issueCount: (data.issues || []).length,
            updated_at: Math.floor(Date.now() / 1000),
        });

        if (data.status === "completed" || data.status === "failed") {
            targetProgress.value = 100;
            displayProgress.value = 100;
            stopPoll();
            stopEase();
        } else schedulePoll(id);
    } catch (e) {
        error.value = e?.message || "查询失败";
        stopPoll();
        stopEase();
    }
}

onBeforeUnmount(() => {
    stopPoll();
    stopEase();
});

function loadTask(item) {
    if (!item?.task_id) return;
    resetState();
    currentSourceMeta.value = {
        source_type: item.source_type || "url",
        source_label: item.source_label || item.url || "",
        url: item.url || "",
        file_name: item.file_name || "",
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
    startAudit();
}
function rerunCurrent() {
    if (inputMode.value !== "url") {
        error.value = "上传任务无法直接重跑，请重新选择文件后提交。";
        return;
    }
    if (!urlInput.value) return;
    startAudit();
}

// ── issue actions ─────────────────────────────────────────────────────────────
const isRejected = (id) => !!decisionMap.value?.[id];
const rejectIssue = (id) => {
    decisionMap.value = { ...decisionMap.value, [id]: true };
};
const undoReject = (id) => {
    decisionMap.value = { ...decisionMap.value, [id]: false };
};
const noteForIssue = (id) => noteMap.value?.[id] || "";
const updateNote = (id, text) => {
    noteMap.value = { ...noteMap.value, [id]: text };
};

function removeCustomIssue(id) {
    customIssues.value = customIssues.value.filter((i) => i.id !== id);
    const nd = { ...decisionMap.value };
    const nn = { ...noteMap.value };
    delete nd[id];
    delete nn[id];
    decisionMap.value = nd;
    noteMap.value = nn;
}
function clearCustomIssues() {
    const ids = new Set(customIssues.value.map((i) => i.id));
    customIssues.value = [];
    const nd = { ...decisionMap.value };
    const nn = { ...noteMap.value };
    for (const id of ids) {
        delete nd[id];
        delete nn[id];
    }
    decisionMap.value = nd;
    noteMap.value = nn;
}

// ── drawing ───────────────────────────────────────────────────────────────────
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
}

// ── screenshot ────────────────────────────────────────────────────────────────
function onShotLoad(e) {
    const img = e.target;
    shotNatural.value = { w: img.naturalWidth || 1, h: img.naturalHeight || 1 };
    shotDisplay.value = { w: img.clientWidth || 1, h: img.clientHeight || 1 };
}
function boxForIssue(issue) {
    return issue?.evidence?.bbox || null;
}
function boxStyle(issue) {
    const bbox = boxForIssue(issue);
    if (!bbox) return {};
    const sx = shotDisplay.value.w / (shotNatural.value.w || 1);
    const sy = shotDisplay.value.h / (shotNatural.value.h || 1);
    return {
        left: `${bbox.x * sx}px`,
        top: `${bbox.y * sy}px`,
        width: `${bbox.width * sx}px`,
        height: `${bbox.height * sy}px`,
    };
}

// ── positioned issues ─────────────────────────────────────────────────────────
const positionedIssues = computed(() => {
    if (!issuesForList.value?.length) return [];
    const sy = shotDisplay.value.h / (shotNatural.value.h || 1);
    const withPos = issuesForList.value
        .map((issue) => {
            const bbox = boxForIssue(issue);
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

function setIssueRef(id, el) {
    if (!el) return;
    const h = el.getBoundingClientRect().height;
    if (Math.abs((issueHeights.value[id] || 0) - h) < 0.5) return;
    issueHeights.value = { ...issueHeights.value, [id]: h };
}

watch(issues, () => {
    decisionMap.value = { ...decisionMap.value };
    issueHeights.value = {};
    nextTick(() => {});
});
watch(displayIssues, () => {
    issueHeights.value = {};
    nextTick(() => {});
});

// ── export PDF ────────────────────────────────────────────────────────────────
async function exportPdf() {
    if (exportingPdf.value || !resultCard.value) {
        if (!resultCard.value) error.value = "未找到可导出的内容区域";
        return;
    }
    exportingPdf.value = true;
    error.value = "";
    exportMode.value = true;
    await nextTick();
    try {
        const h2c = await loadLib(
            "https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js",
            "html2canvas",
        );
        const jPDF = await loadLib(
            "https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js",
            "jspdf.jsPDF",
            true,
        );
        const canvas = await h2c(resultCard.value, {
            scale: 2,
            useCORS: true,
            allowTaint: false,
            backgroundColor: "#ffffff",
            scrollX: 0,
            scrollY: -window.scrollY,
        });
        const img = canvas.toDataURL("image/png");
        const pdf = new jPDF("p", "mm", "a4");
        const pw = pdf.internal.pageSize.getWidth();
        const ph = pdf.internal.pageSize.getHeight();
        const m = 6;
        const iw = pw - m * 2;
        const ih = (canvas.height * iw) / canvas.width;
        let rem = ih;
        pdf.addImage(img, "PNG", m, m, iw, ih);
        rem -= ph - m * 2;
        while (rem > 0) {
            pdf.addPage();
            pdf.addImage(img, "PNG", m, m - (ih - rem), iw, ih);
            rem -= ph - m * 2;
        }
        pdf.save(`audit-report-${Date.now()}.pdf`);
    } catch (e) {
        error.value = e?.message || "导出 PDF 失败";
    } finally {
        exportMode.value = false;
        exportingPdf.value = false;
    }
}

async function loadLib(url, globalPath, nested = false) {
    const parts = globalPath.split(".");
    const root = parts[0];
    if (!window[root]) {
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
    let v = window;
    for (const p of parts) {
        v = v?.[p];
    }
    if (!v) throw new Error(`${globalPath} 加载失败`);
    return v;
}

userToken.value = ensureUserToken();
loadHistory();
fetchLibraries();
</script>

<style scoped>
/* ── reset ─────────────────────────────────────────────────────── */
*,
*::before,
*::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

/* ── shell ─────────────────────────────────────────────────────── */
.shell {
    display: flex;
    min-height: 100vh;
    background: #f5f4f0;
    color: #1a1a1a;
    font-family: "Inter", "Segoe UI", system-ui, sans-serif;
    font-size: 14px;
}

/* ── sidebar (desktop) ─────────────────────────────────────────── */
.sidebar {
    width: 224px;
    flex-shrink: 0;
    background: #ffffff;
    border-right: 0.5px solid #e5e3dc;
    display: flex;
    flex-direction: column;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
}
/* mobile sidebar */
.sidebar-mobile {
    position: fixed;
    top: 0;
    left: -224px;
    height: 100vh;
    z-index: 60;
    transition: left 0.25s ease;
    box-shadow: none;
}
.sidebar-mobile.open {
    left: 0;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.12);
}
.sidebar-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.35);
    z-index: 55;
}
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}

.logo {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 18px 16px 14px;
}
.logo-mark {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: #eeedfe;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 500;
    color: #3c3489;
    flex-shrink: 0;
}
.logo-text {
    font-size: 13px;
    font-weight: 500;
    color: #1a1a1a;
    line-height: 1.3;
}
.logo-sub {
    font-size: 11px;
    color: #aaa;
    line-height: 1.3;
}
.close-btn {
    margin-left: auto;
    background: none;
    border: none;
    color: #aaa;
    font-size: 14px;
    cursor: pointer;
    padding: 4px;
}
.rule {
    height: 0.5px;
    background: #e5e3dc;
    margin: 0 14px;
}

.nav-wrap {
    padding: 8px 8px 4px;
}
.nav-label {
    font-size: 10px;
    color: #bbb;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    padding: 6px 8px 4px;
}
.nav-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    color: #555;
    border: none;
    background: none;
    width: 100%;
    text-align: left;
    transition: background 0.12s;
    margin-bottom: 1px;
    font-family: inherit;
}
.nav-item:hover {
    background: #f5f4f0;
}
.nav-item.active {
    background: #eeedfe;
    color: #3c3489;
    font-weight: 500;
}
.nav-count {
    margin-left: auto;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 999px;
    background: #f0efe8;
    color: #888;
}
.nav-item.active .nav-count {
    background: #cecbf6;
    color: #3c3489;
}

.recent-wrap {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    padding: 8px 8px 12px;
}
.recent-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1px;
    margin-top: 2px;
}
.recent-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 8px;
    cursor: pointer;
    border: none;
    background: none;
    width: 100%;
    text-align: left;
    transition: background 0.12s;
    font-family: inherit;
}
.recent-item:hover {
    background: #f5f4f0;
}
.recent-item.active {
    background: #eeedfe;
}
.recent-body {
    flex: 1;
    min-width: 0;
}
.recent-title {
    display: block;
    font-size: 12px;
    font-weight: 500;
    color: #333;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.recent-time {
    display: block;
    font-size: 10px;
    color: #aaa;
    margin-top: 2px;
}

/* ── main ──────────────────────────────────────────────────────── */
.main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
}

.topbar {
    background: #ffffff;
    border-bottom: 0.5px solid #e5e3dc;
    padding: 10px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
    position: sticky;
    top: 0;
    z-index: 10;
}
.hamburger {
    display: none;
    padding: 6px 8px;
    border-radius: 8px;
    border: 0.5px solid #e5e3dc;
    background: none;
    color: #555;
    cursor: pointer;
}
@media (max-width: 768px) {
    .sidebar:not(.sidebar-mobile) {
        display: none;
    }
    .hamburger {
        display: flex;
        align-items: center;
    }
}
.tab-strip {
    display: flex;
    gap: 2px;
    background: #f0efe8;
    border-radius: 8px;
    padding: 3px;
}
.tstrip-btn {
    padding: 5px 16px;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    border: none;
    background: none;
    color: #888;
    transition: all 0.12s;
    font-family: inherit;
}
.tstrip-btn.active {
    background: #fff;
    color: #1a1a1a;
    font-weight: 500;
    border: 0.5px solid #e5e3dc;
}

.content {
    flex: 1;
    padding: 28px 32px;
    overflow-y: auto;
}
@media (max-width: 640px) {
    .content {
        padding: 16px 14px;
    }
}

/* ── panel layout ──────────────────────────────────────────────── */
.panel {
    max-width: 820px;
    padding-bottom: 80px;
}
.panel-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.eyebrow {
    font-size: 11px;
    color: #534ab7;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 500;
    margin-bottom: 5px;
}
h2 {
    font-size: 20px;
    font-weight: 500;
    color: #1a1a1a;
    margin-bottom: 5px;
}
.sub {
    font-size: 13px;
    color: #888;
    line-height: 1.6;
    margin-bottom: 4px;
}

/* ── form ───────────────────────────────────────────────────────── */
.mode-switch {
    display: flex;
    gap: 6px;
    margin: 12px 0;
}
.mode-btn {
    padding: 6px 16px;
    border-radius: 8px;
    border: 0.5px solid #d8d6ce;
    background: none;
    font-size: 12px;
    color: #666;
    cursor: pointer;
    transition: all 0.12s;
    font-family: inherit;
}
.mode-btn.active {
    background: #eeedfe;
    border-color: #afa9ec;
    color: #3c3489;
    font-weight: 500;
}
.mode-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.form-col {
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.form-label {
    font-size: 12px;
    color: #666;
    font-weight: 500;
}
.hint-text {
    font-weight: 400;
    color: #aaa;
}
.input-row {
    display: flex;
    gap: 8px;
}
.text-input {
    flex: 1;
    padding: 9px 12px;
    border-radius: 8px;
    border: 0.5px solid #d8d6ce;
    background: #fff;
    color: #1a1a1a;
    font-size: 13px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s;
}
.text-input:focus {
    border-color: #afa9ec;
}
.text-input:disabled {
    opacity: 0.6;
}

.file-row {
    display: flex;
    align-items: center;
    gap: 10px;
}
.library-list {
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px;
    border: 1px solid #e6e3d8;
    border-radius: 10px;
    background: #fcfbf7;
    max-height: 180px;
    overflow: auto;
}
.library-item {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #575248;
    font-size: 12px;
    min-width: 0;
}
.lib-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.lib-actions {
    display: flex;
    gap: 4px;
    margin-left: auto;
    flex-shrink: 0;
}
.lib-btn {
    padding: 2px 6px;
    border-radius: 5px;
    border: 0.5px solid #d8d6ce;
    background: none;
    font-size: 11px;
    color: #888;
    cursor: pointer;
    transition: all 0.12s;
    white-space: nowrap;
    line-height: 1.4;
}
.lib-btn:hover {
    background: #f5f4f0;
    color: #333;
}
.lib-btn.ok {
    color: #639922;
    border-color: #b8dea0;
}
.lib-btn.ok:hover {
    background: #edf7e5;
}
.lib-btn.del {
    color: #a32d2d;
    border-color: #f7c1c1;
}
.lib-btn.del:hover {
    background: #fcebeb;
}
.lib-edit-input {
    flex: 1;
    min-width: 0;
    padding: 2px 6px;
    border-radius: 5px;
    border: 0.5px solid #afa9ec;
    background: #fff;
    font-size: 12px;
    font-family: inherit;
    outline: none;
    color: #1a1a1a;
}
.pending-list {
    margin-top: 8px;
    padding: 10px;
    border: 1px solid #e6e3d8;
    border-radius: 10px;
    background: #fafaf7;
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.pending-hint {
    font-size: 11px;
    color: #aaa;
    margin: 0;
}
.pending-item {
    display: flex;
    align-items: center;
    gap: 8px;
}
.pending-orig {
    font-size: 11px;
    color: #aaa;
    flex-shrink: 0;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.pending-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 4px;
}
.file-pick-btn {
    padding: 7px 14px;
    border-radius: 8px;
    border: 0.5px solid #d8d6ce;
    background: #fff;
    font-size: 12px;
    color: #555;
    cursor: pointer;
    transition: background 0.12s;
    white-space: nowrap;
}
.file-pick-btn:hover {
    background: #f5f4f0;
}
.file-name-hint {
    font-size: 12px;
    color: #aaa;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 240px;
}

.textarea-input {
    width: 100%;
    padding: 9px 12px;
    border-radius: 8px;
    border: 0.5px solid #d8d6ce;
    background: #fff;
    color: #1a1a1a;
    font-size: 13px;
    font-family: inherit;
    outline: none;
    resize: vertical;
    min-height: 80px;
    line-height: 1.6;
    transition: border-color 0.15s;
}
.textarea-input:focus {
    border-color: #afa9ec;
}
.textarea-input:disabled {
    opacity: 0.6;
}

.primary-btn {
    padding: 9px 22px;
    border-radius: 8px;
    border: none;
    background: #534ab7;
    color: #eeedfe;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.12s;
    white-space: nowrap;
}
.primary-btn:hover:not(:disabled) {
    background: #3c3489;
}
.primary-btn:disabled {
    background: #e5e3dc;
    color: #aaa;
    cursor: not-allowed;
}

.ghost-btn {
    padding: 5px 12px;
    border-radius: 8px;
    border: 0.5px solid #d8d6ce;
    background: none;
    font-size: 12px;
    color: #555;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.12s;
    white-space: nowrap;
}
.ghost-btn:hover:not(:disabled) {
    background: #f5f4f0;
}
.ghost-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
.ghost-btn.danger {
    color: #a32d2d;
    border-color: #f7c1c1;
}
.ghost-btn.danger:hover {
    background: #fcebeb;
}
.ghost-btn.sm {
    padding: 3px 9px;
    font-size: 11px;
}

.error-banner {
    padding: 9px 12px;
    border-radius: 8px;
    background: #fcebeb;
    border: 0.5px solid #f7c1c1;
    color: #501313;
    font-size: 12px;
}
.task-id-note {
    font-size: 11px;
    color: #aaa;
}
.action-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

/* ── progress ───────────────────────────────────────────────────── */
.progress-wrap {
    margin: 8px 0 2px;
}
.progress-bg {
    height: 3px;
    border-radius: 999px;
    background: #e5e3dc;
}
.progress-fill {
    height: 100%;
    border-radius: 999px;
    background: #534ab7;
    transition: width 0.5s ease;
}
.progress-fill.ok {
    background: #639922;
}
.progress-fill.err {
    background: #e24b4a;
}

/* ── status ─────────────────────────────────────────────────────── */
.status-pill {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 999px;
    font-weight: 500;
    white-space: nowrap;
}
.status-pill.idle {
    background: #f0efe8;
    color: #888;
}
.status-pill.warn {
    background: #faeeda;
    color: #633806;
}
.status-pill.ok {
    background: #eaf3de;
    color: #27500a;
}
.status-pill.err {
    background: #fcebeb;
    color: #501313;
}
.count-chip {
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 999px;
    background: #f0efe8;
    color: #555;
}

/* ── history ────────────────────────────────────────────────────── */
.hist-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.hist-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 11px 13px;
    border-radius: 10px;
    border: 0.5px solid #e5e3dc;
    background: #fff;
    transition: border-color 0.15s;
}
.hist-row.active {
    border-color: #afa9ec;
    background: #faf9ff;
}
.dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
}
.hist-body {
    flex: 1;
    min-width: 0;
}
.hist-title {
    font-size: 13px;
    font-weight: 500;
    color: #1a1a1a;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 4px;
}
.hist-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
.hist-meta span {
    font-size: 11px;
    color: #888;
}
.meta-time {
    margin-left: auto !important;
    color: #aaa !important;
}
.hist-checklist {
    font-size: 11px;
    color: #aaa;
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.hist-actions {
    display: flex;
    flex-direction: column;
    gap: 3px;
    flex-shrink: 0;
}
.mini-pill {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 999px;
    font-weight: 500;
}
.mini-pill.running {
    background: #faeeda;
    color: #633806;
}
.mini-pill.completed {
    background: #eaf3de;
    color: #27500a;
}
.mini-pill.failed {
    background: #fcebeb;
    color: #501313;
}

/* ── review bar ────────────────────────────────────────────────── */
.review-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}
.summary-chips {
    display: flex;
    gap: 8px;
}
.chip {
    font-size: 11px;
    padding: 3px 9px;
    border-radius: 999px;
}
.chip.green {
    background: #eaf3de;
    color: #27500a;
}
.chip.red {
    background: #fcebeb;
    color: #501313;
}

/* ── export wrap ───────────────────────────────────────────────── */
.export-wrap {
    border-radius: 12px;
    border: 0.5px solid #e5e3dc;
    background: #fff;
    padding: 14px;
}
.export-head {
    display: none;
    margin-bottom: 12px;
    padding: 10px 12px;
    border-radius: 8px;
    background: #f5f4f0;
    border: 0.5px solid #e5e3dc;
}
.export-head h3 {
    font-size: 15px;
    font-weight: 500;
    margin-bottom: 4px;
}
.export-head p {
    font-size: 12px;
    color: #666;
    margin-top: 2px;
    word-break: break-all;
}
.export-mode .export-head {
    display: block;
}

/* ── result grid ───────────────────────────────────────────────── */
.result-grid {
    display: grid;
    grid-template-columns: 1.25fr 1fr;
    gap: 14px;
    align-items: start;
}
@media (max-width: 860px) {
    .result-grid {
        grid-template-columns: 1fr;
    }
}

.shot-pane {
    border-radius: 10px;
    border: 0.5px solid #e5e3dc;
    overflow: hidden;
    background: #fafaf8;
    min-height: 160px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.shot-wrapper {
    position: relative;
    width: 100%;
    user-select: none;
}
.shot-wrapper.drawing {
    cursor: crosshair;
}
.shot-img {
    display: block;
    width: 100%;
    height: auto;
    object-fit: contain;
}

.overlay-box {
    position: absolute;
    border: 1.5px solid #7f77dd;
    background: rgba(127, 119, 221, 0.12);
    pointer-events: none;
    transition:
        border-color 0.2s,
        background 0.2s;
    border-radius: 0;
}
.overlay-box.active {
    border-color: #534ab7;
    background: rgba(83, 74, 183, 0.2);
}
.overlay-box.manual {
    border-color: #10b981;
    background: rgba(16, 185, 129, 0.12);
}
.overlay-box.rejected {
    border-color: #e24b4a;
    background: rgba(226, 75, 74, 0.12);
}
.overlay-box.preview {
    border-style: dashed;
    border-color: #10b981;
    background: rgba(16, 185, 129, 0.15);
}

.issues-pane {
    position: relative;
    overflow-x: hidden;
    overflow-y: auto;
    border: 0.5px solid #e5e3dc;
    border-radius: 10px;
    padding: 6px 5px;
    background: #fafaf8;
}
.export-mode .issues-pane {
    overflow: visible;
}

.issue-card {
    position: absolute;
    left: 0;
    right: 0;
    padding: 11px 13px;
    border-radius: 10px;
    background: #fff;
    border: 0.5px solid #e5e3dc;
    transition: border-color 0.15s;
    cursor: default;
}
.issue-card.active {
    border-color: #afa9ec;
    background: #faf9ff;
}
.issue-card.rejected {
    opacity: 0.75;
    border-color: #f7c1c1;
}
.issue-card.manual {
    border-color: #a7f3d0;
}

.issue-top {
    display: flex;
    align-items: center;
    gap: 7px;
    flex-wrap: wrap;
    margin-bottom: 7px;
}
.sev-badge {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 999px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.sev-warn {
    background: #faeeda;
    color: #633806;
}
.sev-critical,
.sev-error {
    background: #fcebeb;
    color: #501313;
}
.sev-info {
    background: #e6f1fb;
    color: #0c447c;
}
.issue-type {
    font-size: 12px;
    font-weight: 500;
    color: #333;
}
.issue-conf {
    font-size: 11px;
    color: #aaa;
    margin-left: auto;
}
.decision-tag {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 999px;
    font-weight: 500;
}
.decision-tag.kept {
    background: #eaf3de;
    color: #27500a;
}
.decision-tag.rej {
    background: #fcebeb;
    color: #501313;
}

.issue-btns {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 8px;
}
.mini-btn {
    padding: 3px 10px;
    border-radius: 6px;
    border: 0.5px solid #d8d6ce;
    background: none;
    font-size: 11px;
    color: #555;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.12s;
}
.mini-btn:hover {
    background: #f5f4f0;
}
.mini-btn.reject {
    color: #a32d2d;
    border-color: #f7c1c1;
}
.mini-btn.reject:hover {
    background: #fcebeb;
}
.mini-btn.danger {
    color: #a32d2d;
    border-color: #f7c1c1;
}

.issue-quote {
    font-size: 12px;
    color: #666;
    border-left: 2px solid #cecbf6;
    padding-left: 8px;
    margin-bottom: 6px;
    font-style: italic;
    line-height: 1.5;
    border-radius: 0;
}
.issue-rec {
    font-size: 12px;
    color: #555;
    line-height: 1.5;
    margin-bottom: 4px;
}
.issue-meta {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 5px;
}
.issue-meta span {
    font-size: 11px;
    color: #aaa;
}

.ann-label {
    display: block;
    font-size: 11px;
    color: #534ab7;
    margin: 8px 0 4px;
}
.ann-input {
    width: 100%;
    min-height: 58px;
    border-radius: 8px;
    border: 0.5px solid #d8d6ce;
    background: #fafaf8;
    color: #1a1a1a;
    padding: 8px;
    resize: vertical;
    font-size: 12px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s;
}
.ann-input:focus {
    border-color: #afa9ec;
}

/* ── empty state ────────────────────────────────────────────────── */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 40px 20px;
    border: 0.5px dashed #d8d6ce;
    border-radius: 10px;
}
.empty-state p {
    font-size: 13px;
    color: #aaa;
}

/* ── floating action bar ────────────────────────────────────────── */
.fab-bar {
    position: fixed;
    left: 50%;
    bottom: 18px;
    transform: translateX(-50%);
    z-index: 90;
    display: flex;
    gap: 10px;
    padding: 8px;
    border-radius: 999px;
    background: #fff;
    border: 0.5px solid #e5e3dc;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}
.fab {
    padding: 9px 20px;
    border-radius: 999px;
    border: none;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    font-family: inherit;
    transition: all 0.15s;
    background: #534ab7;
    color: #eeedfe;
}
.fab:hover:not(:disabled) {
    background: #3c3489;
}
.fab:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
.fab-draw-active {
    background: #059669;
    color: #ecfdf5;
}
.fab-draw-active:hover:not(:disabled) {
    background: #047857;
}
.fab-export {
    background: #92400e;
    color: #fffbeb;
}
.fab-export:hover:not(:disabled) {
    background: #78350f;
}

@media (max-width: 640px) {
    .fab-bar {
        width: calc(100vw - 24px);
        left: 12px;
        bottom: 12px;
        transform: none;
        border-radius: 14px;
        justify-content: space-between;
    }
    .fab {
        flex: 1;
        text-align: center;
        font-size: 12px;
        padding: 9px 10px;
    }
    .hist-row {
        flex-direction: column;
    }
    .hist-actions {
        flex-direction: row;
    }
    .panel-head {
        flex-direction: column;
    }
}
</style>
