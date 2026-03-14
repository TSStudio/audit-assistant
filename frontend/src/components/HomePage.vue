<template>
    <div class="shell">
        <!-- ══ icon sidebar ══════════════════════════════════════════════════════ -->
        <aside class="icon-sb">
            <div class="logo-sq">A</div>

            <button
                class="i-btn"
                :class="{ on: tab === 'submit' }"
                @click="tab = 'submit'"
                title="新建审计"
            >
                <SvgPlus />
                <span class="i-tip">新建审计</span>
            </button>
            <button
                class="i-btn"
                :class="{ on: tab === 'result' }"
                @click="tab = 'result'"
                title="审计结果"
            >
                <SvgDoc />
                <span class="i-tip">审计结果</span>
            </button>
            <button
                class="i-btn"
                :class="{ on: tab === 'history' }"
                @click="tab = 'history'"
                title="历史记录"
                style="position: relative"
            >
                <SvgClock />
                <span v-if="taskHistory.length" class="i-notch" />
                <span class="i-tip">历史记录</span>
            </button>

            <div class="i-sep" />

            <button class="i-btn" title="设置">
                <SvgSettings />
                <span class="i-tip">设置</span>
            </button>

            <div class="i-avatar" style="margin-top: auto">编</div>
            <div class="today-count">今日 {{ todayCount }} 篇</div>
        </aside>

        <!-- ══ main ══════════════════════════════════════════════════════════════ -->
        <div class="main">
            <!-- topbar -->
            <header class="topbar">
                <div class="breadcrumb">
                    Audit Assistant
                    <SvgChevron
                        style="opacity: 0.4; width: 10px; height: 10px"
                    />
                    <span>{{ tabLabel }}</span>
                </div>
                <div class="topbar-right">
                    <!-- motivation toggle -->
                    <button
                        class="mot-toggle"
                        :class="{ active: showMotivation }"
                        @click="showMotivation = !showMotivation"
                        title="激励面板"
                    >
                        <SvgStar />
                    </button>
                    <span v-if="status" class="s-pill" :class="pillClass">{{
                        statusLabel
                    }}</span>
                </div>
            </header>

            <!-- motivation banner (collapsible) -->
            <transition name="slide-down">
                <div v-if="showMotivation" class="mot-banner">
                    <div class="mot-icon">{{ motIcon }}</div>
                    <div class="mot-body">
                        <div class="mot-title">{{ motTitle }}</div>
                        <div class="mot-sub">{{ motSub }}</div>
                    </div>
                    <div v-if="tab === 'submit'" class="ach-row">
                        <div
                            v-for="a in achievements"
                            :key="a.id"
                            class="ach-badge"
                            :class="a.unlocked ? `ab-${a.color}` : 'ab-locked'"
                            :title="a.unlocked ? '已解锁' : `${a.goal} 后解锁`"
                        >
                            <span
                                class="ach-icon"
                                :style="
                                    a.unlocked
                                        ? ''
                                        : 'filter:grayscale(1);opacity:.35'
                                "
                                >{{ a.icon }}</span
                            >
                            <div class="ach-name">{{ a.name }}</div>
                            <div class="ach-prog">
                                {{ a.unlocked ? "已解锁" : a.goal }}
                            </div>
                        </div>
                    </div>
                </div>
            </transition>

            <!-- content -->
            <div class="content">
                <div class="left-panel">
                    <!-- ── SUBMIT ──────────────────────────────────────────────────── -->
                    <template v-if="tab === 'submit'">
                        <div class="submit-card">
                            <div class="pg-eye">新建审计</div>
                            <h2 class="pg-title">今天想审什么？</h2>
                            <p class="pg-sub">
                                粘贴链接或上传文件，AI 替你把关每一个细节。
                            </p>

                            <div class="mode-row">
                                <button
                                    class="mode-pill"
                                    :class="{ on: inputMode === 'url' }"
                                    @click="switchMode('url')"
                                >
                                    URL 链接
                                </button>
                                <button
                                    class="mode-pill"
                                    :class="{ on: inputMode === 'file' }"
                                    @click="switchMode('file')"
                                >
                                    文件上传
                                </button>
                            </div>

                            <label class="f-label" style="margin-top: 12px"
                                >审计模式</label
                            >
                            <div class="mode-row" style="margin-top: 8px">
                                <button
                                    class="mode-pill"
                                    :class="{ on: auditSpeed === 'fast' }"
                                    :disabled="loading"
                                    @click="auditSpeed = 'fast'"
                                >
                                    Fast Mode（关闭 Thinking）
                                </button>
                                <button
                                    class="mode-pill"
                                    :class="{ on: auditSpeed === 'slow' }"
                                    :disabled="loading"
                                    @click="auditSpeed = 'slow'"
                                >
                                    Slow Mode（开启 Thinking）
                                </button>
                            </div>

                            <template v-if="inputMode === 'url'">
                                <label class="f-label">页面链接</label>
                                <div class="inp-row">
                                    <input
                                        v-model="urlInput"
                                        type="url"
                                        class="text-inp"
                                        placeholder="https://example.com/article"
                                        :disabled="loading"
                                        @keydown.enter="startAudit"
                                    />
                                    <button
                                        class="primary-btn"
                                        :disabled="loading || !urlInput"
                                        @click="startAudit"
                                    >
                                        <SvgArrow />{{
                                            loading ? "提交中…" : "开始审计"
                                        }}
                                    </button>
                                </div>
                            </template>

                            <template v-else>
                                <label class="f-label">上传文件</label>
                                <div class="file-row">
                                    <label class="file-lbl">
                                        <SvgUpload />选择文件
                                        <input
                                            ref="fileInputRef"
                                            type="file"
                                            accept=".txt,.docx,.pdf,image/*"
                                            :disabled="loading"
                                            style="display: none"
                                            @change="onFileChange"
                                        />
                                    </label>
                                    <span class="file-nm">{{
                                        selectedFileName || "未选择文件"
                                    }}</span>
                                </div>
                                <div class="inp-row" style="margin-top: 10px">
                                    <button
                                        class="primary-btn"
                                        :disabled="loading || !selectedFile"
                                        @click="startAudit"
                                    >
                                        <SvgArrow />{{
                                            loading ? "提交中…" : "开始审计"
                                        }}
                                    </button>
                                </div>
                            </template>
                        </div>

                        <div class="field-card">
                            <span class="f-label"
                                >审核清单知识库
                                <span class="f-hint"
                                    >（可复用，可多选）</span
                                ></span
                            >
                            <textarea
                                v-model="checklistInput"
                                class="f-ta"
                                rows="4"
                                :disabled="loading"
                                placeholder="输入临时清单（每行一条），或点“保存到知识库”复用"
                            />
                            <div class="inp-row" style="margin-top: 8px">
                                <input
                                    v-model="newChecklistName"
                                    type="text"
                                    class="text-inp"
                                    :disabled="loading"
                                    placeholder="清单名称，例如：金融稿件审核"
                                />
                                <button
                                    class="ghost-sm"
                                    :disabled="
                                        loading || !checklistInput.trim()
                                    "
                                    @click="saveChecklistToKb"
                                >
                                    保存到知识库
                                </button>
                            </div>
                            <div
                                v-if="checklistKbs.length"
                                class="kb-list"
                                style="margin-top: 8px"
                            >
                                <div
                                    v-for="item in checklistKbs"
                                    :key="item.kb_id"
                                    class="kb-item"
                                >
                                    <label class="kb-main">
                                        <input
                                            type="checkbox"
                                            :value="item.kb_id"
                                            v-model="selectedChecklistKbIds"
                                            :disabled="loading"
                                        />
                                        <span>{{ item.name }}</span>
                                    </label>
                                    <div class="kb-ops">
                                        <button
                                            class="kb-op"
                                            :disabled="loading"
                                            @click="renameChecklistKb(item)"
                                        >
                                            改名
                                        </button>
                                        <button
                                            class="kb-op danger"
                                            :disabled="loading"
                                            @click="deleteChecklistKb(item)"
                                        >
                                            删除
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <p v-else class="f-hint" style="margin-top: 8px">
                                暂无清单知识库
                            </p>
                        </div>

                        <div class="field-card">
                            <span class="f-label"
                                >附加资料知识库
                                <span class="f-hint"
                                    >（上传一次，后续可直接选择）</span
                                ></span
                            >
                            <div class="file-row" style="margin-top: 6px">
                                <label class="file-lbl">
                                    <SvgUpload />上传到知识库
                                    <input
                                        ref="referenceFileInputRef"
                                        type="file"
                                        accept=".txt,.docx,.pdf"
                                        multiple
                                        :disabled="loading"
                                        style="display: none"
                                        @change="onReferenceFilesChange"
                                    />
                                </label>
                                <span class="file-nm">{{
                                    referenceFileNamesText
                                }}</span>
                                <button
                                    class="ghost-sm"
                                    :disabled="
                                        loading || !referenceFiles.length
                                    "
                                    @click="saveReferencesToKb"
                                >
                                    保存
                                </button>
                            </div>
                            <div
                                v-if="referenceKbs.length"
                                class="kb-list"
                                style="margin-top: 8px"
                            >
                                <div
                                    v-for="item in referenceKbs"
                                    :key="item.kb_id"
                                    class="kb-item"
                                >
                                    <label class="kb-main">
                                        <input
                                            type="checkbox"
                                            :value="item.kb_id"
                                            v-model="selectedReferenceKbIds"
                                            :disabled="loading"
                                        />
                                        <span>{{ item.name }}</span>
                                    </label>
                                    <div class="kb-ops">
                                        <button
                                            class="kb-op"
                                            :disabled="loading"
                                            @click="renameReferenceKb(item)"
                                        >
                                            改名
                                        </button>
                                        <button
                                            class="kb-op danger"
                                            :disabled="loading"
                                            @click="deleteReferenceKb(item)"
                                        >
                                            删除
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <p v-else class="f-hint" style="margin-top: 8px">
                                暂无附加资料知识库
                            </p>
                        </div>

                        <div v-if="error" class="err-banner">⚠ {{ error }}</div>

                        <div v-if="status" class="prog-card">
                            <div class="prog-top">
                                <span class="prog-msg-txt">{{
                                    message || "准备中…"
                                }}</span>
                                <span class="prog-pct"
                                    >{{ Math.round(displayProgress) }}%</span
                                >
                            </div>
                            <div class="prog-track">
                                <div
                                    class="prog-fill"
                                    :class="{
                                        done: status === 'completed',
                                        err: status === 'failed',
                                    }"
                                    :style="{ width: progressWidth }"
                                />
                            </div>
                            <div v-if="taskId" class="prog-note">
                                任务 {{ taskId }}
                            </div>
                        </div>
                    </template>

                    <!-- ── RESULT ──────────────────────────────────────────────────── -->
                    <template v-if="tab === 'result'">
                        <div
                            v-if="!screenshotSrc && !displayIssues.length"
                            class="empty-ph"
                        >
                            <span class="ep-icon">🔍</span>
                            <div class="ep-title">这里还没有结果</div>
                            <p class="ep-sub">
                                提交一个 URL 或文件，AI
                                会帮你找出每一个值得关注的问题。
                            </p>
                            <button
                                class="primary-btn"
                                style="margin-top: 4px"
                                @click="tab = 'submit'"
                            >
                                <SvgPlus />开始第一次审计
                            </button>
                        </div>

                        <template v-else>
                            <!-- all resolved celebration -->
                            <transition name="fade">
                                <div
                                    v-if="allResolved && displayIssues.length"
                                    class="clean-banner"
                                >
                                    <span>✨</span>
                                    <div>
                                        <div class="cb-title">
                                            所有问题已处理，干得漂亮！
                                        </div>
                                        <div class="cb-sub">
                                            可以放心导出报告了。
                                        </div>
                                    </div>
                                </div>
                            </transition>

                            <div class="result-toolbar">
                                <div class="toolbar-chips">
                                    <span class="schip schip-g"
                                        >已保留 {{ decisionStats.kept }}</span
                                    >
                                    <span class="schip schip-r"
                                        >已驳回
                                        {{ decisionStats.rejected }}</span
                                    >
                                    <span class="ct-chip"
                                        >{{ displayIssues.length }} 个问题</span
                                    >
                                </div>
                                <button
                                    class="ghost-sm"
                                    :disabled="!customIssues.length"
                                    @click="clearCustomIssues"
                                >
                                    清空手工批注
                                </button>
                            </div>

                            <!-- result grid: screenshot + issues -->
                            <div class="result-wrap">
                                <!-- screenshot -->
                                <div
                                    class="shot-pane"
                                    ref="shotWrapper"
                                    :class="{ drawing: drawingMode }"
                                    @mousedown="beginDraw"
                                    @mousemove="moveDraw"
                                    @mouseup="endDraw"
                                    @mouseleave="cancelDraw"
                                >
                                    <img
                                        v-if="screenshotSrc"
                                        ref="shotImg"
                                        class="shot-img"
                                        :src="screenshotSrc"
                                        crossorigin="anonymous"
                                        alt="页面截图"
                                        @load="onShotLoad"
                                    />
                                    <div v-else class="shot-ph">
                                        <SvgImage
                                            style="
                                                width: 32px;
                                                height: 32px;
                                                opacity: 0.3;
                                                margin-bottom: 8px;
                                            "
                                        />
                                        <p>截图在审计完成后显示</p>
                                    </div>
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

                                <!-- issues pane -->
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
                                            class="i-card"
                                            :class="{
                                                active:
                                                    hoverIssueId ===
                                                    item.issue.id,
                                                resolved: isRejected(
                                                    item.issue.id,
                                                ),
                                                manual: item.issue.manual,
                                            }"
                                            :style="{ top: item.top + 'px' }"
                                            :ref="
                                                (el) =>
                                                    setIssueRef(
                                                        item.issue.id,
                                                        el,
                                                    )
                                            "
                                            @mouseenter="
                                                hoverIssueId = item.issue.id
                                            "
                                            @mouseleave="hoverIssueId = null"
                                        >
                                            <div
                                                class="i-stripe"
                                                :class="`is-${item.issue.severity || 'info'}`"
                                            />
                                            <div class="i-body">
                                                <div class="i-top">
                                                    <span
                                                        class="sev-tag"
                                                        :class="`sv-${item.issue.severity || 'info'}`"
                                                        >{{
                                                            item.issue
                                                                .severity ||
                                                            "info"
                                                        }}</span
                                                    >
                                                    <span class="i-type">{{
                                                        item.issue.type ||
                                                        "custom"
                                                    }}</span>
                                                    <span
                                                        v-if="
                                                            item.issue
                                                                .confidence
                                                        "
                                                        class="i-conf"
                                                        >{{
                                                            Number(
                                                                item.issue
                                                                    .confidence,
                                                            ).toFixed(2)
                                                        }}</span
                                                    >
                                                    <span
                                                        class="dtag"
                                                        :class="
                                                            isRejected(
                                                                item.issue.id,
                                                            )
                                                                ? 'dt-r'
                                                                : 'dt-k'
                                                        "
                                                    >
                                                        {{
                                                            isRejected(
                                                                item.issue.id,
                                                            )
                                                                ? "已驳回"
                                                                : "已保留"
                                                        }}
                                                    </span>
                                                </div>
                                                <div class="i-btns">
                                                    <button
                                                        v-if="
                                                            !isRejected(
                                                                item.issue.id,
                                                            )
                                                        "
                                                        class="mi-btn rej"
                                                        @click="
                                                            rejectIssue(
                                                                item.issue.id,
                                                            )
                                                        "
                                                    >
                                                        驳回
                                                    </button>
                                                    <button
                                                        v-else
                                                        class="mi-btn"
                                                        @click="
                                                            undoReject(
                                                                item.issue.id,
                                                            )
                                                        "
                                                    >
                                                        撤销
                                                    </button>
                                                    <button
                                                        v-if="item.issue.manual"
                                                        class="mi-btn danger"
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
                                                    v-if="
                                                        item.issue.evidence
                                                            ?.quote
                                                    "
                                                    class="i-quote"
                                                >
                                                    "{{
                                                        item.issue.evidence
                                                            .quote
                                                    }}"
                                                </p>
                                                <p
                                                    v-if="
                                                        item.issue
                                                            .recommendation
                                                    "
                                                    class="i-rec"
                                                >
                                                    建议：{{
                                                        item.issue
                                                            .recommendation
                                                    }}
                                                </p>
                                                <template
                                                    v-if="item.issue.manual"
                                                >
                                                    <span class="ann-lbl"
                                                        >批注内容</span
                                                    >
                                                    <textarea
                                                        class="ann-ta"
                                                        :value="
                                                            noteForIssue(
                                                                item.issue.id,
                                                            )
                                                        "
                                                        placeholder="输入你的审校意见…"
                                                        @input="
                                                            updateNote(
                                                                item.issue.id,
                                                                $event.target
                                                                    .value,
                                                            )
                                                        "
                                                    />
                                                </template>
                                                <div class="i-meta">
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
                                                            item.issue.evidence
                                                                .image_id
                                                        }}</span
                                                    >
                                                    <span
                                                        v-if="item.issue.manual"
                                                        >手工批注</span
                                                    >
                                                </div>
                                            </div>
                                        </div>
                                    </template>
                                    <div
                                        v-else
                                        class="empty-ph"
                                        style="border: none; padding: 32px 16px"
                                    >
                                        <span
                                            class="ep-icon"
                                            style="font-size: 24px"
                                            >✅</span
                                        >
                                        <p class="ep-sub">暂无问题</p>
                                    </div>
                                </div>
                            </div>
                        </template>
                    </template>

                    <!-- ── HISTORY ─────────────────────────────────────────────────── -->
                    <template v-if="tab === 'history'">
                        <div class="sec-head">
                            <h2 class="pg-title" style="font-size: 18px">
                                所有审计任务
                            </h2>
                            <button
                                v-if="taskHistory.length"
                                class="ghost-sm danger"
                                @click="clearHistory"
                            >
                                清空全部
                            </button>
                        </div>

                        <div v-if="!taskHistory.length" class="empty-ph">
                            <span class="ep-icon">📂</span>
                            <div class="ep-title">还没有历史记录</div>
                            <p class="ep-sub">
                                提交第一次审计后，记录会自动保存在这里。
                            </p>
                        </div>

                        <div v-else class="hist-list">
                            <div
                                v-for="item in taskHistory"
                                :key="item.task_id"
                                class="hist-row"
                                :class="{ on: item.task_id === taskId }"
                            >
                                <span
                                    class="h-dot"
                                    :style="{
                                        background: dotColor(item.status),
                                    }"
                                />
                                <div class="h-body">
                                    <div class="h-title">
                                        {{
                                            item.title ||
                                            item.source_label ||
                                            item.url
                                        }}
                                    </div>
                                    <div class="h-meta">
                                        <span
                                            class="hs"
                                            :class="`hs-${item.status}`"
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
                                        <span class="h-time">{{
                                            fmtTime(item.updated_at)
                                        }}</span>
                                    </div>
                                    <div
                                        v-if="item.checklist?.length"
                                        class="h-cl"
                                    >
                                        清单：{{
                                            formatChecklist(item.checklist)
                                        }}
                                    </div>
                                </div>
                                <div class="h-acts">
                                    <button
                                        class="ghost-sm"
                                        @click="loadTask(item)"
                                    >
                                        查看
                                    </button>
                                    <button
                                        class="ghost-sm"
                                        @click="rerunTask(item)"
                                    >
                                        重跑
                                    </button>
                                    <button
                                        class="ghost-sm danger"
                                        @click="removeTask(item)"
                                    >
                                        删除
                                    </button>
                                </div>
                            </div>
                        </div>
                    </template>
                </div>

                <!-- ── right panel ──────────────────────────────────────────────── -->
                <div class="right-panel">
                    <!-- screenshot preview -->
                    <div class="rp-block">
                        <div class="rp-label">截图预览</div>
                        <div class="shot-thumb">
                            <img
                                v-if="screenshotSrc"
                                :src="screenshotSrc"
                                alt="截图"
                                style="
                                    width: 100%;
                                    border-radius: 8px;
                                    display: block;
                                "
                            />
                            <div v-else class="shot-thumb-ph">
                                <SvgImage
                                    style="
                                        width: 28px;
                                        height: 28px;
                                        opacity: 0.3;
                                        margin-bottom: 6px;
                                    "
                                />
                                <p>截图审计完成后显示</p>
                            </div>
                        </div>
                    </div>

                    <!-- donut chart -->
                    <div v-if="displayIssues.length" class="rp-block">
                        <div class="rp-label">问题分布</div>
                        <div class="donut-wrap">
                            <svg
                                width="64"
                                height="64"
                                viewBox="0 0 64 64"
                                style="flex-shrink: 0"
                            >
                                <circle
                                    cx="32"
                                    cy="32"
                                    r="24"
                                    fill="none"
                                    stroke="#f0ede8"
                                    stroke-width="9"
                                />
                                <circle
                                    v-for="(seg, i) in donutSegments"
                                    :key="i"
                                    cx="32"
                                    cy="32"
                                    r="24"
                                    fill="none"
                                    :stroke="seg.color"
                                    stroke-width="9"
                                    :stroke-dasharray="`${seg.dash} ${seg.gap}`"
                                    stroke-linecap="butt"
                                    :transform="`rotate(${seg.offset} 32 32)`"
                                />
                            </svg>
                            <div class="donut-legend">
                                <div
                                    v-for="seg in donutSegments"
                                    :key="seg.label"
                                    class="dl-row"
                                >
                                    <span
                                        class="dl-dot"
                                        :style="{ background: seg.color }"
                                    />
                                    <span class="dl-lbl">{{ seg.label }}</span>
                                    <span class="dl-val">{{ seg.count }}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- compare with last -->
                    <div
                        v-if="tab === 'result' && taskHistory.length > 1"
                        class="rp-block"
                    >
                        <div class="rp-label">与上次对比</div>
                        <div class="compare-row">
                            <span class="cmp-lbl">问题数量</span>
                            <span
                                class="cmp-arrow"
                                :style="{
                                    color: compareGood ? '#2d9e5f' : '#dc2626',
                                }"
                            >
                                {{ compareGood ? "↓" : "↑" }}
                            </span>
                            <span
                                class="cmp-val"
                                :class="compareGood ? 'cmp-good' : 'cmp-bad'"
                            >
                                {{
                                    compareGood
                                        ? `少 ${Math.abs(compareDiff)} 个`
                                        : `多 ${Math.abs(compareDiff)} 个`
                                }}
                            </span>
                            <span v-if="compareGood" class="cmp-badge"
                                >进步</span
                            >
                        </div>
                    </div>

                    <!-- current task -->
                    <div v-if="taskId" class="rp-block">
                        <div class="rp-label">当前任务</div>
                        <div class="task-info">
                            <div class="ti-title">{{ currentSourceLabel }}</div>
                            <div class="ti-id">{{ taskId }}</div>
                            <div class="ti-bar">
                                <div
                                    class="ti-fill"
                                    :style="{
                                        width: progressWidth,
                                        background:
                                            status === 'completed'
                                                ? '#2d9e5f'
                                                : '#1a1a1a',
                                    }"
                                />
                            </div>
                            <div class="ti-foot">
                                <span>{{ message }}</span>
                                <strong
                                    :style="{
                                        color:
                                            status === 'completed'
                                                ? '#2d9e5f'
                                                : '#1a1a1a',
                                    }"
                                    >{{ Math.round(displayProgress) }}%</strong
                                >
                            </div>
                        </div>
                    </div>

                    <!-- recent history shortcuts -->
                    <div
                        v-if="taskHistory.length"
                        class="rp-block"
                        style="
                            flex: 1;
                            overflow: hidden;
                            display: flex;
                            flex-direction: column;
                        "
                    >
                        <div class="rp-label">最近记录</div>
                        <div
                            style="
                                flex: 1;
                                overflow-y: auto;
                                display: flex;
                                flex-direction: column;
                                gap: 4px;
                            "
                        >
                            <button
                                v-for="item in taskHistory.slice(0, 6)"
                                :key="item.task_id"
                                class="rec-btn"
                                :class="{ on: item.task_id === taskId }"
                                @click="loadTask(item)"
                            >
                                <span
                                    class="h-dot"
                                    :style="{
                                        background: dotColor(item.status),
                                    }"
                                />
                                <span class="rec-title">{{
                                    item.title || item.source_label || item.url
                                }}</span>
                                <span class="rec-time">{{
                                    fmtTime(item.updated_at)
                                }}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- fab bar (result only) -->
            <div
                v-if="
                    tab === 'result' && (screenshotSrc || displayIssues.length)
                "
                class="fab-bar"
            >
                <button
                    class="fab fab-draw"
                    :class="{ on: drawingMode }"
                    :disabled="!screenshotSrc"
                    @click="toggleDrawingMode"
                >
                    <SvgPencil />{{ drawingMode ? "结束画框" : "新增批注画框" }}
                </button>
                <button
                    class="fab fab-export"
                    :disabled="exportingPdf"
                    @click="exportPdf"
                >
                    <SvgDownload />{{ exportingPdf ? "导出中…" : "导出 PDF" }}
                </button>
            </div>
        </div>

        <!-- toast -->
        <transition name="toast-fade">
            <div v-if="toastMsg" class="toast">{{ toastMsg }}</div>
        </transition>
    </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

