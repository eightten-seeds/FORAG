const businessStatus = {
  answered: {
    title: '护理建议',
    description: '以下内容基于当前检索到的官方护理资料生成。',
  },
  needs_more_information: {
    title: '需要补充信息',
    description: '请根据提示补充服装或护理场景信息后再提问。',
  },
  insufficient_evidence: {
    title: '当前证据不足',
    description: '当前知识库证据不足以给出可靠结论。',
  },
}

export function presentBusinessStatus(status) {
  return businessStatus[status] || {
    title: '请求已完成',
    description: '后端返回了未识别的业务状态。',
  }
}

export function formatRequestSeconds(elapsedMs) {
  return `${(elapsedMs / 1000).toFixed(1)} 秒`
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
