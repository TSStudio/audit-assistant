<template>
    <div class="shell">
        <HomeSidebar />

        <div class="main">
            <HomeTopBar />
            <HomeMotivationBanner />

            <div class="content">
                <div class="left-panel">
                    <HomeSubmitTab v-if="activeTab === 'submit'" />
                    <HomeResultTab v-else-if="activeTab === 'result'" />
                    <HomeHistoryTab v-else-if="activeTab === 'history'" />
                </div>

                <HomeRightPanel />
            </div>

            <HomeFabBar />
        </div>

        <HomeToast />
        <!-- ★ COLLAB: 分享协作模态框 -->
        <HomeShareModal />
    </div>
</template>

<script setup>
import { computed, provide } from "vue";
import HomeFabBar from "./home/HomeFabBar.vue";
import HomeHistoryTab from "./home/HomeHistoryTab.vue";
import HomeMotivationBanner from "./home/HomeMotivationBanner.vue";
import HomeResultTab from "./home/HomeResultTab.vue";
import HomeRightPanel from "./home/HomeRightPanel.vue";
import HomeSidebar from "./home/HomeSidebar.vue";
import HomeSubmitTab from "./home/HomeSubmitTab.vue";
import HomeToast from "./home/HomeToast.vue";
import HomeTopBar from "./home/HomeTopBar.vue";
import HomeShareModal from "./home/HomeShareModal.vue";   // ★ COLLAB
import useHomePageLogic from "./home/useHomePageLogic";
import useCollabLogic from "./home/useCollabLogic";       // ★ COLLAB

const vm = useHomePageLogic();
const activeTab = computed(() => vm.tab?.value || "submit");

// ★ COLLAB: 初始化协作逻辑，传入 homeVm 的共享状态
const collabVm = useCollabLogic({
    showToast:    vm.showToast,
    displayIssues: vm.displayIssues,
    decisionStats: vm.decisionStats,
});

// ★ COLLAB: 每次 resetState 时同步重置协作状态（切换/重跑任务时清空评论）
vm.onReset(() => collabVm.resetCollab());

provide("homeVm", vm);
provide("collabVm", collabVm);  // ★ COLLAB
</script>

<style>
@import "../css/home-page.css";
</style>