<template>
    <header class="topbar">
        <div class="breadcrumb">
            Audit Assistant
            <SvgChevron style="opacity: 0.4; width: 10px; height: 10px" />
            <span>{{ tabLabel }}</span>
        </div>
        <div class="topbar-right">
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
</template>

<script setup>
import { inject } from "vue";
import { SvgChevron, SvgStar } from "./icons";

const vm = inject("homeVm");
if (!vm) throw new Error("homeVm is not provided");

const { pillClass, showMotivation, status, statusLabel, tabLabel } = vm;
</script>
