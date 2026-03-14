<template>
    <div
        v-if="tab === 'result' && (screenshotSrc || displayIssues.length)"
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
</template>

<script setup>
import { inject } from "vue";
import { SvgDownload, SvgPencil } from "./icons";

const vm = inject("homeVm");
if (!vm) throw new Error("homeVm is not provided");

const {
    displayIssues,
    drawingMode,
    exportPdf,
    exportingPdf,
    screenshotSrc,
    tab,
    toggleDrawingMode,
} = vm;
</script>
