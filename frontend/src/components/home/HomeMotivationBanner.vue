<template>
    <transition name="slide-down">
        <div v-if="showMotivation" class="mot-banner">
            <div class="mot-icon">{{ motIcon }}</div>
            <div class="mot-body">
                <div class="mot-title">{{ motTitle }}</div>
                <div class="mot-sub">{{ motSub }}</div>
            </div>
            <div v-if="tab === 'submit'" class="ach-row">
                <div
                    v-for="a in achievements"
                    :key="a.id"
                    class="ach-badge"
                    :class="a.unlocked ? `ab-${a.color}` : 'ab-locked'"
                    :title="a.unlocked ? '已解锁' : `${a.goal} 后解锁`"
                >
                    <span
                        class="ach-icon"
                        :style="
                            a.unlocked ? '' : 'filter:grayscale(1);opacity:.35'
                        "
                        >{{ a.icon }}</span
                    >
                    <div class="ach-name">{{ a.name }}</div>
                    <div class="ach-prog">
                        {{ a.unlocked ? "已解锁" : a.goal }}
                    </div>
                </div>
            </div>
        </div>
    </transition>
</template>

<script setup>
import { inject } from "vue";

const vm = inject("homeVm");
if (!vm) throw new Error("homeVm is not provided");

const { achievements, motIcon, motSub, motTitle, showMotivation, tab } = vm;
</script>