// ── SVG icons ─────────────────────────────────────────────────────────────────
const SvgPlus = {
    template: `<svg width="17" height="17" viewBox="0 0 20 20" fill="none"><rect x="3" y="3" width="14" height="14" rx="3" stroke="currentColor" stroke-width="1.4"/><path d="M10 7v6M7 10h6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
};
const SvgDoc = {
    template: `<svg width="17" height="17" viewBox="0 0 20 20" fill="none"><rect x="3" y="3" width="14" height="14" rx="3" stroke="currentColor" stroke-width="1.4"/><path d="M7 10h6M7 7h4M7 13h3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
};
const SvgClock = {
    template: `<svg width="17" height="17" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.4"/><path d="M10 7v3l2 2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
};
const SvgSettings = {
    template: `<svg width="17" height="17" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="3" stroke="currentColor" stroke-width="1.4"/><path d="M10 3v1.5M10 15.5V17M3 10h1.5M15.5 10H17M5.4 5.4l1.1 1.1M13.5 13.5l1.1 1.1M14.6 5.4l-1.1 1.1M6.5 13.5l-1.1 1.1" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
};
const SvgChevron = {
    template: `<svg viewBox="0 0 12 12" fill="none"><path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
};
const SvgArrow = {
    template: `<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M8 3l5 5-5 5M3 8h10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
};
const SvgUpload = {
    template: `<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M8 3v8M5 6l3-3 3 3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 12h10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
};
const SvgImage = {
    template: `<svg viewBox="0 0 28 28" fill="none"><rect x="2" y="2" width="24" height="24" rx="5" stroke="currentColor" stroke-width="1.3"/><circle cx="10" cy="10" r="3" stroke="currentColor" stroke-width="1.3"/><path d="M3 20l6-6 4 4 4-5 8 7" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
};
const SvgPencil = {
    template: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.3"/><path d="M5 11l2-2 5-5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>`,
};
const SvgDownload = {
    template: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M4 12h8M8 3v7M5 7l3 3 3-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
};
const SvgStar = {
    template: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.5 3.5L13 6l-2.5 2.5.5 3.5L8 10.5 5 12l.5-3.5L3 6l3.5-.5z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>`,
};

