<template>
    <div class="sec-head">
        <h2 class="pg-title" style="font-size: 18px">所有审计任务</h2>
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
        <p class="ep-sub">提交第一次审计后，记录会自动保存在这里。</p>
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
                :style="{ background: dotColor(item.status) }"
            />
            <div class="h-body">
                <div class="h-title">
                    {{ item.title || item.source_label || item.url }}
                </div>
                <div class="h-meta">
                    <span class="hs" :class="`hs-${item.status}`">{{
                        statusText(item.status)
                    }}</span>
                    <span
                        v-if="
                            item.issueCount != null &&
                            item.status === 'completed'
                        "
                        >{{ item.issueCount }} 个问题</span
                    >
                    <span
                        v-if="
                            item.progress != null && item.status === 'running'
                        "
                        >{{ item.progress }}%</span
                    >
                    <span class="h-time">{{ fmtTime(item.updated_at) }}</span>
                </div>
                <div v-if="item.checklist?.length" class="h-cl">
                    清单：{{ formatChecklist(item.checklist) }}
                </div>
            </div>
            <div class="h-acts">
                <button class="ghost-sm" @click="loadTask(item)">查看</button>
                <button class="ghost-sm" @click="rerunTask(item)">重跑</button>
                <button class="ghost-sm danger" @click="removeTask(item)">
                    删除
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { inject } from "vue";

const vm = inject("homeVm");
if (!vm) throw new Error("homeVm is not provided");

const {
    clearHistory,
    dotColor,
    fmtTime,
    formatChecklist,
    loadTask,
    removeTask,
    rerunTask,
    statusText,
    taskHistory,
    taskId,
} = vm;
</script>
