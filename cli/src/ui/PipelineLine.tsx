import React from 'react';
import { Text } from 'ink';
import type { ClassifiedLog } from '../logfmt.js';

/** Render one classified pipeline log line as a styled Ink element. Printed into <Static> (terminal
 *  scrollback) so it stays scrollable + selectable/copyable. Purely presentational — all the parsing
 *  lives in ../logfmt.ts. */
export default function PipelineLine({ line }: { line: ClassifiedLog }): React.ReactElement {
  const { kind, text, ts } = line;
  switch (kind) {
    case 'command':
      return (
        <Text>
          <Text color="green">$ </Text>
          <Text color="greenBright">{text}</Text>
        </Text>
      );
    case 'instruction':
      return (
        <Text>
          <Text color="cyan">▸ </Text>
          <Text color="whiteBright">{text}</Text>
        </Text>
      );
    case 'summary':
      return <Text color="cyan" dimColor>{text}</Text>;
    case 'divider':
      return <Text color="gray">{`────── ${text} ──────`}</Text>;
    case 'error':
      return <Text color="red">{text}</Text>;
    case 'warn':
      return <Text color="yellow">{text}</Text>;
    case 'plan-json':
    case 'cont':
    case 'debug':
      return <Text color="gray" dimColor>{`  ${text}`}</Text>;
    case 'info':
    default:
      return (
        <Text>
          {ts ? <Text color="gray" dimColor>{`${ts} `}</Text> : null}
          <Text color="gray">{text}</Text>
        </Text>
      );
  }
}