// ── config ────────────────────────────────────────────────────────────────────
const API_BASE =
    process.env.NODE_ENV === "development"
        ? "http://localhost:8000/api"
        : "/api";
const USER_TOKEN_COOKIE = "audit_user_token";
const MIN_GAP = 14;

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

function apiFetch(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("X-User-Token", userToken);
    return fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
        credentials: "include",
    });
}

// ── state ─────────────────────────────────────────────────────────────────────
const tab = ref("submit");
const showMotivation = ref(true);
const inputMode = ref("url");
const auditSpeed = ref("slow");
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
const todayCount = ref(3);
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

// ── achievements ──────────────────────────────────────────────────────────────
const achievements = ref([
    {
        id: 1,
        icon: "⚡",
        name: "审校先锋",
        color: "amber",
        unlocked: true,
        goal: "首次审计",
    },
    {
        id: 2,
        icon: "🔥",
        name: "连续 7 天",
        color: "green",
        unlocked: true,
        goal: "7 天连续",
    },
    {
        id: 3,
        icon: "🏆",
        name: "审校达人",
        color: "blue",
        unlocked: false,
        goal: "再审 2 篇",
    },
    {
        id: 4,
        icon: "💎",
        name: "精英审校",
        color: "gray",
        unlocked: false,
        goal: "共 50 篇",
    },
]);

