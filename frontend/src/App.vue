<template>
    <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
            <component :is="Component" />
        </transition>
    </router-view>
</template>
<script setup>
import { onMounted } from "vue";
onMounted(() => {
    if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        if (!darkModeEnabled.value) {
            toggleDarkMode();
        }
    }
    router.push("/");
});
</script>
