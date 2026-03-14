<template>
    <header class="topbar">
        <div class="breadcrumb">
            Audit Assistant
            <SvgChevron style="opacity: 0.4; width: 10px; height: 10px" />
            <span>{{ tabLabel }}</span>
        </div>
        <div class="topbar-right">
            <!-- ★ COLLAB: 在线成员头像堆叠，协作开启后显示 -->
            <div v-if="collabActive && tab === 'result'" class="presence-stack">
                <div
                    v-for="m in onlineMembers"
                    :key="m.id"
                    class="presence-avatar"
                    :class="`pav-${m.color}`"
                    :title="m.name + (m.online ? '（在线）' : '（离线）')"
                    :style="m.online ? '' : 'opacity:.5'"
                >
                    {{ m.initials }}
                    <span v-if="m.online" class="presence-dot" />
                </div>
                <span class="online-label">{{ onlineCount }} 人在线</span>
            </div>

            <!-- ★ COLLAB: 分享协作按钮，result tab 有内容时显示 -->
            <button
                v-if="tab === 'result'"
                class="share-btn"
                @click="shareModalOpen = true"
            >
                <SvgShare />{{ collabActive ? '协作中' : '分享协作' }}
            </button>

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
import { SvgChevron, SvgShare, SvgStar } from "./icons";

const vm = inject("homeVm");
if (!vm) throw new Error("homeVm is not provided");
const collabVm = inject("collabVm");
if (!collabVm) throw new Error("collabVm is not provided");

const { pillClass, showMotivation, status, statusLabel, tab, tabLabel } = vm;
const { collabActive, onlineCount, onlineMembers, shareModalOpen } = collabVm;
</script>