// ── motivation content ────────────────────────────────────────────────────────
const motIcon = computed(() => {
    if (tab.value === "history") return "📈";
    if (tab.value === "result" && displayIssues.value.length) return "🎯";
    return "🌟";
});
const motTitle = computed(() => {
    if (tab.value === "history") return "本周已审 12 篇，进步明显！";
    if (tab.value === "result" && displayIssues.value.length)
        return `发现 ${displayIssues.value.length} 个问题，做得很好！`;
    return "连续审校 7 天，太厉害了！";
});
const motSub = computed(() => {
    if (tab.value === "history")
        return "平均每篇发现 2.4 个问题，比上周减少 30%。";
    if (tab.value === "result" && displayIssues.value.length)
        return `你已驳回 ${decisionStats.value.rejected} 条 AI 建议，保持判断力。`;
    return "今日已完成 3 篇审计。再审 2 篇即可解锁「审校达人」成就。";
});

// ── computed ──────────────────────────────────────────────────────────────────
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
const currentSourceLabel = computed(() => historyTitle(currentSourceMeta.value));
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
    displayIssues.value.filter((i) => i.evidence?.bbox && !isRejected(i.id)),
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
const allResolved = computed(
    () =>
        displayIssues.value.length > 0 &&
        displayIssues.value.every((i) => isRejected(i.id)),
);

// donut chart segments
const SEV_COLORS = {
    critical: "#f0817a",
    warn: "#f5c97a",
    error: "#f0817a",
    info: "#80b8f0",
};
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

// compare
const compareDiff = computed(() => {
    const completed = taskHistory.value.filter(
        (t) => t.status === "completed" && t.issueCount != null,
    );
    if (completed.length < 2) return 0;
    return (completed[0].issueCount || 0) - (completed[1].issueCount || 0);
});
const compareGood = computed(() => compareDiff.value <= 0);

