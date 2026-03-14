<template>
    <div v-if="!screenshotSrc && !displayIssues.length" class="empty-ph">
        <span class="ep-icon">🔍</span>
        <div class="ep-title">这里还没有结果</div>
        <p class="ep-sub">
            提交一个 URL 或文件，AI 会帮你找出每一个值得关注的问题。
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
        <transition name="fade">
            <div
                v-if="allResolved && displayIssues.length"
                class="clean-banner"
            >
                <span>✨</span>
                <div>
                    <div class="cb-title">所有问题已处理，干得漂亮！</div>
                    <div class="cb-sub">可以放心导出报告了。</div>
                </div>
            </div>
        </transition>

        <div class="result-toolbar">
            <div class="toolbar-chips">
                <span class="schip schip-g">已保留 {{ decisionStats.kept }}</span>
                <span class="schip schip-r">已驳回 {{ decisionStats.rejected }}</span>
                <span class="ct-chip">{{ displayIssues.length }} 个问题</span>
                <!-- ★ COLLAB: 评论总数 -->
                <span
                    v-if="collabActive && totalCommentCount > 0"
                    class="ct-chip"
                    style="background:#f5f3ff;color:#5b21b6"
                >
                    💬 {{ totalCommentCount }} 条评论
                </span>
            </div>
            <!-- ★ 键盘快捷键提示 -->
            <span class="kbd-hint">↑↓ / J K 切换　空格 驳回</span>
            <button
                class="ghost-sm"
                :disabled="!customIssues.length"
                @click="clearCustomIssues"
            >
                清空手工批注
            </button>
        </div>

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
                        style="width: 32px; height: 32px; opacity: 0.3; margin-bottom: 8px"
                    />
                    <p>截图在审计完成后显示</p>
                </div>
                <!-- ★ overlay-box 增加双向 hover 事件 -->
                <div
                    v-for="issue in issuesWithBox"
                    :key="`box-${issue.id}`"
                    class="overlay-box"
                    :class="{
                        active:   hoverIssueId === issue.id,
                        manual:   issue.manual,
                        rejected: isRejected(issue.id),
                    }"
                    :style="boxStyle(issue)"
                    @mouseenter="hoverIssueId = issue.id"
                    @mouseleave="hoverIssueId = null"
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
                :style="{ height: issuesPaneRenderHeight + 'px' }"
            >
                <template v-if="positionedIssues.length">
                    <div
                        v-for="item in positionedIssues"
                        :key="item.issue.id"
                        class="i-card"
                        :data-id="item.issue.id"
                        :class="{
                            active:   hoverIssueId === item.issue.id,
                            resolved: isRejected(item.issue.id),
                            manual:   item.issue.manual,
                        }"
                        :style="{ top: item.top + 'px' }"
                        :ref="(el) => setIssueRef(item.issue.id, el)"
                        @mouseenter="hoverIssueId = item.issue.id"
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
                                    >{{ item.issue.severity || "info" }}</span
                                >
                                <span class="i-type">{{
                                    item.issue.type || "custom"
                                }}</span>
                                <span
                                    v-if="item.issue.confidence"
                                    class="i-conf"
                                    >{{
                                        Number(item.issue.confidence).toFixed(2)
                                    }}</span
                                >
                                <span
                                    class="dtag"
                                    :class="
                                        isRejected(item.issue.id)
                                            ? 'dt-r'
                                            : 'dt-k'
                                    "
                                >
                                    {{
                                        isRejected(item.issue.id)
                                            ? "已驳回"
                                            : "已保留"
                                    }}
                                </span>
                            </div>
                            <div class="i-btns">
                                <button
                                    v-if="!isRejected(item.issue.id)"
                                    class="mi-btn rej"
                                    @click="rejectIssue(item.issue.id)"
                                >
                                    驳回
                                </button>
                                <button
                                    v-else
                                    class="mi-btn"
                                    @click="undoReject(item.issue.id)"
                                >
                                    撤销
                                </button>
                                <button
                                    v-if="item.issue.manual"
                                    class="mi-btn danger"
                                    @click="removeCustomIssue(item.issue.id)"
                                >
                                    删除批注
                                </button>
                            </div>
                            <p
                                v-if="item.issue.evidence?.quote"
                                class="i-quote"
                            >
                                "{{ item.issue.evidence.quote }}"
                            </p>
                            <p v-if="item.issue.recommendation" class="i-rec">
                                建议：{{ item.issue.recommendation }}
                            </p>
                            <template v-if="item.issue.manual">
                                <span class="ann-lbl">批注内容</span>
                                <textarea
                                    class="ann-ta"
                                    :value="noteForIssue(item.issue.id)"
                                    placeholder="输入你的审校意见…"
                                    @input="
                                        updateNote(
                                            item.issue.id,
                                            $event.target.value,
                                        )
                                    "
                                />
                            </template>
                            <div class="i-meta">
                                <span v-if="item.issue.evidence?.text_block_id"
                                    >段落：{{
                                        item.issue.evidence.text_block_id
                                    }}</span
                                >
                                <span v-if="item.issue.evidence?.image_id"
                                    >图片：{{
                                        item.issue.evidence.image_id
                                    }}</span
                                >
                                <span v-if="item.issue.manual">手工批注</span>
                            </div>

                            <!-- ★ COLLAB: 每张卡片底部挂载评论线程 -->
                            <HomeIssueThread :issue-id="item.issue.id" />
                        </div>
                    </div>
                </template>
                <div
                    v-else
                    class="empty-ph"
                    style="border: none; padding: 32px 16px"
                >
                    <span class="ep-icon" style="font-size: 24px">✅</span>
                    <p class="ep-sub">暂无问题</p>
                </div>
            </div>
        </div>
    </template>
</template>

<script setup>
import { inject } from "vue";
import { SvgImage, SvgPlus } from "./icons";
import HomeIssueThread from "./HomeIssueThread.vue"; // ★ COLLAB

const vm = inject("homeVm");
if (!vm) throw new Error("homeVm is not provided");
const collabVm = inject("collabVm"); // ★ COLLAB
if (!collabVm) throw new Error("collabVm is not provided");

const {
    allResolved,
    beginDraw,
    boxStyle,
    cancelDraw,
    clearCustomIssues,
    customIssues,
    decisionStats,
    displayIssues,
    drawingMode,
    drawingPreview,
    endDraw,
    hoverIssueId,
    isRejected,
    issuesPaneRenderHeight,
    issuesWithBox,
    moveDraw,
    noteForIssue,
    onShotLoad,
    positionedIssues,
    rejectIssue,
    removeCustomIssue,
    screenshotSrc,
    setIssueRef,
    shotImg,
    shotWrapper,
    tab,
    undoReject,
    updateNote,
} = vm;

const { collabActive, totalCommentCount } = collabVm; // ★ COLLAB
</script>