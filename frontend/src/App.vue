<template>
    <div class="app-shell">
        <header class="topbar">
            <h1>Audit Assistant</h1>
            <p class="subtitle">输入 URL，启动审计，查看问题列表</p>
        </header>
        <main class="content">
            <router-view v-slot="{ Component }">
                <transition name="fade" mode="out-in">
                    <component :is="Component" />
                </transition>
            </router-view>
        </main>
    </div>
</template>
<script setup>
import { onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

onMounted(() => {
    router.push("/");
});
</script>

<style scoped>
.app-shell {
    min-height: 100vh;
    background:
        radial-gradient(
            circle at 20% 20%,
            rgba(79, 70, 229, 0.08),
            transparent 30%
        ),
        radial-gradient(
            circle at 80% 0%,
            rgba(16, 185, 129, 0.1),
            transparent 35%
        ),
        linear-gradient(135deg, #0f172a 0%, #111827 45%, #0b1021 100%);
    color: #e5e7eb;
    font-family:
        "Inter",
        "Segoe UI",
        system-ui,
        -apple-system,
        sans-serif;
}

.topbar {
    padding: 32px 6vw 12px;
}

.topbar h1 {
    margin: 0;
    font-size: 28px;
    letter-spacing: 0.4px;
}

.subtitle {
    margin: 6px 0 0;
    color: #9ca3af;
    font-size: 14px;
}

.content {
    padding: 12px 6vw 48px;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
