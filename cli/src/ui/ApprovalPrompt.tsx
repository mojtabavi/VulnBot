/*  ApprovalPrompt — the Ink overlay for a human-in-the-loop approval (R2, TL-4.2).
 *
 *  Shown when the agent sends an `approval_request` control frame before running a high-impact
 *  action. The user approves or denies; the Repl relays the choice back over the control socket.
 *  Defaults to DENY (the safe choice) so an accidental Enter never fires an exploit.
 */
import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';

export interface ApprovalRequest {
  action: string;
  risk?: string;
  host?: string;
  type?: string;
}

export default function ApprovalPrompt({
  req,
  onDecide,
}: {
  req: ApprovalRequest;
  onDecide: (d: 'approve' | 'deny') => void;
}): React.ReactElement {
  const [sel, setSel] = useState<'approve' | 'deny'>('deny'); // safe default

  useInput((ch, key) => {
    if (key.leftArrow || key.rightArrow || key.tab) {
      setSel((s) => (s === 'approve' ? 'deny' : 'approve'));
    } else if (ch === 'a' || ch === 'A') {
      onDecide('approve');
    } else if (ch === 'd' || ch === 'D' || key.escape) {
      onDecide('deny');
    } else if (key.return) {
      onDecide(sel);
    }
  });

  const detail =
    `${req.type ? `[${req.type}] ` : ''}${req.action}` +
    `${req.host ? ` @ ${req.host}` : ''}${req.risk ? `  (risk: ${req.risk})` : ''}`;

  return (
    <Box flexDirection="column" borderStyle="round" borderColor="yellow" paddingX={1}>
      <Text color="yellow" bold>
        ⚠ approval required
      </Text>
      <Text>{detail}</Text>
      <Box marginTop={1}>
        <Text inverse={sel === 'approve'} color="green">
          {' approve (a) '}
        </Text>
        <Text> </Text>
        <Text inverse={sel === 'deny'} color="red">
          {' deny (d) '}
        </Text>
      </Box>
      <Text dimColor>←/→ toggle · enter confirm · esc/d deny</Text>
    </Box>
  );
}
