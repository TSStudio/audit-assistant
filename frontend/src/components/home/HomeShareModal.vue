<template>
    <transition name="modal-fade">
        <div
            v-if="shareModalOpen"
            class="modal-backdrop"
            @click.self="shareModalOpen = false"
        >
            <div class="modal-box">
                <div class="modal-head">
                    <div>
                        <div class="modal-title">分享协作</div>
                        <div class="modal-sub">生成链接邀请团队成员共同审校</div>
                    </div>
                    <button class="modal-close" @click="shareModalOpen = false">✕</button>
                </div>

                <!-- 分享链接 -->
                <div class="f-label">分享链接</div>
                <div class="inp-row" style="margin-bottom: 16px">
                    <input
                        class="text-inp"
                        :value="shareLink"
                        readonly
                        style="font-family: monospace; font-size: 11px; color: #52524f; background: #f5f2ed; cursor: default"
                    />
                    <button class="primary-btn" @click="copyShareLink">
                        <SvgCopy />{{ linkCopied ? '已复制 ✓' : '复制' }}
                    </button>
                </div>

                <!-- 权限选择 -->
                <div class="f-label">默认访问权限</div>
                <div class="perm-row">
                    <div
                        class="perm-opt"
                        :class="{ sel: sharePerm === 'view' }"
                        @click="sharePerm = 'view'"
                    >
                        <div class="perm-icon">👁</div>
                        <div class="perm-name">只读</div>
                        <div class="perm-desc">查看问题和讨论，不可修改</div>
                    </div>
                    <div
                        class="perm-opt"
                        :class="{ sel: sharePerm === 'edit' }"
                        @click="sharePerm = 'edit'"
                    >
                        <div class="perm-icon">✏️</div>
                        <div class="perm-name">可编辑</div>
                        <div class="perm-desc">可驳回问题、参与讨论</div>
                    </div>
                    <div
                        class="perm-opt"
                        :class="{ sel: sharePerm === 'invite' }"
                        @click="sharePerm = 'invite'"
                    >
                        <div class="perm-icon">🔒</div>
                        <div class="perm-name">仅受邀</div>
                        <div class="perm-desc">手动邀请才可访问</div>
                    </div>
                </div>

                <div class="modal-divider" />

                <!-- 邀请成员 -->
                <div class="f-label">邀请成员</div>
                <div class="inp-row" style="margin-bottom: 12px">
                    <input
                        v-model="inviteEmail"
                        class="text-inp"
                        placeholder="输入邮箱地址或姓名"
                        @keydown.enter="inviteMember"
                    />
                    <button class="primary-btn" @click="inviteMember">邀请</button>
                </div>

                <!-- 成员列表 -->
                <div class="member-list-modal">
                    <!-- 自己 -->
                    <div class="modal-member-row">
                        <div class="presence-avatar pav-amber" style="width:28px;height:28px;font-size:11px">编</div>
                        <div class="modal-member-info">
                            <div class="modal-member-name">我（所有者）</div>
                            <div class="modal-member-email">editor@team.com</div>
                        </div>
                        <span class="role-badge rb-owner">所有者</span>
                    </div>
                    <!-- 其他成员 -->
                    <div v-for="m in shareMembers" :key="m.id" class="modal-member-row">
                        <div
                            class="presence-avatar"
                            :class="`pav-${m.color}`"
                            style="width:28px;height:28px;font-size:11px"
                        >
                            {{ m.initials }}
                        </div>
                        <div class="modal-member-info">
                            <div class="modal-member-name">{{ m.name }}</div>
                            <div class="modal-member-email">{{ m.email }}</div>
                        </div>
                        <select
                            class="role-select"
                            :value="m.role"
                            @change="updateMemberRole(m.id, $event.target.value)"
                        >
                            <option value="edit">可编辑</option>
                            <option value="view">只读</option>
                            <option value="remove">移除</option>
                        </select>
                    </div>
                </div>

                <div class="modal-footer">
                    <button class="ghost-sm" @click="shareModalOpen = false">取消</button>
                    <button
                        class="primary-btn"
                        style="background: #8b4d0a"
                        @click="confirmShare"
                    >
                        <SvgShare />保存并分享
                    </button>
                </div>
            </div>
        </div>
    </transition>
</template>

<script setup>
import { inject } from "vue";
import { SvgCopy, SvgShare } from "./icons";

const collabVm = inject("collabVm");
if (!collabVm) throw new Error("collabVm is not provided");

const {
    confirmShare,
    copyShareLink,
    inviteEmail,
    inviteMember,
    linkCopied,
    shareLink,
    shareMembers,
    shareModalOpen,
    sharePerm,
    updateMemberRole,
} = collabVm;
</script>

<style scoped>
.modal-backdrop {
    position: fixed; inset: 0; background: rgba(0,0,0,.35);
    display: flex; align-items: center; justify-content: center; z-index: 400;
}
.modal-box {
    background: #fff; border-radius: 16px; padding: 24px;
    width: 460px; max-width: calc(100vw - 32px);
    box-shadow: 0 16px 48px rgba(0,0,0,.18);
}
.modal-head {
    display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 18px;
}
.modal-title { font-size: 15px; font-weight: 700; color: #1a1a1a; }
.modal-sub   { font-size: 11px; color: #7a7872; margin-top: 3px; }
.modal-close {
    width: 26px; height: 26px; border-radius: 7px; border: 1.5px solid #edeae5;
    background: #fafaf8; cursor: pointer; display: flex; align-items: center;
    justify-content: center; color: #7a7872; font-size: 13px; transition: all .15s; flex-shrink: 0;
}
.modal-close:hover { background: #f0ede8; color: #1a1a1a; }
.perm-row { display: flex; gap: 8px; margin-bottom: 18px; }
.perm-opt {
    flex: 1; border-radius: 10px; border: 1.5px solid #edeae5;
    padding: 10px 12px; cursor: pointer; transition: all .15s; background: #fafaf8;
}
.perm-opt.sel  { border-color: #1a1a1a; background: #fff; }
.perm-opt:hover:not(.sel) { background: #f5f2ed; }
.perm-icon { font-size: 18px; margin-bottom: 4px; }
.perm-name { font-size: 11px; font-weight: 600; color: #1a1a1a; }
.perm-desc { font-size: 10px; color: #7a7872; margin-top: 2px; line-height: 1.4; }
.modal-divider { height: 1px; background: #f0ede8; margin: 14px 0; }
.member-list-modal {
    display: flex; flex-direction: column; gap: 6px; max-height: 160px; overflow-y: auto; margin-bottom: 4px;
}
.modal-member-row {
    display: flex; align-items: center; gap: 9px;
    padding: 7px 10px; border-radius: 9px; background: #fafaf8; border: 1px solid #edeae5;
}
.modal-member-info { flex: 1; min-width: 0; }
.modal-member-name  { font-size: 11px; font-weight: 600; color: #1a1a1a; }
.modal-member-email { font-size: 10px; color: #b0aca6; }
.role-select {
    padding: 3px 7px; border-radius: 20px; border: 1.5px solid #edeae5;
    background: #fff; font-size: 10px; font-weight: 500; color: #7a7872;
    cursor: pointer; font-family: inherit; outline: none; transition: all .15s;
}
.role-select:hover { background: #f0ede8; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }
/* modal 进入/离开动画 */
.modal-fade-enter-active { transition: opacity .2s ease; }
.modal-fade-leave-active { transition: opacity .15s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
</style>