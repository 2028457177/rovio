export function renderMarkdown(text) {
  if (!text) return ''

  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  html = html.replace(/```(\w+)?\n?([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`
  })

  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')

  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')

  html = html.replace(/^### (.+)$/gm, '<strong>$1</strong>')
  html = html.replace(/^## (.+)$/gm, '<strong>$1</strong>')
  html = html.replace(/^# (.+)$/gm, '<strong>$1</strong>')

  html = html.replace(/^- (.+)$/gm, '• $1')

  html = html.replace(/\n{2,}/g, '</p><p>')
  html = html.replace(/\n/g, '<br>')
  html = '<p>' + html + '</p>'

  html = html.replace(/<p><\/p>/g, '')

  return html
}
