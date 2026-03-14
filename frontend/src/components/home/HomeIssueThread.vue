<template>
    <div v-if="collabActive" class="thread">
        <div class="thread-title">
            团队讨论
            <span v-if="hasNew" class="thread-notif" />
        </div>

        <div v-if="!issueComments.length" class="thread-empty">
            暂无讨论，发表第一条评论
        </div>

        <div v-for="c in issueComments" :key="c.id" class="cmt">
            <div class="cmt-av" :class="`pav-${c.color}`">{{ c.initials }}</div>
            <div class="cmt-body">
                <div class="cmt-meta">
                    <span class="cmt-name">{{ c.author }}</span>
                    <span class="cmt-time">{{ c.time }}</span>
                    <span v-if="c.resolved" class="cmt-resolved">✓ 已处理</span>
                </div>
                <div class="cmt-text">{{ c.text }}</div>
            </div>
        </div>

        <div class="cmt-input-row">
            <textarea
                class="cmt-ta"
                rows="1"
                placeholder="添加评论…"
                :value="commentDraft[issueId] || ''"
                @input="commentDraft[issueId] = $event.target.value"
                @keydown.enter.exact.prevent="sendComment(issueId)"
            />
            <button class="cmt-send" @click="sendComment(issueId)">
                <SvgSend />
            </button>
        </div>
    </div>
</template>

<script setup>
import { computed, inject } from "vue";
import { SvgSend } from "./icons";

const props = defineProps({
    issueId: { type: String, required: true },
});

const collabVm = inject("collabVm");
if (!collabVm) throw new Error("collabVm is not provided");

const { collabActive, commentDraft, comments, sendComment } = collabVm;

const issueComments = computed(() => comments.value[props.issueId] || []);
const hasNew        = computed(() => issueComments.value.some(c => c.isNew));
</script>

<style scoped>
.thread {
    border-top: 1px solid #f0ede8;
    padding-top: 9px;
    margin-top: 8px;
}
.thread-title {
    font-size: 9px; font-weight: 700; color: #b0aca6;
    text-transform: uppercase; letter-spacing: .07em;
    margin-bottom: 8px; display: flex; align-items: center; gap: 5px;
}
.thread-notif {
    width: 6px; height: 6px; border-radius: 50%; background: #f0817a; flex-shrink: 0;
}
.thread-empty { font-size: 10px; color: #b0aca6; padding: 2px 0 8px; }
.cmt { display: flex; gap: 7px; margin-bottom: 8px; }
.cmt-av {
    width: 22px; height: 22px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; font-weight: 700; flex-shrink: 0; margin-top: 1px;
}
.cmt-body  { flex: 1; min-width: 0; }
.cmt-meta  { display: flex; align-items: center; gap: 5px; margin-bottom: 3px; }
.cmt-name  { font-size: 10px; font-weight: 600; color: #1a1a1a; }
.cmt-time  { font-size: 9px; color: #b0aca6; }
.cmt-resolved {
    font-size: 9px; color: #1a6e3c; background: #d4f4e2; border-radius: 6px; padding: 1px 6px;
}
.cmt-text {
    font-size: 11px; color: #52524f; line-height: 1.5;
    background: #fafaf8; border-radius: 0 8px 8px 8px;
    padding: 6px 9px; border: 1px solid #edeae5;
}
.cmt-input-row { display: flex; gap: 6px; margin-top: 8px; align-items: flex-start; }
.cmt-ta {
    flex: 1; padding: 6px 9px; border-radius: 8px;
    border: 1.5px solid #edeae5; background: #fafaf8; color: #1a1a1a;
    font-size: 11px; font-family: inherit; resize: none; outline: none;
    line-height: 1.5; transition: border-color .15s;
}
.cmt-ta:focus { border-color: #1a1a1a; background: #fff; }
.cmt-send {
    width: 28px; height: 28px; border-radius: 8px; border: none;
    background: #1a1a1a; color: #fff; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-top: 1px; transition: background .15s;
}
.cmt-send:hover { background: #333; }
/* pav-* 颜色（与 home-page.css 追加部分保持一致） */
.pav-amber  { background: #fde8c8; color: #8b4d0a; }
.pav-blue   { background: #dbeafe; color: #1e3a8a; }
.pav-green  { background: #d4f4e2; color: #1a6e3c; }
.pav-purple { background: #ede9fe; color: #5b21b6; }
.pav-coral  { background: #fce7f3; color: #9d174d; }
</style>