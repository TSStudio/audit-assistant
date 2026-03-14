<template>
    <div class="right-panel">
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

        <div v-if="tab === 'result' && taskHistory.length > 1" class="rp-block">
            <div class="rp-label">与上次对比</div>
            <div class="compare-row">
                <span class="cmp-lbl">问题数量</span>
                <span
                    class="cmp-arrow"
                    :style="{ color: compareGood ? '#2d9e5f' : '#dc2626' }"
                    >{{ compareGood ? "↓" : "↑" }}</span
                >
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
                <span v-if="compareGood" class="cmp-badge">进步</span>
            </div>
        </div>

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
                                status === 'completed' ? '#2d9e5f' : '#1a1a1a',
                        }"
                    />
                </div>
                <div class="ti-foot">
                    <span>{{ message }}</span>
                    <strong
                        :style="{
                            color:
                                status === 'completed' ? '#2d9e5f' : '#1a1a1a',
                        }"
                        >{{ Math.round(displayProgress) }}%</strong
                    >
                </div>
            </div>
        </div>

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
                        :style="{ background: dotColor(item.status) }"
                    />
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

const {
    compareDiff,
    compareGood,
    currentSourceLabel,
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
</script>
