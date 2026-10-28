import { demoApi } from './demoClient'
import { realApi } from './realClient'

export const IS_DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'

export const api = IS_DEMO_MODE ? demoApi : realApi

export * from './types'
