const businessStatus = {
  answered: {
    title: '已根据当前证据生成回答',
    description: '以下建议严格基于知识库官方资料生成并标注出处。',
  },
  needs_more_information: {
    title: '需要补充信息',
    description: '当前问题缺少必要上下文（如服装面料或护理标签），请补充后再试。',
  },
  insufficient_evidence: {
    title: '当前知识库证据不足',
    description: '当前知识库证据不足以给出可靠结论，系统拒绝未经证实的推测。',
  },
}

export function presentBusinessStatus(status) {
  return businessStatus[status] || {
    title: '请求已完成',
    description: '后端返回了未识别的业务状态。',
  }
}

export function presentEvidenceSemantics(status, evidenceCount = 0) {
  if (evidenceCount === 0) {
    return {
      tabTitle: '检索证据',
      note: '当前没有可展示的检索证据。',
      isCandidateOnly: false,
    }
  }

  if (status === 'needs_more_information') {
    return {
      tabTitle: '候选检索结果',
      note: '已检索到候选资料，但因问题缺少面料、品牌或洗标等必要信息，系统未将其作为最终回答依据。',
      isCandidateOnly: true,
    }
  }

  if (status === 'insufficient_evidence') {
    return {
      tabTitle: '已检索资料',
      note: '系统已执行检索，但当前知识库未形成足够证据支撑明确建议，拒绝未经证实的推测。',
      isCandidateOnly: true,
    }
  }

  return {
    tabTitle: '检索证据',
    note: '以下内容为本次回答所依据的核心官方资料切片。',
    isCandidateOnly: false,
  }
}

export function computeProcessSummary(trace, finalStatus) {
  if (!trace) return null

  if (trace.rewrite_count > 0) {
    return {
      type: 'rewrite',
      tag: '改写重检',
      text: '首轮证据不足触发改写 · 完成两轮检索',
    }
  }

  if (finalStatus === 'answered') {
    return {
      type: 'direct',
      tag: '单轮命中',
      text: '单轮混合检索 · 证据充分 · 进入回答生成',
    }
  }

  if (finalStatus === 'needs_more_information') {
    return {
      type: 'needs_info',
      tag: '需要信息',
      text: '缺少必要上下文 · 引导用户补充面料洗标',
    }
  }

  return {
    type: 'insufficient',
    tag: '证据不足',
    text: '知识库证据不足 · 安全终止不编造',
  }
}

export function formatRequestSeconds(elapsedMs) {
  return `${(elapsedMs / 1000).toFixed(1)} 秒`
}

export function formatRetrievalCount(count) {
  if (count === undefined || count === null) {
    return '未记录'
  }
  return `Top ${count}`
}

export function createRequestGate() {
  let busy = false
  return {
    begin() {
      if (busy) return false
      busy = true
      return true
    },
    end() {
      busy = false
    },
  }
}
