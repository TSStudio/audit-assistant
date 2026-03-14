import { computed, ref } from 'vue'

export default function useCollabLogic({ showToast, displayIssues, decisionStats }) {
    const shareModalOpen = ref(false)
    const collabActive = ref(false)
    const sharePerm = ref('edit')
    const shareLink = ref(`https://audit.ai/share/${Math.random().toString(36).slice(2, 10)}`)
    const linkCopied = ref(false)
    const inviteEmail = ref('')
    const comments = ref({})       // { [issueId]: [{id,author,initials,color,text,time,isNew}] }
    const commentDraft = ref({})       // { [issueId]: string }

    const shareMembers = ref([
        { id: 1, name: '张校', email: 'zhang@team.com', role: 'edit', online: true, initials: '张', color: 'blue' },
        { id: 2, name: '李审', email: 'li@team.com', role: 'edit', online: true, initials: '李', color: 'green' },
        { id: 3, name: '王编', email: 'wang@team.com', role: 'view', online: false, initials: '王', color: 'purple' },
    ])
    const activityFeed = ref([])

    const onlineMembers = computed(() => shareMembers.value)
    const onlineCount = computed(() => shareMembers.value.filter(m => m.online).length)

    const totalCommentCount = computed(() =>
        Object.values(comments.value).reduce((s, a) => s + a.length, 0),
    )

    const collabProgress = computed(() => {
        const total = displayIssues.value.length
        if (!total) return 0
        return Math.round((decisionStats.value.rejected / total) * 100)
    })

    function copyShareLink() {
        navigator.clipboard?.writeText(shareLink.value).catch(() => { })
        linkCopied.value = true
        showToast('链接已复制到剪贴板')
        setTimeout(() => { linkCopied.value = false }, 2000)
    }

    function inviteMember() {
        const email = inviteEmail.value.trim()
        if (!email) { showToast('请输入邮箱地址'); return }
        const initials = email.charAt(0).toUpperCase()
        const palette = ['blue', 'green', 'purple', 'coral', 'amber']
        const color = palette[shareMembers.value.length % palette.length]
        shareMembers.value = [...shareMembers.value, {
            id: Date.now(), name: email, email,
            role: sharePerm.value === 'view' ? 'view' : 'edit',
            online: false, initials, color,
        }]
        activityFeed.value = [
            { id: Date.now(), name: email, initials, color, desc: '受到邀请', time: '刚刚' },
            ...activityFeed.value,
        ]
        inviteEmail.value = ''
        showToast(`邀请已发送至 ${email}`)
    }

    function updateMemberRole(memberId, role) {
        if (role === 'remove') {
            shareMembers.value = shareMembers.value.filter(m => m.id !== memberId)
            showToast('成员已移除')
            return
        }
        shareMembers.value = shareMembers.value.map(m =>
            m.id === memberId ? { ...m, role } : m,
        )
        showToast('权限已更新')
    }

    function confirmShare() {
        collabActive.value = true
        shareModalOpen.value = false
        activityFeed.value = [
            { id: Date.now(), name: '我', initials: '编', color: 'amber', desc: '创建了分享链接', time: '刚刚' },
            ...activityFeed.value,
        ]
        showToast('分享链接已生成，协作已开启')
    }

    function sendComment(issueId) {
        const text = (commentDraft.value[issueId] || '').trim()
        if (!text) return
        comments.value = {
            ...comments.value,
            [issueId]: [...(comments.value[issueId] || []), {
                id: Date.now(), author: '我', initials: '编', color: 'amber',
                text, time: '刚刚', resolved: false, isNew: true,
            }],
        }
        commentDraft.value = { ...commentDraft.value, [issueId]: '' }
        activityFeed.value = [
            { id: Date.now(), name: '我', initials: '编', color: 'amber', desc: '在问题中添加了评论', time: '刚刚' },
            ...activityFeed.value,
        ]
        showToast('评论已发送')
    }

    function resetCollab() {
        collabActive.value = false
        comments.value = {}
        commentDraft.value = {}
    }

    return {
        activityFeed,
        collabActive,
        collabProgress,
        commentDraft,
        comments,
        confirmShare,
        copyShareLink,
        inviteEmail,
        inviteMember,
        linkCopied,
        onlineCount,
        onlineMembers,
        resetCollab,
        sendComment,
        shareLink,
        shareMembers,
        shareModalOpen,
        sharePerm,
        totalCommentCount,
        updateMemberRole,
    }
}