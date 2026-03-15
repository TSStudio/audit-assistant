<template>
    <div class="submit-card">
        <div class="pg-eye">新建审计</div>
        <h2 class="pg-title">今天想审什么？</h2>
        <p class="pg-sub">粘贴链接或上传文件，AI 替你把关每一个细节。</p>

        <div class="mode-row">
            <button
                class="mode-pill"
                :class="{ on: inputMode === 'url' }"
                @click="switchMode('url')"
            >
                URL 链接
            </button>
            <button
                class="mode-pill"
                :class="{ on: inputMode === 'file' }"
                @click="switchMode('file')"
            >
                文件上传
            </button>
        </div>

        <label class="f-label" style="margin-top: 12px">审计模式</label>
        <div class="mode-row" style="margin-top: 8px">
            <button
                class="mode-pill"
                :class="{ on: auditSpeed === 'fast' }"
                :disabled="loading"
                @click="auditSpeed = 'fast'"
            >
                Fast Mode（关闭 Thinking）
            </button>
        </div>
        <p v-if="!slowModeEnabled" class="f-hint" style="margin-top: 8px">
            游园会期间，为确保模型使用顺畅，Slow Mode 暂时禁用
        </p>

        <template v-if="inputMode === 'url'">
            <label class="f-label">页面链接</label>
            <div class="inp-row">
                <input
                    v-model="urlInput"
                    type="url"
                    class="text-inp"
                    placeholder="https://example.com/article"
                    :disabled="loading"
                    @keydown.enter="startAudit"
                />
                <button
                    class="primary-btn"
                    :disabled="loading || !urlInput"
                    @click="startAudit"
                >
                    <SvgArrow />{{ loading ? "提交中…" : "开始审计" }}
                </button>
            </div>
        </template>

        <template v-else>
            <label class="f-label">上传文件</label>
            <div class="file-row">
                <label class="file-lbl">
                    <SvgUpload />选择文件
                    <input
                        ref="fileInputRef"
                        type="file"
                        accept=".txt,.docx,.pdf,image/*"
                        :disabled="loading"
                        style="display: none"
                        @change="onFileChange"
                    />
                </label>
                <span class="file-nm">{{
                    selectedFileName || "未选择文件"
                }}</span>
            </div>
            <div class="inp-row" style="margin-top: 10px">
                <button
                    class="primary-btn"
                    :disabled="loading || !selectedFile"
                    @click="startAudit"
                >
                    <SvgArrow />{{ loading ? "提交中…" : "开始审计" }}
                </button>
            </div>
        </template>
    </div>

    <div class="field-card">
        <span class="f-label"
            >审核清单知识库 <span class="f-hint">（可复用，可多选）</span></span
        >
        <textarea
            v-model="checklistInput"
            class="f-ta"
            rows="4"
            :disabled="loading"
            placeholder="输入临时清单（每行一条），或点“保存到知识库”复用"
        />
        <div class="inp-row" style="margin-top: 8px">
            <input
                v-model="newChecklistName"
                type="text"
                class="text-inp"
                :disabled="loading"
                placeholder="清单名称，例如：金融稿件审核"
            />
            <button
                class="ghost-sm"
                :disabled="loading || !checklistInput.trim()"
                @click="saveChecklistToKb"
            >
                保存到知识库
            </button>
        </div>
        <div v-if="checklistKbs.length" class="kb-list" style="margin-top: 8px">
            <div v-for="item in checklistKbs" :key="item.kb_id" class="kb-item">
                <label class="kb-main">
                    <input
                        type="checkbox"
                        :value="item.kb_id"
                        v-model="selectedChecklistKbIds"
                        :disabled="loading"
                    />
                    <span>{{ item.name }}</span>
                </label>
                <div class="kb-ops">
                    <button
                        class="kb-op"
                        :disabled="loading"
                        @click="renameChecklistKb(item)"
                    >
                        改名
                    </button>
                    <button
                        class="kb-op danger"
                        :disabled="loading"
                        @click="deleteChecklistKb(item)"
                    >
                        删除
                    </button>
                </div>
            </div>
        </div>
        <p v-else class="f-hint" style="margin-top: 8px">暂无清单知识库</p>
    </div>

    <div class="field-card">
        <span class="f-label"
            >附加资料知识库
            <span class="f-hint">（上传一次，后续可直接选择）</span></span
        >
        <div class="file-row" style="margin-top: 6px">
            <label class="file-lbl">
                <SvgUpload />上传到知识库
                <input
                    ref="referenceFileInputRef"
                    type="file"
                    accept=".txt,.docx,.pdf"
                    multiple
                    :disabled="loading"
                    style="display: none"
                    @change="onReferenceFilesChange"
                />
            </label>
            <span class="file-nm">{{ referenceFileNamesText }}</span>
            <button
                class="ghost-sm"
                :disabled="loading || !referenceFiles.length"
                @click="saveReferencesToKb"
            >
                保存
            </button>
        </div>
        <div v-if="referenceKbs.length" class="kb-list" style="margin-top: 8px">
            <div v-for="item in referenceKbs" :key="item.kb_id" class="kb-item">
                <label class="kb-main">
                    <input
                        type="checkbox"
                        :value="item.kb_id"
                        v-model="selectedReferenceKbIds"
                        :disabled="loading"
                    />
                    <span>{{ item.name }}</span>
                </label>
                <div class="kb-ops">
                    <button
                        class="kb-op"
                        :disabled="loading"
                        @click="renameReferenceKb(item)"
                    >
                        改名
                    </button>
                    <button
                        class="kb-op danger"
                        :disabled="loading"
                        @click="deleteReferenceKb(item)"
                    >
                        删除
                    </button>
                </div>
            </div>
        </div>
        <p v-else class="f-hint" style="margin-top: 8px">暂无附加资料知识库</p>
    </div>

    <div v-if="error" class="err-banner">⚠ {{ error }}</div>

    <div v-if="status" class="prog-card">
        <div class="prog-top">
            <span class="prog-msg-txt">{{ message || "准备中…" }}</span>
            <span class="prog-pct">{{ Math.round(displayProgress) }}%</span>
        </div>
        <div class="prog-track">
            <div
                class="prog-fill"
                :class="{
                    done: status === 'completed',
                    err: status === 'failed',
                }"
                :style="{ width: progressWidth }"
            />
        </div>
        <div v-if="taskId" class="prog-note">任务 {{ taskId }}</div>
    </div>
</template>

<script setup>
import { inject } from "vue";
import { SvgArrow, SvgUpload } from "./icons";

const vm = inject("homeVm");
if (!vm) throw new Error("homeVm is not provided");

const {
    auditSpeed,
    checklistInput,
    checklistKbs,
    deleteChecklistKb,
    deleteReferenceKb,
    displayProgress,
    error,
    fileInputRef,
    inputMode,
    loading,
    message,
    newChecklistName,
    onFileChange,
    onReferenceFilesChange,
    progressWidth,
    referenceFileInputRef,
    referenceFileNamesText,
    referenceFiles,
    referenceKbs,
    renameChecklistKb,
    renameReferenceKb,
    saveChecklistToKb,
    saveReferencesToKb,
    selectedChecklistKbIds,
    selectedFile,
    selectedFileName,
    selectedReferenceKbIds,
    slowModeEnabled,
    startAudit,
    status,
    switchMode,
    taskId,
    urlInput,
} = vm;
</script>