// ── history helpers ───────────────────────────────────────────────────────────
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
  return String(value || '').trim()
}
function isRealTitle(value) {
  const text = normalizeText(value)
  return !!text && !/^https?:\/\//i.test(text) && !/^upload:\/\//i.test(text)
}
function resolveBundleTitle(result) {
  const title = normalizeText(result?.title)
  return isRealTitle(title) ? title : ''
}
function historyTitle(item) {
  if (!item) return '未命名任务'
  const derived = item.url ? deriveTitle(item.url) : ''
  const articleTitle = isRealTitle(item.article_title) ? normalizeText(item.article_title) : ''
  if (articleTitle) return articleTitle
  const storedTitle = isRealTitle(item.title) ? normalizeText(item.title) : ''
  if (storedTitle && storedTitle !== derived) return storedTitle
  if (item.source_type === 'file') {
    if (item.file_name) return `[文件] ${item.file_name}`
    if (isRealTitle(item.source_label)) return normalizeText(item.source_label)
  }
  if (isRealTitle(item.source_label) && !/^https?:\/\//i.test(item.source_label)) return normalizeText(item.source_label)
  return derived || '未命名任务'
}
function buildHistoryItem(task_id, sourceMeta, data, checklist, issueCount) {
  const article_title = resolveBundleTitle(data?.result) || normalizeText(sourceMeta?.article_title)
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
  }
  if (issueCount != null) item.issueCount = issueCount
  item.title = historyTitle(item)
  return item
}
function loadHistory() {
  try {
    const parsed = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
    taskHistory.value = Array.isArray(parsed)
      ? parsed.map(item => ({ ...(item || {}), title: historyTitle(item || {}) }))
      : []
  } catch { taskHistory.value = [] }
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
    saveHistory(taskHistory.value.filter((t) => t.task_id !== item.task_id));
}
function clearHistory() {
    saveHistory([]);
}
function dotColor(s) {
    return (
        { running: "#d97706", completed: "#2d9e5f", failed: "#dc2626" }[s] ||
        "#b0aca6"
    );
}
function statusText(s) {
    return (
        { running: "运行中", completed: "已完成", failed: "失败" }[s] ||
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
function parseChecklist(v) {
    return (v || "")
        .split(/\r?\n/)
        .map((s) => s.trim())
        .filter(Boolean);
}
function formatChecklist(l) {
    if (!l?.length) return "";
    const p = l.slice(0, 3).join("、");
    return l.length > 3 ? `${p}…` : p;
}

// ── toast ─────────────────────────────────────────────────────────────────────
function showToast(msg) {
    toastMsg.value = msg;
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
        toastMsg.value = "";
    }, 2600);
}

// ── normalise issues ──────────────────────────────────────────────────────────
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

// ── progress easing ───────────────────────────────────────────────────────────
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
        const payload = {
            name: (newChecklistName.value || "未命名清单").trim(),
            items,
        };
        const resp = await apiFetch("/kb/checklists", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!resp.ok) {
            const txt = await resp.text();
            throw new Error(txt || `保存清单失败：${resp.status}`);
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
        if (!resp.ok) {
            const txt = await resp.text();
            throw new Error(txt || `保存附加资料失败：${resp.status}`);
        }
        const data = await resp.json();
        const created = Array.isArray(data.items) ? data.items : [];
        if (created.length) {
            referenceKbs.value = [...created, ...referenceKbs.value];
            const ids = created.map((i) => i.kb_id);
            selectedReferenceKbIds.value = [
                ...new Set([...ids, ...selectedReferenceKbIds.value]),
            ];
        }
        referenceFiles.value = [];
        if (referenceFileInputRef.value) referenceFileInputRef.value.value = "";
        showToast("附加资料已保存到知识库");
    } catch (e) {
        error.value = e?.message || "保存附加资料失败";
        throw e;
    }
}

async function renameChecklistKb(item) {
    try {
        const oldName = String(item?.name || "").trim();
        const name = window.prompt("请输入新的清单名称", oldName);
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
        const ok = window.confirm(`确认删除清单知识库“${item?.name || ""}”？`);
        if (!ok) return;
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
        const oldName = String(item?.name || "").trim();
        const name = window.prompt("请输入新的资料库名称", oldName);
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
        const ok = window.confirm(`确认删除资料库“${item?.name || ""}”？`);
        if (!ok) return;
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

// ── audit ─────────────────────────────────────────────────────────────────────
const funMessages = [
    "正在用 AI 眼睛扫描页面…",
    "召唤多模态模型中…",
    "逐字逐句排查问题…",
    "核对图文一致性…",
    "汇总发现的所有线索…",
    "生成审计报告…",
];

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
        if (referenceFiles.value.length) {
            await saveReferencesToKb();
        }
        const cl = parseChecklist(checklistInput.value);
        const selectedChecklistIds = [...selectedChecklistKbIds.value];
        const selectedReferenceIds = [...selectedReferenceKbIds.value];
        let resp;
        if (inputMode.value === "url") {
            const fd = new FormData();
            fd.append("url", urlInput.value.trim());
            fd.append("checklist", JSON.stringify(cl));
            fd.append("fast_mode", String(auditSpeed.value === "fast"));
            fd.append(
                "selected_checklist_ids",
                JSON.stringify(selectedChecklistIds),
            );
            fd.append(
                "selected_reference_ids",
                JSON.stringify(selectedReferenceIds),
            );
            resp = await apiFetch("/audit/url", { method: "POST", body: fd });
        } else {
            const fd = new FormData();
            fd.append("file", selectedFile.value);
            fd.append("checklist", JSON.stringify(cl));
            fd.append("fast_mode", String(auditSpeed.value === "fast"));
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
            buildHistoryItem(data.task_id, currentSourceMeta.value, data, cl),
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
        if (articleTitle && articleTitle !== currentSourceMeta.value.article_title) {
            currentSourceMeta.value = {
                ...currentSourceMeta.value,
                article_title: articleTitle,
            };
        }
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
                showToast(`审计完成！发现 ${data.issues?.length || 0} 个问题`);
                tab.value = "result";
            }
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

// ── issue actions ─────────────────────────────────────────────────────────────
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
    showToast("手工批注已添加，可在卡片中填写内容");
}

// ── screenshot ────────────────────────────────────────────────────────────────
function onShotLoad(e) {
    const img = e.target;
    shotNatural.value = { w: img.naturalWidth || 1, h: img.naturalHeight || 1 };
    shotDisplay.value = { w: img.clientWidth || 1, h: img.clientHeight || 1 };
}
function boxStyle(issue) {
    const bbox = issue?.evidence?.bbox;
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
function setIssueRef(id, el) {
    if (!el) return;
    const h = el.getBoundingClientRect().height;
    if (Math.abs((issueHeights.value[id] || 0) - h) < 0.5) return;
    issueHeights.value = { ...issueHeights.value, [id]: h };
}

// ── export PDF ────────────────────────────────────────────────────────────────
async function exportPdf() {
    if (exportingPdf.value) return;
    exportingPdf.value = true;
    exportMode.value = true;
    error.value = "";
    await nextTick();
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
        showToast("PDF 已导出，太棒了！");
    } catch (e) {
        error.value = e?.message || "导出 PDF 失败";
    } finally {
        exportMode.value = false;
        exportingPdf.value = false;
    }
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

watch(displayIssues, () => {
    issueHeights.value = {};
    nextTick(() => {});
});
loadHistory();
loadKnowledgeBases().catch((e) => {
    error.value = e?.message || "加载知识库失败";
});
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
    background: #f0ede8;
    color: #1a1a1a;
    font-family: "Inter", "Segoe UI", system-ui, sans-serif;
    font-size: 13px;
    line-height: 1.5;
    position: relative;
}

/* ── icon sidebar ──────────────────────────────────────────────── */
.icon-sb {
    width: 60px;
    flex-shrink: 0;
    background: #fff;
    border-right: 1px solid #edeae5;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 14px 0;
    gap: 4px;
}
.logo-sq {
    width: 34px;
    height: 34px;
    border-radius: 10px;
    background: #1a1a1a;
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-bottom: 12px;
}
.i-btn {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    border: none;
    background: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #c0bdb8;
    transition: all 0.15s;
    position: relative;
    flex-shrink: 0;
}
.i-btn:hover {
    background: #f5f2ed;
    color: #1a1a1a;
}
.i-btn.on {
    background: #1a1a1a;
    color: #fff;
}
.i-tip {
    position: absolute;
    left: 46px;
    top: 50%;
    transform: translateY(-50%);
    background: #1a1a1a;
    color: #fff;
    font-size: 10px;
    font-weight: 500;
    padding: 3px 8px;
    border-radius: 6px;
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s;
    z-index: 200;
}
.i-btn:hover .i-tip {
    opacity: 1;
}
.i-notch {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #f0817a;
    border: 2px solid #fff;
}
.i-sep {
    width: 22px;
    height: 1px;
    background: #edeae5;
    margin: 6px 0;
    flex-shrink: 0;
}
.i-avatar {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: #fde8c8;
    font-size: 11px;
    font-weight: 700;
    color: #8b4d0a;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: auto;
    flex-shrink: 0;
    border: 1.5px solid #f5c97a;
}
.today-count {
    font-size: 9px;
    font-weight: 700;
    color: #8b4d0a;
    background: #fde8c8;
    border-radius: 4px;
    padding: 2px 4px;
    margin-top: 3px;
    line-height: 1.3;
    text-align: center;
}

/* ── main ──────────────────────────────────────────────────────── */
.main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
}

