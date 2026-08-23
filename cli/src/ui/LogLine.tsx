import React from 'react';
import { Text } from 'ink';
import { cleanErrorText } from '../run.js';

/** Render one transcript line as a styled Ink element instead of flat text. Classifies by content
 *  (first match wins) and colors accordingly; compresses raw LLM error blobs via cleanErrorText.
 *  Purely presentational — callers keep pushing plain strings. */
export default function LogLine({ text }: { text: string }): React.ReactElement {
  const raw = cleanErrorText(text);
  const t = raw.trimStart();
  const indented = raw.length - t.length > 0;

  // prompt echo: "❯ <cmd>"
  if (t.startsWith('❯ ')) {
    return (
      <Text>
        <Text color="magenta">❯ </Text>
        <Text color="white" bold>{t.slice(2)}</Text>
      </Text>
    );
  }

  // warnings
  if (t.startsWith('⚠')) return <Text color="yellow">{raw}</Text>;

  // errors / aborts / failures
  if (
    t.startsWith('✗') ||
    t.startsWith('Aborting') ||
    t.startsWith('run failed') ||
    t.startsWith('error:') ||
    t.startsWith('run aborted') ||
    /\berror \d{3}\b/.test(t) ||
    t.includes('**ERROR**')
  ) {
    return <Text color="red">{raw}</Text>;
  }

  // successes
  if (
    t.startsWith('✓') ||
    t.startsWith('run finished') ||
    t.startsWith('signed in') ||
    t.startsWith('Plan Initialized') ||
    t.startsWith('smoke OK')
  ) {
    return <Text color="green">{raw}</Text>;
  }

  // provider/model/thinking switches
  if (t.includes(' -> ')) return <Text color="cyan">{raw}</Text>;

  // start-of-run banner
  if (t.startsWith('starting pentest')) return <Text color="cyanBright">{raw}</Text>;

  // hints + indented continuation lines
  if (t.startsWith('hint:') || indented) return <Text color="gray" dimColor>{raw}</Text>;

  // help header + command rows
  if (t === 'commands:' || t.startsWith('usage:')) return <Text color="cyan" bold>{raw}</Text>;
  if (t.startsWith('/')) return <Text color="cyan">{raw}</Text>;

  return <Text>{raw}</Text>;
}
