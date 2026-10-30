import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

// Drafts the undo took away, newest last.
const redo = atom({ plugin: 'prompt-redo', key: 'redo' } as const, [] as string[], { shape: 'redo-1' })

export const register: Register = on => {
  let last = '' // the draft as it stood before the latest change

  on('prompt.edit', async ($, e, next) => {
    const r = await next(e)
    if (r.text !== e.text) await update($, redo, () => []) // a real edit ends the redo chain
    last = r.text
    return r
  })

  on('prompt.change', async ($, e, next) => {
    if (e.origin.kind === 'undo') {
      const before = last
      if (before !== e.text) await update($, redo, s => [...s, before])
    } else if (!(e.origin.kind === 'plugin' && e.origin.name === 'prompt-redo')) {
      await update($, redo, () => [])
    }
    last = e.text
    return next(e)
  })

  // ctrl+y reaches the Button through ~/.claude/keybindings.json: Global "ctrl+y": "app:cycleDiffBase"
  // (a Chat-context binding never fires: the prompt box keeps ctrl+y). The band shows only with something to redo.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const stack = await read($, redo)
    if (e.props.hasSurvey || stack.length === 0) return next(e)

    const { Box, Button, Text } = $.ui.resolve(e)
    const press = async () => {
      const s = await read($, redo)
      const text = s[s.length - 1]
      if (text === undefined) return
      await update($, redo, x => x.slice(0, -1))
      await $.prompt.fill({ text })
    }

    return (
      <Box>
        <Button key="redo" action="app:cycleDiffBase" onPress={press} label="↷ redo" />
        <Text dimColor> ctrl+y ({stack.length})</Text>
      </Box>
    )
  })
}
