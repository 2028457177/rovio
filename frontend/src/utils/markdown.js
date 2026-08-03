/**
 * 增强版 Markdown 渲染器（无外部依赖）
 *
 * 支持：
 *  - 代码块（```lang ... ```）—— 输出带语言标签和复制按钮的 <pre> 结构
 *  - 行内代码（`code`）
 *  - 表格（GFM 风格 | a | b |\n|---|---|）
 *  - 数学公式（$$...$$ 块级，$...$ 行内）—— 简易美化渲染
 *  - 标题 / 列表 / 引用 / 链接 / 加粗 / 删除线 / 分隔线
 *
 * 渲染结果是纯 HTML 字符串，组件层用 v-html 注入；
 * 代码块的“复制”按钮通过 data-code 属性 + 事件委托实现（见 MessageBubble.vue）。
 */

export function renderMarkdown(text) {
  if (!text) return ''

  // 1. 先抽出代码块（用占位符替换，避免内部内容被其他规则污染）
  const codeBlocks = []
  const codeBlockPlaceholder = (lang, code) => {
    const idx = codeBlocks.length
    codeBlocks.push({ lang, code })
    return `\u0000CODEBLOCK_${idx}\u0000`
  }

  let src = text.replace(/```(\w+)?\n?([\s\S]*?)```/g, (_, lang, code) => {
    return codeBlockPlaceholder((lang || '').toLowerCase(), code.replace(/\n$/, ''))
  })

  // 2. 抽出块级公式
  const blockMaths = []
  src = src.replace(/\$\$([\s\S]+?)\$\$/g, (_, expr) => {
    const idx = blockMaths.length
    blockMaths.push(expr)
    return `\u0000BLOCKMATH_${idx}\u0000`
  })

  // 3. HTML 转义（保护剩余文本）
  src = src
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // 4. 按行切分处理表格、列表、引用、标题
  const lines = src.split('\n')
  const out = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // 表格检测：当前行包含 | 且下一行是分隔行 |---|---|
    if (/\|/.test(line) && i + 1 < lines.length && /^\s*\|?[\s:-]*-{3,}[\s:|-]*\|?\s*$/.test(lines[i + 1])) {
      out.push(renderTable(lines, i))
      // 跳过表头 + 分隔行 + 数据行
      i += 2
      while (i < lines.length && /\|/.test(lines[i])) i++
      continue
    }

    // 标题
    const h = /^(#{1,6})\s+(.*)$/.exec(line)
    if (h) {
      const level = h[1].length
      out.push(`<h${level}>${inlineFormat(h[2])}</h${level}>`)
      i++
      continue
    }

    // 引用块（连续 > 合并）
    if (/^>\s?/.test(line)) {
      const buf = []
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        buf.push(lines[i].replace(/^>\s?/, ''))
        i++
      }
      out.push(`<blockquote>${inlineFormat(buf.join('<br>'))}</blockquote>`)
      continue
    }

    // 无序列表
    if (/^\s*[-*+]\s+/.test(line)) {
      const buf = []
      while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
        buf.push(`<li>${inlineFormat(lines[i].replace(/^\s*[-*+]\s+/, ''))}</li>`)
        i++
      }
      out.push(`<ul>${buf.join('')}</ul>`)
      continue
    }

    // 有序列表
    if (/^\s*\d+\.\s+/.test(line)) {
      const buf = []
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        buf.push(`<li>${inlineFormat(lines[i].replace(/^\s*\d+\.\s+/, ''))}</li>`)
        i++
      }
      out.push(`<ol>${buf.join('')}</ol>`)
      continue
    }

    // 分隔线
    if (/^(\*\*\*|---|___)\s*$/.test(line)) {
      out.push('<hr>')
      i++
      continue
    }

    // 空行
    if (/^\s*$/.test(line)) {
      out.push('')
      i++
      continue
    }

    // 普通段落：连续非空行合并
    const buf = [line]
    i++
    while (
      i < lines.length &&
      !/^\s*$/.test(lines[i]) &&
      !/^(#{1,6})\s+/.test(lines[i]) &&
      !/^>\s?/.test(lines[i]) &&
      !/^\s*[-*+]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i]) &&
      !/^(\*\*\*|---|___)\s*$/.test(lines[i]) &&
      !(/\|/.test(lines[i]) && i + 1 < lines.length && /^\s*\|?[\s:-]*-{3,}[\s:|-]*\|?\s*$/.test(lines[i + 1]))
    ) {
      buf.push(lines[i])
      i++
    }
    out.push(`<p>${inlineFormat(buf.join('<br>'))}</p>`)
  }

  let html = out.join('\n')

  // 5. 还原代码块
  html = html.replace(/\u0000CODEBLOCK_(\d+)\u0000/g, (_, idx) => {
    const { lang, code } = codeBlocks[Number(idx)]
    const langLabel = lang ? `<span class="code-lang">${escapeHtml(lang)}</span>` : '<span class="code-lang">text</span>'
    const encoded = encodeURIComponent(code)
    return (
      `<pre class="code-block" data-code="${encoded}">` +
      `<div class="code-header">${langLabel}<button class="code-copy-btn" type="button" data-copy="${encoded}">复制</button></div>` +
      `<code>${escapeHtml(code)}</code>` +
      `</pre>`
    )
  })

  // 6. 还原块级公式
  html = html.replace(/\u0000BLOCKMATH_(\d+)\u0000/g, (_, idx) => {
    const expr = blockMaths[Number(idx)]
    return `<div class="math-block">${renderMath(expr)}</div>`
  })

  // 7. 清理空段落
  html = html.replace(/<p>\s*<\/p>/g, '')

  return html
}

