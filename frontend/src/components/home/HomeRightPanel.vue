<template>
    <div class="right-panel">
        <!-- 截图预览 -->
        <div class="rp-block">
            <div class="rp-label">截图预览</div>
            <div class="shot-thumb">
                <img
                    v-if="screenshotSrc"
                    :src="screenshotSrc"
                    alt="截图"
                    style="width: 100%; border-radius: 8px; display: block"
                />
                <div v-else class="shot-thumb-ph">
                    <SvgImage
                        style="width: 28px; height: 28px; opacity: 0.3; margin-bottom: 6px"
                    />
                    <p>截图审计完成后显示</p>
                </div>
            </div>
        </div>

        <!-- 问题分布甜甜圈 -->
        <div v-if="displayIssues.length" class="rp-block">
            <div class="rp-label">问题分布</div>
            <div class="donut-wrap">
                <svg width="64" height="64" viewBox="0 0 64 64" style="flex-shrink: 0">
                    <circle cx="32" cy="32" r="24" fill="none" stroke="#f0ede8" stroke-width="9" />
                    <circle
                        v-for="(seg, i) in donutSegments"
                        :key="i"
                        cx="32" cy="32" r="24" fill="none"
                        :stroke="seg.color" stroke-width="9"
                        :stroke-dasharray="`${seg.dash} ${seg.gap}`"
                        stroke-linecap="butt"
                        :transform="`rotate(${seg.offset} 32 32)`"
                    />
                </svg>
                <div class="donut-legend">
                    <div v-for="seg in donutSegments" :key="seg.label" class="dl-row">
                        <span class="dl-dot" :style="{ background: seg.color }" />
                        <span class="dl-lbl">{{ seg.label }}</span>
                        <span class="dl-val">{{ seg.count }}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 与上次对比 -->
        <div v-if="tab === 'result' && taskHistory.length > 1" class="rp-block">
            <div class="rp-label">与上次对比</div>
            <div class="compare-row">
                <span class="cmp-lbl">问题数量</span>
                <span class="cmp-arrow" :style="{ color: compareGood ? '#2d9e5f' : '#dc2626' }">
                    {{ compareGood ? "↓" : "↑" }}
                </span>
                <span class="cmp-val" :class="compareGood ? 'cmp-good' : 'cmp-bad'">
                    {{ compareGood ? `少 ${Math.abs(compareDiff)} 个` : `多 ${Math.abs(compareDiff)} 个` }}
                </span>
                <span v-if="compareGood" class="cmp-badge">进步</span>
            </div>
        </div>

        <!-- 当前任务进度 -->
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
                            background: status === 'completed' ? '#2d9e5f' : '#1a1a1a',
                        }"
                    />
                </div>
                <div class="ti-foot">
                    <span>{{ message }}</span>
                    <strong :style="{ color: status === 'completed' ? '#2d9e5f' : '#1a1a1a' }">
                        {{ Math.round(displayProgress) }}%
                    </strong>
                </div>
            </div>
        </div>

        <!-- ★ COLLAB: 协作成员列表 -->
        <div v-if="collabActive && tab === 'result'" class="rp-block">
            <div class="rp-label">协作成员</div>
            <div style="display:flex;flex-direction:column;gap:5px">
                <!-- 我自己（所有者） -->
                <div class="collab-member-row">
                    <div class="presence-avatar pav-amber" style="position:relative;width:26px;height:26px;font-size:10px">
                        编<span class="presence-dot" />
                    </div>
                    <div class="collab-member-info">
                        <div class="collab-member-name">我</div>
                        <div class="collab-member-status online">在线</div>
                    </div>
                    <span class="role-badge rb-owner">所有者</span>
                </div>
                <!-- 其他成员 -->
                <div
                    v-for="m in shareMembers"
                    :key="m.id"
                    class="collab-member-row"
                    :style="m.online ? '' : 'opacity:.6'"
                >
                    <div
                        class="presence-avatar"
                        :class="`pav-${m.color}`"
                        style="position:relative;width:26px;height:26px;font-size:10px"
                    >
                        {{ m.initials }}
                        <span v-if="m.online" class="presence-dot" />
                    </div>
                    <div class="collab-member-info">
                        <div class="collab-member-name">{{ m.name }}</div>
                        <div class="collab-member-status" :class="m.online ? 'online' : ''">
                            {{ m.online ? '在线' : '离线' }}
                        </div>
                    </div>
                    <span class="role-badge" :class="m.role === 'edit' ? 'rb-edit' : 'rb-view'">
                        {{ m.role === 'edit' ? '可编辑' : '只读' }}
                    </span>
                </div>
            </div>
        </div>

        <!-- ★ COLLAB: 最新动态 -->
        <div v-if="collabActive && tab === 'result' && activityFeed.length" class="rp-block">
            <div class="rp-label">最新动态</div>
            <div>
                <div v-for="act in activityFeed.slice(0, 5)" :key="act.id" class="activity-item">
                    <div
                        class="presence-avatar"
                        :class="`pav-${act.color}`"
                        style="width:22px;height:22px;font-size:9px;flex-shrink:0"
                    >
                        {{ act.initials }}
                    </div>
                    <div class="activity-body">
                        <span class="activity-name">{{ act.name }}</span>
                        <div class="activity-desc">{{ act.desc }}</div>
                    </div>
                    <span class="activity-time">{{ act.time }}</span>
                </div>
            </div>
        </div>

        <!-- ★ COLLAB: 协作进度 -->
        <div v-if="collabActive && tab === 'result' && displayIssues.length" class="rp-block">
            <div class="rp-label">协作进度</div>
            <div class="task-info">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:7px">
                    <span style="font-size:11px;color:#52524f">问题处理率</span>
                    <span style="font-size:14px;font-weight:800;color:#1a1a1a">{{ collabProgress }}%</span>
                </div>
                <div class="ti-bar" style="margin-bottom:10px">
                    <div
                        class="ti-fill"
                        :style="{
                            width: collabProgress + '%',
                            background: collabProgress === 100 ? '#2d9e5f' : '#1a1a1a',
                        }"
                    />
                </div>
                <div style="display:flex;justify-content:space-between;font-size:10px;color:#7a7872">
                    <span>评论 <b style="color:#1a1a1a">{{ totalCommentCount }}</b></span>
                    <span>待处理 <b style="color:#1a1a1a">{{ decisionStats.kept }}</b></span>
                </div>
            </div>
        </div>

        <!-- 最近记录 -->
        <div
            v-if="taskHistory.length"
            class="rp-block"
            style="flex: 1; overflow: hidden; display: flex; flex-direction: column"
        >
            <div class="rp-label">最近记录</div>
            <div style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 4px">
                <button
                    v-for="item in taskHistory.slice(0, 6)"
                    :key="item.task_id"
                    class="rec-btn"
                    :class="{ on: item.task_id === taskId }"
                    @click="loadTask(item)"
                >
                    <span class="h-dot" :style="{ background: dotColor(item.status) }" />
                    <span class="rec-title">{{
                        item.title || item.source_label || item.url
                    }}</span>
                    <span class="rec-time">{{ fmtTime(item.updated_at) }}</span>
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { inject } from "vue";
import { SvgImage } from "./icons";

const vm = inject("homeVm");
if (!vm) throw new Error("homeVm is not provided");
const collabVm = inject("collabVm"); // ★ COLLAB
if (!collabVm) throw new Error("collabVm is not provided");

const {
    compareDiff,
    compareGood,
    currentSourceLabel,
    decisionStats,
    displayIssues,
    displayProgress,
    donutSegments,
    dotColor,
    fmtTime,
    loadTask,
    message,
    progressWidth,
    screenshotSrc,
    status,
    tab,
    taskHistory,
    taskId,
} = vm;

const {
    activityFeed,
    collabActive,
    collabProgress,
    shareMembers,
    totalCommentCount,
} = collabVm; // ★ COLLAB
</script>