.topbar {
    height: 48px;
    background: #fff;
    border-bottom: 1px solid #edeae5;
    padding: 0 20px;
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
}
.breadcrumb {
    font-size: 12px;
    color: #b0aca6;
    display: flex;
    align-items: center;
    gap: 5px;
}
.breadcrumb span {
    color: #1a1a1a;
    font-weight: 600;
}
.topbar-right {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 8px;
}
.mot-toggle {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    border: 1.5px solid #edeae5;
    background: #fafaf8;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #b0aca6;
    transition: all 0.15s;
}
.mot-toggle:hover,
.mot-toggle.active {
    background: #fde8c8;
    border-color: #f5c97a;
    color: #8b4d0a;
}
.s-pill {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 600;
}
.pill-ok {
    background: #d4f4e2;
    color: #1a6e3c;
}
.pill-run {
    background: #fde8c8;
    color: #8b4d0a;
}
.pill-err {
    background: #fcd9d9;
    color: #8b1a1a;
}
.pill-idle {
    background: #f0ede8;
    color: #7a7872;
}

/* ── motivation banner ─────────────────────────────────────────── */
.mot-banner {
    background: #fff;
    border-bottom: 1px solid #edeae5;
    padding: 12px 20px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    flex-shrink: 0;
}
.mot-icon {
    font-size: 24px;
    flex-shrink: 0;
    line-height: 1;
    margin-top: 1px;
}
.mot-body {
    flex: 1;
    min-width: 0;
}
.mot-title {
    font-size: 13px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 2px;
}
.mot-sub {
    font-size: 12px;
    color: #7a7872;
    line-height: 1.5;
}
.ach-row {
    display: flex;
    gap: 7px;
    margin-left: auto;
    flex-shrink: 0;
}
.ach-badge {
    width: 68px;
    border-radius: 10px;
    padding: 8px 6px;
    text-align: center;
    border: 1.5px solid transparent;
    transition: transform 0.15s;
    cursor: default;
}
.ach-badge:hover {
    transform: translateY(-2px);
}
.ab-amber {
    background: #fde8c8;
    border-color: #f5c97a;
}
.ab-green {
    background: #d4f4e2;
    border-color: #a7f3d0;
}
.ab-blue {
    background: #dbeafe;
    border-color: #93c5fd;
}
.ab-gray {
    background: #f0ede8;
    border-color: #e4dfd8;
}
.ab-locked {
    background: #fafaf8;
    border-color: #edeae5;
}
.ach-icon {
    font-size: 18px;
    display: block;
    margin-bottom: 3px;
    line-height: 1;
}
.ach-name {
    font-size: 10px;
    font-weight: 600;
    color: #52524f;
    line-height: 1.3;
}
.ab-locked .ach-name {
    color: #c0bdb8;
}
.ach-prog {
    font-size: 9px;
    color: #b0aca6;
    margin-top: 2px;
}
.slide-down-enter-active {
    transition: all 0.25s ease;
}
.slide-down-leave-active {
    transition: all 0.2s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
    opacity: 0;
    transform: translateY(-8px);
    max-height: 0;
}
.slide-down-enter-to,
.slide-down-leave-from {
    opacity: 1;
    transform: translateY(0);
    max-height: 200px;
}

/* ── content ───────────────────────────────────────────────────── */
.content {
    flex: 1;
    display: flex;
    overflow: hidden;
}
.left-panel {
    flex: 1;
    min-width: 0;
    padding: 20px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.right-panel {
    width: 258px;
    flex-shrink: 0;
    background: #fff;
    border-left: 1px solid #edeae5;
    padding: 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
}

/* ── typography ─────────────────────────────────────────────────── */
.pg-eye {
    font-size: 10px;
    font-weight: 700;
    color: #b0aca6;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 5px;
}
.pg-title {
    font-size: 20px;
    font-weight: 800;
    color: #1a1a1a;
    letter-spacing: -0.03em;
    line-height: 1.2;
    margin-bottom: 4px;
}
.pg-sub {
    font-size: 12px;
    color: #7a7872;
    line-height: 1.6;
    margin-bottom: 16px;
}
.sec-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
}

/* ── submit ─────────────────────────────────────────────────────── */
.submit-card {
    background: #fff;
    border-radius: 14px;
    border: 1.5px solid #edeae5;
    padding: 20px 22px;
}
.mode-row {
    display: flex;
    gap: 7px;
    margin-bottom: 14px;
}
.mode-pill {
    padding: 6px 15px;
    border-radius: 20px;
    border: 1.5px solid #edeae5;
    background: #fafaf8;
    font-size: 12px;
    font-weight: 500;
    color: #7a7872;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
}
.mode-pill.on {
    background: #1a1a1a;
    border-color: #1a1a1a;
    color: #fff;
}
.f-label {
    display: block;
    font-size: 11px;
    font-weight: 600;
    color: #7a7872;
    margin-bottom: 6px;
    letter-spacing: 0.01em;
}
.f-hint {
    font-weight: 400;
    color: #c0bdb8;
}
.inp-row {
    display: flex;
    gap: 8px;
    margin-bottom: 4px;
}
.text-inp {
    flex: 1;
    padding: 9px 12px;
    border-radius: 12px;
    border: 1.5px solid #edeae5;
    background: #fafaf8;
    color: #1a1a1a;
    font-size: 12px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s;
}
.text-inp:focus {
    border-color: #1a1a1a;
    background: #fff;
}
.text-inp:disabled {
    opacity: 0.6;
}
.primary-btn {
    padding: 9px 18px;
    border-radius: 12px;
    border: none;
    background: #1a1a1a;
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    white-space: nowrap;
    display: flex;
    align-items: center;
    gap: 5px;
    transition: background 0.15s;
}
.primary-btn:hover:not(:disabled) {
    background: #333;
}
.primary-btn:disabled {
    background: #e5e2dd;
    color: #b0aca6;
    cursor: not-allowed;
}
.file-row {
    display: flex;
    align-items: center;
    gap: 9px;
}
.file-lbl {
    padding: 7px 13px;
    border-radius: 20px;
    border: 1.5px solid #edeae5;
    background: #fafaf8;
    font-size: 11px;
    font-weight: 500;
    color: #7a7872;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: background 0.15s;
}
.file-lbl:hover {
    background: #f5f2ed;
}
.file-nm {
    font-size: 11px;
    color: #b0aca6;
}
.kb-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}
.kb-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #52524f;
    padding: 5px 9px;
    border: 1px solid #e4dfd8;
    border-radius: 999px;
    background: #fff;
}
.kb-main {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}
.kb-ops {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}
.kb-op {
    border: 1px solid #e4dfd8;
    background: #fff;
    color: #7a7872;
    border-radius: 999px;
    padding: 1px 7px;
    font-size: 10px;
    cursor: pointer;
}
.kb-op:hover:not(:disabled) {
    background: #f5f2ed;
}
.kb-op:disabled {
    opacity: 0.55;
    cursor: not-allowed;
}
.kb-op.danger {
    border-color: #f0a0a0;
    color: #8b1a1a;
    background: #fff5f5;
}

