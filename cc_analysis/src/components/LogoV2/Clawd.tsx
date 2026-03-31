import * as React from 'react'
import { Box, Text } from '../../ink.js'

export type ClawdPose =
  | 'default'
  | 'arms-up'
  | 'look-left'
  | 'look-right'

type Props = {
  pose?: ClawdPose
}

type WhaleArt = {
  top: string
  middle: string
  bottom: string
}

const WHALE_POSES: Record<ClawdPose, WhaleArt> = {
  default: {
    top: '    .-"""-.   ',
    middle: ' .-\'  o o  `-<',
    bottom: ' `-._\\_v_./   ',
  },
  'look-left': {
    top: '    .-"""-.   ',
    middle: ' .-\' o   o `-<',
    bottom: ' `-._\\_v_./   ',
  },
  'look-right': {
    top: '    .-"""-.   ',
    middle: ' .-\'  o   o`-<',
    bottom: ' `-._\\_v_./   ',
  },
  'arms-up': {
    top: '  ~  .-"""-.  ',
    middle: ' .-\'  o o  `-<',
    bottom: ' `-._\\_v_./   ',
  },
}

export function Clawd({ pose = 'default' }: Props = {}): React.ReactNode {
  const art = WHALE_POSES[pose]

  return (
    <Box flexDirection="column">
      <Text color="clawd_body">{art.top}</Text>
      <Text color="clawd_body">{art.middle}</Text>
      <Text color="clawd_body">{art.bottom}</Text>
    </Box>
  )
}
