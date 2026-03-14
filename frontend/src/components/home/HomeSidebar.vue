<template>
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
</template>

<script setup>
import { inject } from "vue";
import { SvgClock, SvgDoc, SvgPlus, SvgSettings } from "./icons";

const vm = inject("homeVm");
if (!vm) throw new Error("homeVm is not provided");

const { tab, taskHistory, todayCount } = vm;
</script>