.field-card {
    background: #fafaf8;
    border-radius: 12px;
    border: 1.5px solid #edeae5;
    padding: 12px 14px;
}
.f-ta {
    width: 100%;
    border: none;
    background: none;
    font-size: 12px;
    color: #1a1a1a;
    font-family: inherit;
    resize: none;
    outline: none;
    line-height: 1.6;
}
.err-banner {
    padding: 9px 12px;
    border-radius: 10px;
    background: #fcd9d9;
    border: 1.5px solid #f0a0a0;
    color: #8b1a1a;
    font-size: 12px;
}
.prog-card {
    background: #fafaf8;
    border-radius: 12px;
    border: 1.5px solid #edeae5;
    padding: 13px 15px;
}
.prog-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 7px;
}
.prog-msg-txt {
    font-size: 12px;
    font-weight: 500;
    color: #1a1a1a;
}
.prog-pct {
    font-size: 12px;
    font-weight: 700;
    color: #1a1a1a;
}
.prog-track {
    height: 5px;
    border-radius: 999px;
    background: #e4dfd8;
    overflow: hidden;
}
.prog-fill {
    height: 100%;
    border-radius: 999px;
    background: #1a1a1a;
    transition: width 0.5s ease;
}
.prog-fill.done {
    background: #2d9e5f;
}
.prog-fill.err {
    background: #dc2626;
}
.prog-note {
    font-size: 10px;
    color: #b0aca6;
    margin-top: 5px;
}

/* ── ghost / small buttons ─────────────────────────────────────── */
.ghost-sm {
    padding: 4px 11px;
    border-radius: 20px;
    border: 1.5px solid #edeae5;
    background: #fff;
    font-size: 11px;
    font-weight: 500;
    color: #7a7872;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.12s;
}
.ghost-sm:hover:not(:disabled) {
    background: #f5f2ed;
}
.ghost-sm:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
.ghost-sm.danger {
    color: #8b1a1a;
    border-color: #f0a0a0;
    background: #fef0f0;
}
.ghost-sm.danger:hover {
    background: #fcd9d9;
}

/* ── result ─────────────────────────────────────────────────────── */
.clean-banner {
    background: #d4f4e2;
    border-radius: 12px;
    border: 1.5px solid #a7f3d0;
    padding: 14px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
}
.clean-banner span {
    font-size: 22px;
    flex-shrink: 0;
}
.cb-title {
    font-size: 13px;
    font-weight: 700;
    color: #1a6e3c;
}
.cb-sub {
    font-size: 12px;
    color: #256040;
    margin-top: 2px;
}
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.3s;
}
.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}

.result-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 7px;
    margin-bottom: 10px;
}
.toolbar-chips {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}
.schip {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 600;
}
.schip-g {
    background: #d4f4e2;
    color: #1a6e3c;
}
.schip-r {
    background: #fcd9d9;
    color: #8b1a1a;
}
.ct-chip {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 20px;
    background: #f0ede8;
    color: #7a7872;
    font-weight: 500;
}

.result-wrap {
    border-radius: 14px;
    border: 1.5px solid #edeae5;
    background: #fff;
    overflow: hidden;
    display: grid;
    grid-template-columns: 1.3fr 1fr;
}
@media (max-width: 860px) {
    .result-wrap {
        grid-template-columns: 1fr;
    }
}

.shot-pane {
    border-right: 1px solid #edeae5;
    background: #f5f2ed;
    min-height: 280px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    user-select: none;
}
.shot-pane.drawing {
    cursor: crosshair;
}
.shot-img {
    display: block;
    width: 100%;
    height: auto;
}
.shot-ph {
    text-align: center;
    color: #c0bdb8;
    padding: 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
}
.shot-ph p {
    font-size: 11px;
    line-height: 1.6;
    margin-top: 6px;
}

.overlay-box {
    position: absolute;
    border: 1.5px solid rgba(127, 119, 221, 0.7);
    background: rgba(127, 119, 221, 0.1);
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
    border-color: #dc2626;
    background: rgba(220, 38, 38, 0.1);
}
.overlay-box.preview {
    border-style: dashed;
    border-color: #10b981;
    background: rgba(16, 185, 129, 0.14);
}

.issues-pane {
    position: relative;
    overflow-x: hidden;
    overflow-y: auto;
    background: #fafaf8;
    padding: 10px 8px;
}
.i-card {
    position: absolute;
    left: 4px;
    right: 4px;
    border-radius: 12px;
    border: 1.5px solid #edeae5;
    background: #fff;
    overflow: hidden;
    cursor: default;
    transition: all 0.2s;
}
.i-card:hover {
    border-color: #d0cdc8;
    transform: translateY(-1px);
}
.i-card.active {
    border-color: #c7c6f0;
}
.i-card.resolved {
    opacity: 0.6;
    border-color: #a7f3d0;
}
.i-card.manual {
    border-color: #b8e8cc;
}

.i-stripe {
    height: 3px;
}
.is-critical,
.is-error {
    background: #f0817a;
}
.is-warn {
    background: #f5c97a;
}
.is-info {
    background: #80b8f0;
}

