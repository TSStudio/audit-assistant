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
import useHomePageLogic from "./home/useHomePageLogic";

const vm = useHomePageLogic();
const activeTab = computed(() => vm.tab?.value || "submit");
provide("homeVm", vm);
</script>

<style>
@import "../css/home-page.css";
</style>