/**
 * 表格渲染：表头 + 分隔行 + 数据行
 */
function renderTable(lines, startIdx) {
  const headerCells = splitTableRow(lines[startIdx])
  const dataRows = []
  let i = startIdx + 2
  while (i < lines.length && /\|/.test(lines[i])) {
    dataRows.push(splitTableRow(lines[i]))
    i++
  }
  const thead = '<thead><tr>' + headerCells.map(c => `<th>${inlineFormat(c)}</th>`).join('') + '</tr></thead>'
  const tbody = '<tbody>' + dataRows.map(row =>
    '<tr>' + row.map(c => `<td>${inlineFormat(c)}</td>`).join('') + '</tr>'
  ).join('') + '</tbody>'
  return `<div class="md-table-wrap"><table>${thead}${tbody}</table></div>`
}

function splitTableRow(line) {
  // 去掉首尾的 |
  let s = line.trim()
  if (s.startsWith('|')) s = s.slice(1)
  if (s.endsWith('|')) s = s.slice(0, -1)
  return s.split('|').map(c => c.trim())
}

/**
 * 行内格式：加粗、斜体、删除线、行内代码、链接、行内公式
 */
function inlineFormat(text) {
  if (!text) return ''
  let s = text
  // 行内公式 $...$
  s = s.replace(/\$([^\$\n]+?)\$/g, (_, expr) => `<span class="math-inline">${renderMath(expr)}</span>`)
  // 加粗 **xxx**
  s = s.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>')
  // 斜体 *xxx* 或 _xxx_
  s = s.replace(/(^|[^\*])\*([^\*\n]+?)\*(?!\*)/g, '$1<em>$2</em>')
  s = s.replace(/(^|\W)_([^_\n]+?)_(?!\w)/g, '$1<em>$2</em>')
  // 删除线 ~~xxx~~
  s = s.replace(/~~([^~]+?)~~/g, '<del>$1</del>')
  // 行内代码 `xxx`
  s = s.replace(/`([^`]+?)`/g, '<code>$1</code>')
  // 链接 [text](url)
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
  return s
}

/**
 * 极简数学公式渲染：把常见 LaTeX 转为 HTML。
 * 复杂公式仍能以原始 LaTeX 文本展示，不会丢失内容。
 */
function renderMath(expr) {
  if (!expr) return ''
  let s = expr.trim()
  // 上下标：x^2 -> x<sup>2</sup>，x_1 -> x<sub>1</sub>；含 {} 时取整组
  s = s.replace(/\^\{([^{}]+)\}/g, '<sup>$1</sup>')
  s = s.replace(/\^(\w)/g, '<sup>$1</sup>')
  s = s.replace(/_\{([^{}]+)\}/g, '<sub>$1</sub>')
  s = s.replace(/_(\w)/g, '<sub>$1</sub>')
  // 分式 \frac{a}{b}
  s = s.replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, '<span class="math-frac"><span class="math-num">$1</span><span class="math-den">$2</span></span>')
  // 常见希腊字母
  const greek = { alpha:'α', beta:'β', gamma:'γ', delta:'δ', epsilon:'ε', zeta:'ζ', eta:'η', theta:'θ', iota:'ι', kappa:'κ', lambda:'λ', mu:'μ', nu:'ν', xi:'ξ', pi:'π', rho:'ρ', sigma:'σ', tau:'τ', upsilon:'υ', phi:'φ', chi:'χ', psi:'ψ', omega:'ω', Gamma:'Γ', Delta:'Δ', Theta:'Θ', Lambda:'Λ', Xi:'Ξ', Pi:'Π', Sigma:'Σ', Phi:'Φ', Psi:'Ψ', Omega:'Ω' }
  s = s.replace(/\\([aA]lpha|[bB]eta|[gG]amma|[dD]elta|[eE]psilon|[zZ]eta|[eE]ta|[tT]heta|[iI]ota|[kK]appa|[lL]ambda|[mM]u|[nN]u|[xX]i|[pP]i|[rR]ho|[sS]igma|[tT]au|[uU]psilon|[pP]hi|[cC]hi|[pP]si|[oO]mega)/g, (_, w) => greek[w] || w)
  // 平方根 \sqrt{x}
  s = s.replace(/\\sqrt\{([^{}]+)\}/g, '<span class="math-sqrt">√<span class="math-sqrt-inner">$1</span></span>')
  // 求和、积分等
  s = s.replace(/\\sum/g, '∑').replace(/\\int/g, '∫').replace(/\\prod/g, '∏').replace(/\\infty/g, '∞')
  s = s.replace(/\\le/g, '≤').replace(/\\ge/g, '≥').replace(/\\ne/g, '≠').replace(/\\approx/g, '≈').replace(/\\pm/g, '±')
  s = s.replace(/\\times/g, '×').replace(/\\div/g, '÷').replace(/\\cdot/g, '·').replace(/\\to/g, '→').replace(/\\rightarrow/g, '→')
  s = s.replace(/\\in/g, '∈').replace(/\\notin/g, '∉').replace(/\\subset/g, '⊂').replace(/\\supset/g, '⊃').replace(/\\cup/g, '∪').replace(/\\cap/g, '∩')
  s = s.replace(/\\forall/g, '∀').replace(/\\exists/g, '∃').replace(/\\nabla/g, '∇').replace(/\\partial/g, '∂')
  // 去掉残留的反斜杠命令前缀（\text{xxx} 等）
  s = s.replace(/\\text\{([^{}]+)\}/g, '$1')
  s = s.replace(/\\[a-zA-Z]+/g, m => m.slice(1)) // 兜底：去掉未知命令的反斜杠
  // 转义 HTML
  return s
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
