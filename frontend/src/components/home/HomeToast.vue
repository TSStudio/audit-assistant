<template>
    <transition name="toast-fade">
        <div v-if="toastMsg" class="toast">{{ toastMsg }}</div>
    </transition>
</template>

<script setup>
import { inject } from "vue";

const vm = inject("homeVm");
if (!vm) throw new Error("homeVm is not provided");

const { toastMsg } = vm;
</script>
