export type Drafts = string[]

declare module 'claude-code' {
  interface PluginState {
    'prompt-redo': { redo: Shaped<Drafts> }
  }
}