.i-body {
    padding: 10px 12px;
}
.i-top {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 7px;
}
.sev-tag {
    font-size: 9px;
    padding: 2px 7px;
    border-radius: 20px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.sv-critical,
.sv-error {
    background: #fee2e2;
    color: #8b1a1a;
}
.sv-warn {
    background: #fef3d0;
    color: #8b5c0a;
}
.sv-info {
    background: #dbeafe;
    color: #1e3a8a;
}
.i-type {
    font-size: 12px;
    font-weight: 600;
    color: #1a1a1a;
}
.i-conf {
    font-size: 10px;
    color: #b0aca6;
    margin-left: auto;
}
.dtag {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 20px;
    font-weight: 600;
}
.dt-k {
    background: #d4f4e2;
    color: #1a6e3c;
}
.dt-r {
    background: #fcd9d9;
    color: #8b1a1a;
}
.i-btns {
    display: flex;
    gap: 5px;
    margin-bottom: 7px;
}
.mi-btn {
    padding: 3px 9px;
    border-radius: 20px;
    border: 1.5px solid #edeae5;
    background: #fafaf8;
    font-size: 11px;
    font-weight: 500;
    color: #7a7872;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
}
.mi-btn:hover {
    background: #f0ede8;
}
.mi-btn.rej {
    color: #8b1a1a;
    border-color: #f0a0a0;
    background: #fef0f0;
}
.mi-btn.rej:hover {
    background: #fcd9d9;
}
.mi-btn.danger {
    color: #8b1a1a;
    border-color: #f0a0a0;
}
.i-quote {
    font-size: 11px;
    color: #7a7872;
    border-left: 3px solid #f0ede8;
    padding-left: 8px;
    margin-bottom: 5px;
    font-style: italic;
    line-height: 1.5;
    border-radius: 0;
}
.i-rec {
    font-size: 11px;
    color: #52524f;
    line-height: 1.5;
    margin-bottom: 3px;
}
.ann-lbl {
    display: block;
    font-size: 10px;
    font-weight: 700;
    color: #7a7872;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin: 8px 0 4px;
}
.ann-ta {
    width: 100%;
    min-height: 40px;
    border-radius: 8px;
    border: 1.5px solid #edeae5;
    background: #fafaf8;
    color: #1a1a1a;
    padding: 6px 8px;
    font-size: 11px;
    font-family: inherit;
    resize: none;
    outline: none;
    transition: border-color 0.15s;
}
.ann-ta:focus {
    border-color: #1a1a1a;
    background: #fff;
}
.i-meta {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 5px;
}
.i-meta span {
    font-size: 10px;
    color: #b0aca6;
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
    gap: 9px;
    padding: 11px 13px;
    border-radius: 12px;
    border: 1.5px solid #edeae5;
    background: #fff;
    transition: border-color 0.15s;
}
.hist-row.on {
    border-color: #c7c6f0;
}
.h-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 3px;
}
.h-body {
    flex: 1;
    min-width: 0;
}
.h-title {
    font-size: 12px;
    font-weight: 600;
    color: #1a1a1a;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 4px;
}
.h-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}
.h-meta span {
    font-size: 10px;
    color: #7a7872;
}
.h-time {
    margin-left: auto !important;
    color: #b0aca6 !important;
}
.h-cl {
    font-size: 10px;
    color: #b0aca6;
    margin-top: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.h-acts {
    display: flex;
    flex-direction: column;
    gap: 3px;
    flex-shrink: 0;
}
.hs {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 20px;
    font-weight: 600;
}
.hs-running {
    background: #fde8c8;
    color: #8b4d0a;
}
.hs-completed {
    background: #d4f4e2;
    color: #1a6e3c;
}
.hs-failed {
    background: #fcd9d9;
    color: #8b1a1a;
}

/* ── empty state ────────────────────────────────────────────────── */
.empty-ph {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 48px 20px;
    gap: 8px;
    border: 2px dashed #e4dfd8;
    border-radius: 14px;
    flex: 1;
}
.ep-icon {
    font-size: 32px;
}
.ep-title {
    font-size: 14px;
    font-weight: 700;
    color: #1a1a1a;
}
.ep-sub {
    font-size: 12px;
    color: #7a7872;
    line-height: 1.6;
    max-width: 260px;
}

/* ── right panel ────────────────────────────────────────────────── */
.rp-block {
    display: flex;
    flex-direction: column;
}
.rp-label {
    font-size: 10px;
    font-weight: 700;
    color: #b0aca6;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 9px;
}
.shot-thumb {
    background: #f5f2ed;
    border-radius: 10px;
    border: 1.5px solid #edeae5;
    min-height: 120px;
    overflow: hidden;
}
.shot-thumb-ph {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 20px;
    text-align: center;
    color: #c0bdb8;
    min-height: 120px;
}
.shot-thumb-ph p {
    font-size: 11px;
    line-height: 1.5;
}

.donut-wrap {
    display: flex;
    align-items: center;
    gap: 14px;
}
.donut-legend {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
}
.dl-row {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #52524f;
}
.dl-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
.dl-lbl {
    flex: 1;
}
.dl-val {
    font-weight: 700;
    color: #1a1a1a;
}

.compare-row {
    background: #fafaf8;
    border-radius: 10px;
    border: 1.5px solid #edeae5;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 7px;
}
.cmp-lbl {
    font-size: 11px;
    color: #52524f;
    flex: 1;
}
.cmp-arrow {
    font-size: 15px;
    font-weight: 700;
}
.cmp-val {
    font-size: 12px;
    font-weight: 700;
}
.cmp-good {
    color: #2d9e5f;
}
.cmp-bad {
    color: #dc2626;
}
.cmp-badge {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 20px;
    background: #d4f4e2;
    color: #1a6e3c;
    font-weight: 600;
}

.task-info {
    background: #fafaf8;
    border-radius: 12px;
    border: 1.5px solid #edeae5;
    padding: 12px;
}
.ti-title {
    font-size: 12px;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ti-id {
    font-size: 10px;
    color: #b0aca6;
    margin-bottom: 8px;
}
.ti-bar {
    height: 4px;
    border-radius: 999px;
    background: #e4dfd8;
    overflow: hidden;
    margin-bottom: 5px;
}
.ti-fill {
    height: 100%;
    border-radius: 999px;
    transition:
        width 0.5s,
        background 0.3s;
}
.ti-foot {
    display: flex;
    justify-content: space-between;
}
.ti-foot span {
    font-size: 10px;
    color: #b0aca6;
}
.ti-foot strong {
    font-size: 10px;
    font-weight: 700;
}

.rec-btn {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 6px 8px;
    border-radius: 8px;
    border: none;
    background: none;
    cursor: pointer;
    font-family: inherit;
    text-align: left;
    transition: background 0.12s;
    width: 100%;
}
.rec-btn:hover {
    background: #f5f2ed;
}
.rec-btn.on {
    background: #f0ede8;
}
.rec-title {
    font-size: 11px;
    font-weight: 500;
    color: #1a1a1a;
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.rec-time {
    font-size: 10px;
    color: #b0aca6;
    flex-shrink: 0;
}

/* ── fab bar ────────────────────────────────────────────────────── */
.fab-bar {
    padding: 11px 20px;
    background: #fff;
    border-top: 1px solid #edeae5;
    display: flex;
    gap: 8px;
    flex-shrink: 0;
}
.fab {
    padding: 9px 18px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s;
    border: 1.5px solid transparent;
}
.fab-draw {
    background: #f0ede8;
    color: #1a1a1a;
    border-color: #e4dfd8;
}
.fab-draw:hover:not(:disabled),
.fab-draw.on {
    background: #1a1a1a;
    color: #fff;
    border-color: #1a1a1a;
}
.fab-export {
    background: #fde8c8;
    color: #8b4d0a;
    border-color: #f5c97a;
    margin-left: auto;
}
.fab-export:hover:not(:disabled) {
    background: #f5c97a;
    color: #5a3000;
}
.fab:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* ── toast ──────────────────────────────────────────────────────── */
.toast {
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    background: #1a1a1a;
    color: #fff;
    font-size: 12px;
    font-weight: 500;
    padding: 9px 18px;
    border-radius: 20px;
    z-index: 300;
    white-space: nowrap;
    pointer-events: none;
}
.toast-fade-enter-active {
    transition: all 0.25s ease;
}
.toast-fade-leave-active {
    transition: all 0.2s ease;
}
.toast-fade-enter-from,
.toast-fade-leave-to {
    opacity: 0;
    transform: translateX(-50%) translateY(8px);
}

/* ── responsive ─────────────────────────────────────────────────── */
@media (max-width: 768px) {
    .right-panel {
        display: none;
    }
    .mot-banner {
        flex-wrap: wrap;
    }
    .ach-row {
        margin-left: 0;
        margin-top: 8px;
        width: 100%;
    }
    .ach-badge {
        flex: 1;
    }
    .fab-bar {
        padding: 8px 12px;
        border-radius: 14px;
    }
    .fab {
        flex: 1;
        justify-content: center;
        font-size: 11px;
        padding: 8px 10px;
    }
}
@media (max-width: 480px) {
    .left-panel {
        padding: 12px;
    }
    .result-wrap {
        grid-template-columns: 1fr;
    }
}
</style>
